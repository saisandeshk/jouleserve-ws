"""Trace replayer: recorded agent sessions as live load on a real engine (OPTIONS_PLAN.md S3, D14).

    python -m jsw.workloads.replay --sessions sets/x.jsonl --gateway http://127.0.0.1:31000 \
        --server http://127.0.0.1:30001 --gpu 1 --n 4 --horizon 3600 --warm 600 --name ret-e1-...

A session file has one JSON object per line: {"id", "source", "ok", "steps": [{"prompt", "out", "wait_s", "tool",
"burst"}]}, built by `to_sessions()` below from analysis/p1_repo.py runs or analysis/sessions.py sessions.
Each call goes to SGLang's native /generate through the gateway with synthetic token IDs:
- the prompt has exactly the recorded length. By default a call's prompt is the previous prompt plus fresh IDs
  (the visible answer and the tool result): P1's thinking agents drop the reasoning from the history, so only
  the previous prompt is reusable, as P1's own cache counts show (cached = previous prompt in 81-100% of calls).
  With --keep-output the token IDs the engine generated last time are kept too (agents that keep all output).
  A prompt shorter than that (a rebuilt prompt) keeps the session's first prompt as far as it fits;
- the output has exactly the recorded length (ignore_eos, max_new_tokens);
- the recorded tool wait follows each call (scaled by --speed), announced to the gateway as tool_start/tool_end;
- a step with "burst": {"n", "prompt", "out"} sends n concurrent tool-tagged requests during its wait instead of
  sleeping (the vision tool's requests to the agent's own server); the wait lasts until the burst is served.
N closed-loop agent slots draw sessions from the shuffled pool (seeded) until --horizon; a session that would
exceed --ctx ends as "overflow". Calls are logged by the gateway; sessions, GPU energy and server metrics by the
runner (jsw/runner/run.py). Text is synthetic, so loops and tool parsing are outside the replayer's scope.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import time
from pathlib import Path

import aiohttp

VOCAB = (1000, 30000)   # synthetic token IDs: ordinary vocabulary range for every model we serve


def _rand(rng, n):
    return [rng.randrange(*VOCAB) for _ in range(max(0, int(n)))]


class Agent:
    def __init__(self, slot, run, gw, args, rng):
        self.slot, self.run, self.gw, self.a, self.rng = slot, run, gw.rstrip("/"), args, rng
        self.http = None

    async def post(self, path, body):
        async with self.http.post(self.gw + path, json=body) as r:
            txt = await r.read()
            if r.status != 200:
                raise RuntimeError(f"{r.status}: {txt[:300]!r}")
            j = json.loads(txt)
            return j[0] if isinstance(j, list) else j

    async def event(self, sid, kind, **kw):
        try:
            async with self.http.post(f"{self.gw}/s/{sid}/event", json={"kind": kind, **kw}) as r:
                await r.read()
        except Exception:
            pass

    async def burst(self, sid, b):
        async def one(i):
            body = {"input_ids": _rand(self.rng, b["prompt"]), "sampling_params": {
                "max_new_tokens": int(b["out"]), "ignore_eos": True, "temperature": 0}}
            return await self.post(f"/s/{sid}/tool/generate", body)
        res = await asyncio.gather(*(one(i) for i in range(int(b["n"]))), return_exceptions=True)
        return sum(not isinstance(x, Exception) for x in res)

    async def session(self, sess, k):
        try:
            return await self._session(sess, k)
        except asyncio.CancelledError:
            self.run.event("session_end", sid=f"{self.a.name}-s{self.slot}-{k}", session=sess["id"], slot=self.slot,
                           status="cut", recorded_ok=sess.get("ok"))
            raise

    async def _session(self, sess, k):
        sid = f"{self.a.name}-s{self.slot}-{k}"
        t0 = time.monotonic()
        self.run.event("session_start", sid=sid, session=sess["id"], slot=self.slot, steps=len(sess["steps"]))
        first, prev, prev_out = None, None, []
        status, done_steps, served_tok = "completed", 0, 0
        for i, st in enumerate(sess["steps"]):
            P, O = int(st["prompt"]), int(st["out"])
            if P + O > self.a.ctx:
                status = "overflow"
                break
            if prev is None or self.a.no_reuse:
                ids = _rand(self.rng, P)         # --no-reuse: every prompt fresh, nothing can be cached
                first = first or ids
            else:
                grown = prev + prev_out if self.a.keep_output else prev
                ids = grown + _rand(self.rng, P - len(grown)) if P >= len(grown) else \
                    first[:min(P, len(first))] + _rand(self.rng, P - min(P, len(first)))
            body = {"input_ids": ids, "sampling_params": {"max_new_tokens": O, "ignore_eos": True, "temperature": 0}}
            try:
                g = await self.post(f"/s/{sid}/generate", body)
            except Exception as e:
                status = "error"
                self.run.event("call_error", sid=sid, step=i, error=repr(e)[:300])
                break
            prev, prev_out = ids, list(g.get("output_ids") or [])[:O]
            done_steps += 1
            served_tok += P + O
            if i == len(sess["steps"]) - 1:
                break
            tool, b, wait = st.get("tool"), st.get("burst"), float(st.get("wait_s") or 0) / self.a.speed
            await self.event(sid, "tool_start", tool=tool, wait_s=wait, burst=b)
            tw = time.monotonic()
            if b and self.a.bursts:
                ok = await self.burst(sid, b)
                self.run.event("burst", sid=sid, step=i, n=b["n"], ok=ok, s=time.monotonic() - tw)
            elif wait > 0:
                await asyncio.sleep(wait)
            await self.event(sid, "tool_end", tool=tool)
        await self.event(sid, "session_end", status=status)
        self.run.event("session_end", sid=sid, session=sess["id"], slot=self.slot, status=status, steps=done_steps,
                       t_start=t0, s=time.monotonic() - t0, tokens=served_tok, recorded_ok=sess.get("ok"))
        return status

    async def loop(self, pool, t_end):
        self.http = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=0),
                                          timeout=aiohttp.ClientTimeout(total=None, sock_read=3600))
        k = 0
        order = list(range(len(pool)))
        try:
            while time.monotonic() < t_end:
                if k % len(order) == 0:
                    self.rng.shuffle(order)
                await self.session(pool[order[k % len(order)]], k)
                k += 1
        finally:
            await self.http.close()


async def drive(args, run):
    pool = [json.loads(x) for x in open(args.sessions) if x.strip()]
    if args.limit:
        pool = pool[:args.limit]
    t_start = time.monotonic()
    t_end = t_start + args.horizon
    run.note(n=args.n, horizon_s=args.horizon, warm_s=args.warm, pool=len(pool), sessions_file=str(args.sessions),
             t_replay_start=t_start, ctx=args.ctx, speed=args.speed)
    agents = []
    for slot in range(args.n):
        agents.append(Agent(slot, run, args.gateway, args, random.Random(args.seed * 1000 + slot)))
    tasks = []
    for slot, ag in enumerate(agents):
        await asyncio.sleep(args.stagger)
        tasks.append(asyncio.create_task(ag.loop(pool, t_end)))
    done, pending = await asyncio.wait(tasks, timeout=max(0.0, t_end + args.grace - time.monotonic()))
    for t in pending:                                   # sessions still running at horizon + grace are cut
        t.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    run.note(t_replay_end=time.monotonic(), cut_slots=len(pending))


def to_sessions(runs, source, cap_tool_wait=None, burst_tools=("ask_vlm",), burst=None):
    """Session dicts from analysis/p1_repo.py runs (calls with t0/t1/prompt/out; tools with t0/t1/tool).
    The wait after a call is the gap to the next call; its tool is the last tool that ran in the gap."""
    out = []
    for r in runs:
        calls = sorted(r["calls"], key=lambda c: c["t0"])
        steps = []
        for i, c in enumerate(calls):
            nxt = calls[i + 1]["t0"] if i + 1 < len(calls) else None
            tools = [t for t in r.get("tools") or [] if nxt is not None and c["t1"] <= t["t0"] < nxt]
            wait = max(0.0, nxt - c["t1"]) if nxt is not None else 0.0
            if cap_tool_wait:
                wait = min(wait, cap_tool_wait)
            tool = tools[-1]["tool"] if tools else None
            st = {"prompt": int(c["prompt"]), "out": int(c["out"]), "wait_s": round(wait, 3), "tool": tool}
            if burst and tool in burst_tools:
                st["burst"] = burst(r, c, tools)
            steps.append(st)
        if steps:
            out.append({"id": f"{source}/{r.get('task')}/{r.get('instance')}/{r.get('rep')}", "source": source,
                        "ok": r.get("ok"), "status": r.get("status"), "steps": steps})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", required=True)
    ap.add_argument("--gateway", default="http://127.0.0.1:31000")
    ap.add_argument("--server", default=None, help="SGLang URL, for the manifest and /metrics sampling")
    ap.add_argument("--gpu", type=int, default=None)
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--horizon", type=float, default=3600)
    ap.add_argument("--warm", type=float, default=0)
    ap.add_argument("--stagger", type=float, default=2.0)
    ap.add_argument("--speed", type=float, default=1.0, help="divide recorded tool waits by this")
    ap.add_argument("--ctx", type=int, default=65536)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--bursts", action="store_true", help="replay vision-tool bursts as concurrent requests")
    ap.add_argument("--keep-output", action="store_true", help="keep generated IDs in the next prompt")
    ap.add_argument("--no-reuse", action="store_true", help="fresh IDs for every prompt (drop state at every wait)")
    ap.add_argument("--grace", type=float, default=300, help="seconds after --horizon before running sessions are cut")
    ap.add_argument("--name", required=True)
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    from jsw.runner.run import Run
    with Run(a.name, args=vars(a), gpu=a.gpu, server=a.server) as run:
        asyncio.run(drive(a, run))


if __name__ == "__main__":
    main()

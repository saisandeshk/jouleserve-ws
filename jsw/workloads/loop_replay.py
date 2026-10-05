"""A-E1/A-E2 runner: replay P1's recorded drone requests under different decoding settings (OPTIONS_PLAN.md §2.4).

    python -m jsw.workloads.loop_replay --prompts data/a_e1/prompts.jsonl --select pilot --arms greedy,sampled:0 \
        --gateway http://127.0.0.1:31000 --server http://127.0.0.1:30000 --gpu 0 --name a-e1-pilot

Each row of the prompt set (analysis/loop_prompts.py) is P1's exact request: messages, tools, tool_choice,
max_tokens (32,768 for generator and reflector calls), thinking on. Arms:
- greedy: P1's protocol (temperature 0, top_p 1, top_k 1, seed 42);
- sampled:<seed>: Gemma-4's own default (generation_config: temperature 1.0, top_p 0.95, top_k 64).
Run the gateway with the decode guard in "truncate" mode, so a call stops where the loop detector fires (we only
need to know that it loops). Arms run one after the other, so the GPU energy of each arm is a clean window in the
run's NVML samples; within an arm, --concurrency requests run at once. Every output is saved (texts/*.json.gz)
for the validity checks (parses as Python, calls only P1's drone API) and for A-E2.
"""
from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import random
import time
from collections import defaultdict
from pathlib import Path

import aiohttp

ARMS = {
    "greedy": {"temperature": 0.0, "top_p": 1.0, "top_k": 1, "seed": 42},
    "sampled": {"temperature": 1.0, "top_p": 0.95, "top_k": 64},
}


def select(rows, how, seed=0, srcs=("thor_rfx", "thor_tc")):
    """pilot: 30 loops + 20 controls from each of the two Thor sweeps, spread over tasks; full: every loop and
    control of those sweeps; o32: the Orin 32 E4B rows (loops and 40 controls)."""
    rng = random.Random(seed)
    if how == "full":
        return [r for r in rows if r["src"] in srcs and r["kind"] in ("loop", "control")]
    if how == "rfx":                                     # Thor Reflexion only (no tools): pilot sizes
        return select(rows, "pilot", seed, srcs=("thor_rfx",))
    if how == "o32":
        loops = [r for r in rows if r["src"] == "o32_e4b" and r["kind"] == "loop"]
        ctrl = [r for r in rows if r["src"] == "o32_e4b" and r["kind"] == "control"]
        return loops + rng.sample(ctrl, min(40, len(ctrl)))
    out = []
    for src in srcs:
        for kind, n in (("loop", 30), ("control", 20)):
            pool = [r for r in rows if r["src"] == src and r["kind"] == kind]
            by_task = defaultdict(list)
            for r in pool:
                by_task[r["task"]].append(r)
            for v in by_task.values():
                rng.shuffle(v)
            picked, tasks = [], sorted(by_task)
            while len(picked) < min(n, len(pool)):          # round-robin over tasks
                for t in tasks:
                    if by_task[t] and len(picked) < n:
                        picked.append(by_task[t].pop())
            out += picked
    return out


def body_for(row, arm, model, max_tokens=None):
    req = row["request"]
    name, _, seed = arm.partition(":")
    samp = dict(ARMS[name])
    if seed:
        samp["seed"] = int(seed)
    extra = req.get("extra_body") or {}
    b = {"model": model, "messages": req["messages"], "max_tokens": max_tokens or req.get("max_tokens") or 32768,
         "chat_template_kwargs": extra.get("chat_template_kwargs") or {"enable_thinking": True}, **samp}
    if req.get("tools"):
        b["tools"] = req["tools"]
        if req.get("tool_choice"):
            b["tool_choice"] = req["tool_choice"]
    return b


async def one(http, gw, row, arm, model, run, out_dir, sem, max_tokens):
    async with sem:
        sid = f"{arm.replace(':', '')}-{abs(hash(row['id'])) % 10**8}"
        t0 = time.monotonic()
        err, j = None, {}
        try:
            async with http.post(f"{gw}/s/{sid}/v1/chat/completions",
                                 json=body_for(row, arm, model, max_tokens)) as r:
                j = await r.json(content_type=None)
                if r.status != 200:
                    err = str(j)[:500]
        except Exception as e:
            err = repr(e)
        t1 = time.monotonic()
        ch = (j.get("choices") or [{}])[0]
        msg = ch.get("message") or {}
        g = j.get("gateway") or {}
        usage = j.get("usage") or {}
        text = (msg.get("reasoning_content") or "") + (msg.get("content") or "") + "".join(
            (tc.get("function") or {}).get("arguments") or "" for tc in msg.get("tool_calls") or [])
        rec = dict(id=row["id"], src=row["src"], kind=row["kind"], task=row["task"], role=row["role"], arm=arm,
                   sid=sid, t0=t0, t1=t1, s=round(t1 - t0, 2), error=err, finish_reason=ch.get("finish_reason"),
                   stopped_by=g.get("stopped_by"), completion_tokens=usage.get("completion_tokens"),
                   est_tokens=usage.get("estimated_completion_tokens"), prompt_tokens=usage.get("prompt_tokens"),
                   chars=len(text), reasoning_chars=len(msg.get("reasoning_content") or ""),
                   has_tool_call=bool(msg.get("tool_calls")), recorded=row["recorded"])
        run.call(**rec)
        p = out_dir / f"{arm.replace(':', '_')}__{row['id'].replace('/', '__')}.json.gz"
        with gzip.open(p, "wt") as f:
            json.dump({"rec": rec, "message": msg}, f)
        return rec


async def drive(a, run):
    rows = [json.loads(x) for x in open(a.prompts)]
    picked = select(rows, a.select, a.seed)
    if a.from_run:                                 # A-E2: only the prompts that looped in an earlier run's arm
        looped = {json.loads(x)["id"] for x in open(Path(a.from_run) / "calls.jsonl")
                  if json.loads(x).get("stopped_by") == "loop" and json.loads(x).get("arm") == a.from_arm}
        picked = [r for r in rows if r["id"] in looped]
    if a.limit:
        picked = picked[:a.limit]
    rng = random.Random(a.seed)
    rng.shuffle(picked)                                     # mix loops and controls inside each batch
    out_dir = run.dir / "texts"
    out_dir.mkdir(exist_ok=True)
    run.note(selected=len(picked), select=a.select, arms=a.arms,
             counts={k: sum(r["src"] + "/" + r["kind"] == k for r in picked)
                     for k in sorted({r["src"] + "/" + r["kind"] for r in picked})})
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None, sock_read=7200)) as http:
        for arm in a.arms.split(","):
            done = {json.loads(x)["id"] for x in open(run.dir / "calls.jsonl")
                    if json.loads(x).get("arm") == arm} if (run.dir / "calls.jsonl").exists() else set()
            todo = [r for r in picked if r["id"] not in done]
            run.event("arm_start", arm=arm, n=len(todo), skipped=len(done))
            sem = asyncio.Semaphore(a.concurrency)
            res = await asyncio.gather(*(one(http, a.gateway, r, arm, a.model, run, out_dir, sem, a.max_tokens)
                                         for r in todo))
            run.event("arm_end", arm=arm, n=len(res), errors=sum(bool(x["error"]) for x in res),
                      loops=sum(x["stopped_by"] == "loop" for x in res))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", default="data/a_e1/prompts.jsonl")
    ap.add_argument("--select", default="pilot", choices=("pilot", "full", "o32", "rfx"))
    ap.add_argument("--arms", default="greedy,sampled:0")
    ap.add_argument("--gateway", default="http://127.0.0.1:31000")
    ap.add_argument("--server", default="http://127.0.0.1:30000")
    ap.add_argument("--model", default="gemma-4-26B-A4B-it-fp8")
    ap.add_argument("--gpu", default="0", help="GPU index or list, e.g. 0,1 when the model runs with TP=2")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--max-tokens", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--from-run", default="", help="replay only the prompts that looped in this run's --from-arm")
    ap.add_argument("--from-arm", default="greedy")
    ap.add_argument("--name", required=True)
    a = ap.parse_args()
    from jsw.runner.run import Run
    with Run(a.name, args=vars(a), gpu=a.gpu, server=a.server) as run:
        asyncio.run(drive(a, run))


if __name__ == "__main__":
    main()

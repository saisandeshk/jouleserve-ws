"""Run aerogen_mcp (a native tool-calling drone agent by mayankarya) against an
OpenAI-compatible SGLang server, and log every LLM call and every tool call.

The agent code comes from a private copy (not vendored in this repo: ask the author
first) and runs unmodified. This driver monkeypatches three things around it:
  1. the agent's OpenAI client: sampling parameters, reasoning effort, streaming (for
     TTFT), and one JSONL record per LLM call;
  2. `AeroStack2MCP.call`: one JSONL record per tool call;
  3. the random system-prompt prefix the agent adds to defeat cloud prompt caching
     (removed, so the prefix is stable as it would be on a real deployment).
Real-time flight pacing is a small hook in the private copy's sim server: `_advance(dt)`
sleeps `dt / AEROGEN_PACE_SPEEDUP` seconds (0 = original instant behaviour).

Parent mode schedules missions over N concurrent session slots (closed loop), runs the
NVML and /metrics samplers, and writes a manifest. `--child` runs one mission.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import types
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# K2 Horizon's template requires a thinking field on every assistant message. SGLang
# 0.5.20 only forwards `reasoning_content` (it drops `think_fast`/`think_faster`), which the
# template re-renders under the high-effort tag; for low/medium effort the re-rendered
# history therefore differs from the generated tokens at the think tag of each turn.
THINK_KEY = {"high": "reasoning_content", "medium": "reasoning_content", "low": "reasoning_content"}


# ---------------------------------------------------------------- child: one mission
class LoggingClient:
    """Drop-in for `openai.OpenAI` as used by the agent (`client.chat.completions.create`)."""

    def __init__(self, a, log):
        from openai import OpenAI
        self._c = OpenAI(base_url=a.base_url, api_key="EMPTY", timeout=7200, max_retries=0)
        self.a, self.log, self.idx = a, log, 0
        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(create=self._create))

    def _create(self, model=None, messages=None, tools=None, tool_choice=None, **_):
        from openai.types.chat import ChatCompletion
        a = self.a
        self.idx += 1
        req = dict(model=a.model, messages=messages, tools=tools, tool_choice=tool_choice,
                   temperature=a.temperature, top_p=a.top_p, seed=a.seed,
                   max_tokens=a.max_tokens, stream=True,
                   stream_options={"include_usage": True},
                   extra_body={"chat_template_kwargs": {"reasoning_effort": a.effort}})
        rec = {"session": a.session, "call_index": self.idx, "n_messages": len(messages),
               "effort": a.effort, "t_req": time.monotonic(), "t_req_wall": time.time()}
        t_first, reasoning, content, tcs, finish, usage = None, [], [], {}, None, None
        try:
            for ch in self._c.chat.completions.create(**req):
                if ch.usage:
                    usage = ch.usage
                for choice in ch.choices:
                    d = choice.delta
                    rc = getattr(d, "reasoning_content", None)
                    if t_first is None and (rc or d.content or d.tool_calls):
                        t_first = time.monotonic()
                    if rc:
                        reasoning.append(rc)
                    if d.content:
                        content.append(d.content)
                    for tc in d.tool_calls or []:
                        e = tcs.setdefault(tc.index, {"id": None, "name": "", "args": ""})
                        if tc.id:
                            e["id"] = tc.id
                        if tc.function is not None:
                            if tc.function.name and not e["name"]:
                                e["name"] = tc.function.name
                            if tc.function.arguments:
                                e["args"] += tc.function.arguments
                    if choice.finish_reason:
                        finish = choice.finish_reason
        except Exception as e:
            rec.update(t_end=time.monotonic(), error=repr(e)[:2000])
            self._write(rec)
            raise
        t_end = time.monotonic()
        msg = {"role": "assistant", "content": "".join(content) or None,
               THINK_KEY[a.effort]: "".join(reasoning)}
        if tcs:
            msg["tool_calls"] = [
                {"id": e["id"] or f"call_{self.idx}_{i}", "type": "function",
                 "function": {"name": e["name"], "arguments": e["args"] or "{}"}}
                for i, e in sorted(tcs.items())]
        u = usage.model_dump() if usage is not None else {}
        details = u.get("prompt_tokens_details") or {}
        rec.update(
            t_first=t_first, t_end=t_end,
            ttft_s=(t_first - rec["t_req"]) if t_first else None,
            decode_s=(t_end - t_first) if t_first else None,
            prompt_tokens=u.get("prompt_tokens"), completion_tokens=u.get("completion_tokens"),
            cached_tokens=details.get("cached_tokens"),
            reasoning_chars=len(msg[THINK_KEY[a.effort]]),
            content_chars=len(msg["content"] or ""),
            tool_names=[t["function"]["name"] for t in msg.get("tool_calls", [])],
            finish_reason=finish)
        self._write(rec)
        return ChatCompletion.model_validate({
            "id": f"{a.session}-{self.idx}", "object": "chat.completion",
            "created": int(time.time()), "model": a.model,
            "choices": [{"index": 0, "finish_reason": finish or "stop", "message": msg}],
            "usage": u or None})

    def _write(self, rec):
        self.log.write(json.dumps(rec) + "\n")
        self.log.flush()


def child_main(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, a.aerogen_root)
    from aerogen_mcp import config
    config.RANDOM_PREFIX_TO_AVOID_CACHED_TOKENS = [""]
    from aerogen_mcp import aerogen_mcp_agent as agent
    from aerogen_mcp import mcp_session, validators

    llm_log = open(out / "llm_calls.jsonl", "a")
    tool_log = open(out / "tool_calls.jsonl", "a")
    agent.client = LoggingClient(a, llm_log)

    orig_call = mcp_session.AeroStack2MCP.call
    seq = {"n": 0}

    async def logged_call(self, name, arguments):
        seq["n"] += 1
        t0 = time.monotonic()
        res = await orig_call(self, name, arguments)
        t1 = time.monotonic()
        status = res.get("status") if isinstance(res, dict) else None
        tool_log.write(json.dumps({
            "session": a.session, "seq": seq["n"], "tool": name, "t_start": t0, "t_end": t1,
            "dur_s": t1 - t0, "args_chars": len(json.dumps(arguments)),
            "result_chars": len(json.dumps(res)), "status": status}) + "\n")
        tool_log.flush()
        return res

    mcp_session.AeroStack2MCP.call = logged_call

    task = a.task_text
    summary = {"session": a.session, "task_index": a.task_index, "task": task,
               "seed": a.seed, "effort": a.effort, "t_start": time.monotonic()}
    try:
        mission, usage = asyncio.run(agent.run_mission_async(
            task, "", 0, backend="sim", scenario=a.scenario, verbose=False))
        val, _ = validators.mission_validator(task, mission)
        summary.update(status="done", stop_reason=mission["stop_reason"],
                       tool_calls=mission["tool_calls"], flight_time_s=mission["flight_time_s"],
                       validator=val, usage=usage.as_dict())
        (out / "mission.json").write_text(json.dumps(mission, indent=1, default=str))
    except Exception as e:
        summary.update(status="error", error=repr(e)[:4000])
    summary["t_end"] = time.monotonic()
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return 0 if summary["status"] == "done" else 1


# ---------------------------------------------------------------- parent: a run
def _get(url, timeout=5):
    try:
        return json.loads(urllib.request.urlopen(url, timeout=timeout).read().decode())
    except Exception as e:
        return {"error": repr(e)}


def _post(url, timeout=30):
    try:
        req = urllib.request.Request(url, data=b"", method="POST")
        return urllib.request.urlopen(req, timeout=timeout).read().decode()[:200]
    except Exception as e:
        return repr(e)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def parent_main(a):
    from jsw.telemetry.samplers import NvmlSampler, SglangMetricsSampler

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    root = Path(a.aerogen_root)
    tasks = [t.strip() for t in
             (root / "aerogen_mcp/task_sets/aerogen_aeroeval_radio_tower.txt").read_text().splitlines()
             if t.strip()]
    task_ids = range(len(tasks)) if a.tasks == "all" else [int(x) for x in a.tasks.split(",")]
    # Interleave by run so concurrent slots fly different tasks.
    missions = [(t, r) for r in range(a.runs) for t in task_ids]
    base = a.base_url.rsplit("/v1", 1)[0]

    manifest = {
        "args": vars(a), "host": socket.gethostname(), "t_start_wall": time.time(),
        "t_start_mono": time.monotonic(), "tasks": tasks,
        "server_info": _get(base + "/get_server_info"), "models": _get(base + "/v1/models"),
        "aerogen_snapshot": subprocess.run(["git", "-C", str(root), "log", "--oneline", "-1"],
                                           capture_output=True, text=True).stdout.strip(),
        "aerogen_diff": subprocess.run(["git", "-C", str(root), "diff", "--stat"],
                                       capture_output=True, text=True).stdout.strip(),
        "driver_sha": _sha(__file__),
        "nvidia_smi": subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,driver_version,memory.used,temperature.gpu,"
             "power.draw,clocks.sm", "--format=csv,noheader"],
            capture_output=True, text=True).stdout.strip(),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))

    samplers = [NvmlSampler(str(out / "nvml.jsonl"), a.gpu),
                SglangMetricsSampler(str(out / "sglang_metrics.jsonl"), base)]
    for s in samplers:
        s.start()
    if a.flush_start:
        print("flush_cache:", _post(base + "/flush_cache"), flush=True)
    time.sleep(2)

    env = dict(os.environ, OPENAI_API_KEY="EMPTY", OPENAI_BASE_URL=a.base_url,
               AEROGEN_MODEL=a.model, AEROGEN_MCP_PYTHON=sys.executable,
               AEROGEN_PACE_SPEEDUP=str(a.pace_speedup),
               PYTHONPATH=f"{REPO}:{a.aerogen_root}:" + os.environ.get("PYTHONPATH", ""))
    pending = list(missions)
    running = {}  # Popen -> (session, t_launch)
    last_launch = -1e9
    events = open(out / "events.jsonl", "a")

    def ev(**kw):
        kw["t_mono"] = time.monotonic()
        events.write(json.dumps(kw) + "\n")
        events.flush()
        print(json.dumps(kw), flush=True)

    k = 0
    while pending or running:
        while (pending and len(running) < a.concurrency
               and time.monotonic() - last_launch >= a.stagger_s):
            t, r = pending.pop(0)
            k += 1
            session = f"s{k:03d}_t{t}_r{r}"
            if a.flush_each and a.concurrency == 1:
                _post(base + "/flush_cache")
                time.sleep(1)
            sdir = out / "sessions" / session
            sdir.mkdir(parents=True, exist_ok=True)
            cmd = [sys.executable, "-m", "jsw.workloads.aerogen_driver", "--child",
                   "--aerogen-root", a.aerogen_root, "--base-url", a.base_url,
                   "--model", a.model, "--effort", a.effort, "--temperature", str(a.temperature),
                   "--top-p", str(a.top_p), "--seed", str(a.seed + r), "--max-tokens",
                   str(a.max_tokens), "--scenario", a.scenario, "--out", str(sdir),
                   "--session", session, "--task-index", str(t), "--task-text", tasks[t]]
            p = subprocess.Popen(cmd, env=env, cwd=str(REPO),
                                 stdout=open(sdir / "stdout.log", "w"), stderr=subprocess.STDOUT)
            running[p] = (session, time.monotonic())
            last_launch = time.monotonic()
            ev(event="launch", session=session, task=t, run=r, pid=p.pid,
               running=len(running), pending=len(pending))
        for p in list(running):
            session, t0 = running[p]
            rc = p.poll()
            if rc is None and time.monotonic() - t0 > a.mission_timeout_s:
                p.kill()
                rc = "timeout"
            if rc is not None:
                del running[p]
                ev(event="exit", session=session, rc=rc, wall_s=round(time.monotonic() - t0, 1))
        time.sleep(0.5)

    time.sleep(3)
    for s in samplers:
        s.stop()
    manifest.update(t_end_wall=time.time(), t_end_mono=time.monotonic())
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    print("done:", out, flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--child", action="store_true")
    ap.add_argument("--aerogen-root", default=os.path.expanduser("~/work/aeroeval"))
    ap.add_argument("--base-url", default="http://127.0.0.1:30000/v1")
    ap.add_argument("--model", default="IFM/K2-Horizon-7B")
    ap.add_argument("--effort", default="low", choices=list(THINK_KEY))
    ap.add_argument("--temperature", type=float, default=1.0)   # K2 Horizon model-card setting
    ap.add_argument("--top-p", type=float, default=0.95)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-tokens", type=int, default=16384)
    ap.add_argument("--scenario", default=os.path.expanduser(
        "~/work/aeroeval/aerogen_mcp/scenario_radio_tower.json"))
    ap.add_argument("--out", required=True)
    # parent
    ap.add_argument("--tasks", default="all")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--stagger-s", type=float, default=0.0)
    ap.add_argument("--pace-speedup", type=float, default=1.0)
    ap.add_argument("--gpu", type=int, default=1, help="NVML index of the server's GPU")
    ap.add_argument("--flush-start", action="store_true")
    ap.add_argument("--flush-each", action="store_true", help="flush before each mission (N=1 only)")
    ap.add_argument("--mission-timeout-s", type=float, default=5400)
    # child
    ap.add_argument("--session", default="s000")
    ap.add_argument("--task-index", type=int, default=0)
    ap.add_argument("--task-text", default="")
    a = ap.parse_args()
    sys.exit(child_main(a) if a.child else parent_main(a))


if __name__ == "__main__":
    main()

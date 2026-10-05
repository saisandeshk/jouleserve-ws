"""Replay sets for the trace replayer (jsw/workloads/replay.py): P1's traffic runs as session files.

    python -m analysis.replay_sets            # writes data/replay/<config>.jsonl and data/replay/summary.json

For each traffic configuration used on the WS (RET-E1: the granite cells, served by granite-4.2-8b; D-E2: the
Orin 32 gemma-E4B cell, served by gemma-4-E4B) every recorded run becomes one session: per call its prompt and
output tokens, the gap to the next call (tool time) and the tool. For D-E2 the vision-tool gaps also carry a
burst: the number of concurrent requests and their size, read from the run's vitals stream (1 s KV samples)
during the tool's window (median running requests; peak KV in use split evenly over them; a short output).
"""
from __future__ import annotations

import gzip
import json
import os
import statistics as st
from pathlib import Path

from analysis import p1_repo
from jsw.workloads.replay import to_sessions

OUT = p1_repo.REPO / "data/replay"
CONFIGS = ("t_o32_granite", "t_o64_granite", "t_thor_granite", "t_o32_e4b")


def _vitals(d, cache={}):
    """(t, running requests, KV tokens in use) samples of one run directory's vitals stream."""
    if d not in cache:
        rows = []
        with gzip.open(os.path.join(d, "vitals.jsonl.gz"), "rt") as f:
            for line in f:
                if '"kv_num_running_reqs"' in line:
                    v = json.loads(line)
                    if v.get("t_monotonic") is not None and v.get("kv_num_running_reqs") is not None:
                        rows.append((v["t_monotonic"], v["kv_num_running_reqs"], v.get("kv_used_tokens") or 0))
        cache[d] = rows
    return cache[d]


def burst_fn(cfg_key):
    """(run, call, tools) -> {"n", "prompt", "out"} for a vision-tool gap, from the vitals during its window:
    n = median running requests; prompt = peak KV in use / peak running requests; out = 64 tokens (short
    answers). Falls back to the Orin 32 E4B medians (23 requests) when the window has no samples."""
    def f(run, call, tools):
        t = [x for x in tools if x["tool"] == "ask_vlm"]
        if not t or not run.get("vitals_dir"):
            return {"n": 23, "prompt": 1500, "out": 64, "source": "default"}
        a, b = t[-1]["t0"], t[-1]["t1"]
        inside = [(q, kv) for (ts, q, kv) in _vitals(run["vitals_dir"]) if a <= ts <= b and q > 0]
        if not inside:
            return {"n": 23, "prompt": 1500, "out": 64, "source": "default"}
        qmax = max(q for q, _ in inside)
        return {"n": int(st.median(q for q, _ in inside)), "prompt": int(max(kv for _, kv in inside) / qmax),
                "out": 64, "source": "vitals"}
    return f


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {}
    for key in CONFIGS:
        runs = p1_repo.load(key)
        runs = [r for r in runs if r["calls"]]
        sess = to_sessions(runs, key, burst=burst_fn(key) if key == "t_o32_e4b" else None)
        with open(OUT / f"{key}.jsonl", "w") as f:
            for s in sess:
                f.write(json.dumps(s) + "\n")
        steps = [st_ for s in sess for st_ in s["steps"]]
        summary[key] = dict(
            sessions=len(sess), completed=sum(s["status"] == "completed" for s in sess),
            calls=len(steps), prompt_median=st.median(x["prompt"] for x in steps),
            out_median=st.median(x["out"] for x in steps),
            peak_context_max=max(x["prompt"] + x["out"] for x in steps),
            wait_median_s=st.median(x["wait_s"] for x in steps if x["wait_s"] > 0),
            bursts=sum(bool(x.get("burst")) for x in steps))
        print(key, summary[key])
    json.dump(summary, open(OUT / "summary.json", "w"), indent=1)


if __name__ == "__main__":
    main()

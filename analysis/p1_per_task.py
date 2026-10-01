"""Per-task retention metrics for P1's drone runs on the Thor (Reflexion and tool calling).

Usage: python3 -m analysis.p1_per_task   (writes reports/2026-10-01-p1-task-overview/per_task.json)
"""
from __future__ import annotations

import collections
import json
import statistics as st
from pathlib import Path

from analysis.sessions import REPO, load_p1, session_metrics, thor_prefill_rate

TASKS = ["B5", "B13", "B29", "B37", "A3", "A5", "A6", "A7", "A8", "A9", "A16", "A20",
         "D1_ORDERED", "D2_CHECKPOINT", "D3_OUTBACK", "F1_FARM_SURVEY"]
SOURCES = {"reflexion": REPO / "data/p1_thor_drone", "toolcalling": REPO / "data/p1_thor_toolcalling"}
OUT = REPO / "reports/2026-10-01-p1-task-overview/per_task.json"


def task_row(ss, rate):
    ms = [session_metrics(s, rate) for s in ss]
    total = sum(m["total_s"] for m in ms)
    llm = sum(m["llm_s"] for m in ms)
    # Real waits only: bookkeeping tools return in milliseconds.
    waits = [w["t1"] - w["t0"] for s in ss for w in s.waits if w["t1"] - w["t0"] > 0.5]
    return dict(
        runs=len(ss), passed=sum(bool(s.success) for s in ss),
        min_per_run=total / len(ss) / 60,
        llm_calls_per_run=st.mean(m["n_calls"] for m in ms),
        tool_waits_per_run=len(waits) / len(ss),
        wait_s_p50=st.median(waits) if waits else None,
        llm_share_of_time=llm / total,
        bound_prefill_share_of_llm=sum(m["prefill_s"] for m in ms) / llm,
        observed_saving_of_llm=sum(m["ceiling_s"] for m in ms) / llm,
        prompt_reuse=sum(m["cached"] for m in ms) / max(1, sum(m["prompt"] for m in ms)),
        peak_ctx=max(m["peak_ctx"] for m in ms),
        capped_calls=sum(1 for s in ss for c in s.calls if c["completion"] >= 32700),
    )


def main():
    sessions = {label: load_p1(root, label) for label, root in SOURCES.items()}
    rate = thor_prefill_rate(sessions["reflexion"])
    print(f"Thor cold prefill: {rate:.0f} tokens/s")
    out = {}
    for label, ss in sessions.items():
        by = collections.defaultdict(list)
        for s in ss:
            by[s.task].append(s)
        out[label] = {t: task_row(by[t], rate) for t in TASKS if by.get(t)}
        print(f"\n{label}")
        print(f"{'task':15} runs pass  min  calls waits wait_p50  llm%  bound  saved  capped")
        for t, r in out[label].items():
            w = f"{r['wait_s_p50']:.0f}" if r["wait_s_p50"] else "-"
            print(f"{t:15} {r['runs']:4d} {r['passed']:4d} {r['min_per_run']:5.1f} {r['llm_calls_per_run']:5.1f}"
                  f" {r['tool_waits_per_run']:5.1f} {w:>8} {r['llm_share_of_time']:5.0%}"
                  f" {r['bound_prefill_share_of_llm']:6.1%} {r['observed_saving_of_llm']:6.2%} {r['capped_calls']:6d}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

"""P1's two drone agents on the same 12 CLGSCE tasks, and what runaway thinking costs them.

For P1's Reflexion and tool-calling sweeps (Thor, Gemma-4-26B-A4B, measured): runs, passes,
board energy per run and per success, the long advanced tasks, and the calls that hit the
32,768-token output cap. Then an upper bound on what stopping those calls earlier would save:
the decode time each capped call spent past a cut of K tokens, at the board's 71.9 W while a
call runs (the fit in analysis/admission_sim.py), assuming the rest of each run goes as
recorded. Also counts the calls that finished on their own past K, which a fixed cut would stop.

Usage: python3 -m analysis.p1_runaway   (writes reports/2026-10-03-admission-sim/p1_agents.json)
"""
from __future__ import annotations

import collections
import glob
import json
import statistics as st

from analysis.sessions import REPO

TASKS = ["B5", "B13", "B29", "B37", "A3", "A5", "A6", "A7", "A8", "A9", "A16", "A20"]
LONG = {"A6", "A7", "A8", "A9", "A20"}
SOURCES = {"reflexion": REPO / "data/p1_thor_drone", "toolcalling": REPO / "data/p1_thor_toolcalling"}
CAP, P_ACTIVE_W = 32700, 71.9
OUT = REPO / "reports/2026-10-03-admission-sim/p1_agents.json"


def load(root):
    runs = []
    for f in glob.glob(str(root / "*/*/instance_*/run_*/run_meta.json")):
        meta = json.loads(open(f).read())
        if meta["task_id"] not in TASKS:
            continue
        it = [json.loads(l) for l in open(f.replace("run_meta.json", "iterations.jsonl"))]
        calls = [dict(out=float(r.get("completion_tokens") or 0), rate=float(r.get("decode_tokens_per_s") or 28),
                      s=float(r["t_phase_end"]) - float(r["t_phase_start"]), finish=r.get("finish_reason"))
                 for r in it if r.get("kind") == "llm" and r.get("t_phase_start") and r.get("t_phase_end")]
        runs.append((meta, calls))
    return runs


def summarize(runs):
    E = sum(m["workflow_energy_J"] for m, _ in runs)
    T = sum(m["workflow_time_s"] for m, _ in runs)
    ok = sum(m["final_result"] == "pass" for m, _ in runs)
    calls = [c for _, cs in runs for c in cs]
    llm = sum(c["s"] for c in calls)
    capped = [c for c in calls if c["out"] >= CAP]
    long_runs = [m for m, _ in runs if m["task_id"] in LONG]
    fails = [(m, cs) for m, cs in runs if m["final_result"] != "pass"]
    cuts = {}
    for k in (4096, 8192, 16384):
        saved = sum((c["out"] - k) / c["rate"] for c in capped)
        cuts[k] = dict(saved_h=saved / 3600, saved_time_share=saved / T, saved_energy_share=saved * P_ACTIVE_W / E,
                       finished_calls_cut=sum(1 for c in calls if k < c["out"] < CAP))
    return dict(
        runs=len(runs), passed=ok, kj_per_run=E / len(runs) / 1e3, kj_per_success=E / ok / 1e3,
        run_hours=T / 3600, llm_hours=llm / 3600, calls=len(calls), capped_calls=len(capped),
        capped_share_of_llm=sum(c["s"] for c in capped) / llm,
        capped_finish_reasons=dict(collections.Counter(c["finish"] for c in capped)),
        failed=len(fails), failed_with_capped_call=sum(any(c["out"] >= CAP for c in cs) for _, cs in fails),
        failure_classes=dict(collections.Counter(m.get("failure_class") for m, _ in fails)),
        long_tasks=dict(runs=len(long_runs), passed=sum(m["final_result"] == "pass" for m in long_runs),
                        median_min=st.median(m["workflow_time_s"] for m in long_runs) / 60),
        cut=cuts)


def main():
    out = {k: summarize(load(root)) for k, root in SOURCES.items()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    for k, v in out.items():
        c = v["cut"][16384]
        print(f"{k}: {v['runs']} runs, {v['passed']} passed, {v['kj_per_run']:.0f} kJ/run, {v['kj_per_success']:.0f} kJ/success; "
              f"long tasks {v['long_tasks']['passed']}/{v['long_tasks']['runs']} at {v['long_tasks']['median_min']:.0f} min; "
              f"capped {v['capped_calls']}/{v['calls']} = {v['capped_share_of_llm']:.0%} of LLM time, {v['capped_finish_reasons']}; "
              f"failures with a capped call {v['failed_with_capped_call']}/{v['failed']}; cut at 16K saves {c['saved_energy_share']:.0%} "
              f"of board energy, stopping {c['finished_calls_cut']} finished calls")


if __name__ == "__main__":
    main()

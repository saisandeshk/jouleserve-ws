"""CAND-T1/T2: traffic candidates on Thor-2 (reports/2026-10-15-candidates/PLAN.md, rules fixed before the data).

Each arm is one run folder copied from Thor-2 to ~/work/runs/thor2/ (runs.jsonl, traces, vitals, gw/calls.jsonl):
  G   P1's recorded greedy runs of the same tasks (instance A, all repeats), graded by P1's grader;
  S1  one sampled answer (gateway k = 1);  F4  first-of-4 (gateway k = 4).
Per arm: runs, passes (P1's grader, from a copy), board energy (workflow_energy_j), energy per success = total / passes,
capped calls (output >= 99% of the 8,000 budget), time; from the gateway log: agent calls, how often the winner was
not the first candidate, tokens decoded by cancelled candidates.
Verdict (PLAN.md): F4 against S1 in energy per success: >= 30% lower with passes not lower by more than 1 -> "pays";
10-30% "weaker"; < 10% "absent". Differences of 2 passes or fewer are not read.

Usage (WS): python -m analysis.candidates_traffic <model> <s1_dir> <f4_dir>   (model: gemma | granite)
"""
from __future__ import annotations

import glob
import json
import os
import statistics
import sys

from analysis import traffic_validate as tv

CELLS = {"gemma": "traffic/final_sweep_thor/tool_calling/gemma-4-26B-A4B-it",
         "granite": "traffic/final_sweep_thor/tool_calling/granite-4.2-8b"}
OUT = os.path.join(os.path.dirname(__file__), "..", "reports", "2026-10-15-candidates")


def runs_of(run_dir, g, KEY, tasks=None):
    out = []
    traces = {os.path.basename(f)[:-5]: f for f in glob.glob(os.path.join(run_dir, "2026*.json"))}
    for rec in tv.rows(os.path.join(run_dir, "runs.jsonl")):
        if tasks and rec.get("task_id") not in tasks:
            continue
        tr = json.load(open(traces[rec["run_id"]])) if rec["run_id"] in traces else None
        res = g.grade_run(rec, tr, KEY)[0]
        calls = [c for c in (((tr or {}).get("benchmark") or {}).get("llm_calls") or []) if c.get("output_tokens") is not None]
        cap = lambda c: c["output_tokens"] >= 0.99 * min(8000, ((c.get("token_budget") or {}).get("granted_max_tokens") or 8000))
        out.append(dict(task=rec.get("task_id"), passed=res == "pass", failure=rec.get("failure_class"),
                        energy_J=rec.get("workflow_energy_j") or rec.get("workflow_energy_j_reconstructed") or 0.0,
                        time_s=rec.get("workflow_time_s") or 0.0, calls=len(calls), capped=sum(map(cap, calls)),
                        out_tokens=sum(c["output_tokens"] for c in calls)))
    return out


def summary(runs):
    n, p = len(runs), sum(r["passed"] for r in runs)
    E = sum(r["energy_J"] for r in runs)
    return dict(runs=n, passes=p, pass_rate=p / n if n else None, energy_J=E, energy_per_success_J=E / p if p else None,
                capped_calls=sum(r["capped"] for r in runs), calls=sum(r["calls"] for r in runs),
                mean_time_s=statistics.mean(r["time_s"] for r in runs) if runs else None)


def gateway(run_dir):
    p = os.path.join(run_dir, "gw", "calls.jsonl")
    if not os.path.exists(p):
        return None
    calls = [json.loads(l) for l in open(p) if l.strip()]
    by = {}
    for c in calls:
        by.setdefault((c["sid"], c["index"]), []).append(c)
    winners = [next((c for c in cs if (c.get("meta") or {}).get("winner")), None) for cs in by.values()]
    lost_tok = sum((c.get("completion_tokens") or (c.get("chunks") or 0)) for cs in by.values() for c in cs
                   if not (c.get("meta") or {}).get("winner"))
    win_tok = sum((w.get("completion_tokens") or w.get("chunks") or 0) for w in winners if w)
    return dict(agent_calls=len(by), winner_not_first=sum(1 for w in winners if w and w["attempt"] != 0),
                winner_capped=sum(1 for w in winners if w and w.get("finish_reason") == "length"),
                loser_tokens=lost_tok, winner_tokens=win_tok)


def main(model, s1_dir, f4_dir):
    g, KEY = tv.grader()
    s1 = runs_of(s1_dir, g, KEY)
    f4 = runs_of(f4_dir, g, KEY)
    tasks = {r["task"] for r in s1} | {r["task"] for r in f4}
    G = []
    for rd in sorted(glob.glob(os.path.join(tv.P1, CELLS[model], "A_kamath_mon_peak", "run*"))):
        G += runs_of(rd, g, KEY, tasks)
    arms = {"G (P1 greedy, recorded)": summary(G), "S1 (one sampled answer)": summary(s1), "F4 (first-of-4)": summary(f4)}
    gw = {"S1": gateway(s1_dir), "F4": gateway(f4_dir)}
    es1, ef4 = arms["S1 (one sampled answer)"]["energy_per_success_J"], arms["F4 (first-of-4)"]["energy_per_success_J"]
    d_pass = arms["F4 (first-of-4)"]["passes"] - arms["S1 (one sampled answer)"]["passes"]
    change = (ef4 / es1 - 1) if es1 and ef4 else None
    if change is None:
        verdict = "undecided (no passes in an arm)"
    elif change <= -0.30 and d_pass >= -1:
        verdict = "first-of-k pays on traffic"
    elif change <= -0.10 and d_pass >= -1:
        verdict = "weaker"
    else:
        verdict = "absent"
    per_task = {}
    for name, rs in (("G", G), ("S1", s1), ("F4", f4)):
        for r in rs:
            per_task.setdefault(r["task"], {}).setdefault(name, []).append(int(r["passed"]))
    res = dict(model=model, s1_dir=s1_dir, f4_dir=f4_dir, arms=arms, gateway=gw, f4_vs_s1_energy_per_success=change,
               f4_minus_s1_passes=d_pass, verdict=verdict, per_task=per_task)
    for name, a in arms.items():
        es = a["energy_per_success_J"]
        print(f"{name:26s} runs {a['runs']:3d} passes {a['passes']:3d} ({100 * (a['pass_rate'] or 0):4.0f}%)  "
              f"kJ/success {es / 1e3 if es else float('nan'):7.1f}  capped calls {a['capped_calls']:3d}  "
              f"mean time {a['mean_time_s'] or 0:6.0f} s")
    print("gateway:", gw)
    print(f"F4 vs S1 energy per success: {100 * change:+.1f}% , passes {d_pass:+d} -> {verdict}" if change is not None
          else verdict)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"cand_traffic_{model}.json"), "w") as f:
        json.dump(res, f, indent=1, default=str)


if __name__ == "__main__":
    main(*sys.argv[1:4])

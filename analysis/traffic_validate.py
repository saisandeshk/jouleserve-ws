"""TRF-3: check our runs of P1's traffic agent against P1's recorded runs, graded by P1's own grader.

P1's grader (`traffic/grading/grade.py`, version traffic-grader-2026-10-07a) is used from a COPY of the grading folder
(never in P1's clone): `cp -r ~/work/p1/edge-agent-bench/traffic/grading ~/work/p1/grading_copy`.

    python -m analysis.traffic_validate selftest            # regrade P1's Thor gemma runs; must match P1's grades.csv
    python -m analysis.traffic_validate compare <run_dir>   # our run folder (runs.jsonl + traces) against P1's runs

`compare` grades every run in our folder with P1's grader, then sets each task beside P1's recorded runs of the same
task and instance on the same configuration (Thor gemma-26B tool calling by default): pass, LLM calls, generated
tokens, board energy, failure class.
"""
from __future__ import annotations

import csv
import glob
import gzip
import importlib.util
import json
import os
import statistics
import sys
from collections import defaultdict

sys.dont_write_bytecode = True
GRADER_DIR = os.environ.get("P1_GRADER_COPY", os.path.expanduser("~/work/p1/grading_copy"))
P1 = os.path.expanduser("~/work/p1/edge-agent-bench")
CELL = "traffic/final_sweep_thor/tool_calling/gemma-4-26B-A4B-it"


def grader():
    spec = importlib.util.spec_from_file_location("p1_grade", os.path.join(GRADER_DIR, "grade.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, mod.load_key()


def rows(path):
    for p in (path, path + ".gz"):
        if os.path.exists(p):
            op = gzip.open if p.endswith(".gz") else open
            with op(p, "rt") as f:
                return [json.loads(l) for l in f if l.strip()]
    return []


def summarize(rec, trace):
    b = (trace or {}).get("benchmark") or {}
    calls = [c for c in (b.get("llm_calls") or []) if c.get("output_tokens") is not None]
    return dict(calls=len(calls), out=sum(c["output_tokens"] for c in calls),
                energy_J=rec.get("workflow_energy_j") or rec.get("workflow_energy_j_reconstructed"),
                time_s=rec.get("workflow_time_s"), failure=rec.get("failure_class"))


def selftest(cell=CELL):
    g, KEY = grader()
    p1 = {(r["run_dir"], r["run_id"]): r["final_result"] for r in csv.DictReader(open(os.path.join(GRADER_DIR, "grades.csv")))}
    agree = n = 0
    bad = []
    for rd in sorted(glob.glob(os.path.join(P1, cell, "*", "run*"))):
        traces = {os.path.basename(f)[:-5]: f for f in glob.glob(os.path.join(rd, "2026*.json"))}
        rel = os.path.relpath(rd, P1)
        for rec in rows(os.path.join(rd, "runs.jsonl")):
            want = p1.get((rel, rec["run_id"]))
            if want is None:
                continue
            tr = json.load(open(traces[rec["run_id"]])) if rec["run_id"] in traces else None
            got = g.grade_run(rec, tr, KEY)[0]
            n += 1
            agree += got == want
            if got != want:
                bad.append((rel, rec["run_id"], want, got))
    print(f"selftest {cell}: {agree}/{n} grades agree with P1's grades.csv")
    for b in bad[:10]:
        print("  differs:", b)
    return agree, n


def compare(run_dir, cell=CELL):
    g, KEY = grader()
    ours = []
    traces = {os.path.basename(f)[:-5]: f for f in glob.glob(os.path.join(run_dir, "2026*.json"))}
    for rec in rows(os.path.join(run_dir, "runs.jsonl")):
        tr = json.load(open(traces[rec["run_id"]])) if rec["run_id"] in traces else None
        res, rule, det = g.grade_run(rec, tr, KEY)
        ours.append(dict(task=rec.get("task_id"), instance=rec.get("work_instance"), result=res, rule=rule,
                         detail=det, **summarize(rec, tr)))
    theirs = defaultdict(list)
    for rd in sorted(glob.glob(os.path.join(P1, cell, "*", "run*"))):
        trs = {os.path.basename(f)[:-5]: f for f in glob.glob(os.path.join(rd, "2026*.json"))}
        for rec in rows(os.path.join(rd, "runs.jsonl")):
            tr = json.load(open(trs[rec["run_id"]])) if rec["run_id"] in trs else None
            theirs[(rec.get("task_id"), rec.get("work_instance"))].append(
                dict(result=rec.get("final_result"), **summarize(rec, tr)))
    print(f"{'task':22s} {'ours':>5s} {'P1 passes':>10s} | {'calls ours/P1 med':>18s} | {'out tok ours/P1 med':>20s} | "
          f"{'kJ ours/P1 med':>15s}")
    out = []
    for o in ours:
        t = theirs.get((o["task"], o["instance"]), [])
        med = lambda k: statistics.median([x[k] for x in t if x[k] is not None]) if any(x[k] is not None for x in t) else None
        es = [x["energy_J"] for x in t if x["energy_J"] is not None]
        row = dict(o, p1_runs=len(t), p1_passes=sum(x["result"] == "pass" for x in t), p1_calls=med("calls"),
                   p1_out=med("out"), p1_energy_J=med("energy_J"), p1_energy_min_J=min(es) if es else None,
                   p1_energy_max_J=max(es) if es else None,
                   energy_in_p1_range=bool(es) and o["energy_J"] is not None and min(es) <= o["energy_J"] <= max(es))
        out.append(row)
        e = (o["energy_J"] or 0) / 1e3
        pe = (row["p1_energy_J"] or 0) / 1e3
        print(f"{o['task']:22s} {o['result']:>5s} {row['p1_passes']:>4d}/{row['p1_runs']:<5d} | "
              f"{o['calls']:>7d} / {row['p1_calls'] or 0:<8.0f} | {o['out']:>8d} / {row['p1_out'] or 0:<9.0f} | "
              f"{e:>6.1f} / {pe:<6.1f}")
    n = len(out)
    print(f"summary: ours passed {sum(r['result'] == 'pass' for r in out)}/{n}; P1 passed "
          f"{sum(r['p1_passes'] for r in out)}/{sum(r['p1_runs'] for r in out)} on the same tasks; our energy within P1's "
          f"min-max on {sum(r['energy_in_p1_range'] for r in out)}/{n} tasks; total {sum(r['energy_J'] or 0 for r in out) / 1e3:.1f} kJ "
          f"against P1's medians {sum(r['p1_energy_J'] or 0 for r in out) / 1e3:.1f} kJ")
    json.dump(out, open(os.path.join(run_dir, "p5_validate.json"), "w"), indent=1, default=str)
    print("wrote", os.path.join(run_dir, "p5_validate.json"))


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "selftest":
        selftest()
    elif len(sys.argv) >= 3 and sys.argv[1] == "compare":
        compare(sys.argv[2])
    else:
        print(__doc__)

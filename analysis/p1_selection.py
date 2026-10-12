"""P1's selection rule for traffic runs, and the clean per-configuration outcomes it gives (P1F-2, OPTIONS_PLAN.md §5.1).

Ported from P1's `analysis/edgebench/selection.py` (EdgeAgentBench, dream-lab/edge-agent-bench at 0cc2311a; author
Mayank Arya, last changed 9 Oct, commit 577ef7a6), with the permission of P1's mentor (12 Oct) to use P1's code. The
logic is copied, not imported: importing it in place would write __pycache__ into P1's read-only clone. Keep it in step
with P1's file when P1's clone is pulled (`select()` below is that file's function, unchanged in behaviour).

P1's rule, per (device, paradigm, model, instance, run<N>, task):
- the highest re-run generation present wins: run<N> 0, _topup 1, _topupB 1.5, _topup2 2, _cap8000 3;
- a re-run never replaces an original that overflowed the context (failure_class input_ceiling);
- rows in traffic/grading/no_supersede.csv never replace an earlier row;
- excluded: `_ceilretry` and any other suffix, repeats beyond the three used (Thor gemma-26B tool calling keeps
  runs 2-4), and the 7 camera-image tasks for the text-only models (granite, Devstral).

`grades.csv` holds exactly one row per runs.jsonl row of P1's edge sweeps (4,737 at 0cc2311a), with the grader's verdict.
P1's outcome is that verdict with `overrides.csv` applied on top, as P1's `traffic/grading/apply_grades.py` writes it into
runs.jsonl: a run with an infrastructure fault (a missing sandbox image, a full disk) is a fail whatever the grader said,
and is marked `grade_override`. The clean outcomes per configuration come from these two files (`clean_rows`,
`outcomes`). The call-level loader
(analysis/p1_repo.py) applies the same `select()` to the runs.jsonl rows it reads.
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict

from analysis.sessions import REPO

P1 = REPO / "data/edge-agent-bench"
GRADES = P1 / "traffic/grading/grades.csv"
OVERRIDES = P1 / "traffic/grading/overrides.csv"
NO_SUPERSEDE = P1 / "traffic/grading/no_supersede.csv"
EDGE_SWEEPS = ("final_sweep_orin_32", "final_sweep_orin_64", "final_sweep_thor")

GENERATION = {"": 0, "topup": 1, "topupB": 1.5, "topup2": 2, "cap8000": 3}
REPEATS = {("thor", "tool_calling", "gemma-4-26B-A4B-it"): (2, 3, 4)}
VISION_TASKS = {"accident", "ambulance-count", "camera-bumped", "mis-pointed-fraction", "obstructed-camera",
                "potholes", "special-vehicle"}
TEXT_ONLY = {"Devstral-Small-2-24B-Instruct-2512", "granite-4.2-8b"}

# P1's canonical cell names (its figdata/*.csv `cell` column): traffic/<device>/<paradigm>/<model>
DEVICE = {"orin_32": "orin32", "orin_64": "orin64", "thor": "thor"}
MODEL = {"gemma-4-E4B-it": "gemma4-e4b", "gemma-4-26B-A4B-it": "gemma4-26b-a4b", "granite-4.2-8b": "granite4.2-8b",
         "Qwen2.5-VL-7B-Instruct": "qwen2.5-vl-7b", "Ministral-3-8B-Instruct-2512": "ministral3-8b",
         "Devstral-Small-2-24B-Instruct-2512": "devstral-24b", "Qwen3.6-35B-A3B-FP8": "qwen3.6-35b-a3b"}


def cell_name(device, paradigm, model):
    return f"traffic/{DEVICE[device]}/{paradigm}/{MODEL[model]}"


def parse_run(name: str) -> tuple[int | None, str]:
    """'run3_topup2' -> (3, 'topup2'); 'run1' -> (1, ''); 'gate' -> (None, 'gate')."""
    m = re.fullmatch(r"run(\d+)(?:_(.+))?", name)
    return (int(m.group(1)), m.group(2) or "") if m else (None, name)


def _no_supersede(path=NO_SUPERSEDE) -> dict[tuple, str]:
    if not path.exists():
        return {}
    with open(path, newline="") as f:
        return {(r["device"], r["paradigm"], r["model"], r["instance"], r["run"], r["task_id"]): r.get("reason") or ""
                for r in csv.DictReader(line for line in f if not line.startswith("#"))}


def select(rows: list[dict], no_supersede: dict | set | None = None) -> list[dict]:
    """rows: dicts with device, paradigm, model, instance, run (folder name), task_id, and failure_class (optional;
    without it the overflow rule cannot apply).
    Returns one dict per row, in order: repeat (1..3 or None), variant, generation (None if the variant never
    supersedes), excluded (bool) and reason ('' when kept)."""
    pad = _no_supersede() if no_supersede is None else no_supersede
    out, best = [], {}
    for i, r in enumerate(rows):
        n, variant = parse_run(r["run"])
        gen = GENERATION.get(variant)
        key = (r["device"], r["paradigm"], r["model"], r["instance"], r["run"], r["task_id"])
        if gen and key in pad:
            gen = None
            why = pad.get(key) if isinstance(pad, dict) else ""
            reason = f"re-run listed in no_supersede.csv: {why}" if why else "re-run listed in no_supersede.csv"
        elif gen is None:
            reason = f"run variant '{variant}' is not a superseding re-run"
        else:
            reason = ""
        keep = REPEATS.get((r["device"], r["paradigm"], r["model"]))
        repeat = n
        if keep and n is not None:
            if n in keep:
                repeat = keep.index(n) + 1
            elif not reason:
                reason, gen = "extra repeat (not one of the three used)", None
        if not reason and r["model"] in TEXT_ONLY and r["task_id"] in VISION_TASKS:
            reason = "camera-image workload run by a text-only model"
        out.append(dict(repeat=repeat, variant=variant, generation=gen, excluded=bool(reason), reason=reason))
        if gen is not None and not reason:
            task = (r["device"], r["paradigm"], r["model"], r["instance"], n, r["task_id"])
            if task not in best or gen > out[best[task]]["generation"]:
                best[task] = i
            elif gen == out[best[task]]["generation"]:
                raise ValueError(f"two rows of generation {gen} for {task}")
    # an overflow is kept: no re-run of a task whose original (generation 0) row overflowed supersedes it
    key = lambda r: (r["device"], r["paradigm"], r["model"], r["instance"], parse_run(r["run"])[0], r["task_id"])
    original = {key(r): i for i, (r, o) in enumerate(zip(rows, out)) if o["generation"] == 0 and not o["excluded"]}
    overflowed = {t for t, i in original.items() if rows[i].get("failure_class") == "input_ceiling"}
    for r, o in zip(rows, out):
        if o["generation"] and not o["excluded"] and key(r) in overflowed:
            o.update(excluded=True, reason="re-run of a context overflow (a model outcome, not a fault)")
    for t in overflowed:
        best[t] = original[t]
    winners = set(best.values())
    for i, (r, o) in enumerate(zip(rows, out)):
        if o["generation"] is not None and not o["excluded"] and i not in winners:
            n, _ = parse_run(r["run"])
            task = (r["device"], r["paradigm"], r["model"], r["instance"], n, r["task_id"])
            o["excluded"], o["reason"] = True, f"superseded by {rows[best[task]]['run']}"
    return out


def graded_rows():
    """grades.csv rows of P1's edge traffic sweeps (P1's main analysis; cloud and RTX rows are references), with P1's
    overrides applied (apply_grades.py): final_result from overrides.csv where listed, grade_override = its reason."""
    with open(OVERRIDES, newline="") as f:
        ov = {(r["run_dir"].strip().rstrip("/"), r["run_id"].strip()): (r["final_result"].strip().lower(), r["reason"])
              for r in csv.DictReader(f)}
    with open(GRADES, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["run_dir"].split("/")[1] in EDGE_SWEEPS]
    for r in rows:
        r["failure_class"] = r["failure_class"] or None
        o = ov.get((r["run_dir"], r["run_id"]))
        r["grader_result"] = r["final_result"]
        r["final_result"], r["grade_override"] = (o[0], o[1]) if o else (r["final_result"], None)
    return rows


def clean_rows():
    """The rows P1's main analysis keeps, each with its cell name and selection record."""
    rows = graded_rows()
    sel = select(rows)
    return [dict(r, cell=cell_name(r["device"], r["paradigm"], r["model"]), **s) for r, s in zip(rows, sel)
            if not s["excluded"]]


def outcomes():
    """Per cell: runs, passed, overflowed (input_ceiling), harness failures and overridden (infrastructure-faulted)
    runs, over P1's clean rows."""
    out = defaultdict(lambda: dict(runs=0, passed=0, overflow=0, harness_failures=0, overridden=0, tasks=set()))
    for r in clean_rows():
        c = out[r["cell"]]
        c["runs"] += 1
        c["passed"] += r["final_result"] == "pass"
        c["overflow"] += r["failure_class"] == "input_ceiling"
        c["harness_failures"] += r["failure_class"] is not None
        c["overridden"] += r["grade_override"] is not None
        c["tasks"].add(r["task_id"])
    return {k: dict(v, tasks=len(v["tasks"]), pass_rate=v["passed"] / v["runs"]) for k, v in sorted(out.items())}


if __name__ == "__main__":
    tot = ov = 0
    for cell, c in outcomes().items():
        tot += c["runs"]
        print(f"{cell:45s} runs {c['runs']:4d}  tasks {c['tasks']:2d}  pass {c['passed']:4d} ({100 * c['pass_rate']:5.1f}%)"
              f"  overflow {c['overflow']:3d}  harness failures {c['harness_failures']:3d}  overridden {c['overridden']:3d}")
        ov += c["overridden"]
    print(f"total runs {tot}, overridden (infrastructure-faulted) {ov}")

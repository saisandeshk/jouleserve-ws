"""P1F-2: our port of P1's traffic selection rule gives P1's own per-configuration outcomes (OPTIONS_PLAN.md §5.1).

Checked against P1's committed outputs at 0cc2311a (analysis/outputs/figdata/), never against P1's code:
- G2_failure_cost.csv `nonpassing_run_share` (1 - pass rate) and B5_context_capacity.csv `overflow_share`, per cell;
- suite_stats.numbers.json: 17 cells and 3,605 clean runs; its per-class counts are over all 4,737 rows (before selection);
- P1's paper: 142 infrastructure-faulted runs remain, all in the Orin 64 gemma-26B and Devstral Reflexion arms.
EXPECTED pins our counts, so a pull of P1's clone that changes them fails here first.

Run (laptop or WS, stdlib only): python -m tests.test_p1_selection
"""
import csv
import json
from collections import Counter

from analysis.p1_repo import load
from analysis.p1_selection import P1, cell_name, clean_rows, graded_rows, outcomes

FIG = P1 / "analysis/outputs/figdata"

# cell: (runs, passed, overflowed), our counts at P1's 0cc2311a
EXPECTED = {
    "traffic/orin32/reflexion/granite4.2-8b": (126, 73, 25),
    "traffic/orin32/reflexion/qwen2.5-vl-7b": (252, 70, 0),
    "traffic/orin32/tool_calling/gemma4-e4b": (252, 184, 0),
    "traffic/orin32/tool_calling/granite4.2-8b": (189, 97, 40),
    "traffic/orin32/tool_calling/ministral3-8b": (252, 154, 7),
    "traffic/orin32/tool_calling/qwen2.5-vl-7b": (252, 66, 0),
    "traffic/orin64/reflexion/devstral-24b": (126, 31, 5),
    "traffic/orin64/reflexion/gemma4-26b-a4b": (196, 64, 55),
    "traffic/orin64/tool_calling/devstral-24b": (189, 111, 11),
    "traffic/orin64/tool_calling/gemma4-26b-a4b": (252, 113, 61),
    "traffic/orin64/tool_calling/granite4.2-8b": (189, 111, 36),
    "traffic/orin64/tool_calling/qwen2.5-vl-7b": (252, 60, 0),
    "traffic/thor/reflexion/gemma4-26b-a4b": (196, 167, 1),
    "traffic/thor/tool_calling/devstral-24b": (189, 126, 3),
    "traffic/thor/tool_calling/gemma4-26b-a4b": (252, 187, 0),
    "traffic/thor/tool_calling/granite4.2-8b": (189, 124, 0),
    "traffic/thor/tool_calling/qwen3.6-35b-a3b": (252, 226, 0),
}


def _col(name, col):
    with open(FIG / name, newline="") as f:
        return {r["cell"]: float(r[col]) for r in csv.DictReader(f) if r["cell"].startswith("traffic/")}


def test_against_p1_outputs():
    ours = outcomes()
    nonpass = _col("G2_failure_cost.csv", "nonpassing_run_share")
    overflow = _col("B5_context_capacity.csv", "overflow_share")
    assert set(ours) == set(nonpass) == set(overflow) == set(EXPECTED), set(ours) ^ set(nonpass)
    for cell, c in ours.items():
        assert abs((1 - c["passed"] / c["runs"]) - nonpass[cell]) < 1e-9, (cell, c, nonpass[cell])
        assert abs(c["overflow"] / c["runs"] - overflow[cell]) < 1e-9, (cell, c, overflow[cell])
        assert (c["runs"], c["passed"], c["overflow"]) == EXPECTED[cell], (cell, c)
    suite = json.loads((FIG / "suite_stats.numbers.json").read_text())["traffic"]
    assert suite["all"]["configs"] == len(ours) == 17
    assert suite["all"]["runs"] == sum(c["runs"] for c in ours.values()) == 3605
    by_class = Counter(r["task_class"].replace("/", "") for r in graded_rows())
    assert all(suite[f"class_{k}"]["runs"] == n for k, n in by_class.items()), by_class
    faulted = Counter(c for c, o in ours.items() for _ in range(o["overridden"]))
    assert sum(faulted.values()) == 142 and set(faulted) == {"traffic/orin64/reflexion/gemma4-26b-a4b",
                                                             "traffic/orin64/reflexion/devstral-24b"}, faulted


def test_rule_cases():
    rows = clean_rows()
    # text-only models never keep a camera-image task; Thor gemma tool calling keeps runs 2-4 only
    assert not [r for r in rows if r["model"] == "granite-4.2-8b" and r["task_id"] == "potholes"]
    assert {r["run"].split("_")[0] for r in rows if r["cell"] == "traffic/thor/tool_calling/gemma4-26b-a4b"} == \
        {"run2", "run3", "run4"}
    assert not [r for r in rows if "ceilretry" in r["run"]]
    # one row per (cell, instance, run<N>, task)
    keys = Counter((r["cell"], r["instance"], r["run"].split("_")[0], r["task_id"]) for r in rows)
    assert max(keys.values()) == 1
    # an original that overflowed is kept: its re-run never replaces it
    over = {(cell_name(r["device"], r["paradigm"], r["model"]), r["instance"], r["run"], r["task_id"])
            for r in graded_rows() if r["failure_class"] == "input_ceiling" and "_" not in r["run"]}
    kept = {(r["cell"], r["instance"], r["run"].split("_")[0], r["task_id"]): r["run"] for r in rows}
    assert over and all(kept[k] == k[2] for k in over if k in kept)


def test_loader_agrees():
    """analysis/p1_repo.py applies the same rule to runs.jsonl: same runs and outcomes per configuration."""
    ours = outcomes()
    for key, cell in (("t_o32_granite", "traffic/orin32/tool_calling/granite4.2-8b"),
                      ("t_o32_e4b", "traffic/orin32/tool_calling/gemma4-e4b")):
        runs = load(key, refresh=True)
        assert len(runs) == ours[cell]["runs"], (key, len(runs))
        assert sum(r["passed"] for r in runs) == ours[cell]["passed"], key
        assert sum(r["status"] == "input_ceiling" for r in runs) == ours[cell]["overflow"], key


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"{name}: ok")

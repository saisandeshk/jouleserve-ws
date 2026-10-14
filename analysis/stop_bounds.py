"""Q1 and Q2 bounds for the "doomed work" lever (planning/ENERGY_PLAN.md §5), from P1's logs.

A stop rule ends a run early; a stopped run counts as a failure. Energy per success after a rule is
(total energy - energy saved) / (passes - passing runs it cut). Rules (fixed before the numbers were read):
- signs (analysis/waterfall.py): stop at the first capped call, two consecutive caps, a prompt at 80% of the window,
  or the earliest of these;
- energy budget: stop a run once it has spent m x the median energy of the configuration's passing runs
  (task-agnostic), or m x the median of the passing runs of the same task, the run itself left out (task-aware;
  the configuration median when the task has no other passing run); m in M;
- oracle: every failing run stopped at its start, no pass lost (the most any stop policy could save);
- task oracle: every run of a task the configuration never passes stopped at its start (what a perfect per-task
  history could save).
A rule counts only if it keeps the pass rate (plan §5, Q2): it may cut at most PASS_LOSS_MAX of the passes (added
14 Oct after the first run picked rules that halved the passes; the plan already required "at the same pass rate").
Q1 (is one fixed value best everywhere?): the best admissible rule per configuration against the single rule that is
admissible everywhere and best summed over all configurations. Q2 bound: the gap between the best admissible fixed
rule and the oracle is the most an adaptive stop policy could add on top of B*.

Usage (WS, ~/jsw-dev): python -m analysis.stop_bounds  -> reports/2026-10-14-waterfall/stop_bounds.json
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict

from analysis.p1_repo import CONFIGS, load
from analysis.sessions import REPO
from analysis.waterfall import energy_after, passed, signs

OUT = REPO / "reports/2026-10-14-waterfall"
M = (1.5, 2.0, 3.0, 5.0, 8.0, 12.0)
PASS_LOSS_MAX = 0.05


def evaluate(total, S, cuts):
    """cuts: list of (energy saved, run passed) for the runs a rule stops."""
    saved = sum(s for s, _ in cuts)
    lost = sum(1 for _, p in cuts if p)
    es = (total - saved) / (S - lost) if S - lost > 0 else None
    base = total / S
    return dict(saved_J=saved, passes_lost=lost, e_per_success_J=es, change=(es / base - 1) if es else None)


def bounds(key):
    cfg = next(c for c in CONFIGS if c.key == key)
    dom = cfg.domain
    runs = load(key)
    total = sum(r["energy_J"] for r in runs)
    S = sum(passed(r, dom) for r in runs)
    out = dict(key=key, domain=dom, runs=len(runs), passes=S, e_per_success_J=total / S, rules={})
    for kind in ("cap1", "cap2", "ctx80", "any"):
        cuts = []
        for r in runs:
            s = signs(r).get(kind)
            if s is not None:
                cuts.append((min(energy_after(r, s), r["energy_J"]), passed(r, dom)))
        out["rules"][f"sign_{kind}"] = evaluate(total, S, cuts)
    pe = [r["energy_J"] for r in runs if passed(r, dom)]
    med_cfg = statistics.median(pe)
    by_task = defaultdict(list)
    for i, r in enumerate(runs):
        if passed(r, dom):
            by_task[r["task"]].append((i, r["energy_J"]))
    for m in M:
        for aware in (False, True):
            cuts = []
            for i, r in enumerate(runs):
                if aware:
                    others = [e for j, e in by_task.get(r["task"], []) if j != i]
                    ref = statistics.median(others) if others else med_cfg
                else:
                    ref = med_cfg
                B = m * ref
                if r["energy_J"] > B:
                    cuts.append((r["energy_J"] - B, passed(r, dom)))
            out["rules"][f"budget_{'task' if aware else 'cfg'}_{m:g}"] = evaluate(total, S, cuts)
    fail_E = sum(r["energy_J"] for r in runs if not passed(r, dom))
    out["rules"]["oracle"] = evaluate(total, S, [(r["energy_J"], False) for r in runs if not passed(r, dom)])
    never = {t for t in {r["task"] for r in runs} if not any(passed(x, dom) for x in runs if x["task"] == t)}
    out["rules"]["oracle_task"] = evaluate(total, S, [(r["energy_J"], False) for r in runs if r["task"] in never])
    out["failed_share"] = fail_E / total
    return out


def main():
    res = [bounds(c.key) for c in CONFIGS]
    # Q1: per-configuration best fixed rule vs one rule for all (summed relative change)
    names = sorted(res[0]["rules"])
    fixed = [n for n in names if not n.startswith("oracle")]

    def ok(r, n):
        return r["rules"][n]["passes_lost"] <= int(PASS_LOSS_MAX * r["passes"])

    everywhere = [n for n in fixed if all(ok(r, n) for r in res)]
    summed = {n: sum((r["rules"][n]["change"] or 0.0) for r in res) for n in everywhere}
    global_best = min(summed, key=summed.get)
    for r in res:
        adm = [n for n in fixed if ok(r, n)]
        best = min(adm, key=lambda n: r["rules"][n]["e_per_success_J"] or float("inf"))
        r["best_fixed"] = best
        r["global_rule"] = global_best
        es0 = r["e_per_success_J"]
        r["summary"] = dict(
            best_fixed_change=r["rules"][best]["change"], best_fixed_lost=r["rules"][best]["passes_lost"],
            global_change=r["rules"][global_best]["change"], global_lost=r["rules"][global_best]["passes_lost"],
            oracle_change=r["rules"]["oracle"]["change"], oracle_task_change=r["rules"]["oracle_task"]["change"],
            gap_oracle_vs_best_fixed=(r["rules"]["oracle"]["e_per_success_J"] / r["rules"][best]["e_per_success_J"]
                                      - 1),
            e_per_success_J=es0)
        s = r["summary"]
        print(f"{r['key']:20s} fail {100 * r['failed_share']:4.0f}%  best fixed {best:16s} "
              f"{100 * s['best_fixed_change']:+6.1f}% (-{s['best_fixed_lost']:2d} pass)  "
              f"global {100 * s['global_change']:+6.1f}% (-{s['global_lost']:2d})  "
              f"task-oracle {100 * s['oracle_task_change']:+6.1f}%  oracle {100 * s['oracle_change']:+6.1f}%  "
              f"oracle vs best fixed {100 * s['gap_oracle_vs_best_fixed']:+6.1f}%")
    print("global best rule:", global_best)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stop_bounds.json").write_text(json.dumps(dict(M=M, pass_loss_max=PASS_LOSS_MAX, global_best=global_best,
                                                         configs=res), indent=1))
    print("wrote", OUT / "stop_bounds.json")


if __name__ == "__main__":
    main()

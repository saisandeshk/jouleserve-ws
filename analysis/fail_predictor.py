"""WF-3b: can an online failure predictor capture the gap between the best fixed stop rule and the oracle?
(planning/THESIS.md, "What we have"; ENERGY_PLAN §5.)

At the end of every LLM call of a run, a policy may stop the run (a stopped run counts as a failure). The predictor sees
only what the serving layer has seen by then. Features (fixed before the numbers were read):
  energy so far / a reference energy (median energy of passing runs; per task when history is available),
  calls so far, capped calls so far, whether the last call and the last two calls were capped,
  largest prompt so far / context window, last output / its cap, tool calls so far, distinct tools so far,
  and, with history, the task's pass rate in the training runs.
Model: L2-regularised logistic regression (numpy), one per configuration and fold; label = the run fails.
Threshold: chosen on the training runs as the one that saves the most energy while cutting at most 5% of the training
passes; then applied to the held-out runs.
Two evaluations:
  new tasks   - folds by task (4 folds): the predictor never saw the held-out tasks; no task history;
  repeats     - folds by repeat (leave one repeat out): the held-out task was seen in the other repeats, so the task's
                pass rate and median passing energy come from those.
Reported per configuration: energy per success after the policy (against as run), passes cut, and the share of the
gap between the best fixed rule (stop_bounds.json, chosen in-sample, so favoured) and the oracle that it captures.

Usage (WS): python -m analysis.fail_predictor -> reports/2026-10-14-waterfall/fail_predictor.json
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict

import numpy as np

from analysis.p1_repo import BY_KEY, CONFIGS, load
from analysis.sessions import REPO
from analysis.waterfall import energy_after, passed

OUT = REPO / "reports/2026-10-14-waterfall"
PASS_LOSS_MAX = 0.05
SEED = 7


def run_points(r, ref_E, prior):
    """Feature rows at the end of each call of a run: (t_stop, features)."""
    calls, tools = r["calls"], r["tools"]
    ctx = r.get("ctx") or 0
    rows = []
    caps = 0
    maxp = 0
    for i, c in enumerate(calls):
        caps += bool(c["capped"])
        maxp = max(maxp, c["prompt"])
        t = c["t1"]
        e_so_far = sum((x["energy"] or 0.0) for x in calls[:i + 1]) + \
            sum((x["energy"] or 0.0) for x in tools if x["t1"] <= t)
        tl = [x for x in tools if x["t1"] <= t]
        f = [e_so_far / ref_E if ref_E else 0.0, i + 1, caps, float(c["capped"]),
             float(c["capped"] and i > 0 and calls[i - 1]["capped"]),
             maxp / ctx if ctx else 0.0, c["out"] / c["cap"] if c.get("cap") else 0.0,
             len(tl), len({x["tool"] for x in tl})]
        if prior is not None:
            f.append(prior)
        rows.append((t, f))
    return rows


def fit_logreg(X, y, lam=1.0, iters=400, lr=0.5):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = (X - mu) / sd
    w = np.zeros(Z.shape[1])
    b = 0.0
    n = len(y)
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(Z @ w + b)))
        g = p - y
        w -= lr * (Z.T @ g / n + lam * w / n)
        b -= lr * g.mean()
    return lambda Xn: 1 / (1 + np.exp(-(((Xn - mu) / sd) @ w + b)))


def simulate(runs, dom, rows_by_run, prob, tau):
    """Stop each run at its first point with p >= tau. Returns (energy saved, passes cut)."""
    saved, cut = 0.0, 0
    for r in runs:
        pts = rows_by_run.get(id(r), [])
        if not pts:
            continue
        ps = prob(np.array([f for _, f in pts]))
        hit = next((k for k, p in enumerate(ps) if p >= tau), None)
        if hit is None:
            continue
        saved += min(energy_after(r, pts[hit][0]), r["energy_J"])
        cut += passed(r, dom)
    return saved, cut


def evaluate(key, mode):
    cfg = BY_KEY[key]
    dom = cfg.domain
    runs = [r for r in load(key)]
    total = sum(r["energy_J"] for r in runs)
    S = sum(passed(r, dom) for r in runs)
    if mode == "tasks":
        tasks = sorted({r["task"] for r in runs})
        rng = np.random.default_rng(SEED)
        rng.shuffle(tasks)
        fold_of = {t: i % 4 for i, t in enumerate(tasks)}
        folds = [[r for r in runs if fold_of[r["task"]] == k] for k in range(4)]
    else:
        reps = sorted({r.get("rep") for r in runs}, key=lambda x: (x is None, x))
        folds = [[r for r in runs if r.get("rep") == rp] for rp in reps]
    saved_all, cut_all = 0.0, 0
    for k, test in enumerate(folds):
        tid = {id(r) for r in test}
        train = [r for r in runs if id(r) not in tid]
        if not test or not train or not any(passed(r, dom) for r in train):
            continue
        med = statistics.median([r["energy_J"] for r in train if passed(r, dom)])
        by_task = defaultdict(list)
        for r in train:
            by_task[r["task"]].append(r)

        def ref_prior(r):
            if mode == "tasks":
                return med, None
            tr = by_task.get(r["task"], [])
            pe = [x["energy_J"] for x in tr if passed(x, dom)]
            prior = (sum(passed(x, dom) for x in tr) / len(tr)) if tr else 0.5
            return (statistics.median(pe) if pe else med), prior

        rows = {}
        for r in train + test:
            ref, prior = ref_prior(r)
            rows[id(r)] = run_points(r, ref, prior)
        X = np.array([f for r in train for _, f in rows[id(r)]])
        y = np.array([0.0 if passed(r, dom) else 1.0 for r in train for _ in rows[id(r)]])
        if len(X) < 10 or y.min() == y.max():
            continue
        prob = fit_logreg(X, y)
        S_tr = sum(passed(r, dom) for r in train)
        best_tau, best_saved = None, 0.0
        for tau in (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.93, 0.95, 0.97, 0.98, 0.99):
            sv, ct = simulate(train, dom, rows, prob, tau)
            if ct <= int(PASS_LOSS_MAX * S_tr) and sv > best_saved:
                best_tau, best_saved = tau, sv
        if best_tau is None:
            continue
        sv, ct = simulate(test, dom, rows, prob, best_tau)
        saved_all += sv
        cut_all += ct
    es = (total - saved_all) / (S - cut_all) if S - cut_all > 0 else None
    return dict(mode=mode, saved_J=saved_all, passes_cut=cut_all, passes=S,
                e_per_success_J=es, change=(es / (total / S) - 1) if es else None)


def main():
    sb = {c["key"]: c for c in json.loads((OUT / "stop_bounds.json").read_text())["configs"]}
    out = []
    for c in CONFIGS:
        b = sb[c.key]
        base = b["e_per_success_J"]
        fixed = b["rules"][b["best_fixed"]]["e_per_success_J"]
        orac = b["rules"]["oracle"]["e_per_success_J"]
        res = dict(key=c.key, domain=c.domain, best_fixed=b["best_fixed"], fixed_change=fixed / base - 1,
                   oracle_change=orac / base - 1)
        for mode in ("tasks", "repeats"):
            ev = evaluate(c.key, mode)
            gap = fixed - orac
            ev["captured_gap"] = ((fixed - ev["e_per_success_J"]) / gap) if (ev["e_per_success_J"] and gap > 0) else None
            res[mode] = ev
        out.append(res)
        t, rp = res["tasks"], res["repeats"]

        def f(v):
            return f"{100 * v:+6.1f}%" if v is not None else "   n/a"
        print(f"{c.key:20s} fixed {f(res['fixed_change'])} oracle {f(res['oracle_change'])} | new tasks "
              f"{f(t['change'])} (-{t['passes_cut']}/{t['passes']}) gap {f(t['captured_gap'])} | repeats "
              f"{f(rp['change'])} (-{rp['passes_cut']}/{rp['passes']}) gap {f(rp['captured_gap'])}", flush=True)
    (OUT / "fail_predictor.json").write_text(json.dumps(dict(pass_loss_max=PASS_LOSS_MAX, configs=out), indent=1))
    print("wrote", OUT / "fail_predictor.json")


if __name__ == "__main__":
    main()

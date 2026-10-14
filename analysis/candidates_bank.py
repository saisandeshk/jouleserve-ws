"""WF-4 (first part): when do parallel candidates pay, and does the best number of candidates change with load?
From the mentor's sample banks and cost curves (13-14 Oct, `p5_osdi` on Thor-1 and Orin-32-1; copied read-only to
~/work/mentor/), with her drone tasks. Definitions fixed before the numbers were read:

- A bank holds 8 sampled answers per prompt (P1's recorded first-attempt prompt of a task and instance; Gemma's model-card
  sampling), each flown and graded by P1's deterministic check.
- First-of-k: every k-subset of the 8 is enumerated; the winner is the shortest answer that finished on its own
  (finish reason other than "length"), or the shortest if none did. Per prompt: the mean winner length and the
  probability the winner's program passes, over all subsets.
- Cost of one call at load A (A agents on the board, each running k candidates, decoding in lockstep): the winner's
  length x the board's energy per decode step at A x k streams / A (each agent's share), from the cost curve at the
  16K context (the banks' prompts are about 7K tokens and answers 5-20K). Prefill is left out (one shared prompt, cheap).
- Energy per success at (A, k) = mean energy per call / mean pass probability, over the set's prompts.
- Memory: A x (prompt + k x winner length) tokens must fit the server's KV pool, else (A, k) is infeasible.
- Only widths the cost curve measured are used (A x k <= 16); nothing is extrapolated.
- Q1: the best feasible k at each load; Q2: energy per success of the best k per load against the best single k for
  all loads (both over the loads where that single k is feasible).

Usage (WS): python -m analysis.candidates_bank -> reports/2026-10-15-candidates/candidates_bank.json
"""
from __future__ import annotations

import itertools
import json
import os
import statistics
from collections import defaultdict

from analysis.sessions import REPO

M = os.path.expanduser("~/work/mentor")
OUT = REPO / "reports/2026-10-15-candidates"
KS = (1, 2, 4, 8)
LOADS = (1, 2, 4, 8, 16)
BANKS = [  # (label, cost curve, bank folder, pool tokens)
    ("Thor-1 gemma-26B, hard prompts", "thor1/runs/t1_bf16/costcurve.jsonl", "thor1/runs/t2_bf16_hard", 296823),
    ("Thor-1 gemma-26B, controls", "thor1/runs/t1_bf16/costcurve.jsonl", "thor1/runs/t2_bf16_ctrl", 296823),
    ("Orin-32-1 gemma-E4B", "orin32_1/runs/o1_bf16/costcurve.jsonl", "orin32_1/runs/o3_bf16", 45990),
]


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def step_energy(curve_path, ctx=16384):
    """Board energy per decode step by width, median over repeats, at one context."""
    by = defaultdict(list)
    for r in jl(os.path.join(M, curve_path)):
        if r.get("ctx") == ctx and not r.get("errors"):
            by[r["k"]].append(r["j_per_step"])
    return {k: statistics.median(v) for k, v in sorted(by.items())}


def first_of_k(samples, k):
    """Mean winner length and pass probability over all k-subsets of one prompt's samples."""
    Ls, ps = [], []
    for sub in itertools.combinations(samples, k):
        fin = [s for s in sub if s["finished"]]
        w = min(fin or sub, key=lambda s: s["L"])
        Ls.append(w["L"])
        ps.append(1.0 if w["passed"] else 0.0)
    return statistics.mean(Ls), statistics.mean(ps)


def analyse(label, curve, bank, pool):
    e = step_energy(curve)
    samples = {(r["task"], r["inst"], r["sample"]): r for r in jl(os.path.join(M, bank, "samples.jsonl"))}
    prompts = defaultdict(list)
    for f in jl(os.path.join(M, bank, "flights.jsonl")):
        s = samples.get((f["task"], f["inst"], f["sample"]))
        if s is None:
            continue
        prompts[(f["task"], f["inst"])].append(dict(
            L=s["completion_tokens"], finished=s["finish_reason"] != "length", passed=bool(f["passed"]),
            prompt=s["prompt_tokens"]))
    per_k = {}
    for k in KS:
        Lw, pw, pr = [], [], []
        for key, ss in prompts.items():
            if len(ss) < k:
                continue
            L, p = first_of_k(ss, k)
            Lw.append(L)
            pw.append(p)
            pr.append(statistics.mean(s["prompt"] for s in ss))
        per_k[k] = dict(prompts=len(Lw), mean_len=statistics.mean(Lw), pass_rate=statistics.mean(pw),
                        mean_prompt=statistics.mean(pr), per_prompt_pass=pw)
    grid = {}
    for A in LOADS:
        for k in KS:
            w = A * k
            if w not in e:
                continue
            pk = per_k[k]
            kv = A * (pk["mean_prompt"] + k * pk["mean_len"])
            e_call = pk["mean_len"] * e[w] / A
            grid[f"{A}x{k}"] = dict(A=A, k=k, width=w, feasible=kv <= pool, kv_tokens=round(kv),
                                    energy_per_call_J=e_call,
                                    energy_per_success_J=(e_call / pk["pass_rate"]) if pk["pass_rate"] else None)
    best_by_load, rows = {}, []
    for A in LOADS:
        cands = [g for g in grid.values() if g["A"] == A and g["feasible"] and g["energy_per_success_J"]]
        if cands:
            b = min(cands, key=lambda g: g["energy_per_success_J"])
            best_by_load[A] = dict(k=b["k"], energy_per_success_J=b["energy_per_success_J"])
    fixed = {}
    for k in KS:
        loads = [A for A in best_by_load if f"{A}x{k}" in grid and grid[f"{A}x{k}"]["feasible"]]
        if loads:
            fixed[k] = dict(loads=loads, mean_ratio_to_adaptive=statistics.mean(
                grid[f"{A}x{k}"]["energy_per_success_J"] / best_by_load[A]["energy_per_success_J"] for A in loads))
    g2 = per_k[4]["mean_len"] * e[4] / per_k[4]["pass_rate"] / (per_k[1]["mean_len"] * e[1] / per_k[1]["pass_rate"]) \
        if per_k[4]["pass_rate"] and per_k[1]["pass_rate"] else None
    return dict(label=label, pool=pool, step_energy_J=e, per_k={k: {kk: vv for kk, vv in v.items() if kk != "per_prompt_pass"}
                                                                 for k, v in per_k.items()},
                grid=grid, best_k_by_load=best_by_load, fixed_k=fixed, g2_ratio_k4_vs_k1_at_A1=g2)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = [analyse(*b) for b in BANKS]
    for r in res:
        print("==", r["label"], "| energy per step by width:", {k: round(v, 2) for k, v in r["step_energy_J"].items()})
        for k, v in r["per_k"].items():
            print(f"   k={k}: winner {v['mean_len']:8.0f} tokens, pass {100 * v['pass_rate']:5.1f}% ({v['prompts']} prompts)")
        print("   first-of-4 vs one sampled answer, energy per success at one agent:",
              f"{100 * (r['g2_ratio_k4_vs_k1_at_A1'] - 1):+.0f}%" if r["g2_ratio_k4_vs_k1_at_A1"] else "n/a")
        print("   best k by load:", {A: v["k"] for A, v in r["best_k_by_load"].items()})
        print("   fixed k against adaptive (mean ratio over its feasible loads):",
              {k: (v["loads"], round(v["mean_ratio_to_adaptive"], 3)) for k, v in r["fixed_k"].items()})
    (OUT / "candidates_bank.json").write_text(json.dumps(res, indent=1, default=str))
    print("wrote", OUT / "candidates_bank.json")


if __name__ == "__main__":
    main()

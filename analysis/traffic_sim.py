"""Many traffic agents on one Jetson: does a memory controller beat SGLang's default?

The 2026-10-03 admission simulation (analysis/admission_sim.py) asked this for drones and found no.
Here the same simulator replays P1's traffic traces (analysis/p1_repo.py): N closed-loop agents per
device, each starting a new recorded run when one ends, under 12 serving policies and unlimited memory.

Per configuration, from P1's own measurements (one agent per device, temperature 0):
- workload: every recorded run's calls (prompt, cached and output tokens) and the gaps between them
  (tool time at real time); success = completed without a harness failure (traffic is ungraded);
  no prefix is shared between agents (every traffic prompt opens with the current date and time);
- device: cold prefill tokens/s, and decode time per step = t1 * f(batch) + c * (context tokens in the
  batch), with t1 and c fitted on the configuration's calls (decode_s / out = t1 + c * (prompt + out/2),
  P1's form) and f the weight-read growth with batch size: gemma-4-26B-A4B by its experts (as in
  admission_sim: 128 experts, top 8), dense models (granite, gemma-E4B) as on the WS (16 requests take
  1.13x one step);
- power: board power while any call runs (sum of call energy over call time) and otherwise (the
  board power measured during the tools other than ask_vlm, 15-35 W);
- memory: the configuration's real KV pool in tokens (half, as recorded, and double, about what an
  FP8 KV cache buys), as one budget for every agent's paused and running state.
The vision tool's own requests to the server (ask_vlm) are treated as tool time, so on the image tasks
the simulation understates contention.

Usage: python3 -m analysis.traffic_sim   (writes reports/2026-10-05-p1-repo/traffic_sim.json)
"""
from __future__ import annotations

import json
import math
import statistics as st
from dataclasses import dataclass
from multiprocessing import Pool

import numpy as np

from analysis.admission_sim import (GiB, Call, Device, Layout, Mission, Workload, POLICIES, simulate,
                                    summarize)
from analysis.p1_opportunity import rates
from analysis.p1_repo import BY_KEY, load
from analysis.sessions import REPO

OUT = REPO / "reports/2026-10-05-p1-repo"
CONFIGS = ["t_thor_gemma", "t_thor_granite", "t_o64_gemma", "t_o64_granite", "t_o32_granite", "t_o32_e4b"]
MOE = {"t_thor_gemma", "t_o64_gemma"}
TOKENS = Layout("KV pool in tokens", 1.0, 0.0, 0.0)
NS = (1, 2, 4, 8)
SCALES = (0.5, 1.0, 2.0)
SEEDS = (0, 1, 2)
HORIZON, WARM = 24 * 3600.0, 2 * 3600.0


def _moe_weights(b):
    distinct = 128 * (1 - (1 - 8 / 128) ** b)
    return 4.5e9 + distinct * 30 * 11.9e6


@dataclass
class FitDevice(Device):
    ctx_s: float = 0.0
    moe: bool = False

    def step(self, b, ctx_sum):
        if b <= 0:
            return 0.0
        f = _moe_weights(b) / _moe_weights(1) if self.moe else 1 + 0.13 * (b - 1) / 15
        return self.t1 * f + self.ctx_s * ctx_sum


def fit(key):
    runs = load(key)
    calls = [c for r in runs for c in r["calls"] if c["out"] >= 64 and c["decode"] > 0]
    X = np.array([[1.0, c["prompt"] + c["out"] / 2] for c in calls])
    y = np.array([c["decode"] / c["out"] for c in calls])
    w = np.array([c["out"] for c in calls], dtype=float)
    keep = np.ones(len(y), bool)
    for _ in range(3):  # weighted least squares, dropping > 5 MAD residuals (stalled calls)
        coef, *_ = np.linalg.lstsq(X[keep] * np.sqrt(w[keep])[:, None], y[keep] * np.sqrt(w[keep]), rcond=None)
        res = y - X @ coef
        mad = np.median(np.abs(res[keep] - np.median(res[keep])))
        keep = np.abs(res - np.median(res[keep])) <= 5 * 1.4826 * mad
    t1, c = float(coef[0]), max(0.0, float(coef[1]))
    pre, _ = rates(runs)
    E_calls = sum(x["energy"] or 0 for r in runs for x in r["calls"])
    T_calls = sum(x["t1"] - x["t0"] for r in runs for x in r["calls"])
    tools = [t for r in runs for t in r["tools"] if t["tool"] != "ask_vlm" and t["energy"] is not None]
    p_act = E_calls / T_calls
    p_idle = sum(t["energy"] for t in tools) / sum(t["t1"] - t["t0"] for t in tools)
    dev = FitDevice(f"{BY_KEY[key].device} · {BY_KEY[key].model} (fitted on P1's calls)", pre, p_act, p_idle,
                    "fit", t1=t1, ctx_s=c, moe=key in MOE)
    pool = st.median(r["pool"] for r in runs if r["pool"])
    return dev, pool, dict(t1_ms=t1 * 1e3, ctx_us_per_token=c * 1e6, prefill_tok_s=pre, p_active_w=p_act,
                           p_idle_w=p_idle, kv_pool_tokens=pool, fit_calls=int(keep.sum()), calls=len(calls))


def workload(key):
    ms = []
    for r in load(key):
        cs = r["calls"]
        if not cs:
            continue
        waits = [max(0.0, b["t0"] - a["t1"]) for a, b in zip(cs, cs[1:])]
        tools = []
        for a, b in zip(cs, cs[1:]):
            names = [t["tool"] for t in r["tools"] if t["t0"] >= a["t1"] - 0.5 and t["t1"] <= b["t0"] + 0.5]
            tools.append(names[0] if names else None)
        ms.append(Mission(f"{r['task']}|{r['instance']}|{r['rep']}", [Call(c["prompt"], c["cached"], c["out"]) for c in cs],
                          waits, tools, bool(r["ok"])))
    return Workload(BY_KEY[key].label, ms, 0, 8000)


_CACHE = {}


def _job(args):
    key, scale, n, pol, seed = args
    if key not in _CACHE:
        dev, pool, _ = fit(key)
        _CACHE[key] = (workload(key), dev, pool)
    wl, dev, pool = _CACHE[key]
    r = simulate(wl, dev, TOKENS, pool * scale / GiB, n, pol, horizon=HORIZON, warm=WARM, seed=seed)
    r.update(scenario=key, workload=key, layout="tokens", device=key, budget_gib=scale)
    return r


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    devices = {k: fit(k)[2] for k in CONFIGS}
    jobs = [(k, s, n, p, seed) for k in CONFIGS for s in SCALES for n in NS for p in POLICIES for seed in SEEDS]
    print(f"{len(jobs)} simulations")
    with Pool(20) as p:
        rows = p.map(_job, jobs, chunksize=4)
    cells = summarize(rows)
    for c in cells:
        c["pool_scale"] = c.pop("budget_gib")
        c.pop("policies", None)
    out = dict(devices=devices, cells=cells)
    (OUT / "traffic_sim.json").write_text(json.dumps(out, indent=1, default=lambda x: None if x != x else x))
    for k, d in devices.items():
        print(k, {a: round(b, 3) if isinstance(b, float) else b for a, b in d.items()})
    print("config            pool  n  default kJ  inf kJ  bound  found best      keepval  fail")
    for c in cells:
        print(f"{c['scenario']:16s} {c['pool_scale']:4.1f} {c['n']:2d} {c['e_default']/1e3:10.1f} {c['e_inf']/1e3:7.1f}"
              f" {c['bound_vs_default']:6.1%} {c['found_vs_default']:6.1%} {c['best_any']:9s} {c['retention_value']:6.1%}"
              f" {c['default_fail_share']:5.1%}")


if __name__ == "__main__":
    main()

"""Energy waterfall (planning/ENERGY_PLAN.md §4): where P1's board energy went, per configuration, how much of it was
avoidable, and what fixed stop rules would have saved (the first piece of Q1/Q2, §5).

Data: P1's final data (repository 0cc2311a) through analysis/p1_repo.py, i.e. P1's selection rule for traffic. Drone
cells read the run folders as they are now (for the sweeps P1 re-ran with its E2 evaluator, the E2 record). Energy is
P1's board energy: per run `workflow_energy_J`, per LLM call and per tool phase P1's `iter_energy_j` (board power
integrated over the phase). Success is P1's grade (traffic: final_result after P1's overrides; drone: final_result).

Buckets, each joule counted once, in this order (fixed before the numbers were read):
  1. failed runs, by cause (first match: window overflow, a capped call, completed but graded wrong, other), split
     into the energy after the first warning sign (what a stop rule could save) and before it;
  2. degenerate decode in passing runs: decode energy of capped calls above the median decode energy of a finished
     call of the same role in the same configuration;
  3. tool phases in passing runs: the vision tool (ask_vlm / get_camera_frames: the agent's own model reading
     images, so model work) and other tools (the board waiting; drone flights include P1's simulator on the board);
  4. prefill in passing runs: call energy x TTFT / call time;
  5. the remaining decode in passing runs, split into the batch-1 cost and the floor: the floor is that decode
     priced at k requests decoding together with the board's cost curve (RATIO, k = 4 headline, 8 reported);
  6. other: run energy outside LLM calls and tool phases (harness, setup), and passing runs without a trace.
Warning signs (fixed before the numbers were read): the end of the first capped call; the start of the first call
whose prompt reaches 80% of the context window. The detectable bound charges a failed run's energy after the earlier
sign. Stop rules then ask what stopping at a sign would have done to energy per success, counting the passing runs it
would also have cut (their success lost).

Usage (on the WS, ~/jsw-dev): python -m analysis.waterfall [--refresh]
    -> reports/2026-10-14-waterfall/waterfall.json and a printed table
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict

from analysis.p1_repo import BY_KEY, CONFIGS, load
from analysis.sessions import REPO

OUT = REPO / "reports/2026-10-14-waterfall"
SIGN_CTX_FRAC = 0.80
VISION = ("ask_vlm", "get_camera_frames")
K_HEAD = 4

# Board energy per generated token with k requests decoding together, relative to one request (board energy; the
# per-step cost curves of 12-13 Oct).
RATIO = {
    "moe": {4: 0.450, 8: 0.316},     # gemma-4-26B-A4B on Thor-1 (mentor's T1 curve, bf16, 4K and 16K agree)
    "dense": {4: 0.262, 8: 0.140},   # gemma-4-E4B on Orin-32-1 (mentor's O1 curve, 4K and 16K agree);
                                     # granite on Orin-32-1/2/3 at k = 8 (DEV-6: 0.140)
}
# Which curve prices each configuration, and whether it was measured for that model and board or is a proxy.
CURVE = {
    "d_thor_gemma_rfx": ("moe", "measured"), "d_thor_gemma_tc": ("moe", "measured"),
    "t_thor_gemma": ("moe", "measured"), "t_thor_gemma_rfx": ("moe", "measured"),
    "t_thor_qwen36": ("moe", "proxy"),
    "t_o64_gemma": ("moe", "proxy"), "t_o64_gemma_rfx": ("moe", "proxy"),
    "t_o32_granite": ("dense", "measured"), "t_o32_granite_rfx": ("dense", "measured"),
    "d_o32_granite_tc": ("dense", "measured"),
    "t_o32_e4b": ("dense", "measured"), "d_o32_e4b_tc": ("dense", "measured"),
}
BUCKETS = ["failed_after_sign", "failed_before_sign", "degenerate", "tool_wait", "vision_tool", "prefill",
           "batch1_cost", "decode_floor", "other"]


def curve(key):
    return CURVE.get(key, ("dense", "proxy"))


def passed(r, domain):
    return bool(r["passed"]) if domain == "traffic" else bool(r["ok"])


def cause(r, domain):
    st = r["status"]
    if domain == "traffic" and st == "input_ceiling":
        return "overflow"
    if any(c["capped"] for c in r["calls"]):
        return "capped"
    if (domain == "traffic" and st == "completed") or (domain == "drone" and st == "fail"):
        return "wrong"
    return "other"


def phases(r):
    return [(c["t0"], c["t1"], c["energy"] or 0.0) for c in r["calls"]] + \
           [(t["t0"], t["t1"], t["energy"] or 0.0) for t in r["tools"]]


def other_energy(r):
    return max(0.0, r["energy_J"] - sum(e for _, _, e in phases(r)))


def energy_after(r, t):
    """Board energy of a run after time t: phases after t, the part of a straddling phase after t, and the run's
    unattributed energy prorated by time over the traced span."""
    ph = phases(r)
    if not ph:
        return 0.0
    t_start, t_end = min(a for a, _, _ in ph), max(b for _, b, _ in ph)
    e = 0.0
    for a, b, en in ph:
        if a >= t:
            e += en
        elif b > t and b > a:
            e += en * (b - t) / (b - a)
    span = t_end - t_start
    return e + (other_energy(r) * max(0.0, t_end - t) / span if span > 0 else 0.0)


def signs(r):
    """Times of the warning signs in a run: cap1 (end of the first capped call), cap2 (end of the second of two
    consecutive capped calls), ctx80 (start of the first call whose prompt reaches 80% of the window)."""
    out = {}
    calls = r["calls"]
    for i, c in enumerate(calls):
        if c["capped"]:
            out.setdefault("cap1", c["t1"])
            if i and calls[i - 1]["capped"]:
                out.setdefault("cap2", c["t1"])
    ctx = r.get("ctx")
    if ctx:
        big = next((c for c in calls if c["prompt"] >= SIGN_CTX_FRAC * ctx), None)
        if big:
            out["ctx80"] = big["t0"]
    if "cap1" in out or "ctx80" in out:
        out["any"] = min(out.get("cap1", float("inf")), out.get("ctx80", float("inf")))
    return out


def waterfall(key):
    cfg = BY_KEY[key]
    dom = cfg.domain
    runs = load(key)
    cls, prov = curve(key)
    ratio = RATIO[cls]
    # median decode energy of a finished (uncapped) call, per role, over the configuration
    dec = defaultdict(list)
    for r in runs:
        for c in r["calls"]:
            if not c["capped"] and c["energy"]:
                dur = c["t1"] - c["t0"]
                pre = c["energy"] * min(1.0, c["ttft"] / dur) if dur > 0 else 0.0
                dec[c["role"]].append(c["energy"] - pre)
    med = {role: statistics.median(v) for role, v in dec.items() if v}

    b = defaultdict(float)
    floor8 = 0.0
    by_cause = defaultdict(lambda: {"runs": 0, "energy_J": 0.0, "after_sign_J": 0.0})
    n_pass = n_untraced_pass = 0
    for r in runs:
        E = r["energy_J"]
        if not passed(r, dom):
            cz = cause(r, dom)
            s = signs(r).get("any")
            after = energy_after(r, s) if s is not None else 0.0
            after = min(after, E)
            b["failed_after_sign"] += after
            b["failed_before_sign"] += E - after
            by_cause[cz]["runs"] += 1
            by_cause[cz]["energy_J"] += E
            by_cause[cz]["after_sign_J"] += after
            continue
        n_pass += 1
        if not r["calls"]:
            n_untraced_pass += 1
            b["other"] += E
            continue
        useful = 0.0
        for c in r["calls"]:
            en = c["energy"] or 0.0
            dur = c["t1"] - c["t0"]
            pre = en * min(1.0, c["ttft"] / dur) if dur > 0 else 0.0
            d = en - pre
            b["prefill"] += pre
            if c["capped"]:
                g = max(0.0, d - med.get(c["role"], 0.0))
                b["degenerate"] += g
                d -= g
            useful += d
        b["decode_floor"] += useful * ratio[K_HEAD]
        b["batch1_cost"] += useful * (1 - ratio[K_HEAD])
        floor8 += useful * ratio[8]
        for t in r["tools"]:
            b["vision_tool" if t["tool"] in VISION else "tool_wait"] += t["energy"] or 0.0
        b["other"] += other_energy(r)
    total = sum(r["energy_J"] for r in runs)
    S = n_pass

    # fixed stop rules: stop a run at its first sign of the given kind (a stopped run counts as a failure)
    rules = {}
    for rule in ("cap1", "cap2", "ctx80", "any"):
        saved, lost, e_lost_pass = 0.0, 0, 0.0
        for r in runs:
            s = signs(r).get(rule)
            if s is None:
                continue
            a = min(energy_after(r, s), r["energy_J"])
            saved += a
            if passed(r, dom):
                lost += 1
                e_lost_pass += a
        es = (total - saved) / (S - lost) if S - lost > 0 else None
        rules[rule] = dict(saved_J=saved, passes_lost=lost, passes_left=S - lost,
                           e_per_success_J=es,
                           change=(es / (total / S) - 1) if es and S else None)
    return dict(
        key=key, label=cfg.label, domain=dom, device=cfg.device, model=cfg.model, agent=cfg.agent,
        runs=len(runs), passes=S, untraced_passes=n_untraced_pass, total_J=total,
        e_per_success_J=total / S if S else None, curve=cls, curve_source=prov, ratio=ratio,
        buckets_J=dict(b), floor_k8_J=floor8,
        by_cause={k: dict(v) for k, v in by_cause.items()},
        stop_rules=rules,
        ctx=sorted({r.get("ctx") for r in runs if r.get("ctx")}),
    )


def fmt(res):
    t, S = res["total_J"], res["passes"]
    sh = {k: res["buckets_J"].get(k, 0.0) / t for k in BUCKETS}
    es = res["e_per_success_J"]
    best = min((v for v in res["stop_rules"].values() if v["e_per_success_J"]), key=lambda v: v["e_per_success_J"],
               default=None)
    return (f"{res['key']:20s} runs {res['runs']:4d} pass {S:4d}  E/S {es / 1e3 if es else float('nan'):8.1f} kJ  "
            + " ".join(f"{k[:6]} {100 * sh[k]:4.1f}" for k in BUCKETS)
            + (f"  best-stop {100 * best['change']:+.1f}% (-{best['passes_lost']} pass)" if best else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-parse P1's runs instead of the cache")
    ap.add_argument("--only", default="", help="comma-separated configuration keys")
    a = ap.parse_args()
    keys = [k for k in a.only.split(",") if k] or [c.key for c in CONFIGS]
    out = []
    for k in keys:
        if a.refresh:
            load(k, refresh=True)
        res = waterfall(k)
        out.append(res)
        print(fmt(res), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    meta = dict(sign_ctx_frac=SIGN_CTX_FRAC, k_head=K_HEAD, ratio=RATIO, buckets=BUCKETS,
                note="P1's final data at 0cc2311a; board energy; see analysis/waterfall.py for definitions")
    (OUT / "waterfall.json").write_text(json.dumps(dict(meta=meta, configs=out), indent=1))
    print("wrote", OUT / "waterfall.json")


if __name__ == "__main__":
    main()

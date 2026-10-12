"""Plan §6 metrics for fixed-window replay runs, on the WS (NVML energy counter, GPU only) or on a Jetson (board power,
P1's total), and the decision rules of CAP-J1, its anchor, RET-J1 and P1F-3 (planning/OPTIONS_PLAN.md §5.1-§5.4, §6;
D21). Written on 12 Oct before any of these runs had data (§6 rule 7); a rule changed later is reported as a change.

    python -m analysis.device_runs <run_dir>...                       # window metrics, one JSON per run
    python -m analysis.device_runs --rules [--out reports/2026-10-06-options/device_runs.json]

Window metrics (§6.2): the measured window runs from t_replay_start + warm to t_replay_start + horizon (WS monotonic
clock). A call straddling an edge counts with the share of its output generated inside the window, prorated by time over
its decode span (first token to last; send to last when the first token was not timed). Primary metric: J per generated
token over the window. Secondary: energy per completed session, prorated (J/token x the mean generated tokens of the
sessions completed in the window). Raw energy per completed session (window energy / sessions completed in it) is kept
only for continuity with CMP-2, biased by the sessions cut at the window's end. Sessions per hour. On a Jetson also the
active energy (window energy - idle baseline x window, §6.5), the idle baseline being the mean of the preflight idle
readings before and after the run.

Device clocks: board samples carry the unit's wall clock; a WS monotonic instant t maps to unit wall time as
t + (t_start_wall - t_start_mono) + offset, offset = the mean of the unit-minus-WS offsets measured at the run's start and
end (jsw/telemetry/jetson.py, one ssh session, round trip < 1 ms).

Completeness (§6.6): preflight passed before and after (device runs), no telemetry gap over 1 s in the window, the run
reached its window's end, SHA-256 sums present. A run that fails any of these is reported but marked incomplete.
"""
from __future__ import annotations

import argparse
import glob
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

from jsw.runner.run import gpu_energy_j
from jsw.telemetry.jetson import board_energy, load as load_samples

RUNS = Path.home() / "work/runs"
TIE = 0.02                                   # §6.4: differences under 2% are ties (D18)


def _jl(p):
    p = Path(p)
    return [json.loads(l) for l in open(p) if l.strip()] if p.exists() else []


def _overlap(a, b, t0, t1):
    if b <= a:
        return 1.0 if t0 <= a <= t1 else 0.0
    return max(0.0, min(b, t1) - max(a, t0)) / (b - a)


class Clock:
    """WS monotonic instant -> unit wall time (device runs)."""

    def __init__(self, man):
        dev = man.get("device") or {}
        offs = [dev[k]["offset_s"] for k in ("clock_offset_start", "clock_offset_end") if dev.get(k)]
        self.offset = sum(offs) / len(offs) if offs else 0.0
        self.base = man["t_start_wall"] - man["t_start_mono"]
        self.spread = (max(offs) - min(offs)) if len(offs) == 2 else None

    def unit(self, t_mono):
        return t_mono + self.base + self.offset


def _preflight(d, which):
    p = Path(d) / f"preflight_{which}" / "preflight.json"
    if not p.exists():
        return None
    j = json.loads(p.read_text())
    idle = (j["checks"].get("7_idle") or {}).get("mean_W")
    return {"ok": j["ok"], "idle_W": idle, "failed": [k for k, c in j["checks"].items() if not c["ok"]]}


def window(run_dir) -> dict:
    d = Path(run_dir)
    man = json.loads((d / "manifest.json").read_text())
    ev = _jl(d / "events.jsonl")
    calls = [c for c in _jl(d / "gw" / "calls.jsonl") if c.get("t_sent") and c.get("t_last")]
    t_rs, warm, hor = man["t_replay_start"], man.get("warm_s", 0), man["horizon_s"]
    t0, t1 = t_rs + warm, t_rs + hor
    span = t1 - t0
    out_in, prompt_in, cached_in, gen_by_sid = 0.0, 0, 0, defaultdict(int)
    for c in calls:
        o = c.get("completion_tokens") or 0
        gen_by_sid[c.get("sid")] += o
        out_in += o * _overlap(c.get("t_first") or c["t_sent"], c["t_last"], t0, t1)
        if t0 <= c["t_sent"] <= t1:
            prompt_in += c.get("prompt_tokens") or 0
            cached_in += c.get("cached_tokens") or 0
    ends = [e for e in ev if e["kind"] == "session_end"]
    done_in = [e for e in ends if e.get("status") == "completed" and t0 <= e["t_mono"] <= t1]
    device = man.get("device")
    res = {"name": d.name, "n": man.get("n"), "pool": (man.get("server_info") or {}).get("max_total_num_tokens"),
           "kv": (man.get("server_info") or {}).get("kv_cache_dtype"), "no_reuse": man["args"].get("no_reuse", False),
           "platform": "jetson" if device else "ws", "unit": (device or {}).get("unit"), "window_s": span,
           "reached_window_end": (man.get("t_replay_end") or 0) >= t1}
    if device:
        clk = Clock(man)
        e = board_energy(load_samples(str(d / "device" / "device_samples.jsonl")), clk.unit(t0), clk.unit(t1))
        E = e["energy_J"]
        pre, post = _preflight(d, "before"), _preflight(d, "after")
        idles = [x["idle_W"] for x in (pre, post) if x and x.get("idle_W")]
        idle = sum(idles) / len(idles) if idles else None
        res.update(energy_J=E, mean_W=e.get("mean_W"), telemetry_gaps=e.get("gaps"), sample_interval_s=e.get(
            "median_interval_s"), clock_offset_s=clk.offset, clock_offset_drift_s=clk.spread, idle_W=idle,
                   active_energy_J=(E - idle * span) if (E is not None and idle) else None,
                   preflight_before=pre, preflight_after=post)
        complete = bool(pre and pre["ok"] and post and post["ok"] and not e.get("gaps"))
    else:
        E = gpu_energy_j(d, t0, t1)
        res.update(energy_J=E)
        complete = True
    res["sha256"] = (d / "SHA256SUMS").exists()
    res["complete"] = complete and res["reached_window_end"] and (res["sha256"] or not device)
    gen_done = [gen_by_sid[e["sid"]] for e in done_in if gen_by_sid.get(e["sid"])]
    jtok = E / out_in if E and out_in else None
    res.update(
        out_tokens_in_window=round(out_in, 1), j_per_token=jtok,
        active_j_per_token=(res.get("active_energy_J") / out_in) if res.get("active_energy_J") and out_in else None,
        completed_in_window=len(done_in), mean_gen_tokens_completed=st.mean(gen_done) if gen_done else None,
        energy_per_completed_prorated_J=jtok * st.mean(gen_done) if jtok and gen_done else None,
        energy_per_completed_raw_J=E / len(done_in) if E and done_in else None,
        sessions_per_hour=len(done_in) / span * 3600 if span > 0 else None,
        prompt_tokens_in_window=prompt_in, cached_tokens_in_window=cached_in,
        computed_prompt_tokens_in_window=prompt_in - cached_in,
        overflowed=sum(e.get("status") == "overflow" for e in ends), cut=sum(e.get("status") == "cut" for e in ends),
        errors=sum(e.get("status") == "error" for e in ends), started=sum(e["kind"] == "session_start" for e in ev))
    met = _jl(d / "sglang_metrics.jsonl")
    retr = [r["m"].get("sglang:num_retracted_reqs") for r in met if "m" in r and t0 <= r["t_mono"] <= t1]  # scrape timeouts carry no "m"
    retr = [x for x in retr if x is not None]
    res["retracted_reqs_max"] = max(retr) if retr else None
    return res


# ----------------------------------------------------------------------------- rules

def _best(rows, kv):
    xs = [r for r in rows if r["kv"] == kv and r["j_per_token"]]
    return min(xs, key=lambda r: r["j_per_token"]) if xs else None


def capj1(points: dict[str, list[dict]]) -> dict:
    """points: unit -> window() rows of that replicate (bf16 and fp8 at N = 4, 8). Plan §5.2 rules 2-3."""
    out = {}
    for unit, rows in points.items():
        rows = [r for r in rows if r["complete"]]
        rep = {}
        for n in (4, 8):
            b = [r for r in rows if r["kv"] in ("auto", "bfloat16", None) and r["n"] == n]
            f = [r for r in rows if r["kv"] == "fp8_e5m2" and r["n"] == n]
            if b and f:
                rep[f"fp8_over_bf16_n{n}"] = f[0]["j_per_token"] / b[0]["j_per_token"]
        bb = [r for r in rows if r["kv"] in ("auto", "bfloat16", None)]
        ff = [r for r in rows if r["kv"] == "fp8_e5m2"]
        if bb and ff:
            b, f = min(bb, key=lambda r: r["j_per_token"]), min(ff, key=lambda r: r["j_per_token"])
            red = 1 - f["j_per_token"] / b["j_per_token"]
            rep.update(best_bf16=(b["name"], b["j_per_token"]), best_fp8=(f["name"], f["j_per_token"]),
                       best_vs_best_reduction=red)
        out[unit] = rep
    reds = [v["best_vs_best_reduction"] for v in out.values() if "best_vs_best_reduction" in v]
    if len(reds) == 2:
        spread_pp = abs(reds[0] - reds[1]) * 100
        lo = min(reds)
        verdict = "holds on the board" if lo >= 0.25 else "weaker on the board" if lo >= 0.10 else "absent"
        out["_rule"] = {"reductions": reds, "replicate_spread_pp": spread_pp, "verdict": verdict,
                        "noise_note": f"no effect smaller than {spread_pp:.1f} pp is claimed" if spread_pp > 10 else ""}
    elif len(reds) == 1:
        r = reds[0]
        out["_rule"] = {"reductions": reds, "verdict": ("holds on the board" if r >= 0.25 else "weaker on the board"
                                                        if r >= 0.10 else "absent") + " (single replicate)"}
    return out


def anchor(run_dir, p1_key="t_o32_granite") -> dict:
    """CAP-J1 rule 1: our N = 1 replay against P1's measured Orin 32 runs of the same sessions (matched by task,
    instance and repeat). Per-call decode rate (output tokens / decode time) median within +-10%; median LLM-call board
    energy per session (integrated over the call intervals) within +-15%."""
    from analysis import p1_repo
    d = Path(run_dir)
    man = json.loads((d / "manifest.json").read_text())
    clk = Clock(man)
    samples = load_samples(str(d / "device" / "device_samples.jsonl"))
    calls = [c for c in _jl(d / "gw" / "calls.jsonl") if c.get("t_sent") and c.get("t_last")]
    ev = _jl(d / "events.jsonl")
    sid_of = {e["sid"]: e["session"] for e in ev if e["kind"] == "session_end" and e.get("status") == "completed"}
    ours_rate, ours_e = [], defaultdict(float)
    for c in calls:
        if c.get("t_first") and c["t_last"] > c["t_first"] and (c.get("completion_tokens") or 0) > 1:
            ours_rate.append((c["completion_tokens"] - 1) / (c["t_last"] - c["t_first"]))
        if c.get("sid") in sid_of:
            ours_e[sid_of[c["sid"]]] += board_energy(samples, clk.unit(c["t_sent"]), clk.unit(c["t_last"]))["energy_J"] or 0
    p1 = {f"{p1_key}/{r['task']}/{r['instance']}/{r['rep']}": r for r in p1_repo.load(p1_key)}
    matched = [s for s in ours_e if s in p1]
    p1_rate = [c["out"] / c["decode"] for s in matched for c in p1[s]["calls"] if c["decode"] > 0 and c["out"] > 1]
    p1_e = [sum(c["energy"] or 0 for c in p1[s]["calls"]) for s in matched]
    our_e = [ours_e[s] for s in matched]
    res = {"sessions_matched": len(matched), "our_decode_rate_median": st.median(ours_rate) if ours_rate else None,
           "p1_decode_rate_median": st.median(p1_rate) if p1_rate else None,
           "our_llm_energy_per_session_median_J": st.median(our_e) if our_e else None,
           "p1_llm_energy_per_session_median_J": st.median(p1_e) if p1_e else None}
    if res["our_decode_rate_median"] and res["p1_decode_rate_median"] and our_e:
        dr = res["our_decode_rate_median"] / res["p1_decode_rate_median"] - 1
        de = res["our_llm_energy_per_session_median_J"] / res["p1_llm_energy_per_session_median_J"] - 1
        res.update(decode_rate_gap=dr, energy_gap=de, passes=abs(dr) <= 0.10 and abs(de) <= 0.15)
    return res


def retj1(default_run: dict, noreuse_run: dict) -> dict:
    """RET-J1 (plan §5.4): value of kept state = (no-reuse - default) / default in J per generated token."""
    v = noreuse_run["j_per_token"] / default_run["j_per_token"] - 1
    verdict = ("'retention gains little on P1's workloads' holds on the board" if v < 0.05 else
               "reported as measured" if v < 0.10 else "the claim is restated with the device number")
    return {"value_of_kept_state": v, "verdict": verdict,
            "computed_prompt_tokens": {"default": default_run["computed_prompt_tokens_in_window"],
                                       "no_reuse": noreuse_run["computed_prompt_tokens_in_window"]}}


def _finished(d) -> bool:
    """The run's replay ended (its manifest has t_end_mono); a point still running has no board samples yet."""
    m = Path(d) / "manifest.json"
    return m.exists() and "t_end_mono" in json.loads(m.read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="*")
    ap.add_argument("--rules", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if not a.rules:
        for r in a.runs:
            print(json.dumps(window(r), default=str))
        return
    res = {}
    cap = defaultdict(list)
    for d in sorted(glob.glob(str(RUNS / "capj1-*"))):
        if _finished(d) and "anchor" not in d and "retj1" not in d:
            w = window(d)
            cap[w["unit"]].append(w)
    res["capj1_points"] = {u: rows for u, rows in cap.items()}
    res["capj1"] = capj1(cap)
    anc = [d for d in sorted(glob.glob(str(RUNS / "capj1-*anchor*"))) if _finished(d)]
    if anc:
        res["anchor_window"] = window(anc[-1])
        res["anchor"] = anchor(anc[-1])
    ret = [d for d in sorted(glob.glob(str(RUNS / "retj1-*"))) if _finished(d)]
    if anc and ret:
        res["retj1"] = retj1(res["anchor_window"], window(ret[-1]))
    p1f3 = [window(d) for d in sorted(glob.glob(str(RUNS / "p1f3-ws-*"))) if _finished(d)]
    res["p1f3_points"] = p1f3
    res["p1f3_capacity"] = capj1({"ws": p1f3}).get("ws")
    txt = json.dumps(res, indent=1, default=str)
    if a.out:
        Path(a.out).write_text(txt)
    print(txt[:6000])


if __name__ == "__main__":
    main()

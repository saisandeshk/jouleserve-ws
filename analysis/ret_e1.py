"""RET-E1 (OPTIONS_PLAN.md §2.4): the simulator's traffic results against a live engine.

    python -m analysis.ret_e1      (WS: reads ~/work/runs/ret-e1-*; writes reports/2026-10-06-options/ret_e1.json)

Live: P1's Orin 32 granite traffic sessions replayed (jsw/workloads/replay.py) on granite-4.2-8b, one A5000, at
P1's pool size, N = 1, 4, 8 agents, SGLang's default; N = 8 with no reuse (state dropped at every wait).
Simulated: analysis/admission_sim.simulate on the same session sequence each live run drew (plan mode: the
sessions in their live start order, taken by whichever agent frees first), the same N and pool, with
- timing from today's calibration (jsw/costs/calibrate2.py): cold prefill rate; decode step = t1 * f(batch) +
  c * (total context), t1 and c fitted at batch 1 over context length, f(b) measured at 1K context;
- power measured in the live run itself (GPU power while a call runs, and while none runs, from NVML's energy
  counter like the live energy), so the comparison tests the scheduling and memory model, not the power calibration
  (as admission_sim.validate does).
Compared: energy per completed session, energy per generated token, sessions per hour, and the ranking of
default vs no reuse. Decision rule (D15): the anchor holds if live and simulated energy per completed session
agree within 15% at every point and the two policies rank the same.
"""
from __future__ import annotations

import glob
import json
import statistics as st
from pathlib import Path

import numpy as np

from analysis import p1_repo
from analysis.admission_sim import GiB, Call, Device, Mission, Workload, simulate
from analysis.sessions import REPO
from analysis.traffic_sim import TOKENS
from jsw.runner.run import gpu_energy_j, load_nvml

RUNS = REPO / "data/ws_runs"
CALIB = RUNS / "calib/granite8b_tp1_gpu0.json"
OUT = REPO / "reports/2026-10-06-options/ret_e1.json"


class CalibDevice(Device):
    """WS device: decode step = t1 * f(batch) + c * total context; f from a measured table."""

    def __init__(self, name, prefill, p_active, p_idle, t1, ctx_s, ftable):
        super().__init__(name, prefill, p_active, p_idle, "calib")
        self.t1, self.ctx_s, self.ftable = t1, ctx_s, ftable

    def step(self, b, ctx_sum):
        if b <= 0:
            return 0.0
        bs = self.ftable
        f = bs[-1][1] + (bs[-1][1] - bs[-2][1]) * (b - bs[-1][0]) / (bs[-1][0] - bs[-2][0])
        for (b0, f0), (b1, f1) in zip(bs, bs[1:]):
            if b <= b1:
                f = f0 + (f1 - f0) * (b - b0) / (b1 - b0)
                break
        return self.t1 * max(1.0, f) + self.ctx_s * ctx_sum


def device_from_calibration(p_active, p_idle):
    c = json.loads(CALIB.read_text())
    pre = st.median(r["tok_s"] for r in c["prefill"] if r["L"] >= 4000)
    one = sorted((r["L"], r["step_s"]) for r in c["decode"] if r["batch"] == 1)
    A = np.array([[1.0, L] for L, _ in one])
    t1, ctx_s = np.linalg.lstsq(A, np.array([s for _, s in one]), rcond=None)[0]
    L0 = min(r["L"] for r in c["decode"])
    ft = sorted((r["batch"], (r["step_s"] - ctx_s * r["batch"] * L0) / t1) for r in c["decode"] if r["L"] == L0)
    return CalibDevice("A5000 granite-4.2-8b (calibrated)", pre, p_active, p_idle, float(t1), max(0.0, float(ctx_s)),
                       ft), dict(prefill_tok_s=pre, t1_ms=t1 * 1e3, ctx_us_per_token=ctx_s * 1e6,
                                 f_table=ft, idle_w_calib=c["idle_w"])


def live(run_dir):
    d = Path(run_dir)
    man = json.loads((d / "manifest.json").read_text())
    ev = [json.loads(l) for l in open(d / "events.jsonl")]
    calls = [json.loads(l) for l in open(d / "gw" / "calls.jsonl")] if (d / "gw" / "calls.jsonl").exists() else []
    t0 = man.get("t_replay_start") or man["t_start_mono"]
    t1 = man.get("t_replay_end") or man["t_end_mono"]
    E = gpu_energy_j(d, t0, t1)
    ends = [e for e in ev if e["kind"] == "session_end"]
    done = [e for e in ends if e["status"] == "completed"]
    starts = [e for e in ev if e["kind"] == "session_start"]
    # power while a call runs vs none (NVML samples against the gateway's call windows)
    wins = sorted((c["t_sent"], c["t_last"]) for c in calls if c.get("t_sent") and c.get("t_last"))
    rows = [r for r in load_nvml(d) if t0 <= r["t_mono"] <= t1]

    def busy(t):
        lo, hi = 0, len(wins)
        while lo < hi:
            mid = (lo + hi) // 2
            if wins[mid][0] <= t:
                lo = mid + 1
            else:
                hi = mid
        return any(a <= t <= b for a, b in wins[max(0, lo - 64):lo])
    # power from NVML's energy counter (the source of every energy here), per sample interval: on the A5000s the
    # power reading runs above the counter's average (24% under load in CAP-E1), which would bias the simulator
    pb, pi = [], []
    for x, y in zip(rows, rows[1:]):
        dt = y["t_mono"] - x["t_mono"]
        if dt > 0:
            (pb if busy((x["t_mono"] + y["t_mono"]) / 2) else pi).append((y["energy_mj"] - x["energy_mj"]) / 1e3 / dt)
    pr = [r["power_w"] for r in rows]
    out_tok = sum(c.get("completion_tokens") or 0 for c in calls)
    prompt_tok = sum(c.get("prompt_tokens") or 0 for c in calls)
    cached = sum(c.get("cached_tokens") or 0 for c in calls)
    hits = sum((c.get("cached_tokens") or 0) > 0 for c in calls)
    return dict(name=d.name, n=man["args"]["n"], no_reuse=man["args"].get("no_reuse", False),
                pool=(man.get("server_info") or {}).get("max_total_num_tokens"), span_s=t1 - t0, energy_j=E,
                sessions_started=len(starts), completed=len(done), cut=sum(e["status"] == "cut" for e in ends),
                overflow=sum(e["status"] == "overflow" for e in ends), errors=sum(e["status"] == "error" for e in ends),
                energy_per_completed_j=E / len(done) if done else None,
                energy_per_out_token_j=E / out_tok if out_tok else None,
                sessions_per_hour=len(done) / (t1 - t0) * 3600, cache_share=cached / prompt_tok if prompt_tok else None,
                calls=len(calls), calls_with_cache_hit=hits,
                session_s_median=st.median(e["s"] for e in done) if done else None,
                p_call_w=st.mean(pb) if pb else None, p_idle_w=st.mean(pi) if pi else None,
                busy_share=len(pb) / max(1, len(pb) + len(pi)), p_reading_mean_w=st.mean(pr) if pr else None,
                p_counter_mean_w=E / (t1 - t0) if E else None,
                plan=[e["session"] for e in sorted(starts, key=lambda e: e["t_mono"])], out_tokens=out_tok)


def sim_for(lv, dev, sessions, cut=False):
    by_id = {s["id"]: s for s in sessions}
    ms = []
    for sid in lv["plan"]:
        s = by_id[sid]
        steps = s["steps"]
        ms.append(Mission(sid, [Call(x["prompt"], 0, x["out"]) for x in steps], [x["wait_s"] for x in steps[:-1]],
                          [x.get("tool") for x in steps[:-1]], bool(s.get("ok"))))
    wl = Workload("o32 granite (live plan)", ms, 0, 8000)
    r = simulate(wl, dev, TOKENS, lv["pool"] / GiB, lv["n"], "drop" if lv["no_reuse"] else "default",
                 plan=list(wl.missions), stagger=2.0, plan_horizon=lv["span_s"] if cut else None)
    # cut: stop at the live run's span and count what finished by then (the live run cuts its last sessions);
    # else every started session runs to its end
    out_tok = sum(x["out"] for sid in lv["plan"] for x in by_id[sid]["steps"]) if not cut else None
    return dict(energy_j=r["energy_j"], energy_per_session_j=r["energy_per_mission_j"],
                energy_per_out_token_j=r["energy_j"] / out_tok if out_tok else None,
                completed=r["missions"], sessions_per_hour=r["missions_per_hour"],
                span_s=r["span_s"], reprefill_tok=r["reprefill_tok"], retract_tok=r["retract_tok"])


def main():
    sessions = [json.loads(l) for l in open(REPO / "data/replay/t_o32_granite.jsonl")]
    lives = [live(d) for d in sorted(glob.glob(str(RUNS / "ret-e1-o32granite-*")))
             if (Path(d) / "manifest.json").exists() and "t_end_mono" in json.loads((Path(d) / "manifest.json").read_text())]
    res = {"live": [], "device": None}
    for lv in lives:
        dev, info = device_from_calibration(lv["p_call_w"], lv["p_idle_w"])
        res["device"] = info
        sm = sim_for(lv, dev, sessions)
        row = {k: v for k, v in lv.items() if k != "plan"}
        row["sim"] = sm
        row["sim_cut"] = sim_for(lv, dev, sessions, cut=True)      # same span as live: the rule's basis
        row["sim_cut_vs_live_energy_per_session"] = (row["sim_cut"]["energy_per_session_j"] /
                                                     lv["energy_per_completed_j"] - 1) if lv["energy_per_completed_j"] else None
        row["sim_vs_live_energy_per_session"] = (sm["energy_per_session_j"] / lv["energy_per_completed_j"] - 1) \
            if lv["energy_per_completed_j"] else None
        row["sim_vs_live_energy_per_token"] = (sm["energy_per_out_token_j"] / lv["energy_per_out_token_j"] - 1) \
            if lv["energy_per_out_token_j"] else None
        res["live"].append(row)
        print(f"{lv['name']:34s} n={lv['n']} sessions {lv['completed']:3d} (+{lv['cut']} cut) "
              f"E/session live {lv['energy_per_completed_j'] or 0:8.0f} sim {sm['energy_per_session_j']:8.0f} J "
              f"| J/token live {lv['energy_per_out_token_j'] or 0:.3f} sim {sm['energy_per_out_token_j']:.3f} "
              f"| cache {lv['cache_share'] or 0:.0%} | P call/idle {lv['p_call_w'] or 0:.0f}/{lv['p_idle_w'] or 0:.0f} W "
              f"| same span: sim {row['sim_cut']['energy_per_session_j']:8.0f} J, {row['sim_cut']['completed']} sessions")
    # D15 rule: within 15% at every point (same span as live), and default vs no reuse rank the same at N = 8
    rows = res["live"]
    gaps = [r["sim_cut_vs_live_energy_per_session"] for r in rows if r["sim_cut_vs_live_energy_per_session"] is not None]
    rank = None
    d8 = next((r for r in rows if r["n"] == 8 and not r["no_reuse"]), None)
    r8 = next((r for r in rows if r["n"] == 8 and r["no_reuse"]), None)
    if d8 and r8 and d8["energy_per_completed_j"] and r8["energy_per_completed_j"]:
        # order of no reuse vs default: +1 no reuse costs more, -1 less, 0 a tie (within 2%, one run per cell)
        def order(x):
            return 0 if abs(x) < 0.02 else (1 if x > 0 else -1)
        lv_d = float(r8["energy_per_completed_j"] / d8["energy_per_completed_j"] - 1)
        sm_d = float(r8["sim_cut"]["energy_per_session_j"] / d8["sim_cut"]["energy_per_session_j"] - 1)
        rank = dict(live_noreuse_vs_default=lv_d, sim_noreuse_vs_default=sm_d, live_order=order(lv_d),
                    sim_order=order(sm_d), same=order(lv_d) == order(sm_d),
                    default_cache_hits_n8=f"{d8['calls_with_cache_hit']}/{d8['calls']}",
                    degenerate=d8["calls_with_cache_hit"] == 0)
    res["rule"] = dict(points=len(gaps), max_abs_gap=float(max(map(abs, gaps))) if gaps else None, ranking=rank,
                       met=bool(gaps) and max(map(abs, gaps)) <= 0.15 and bool(rank and rank["same"]))
    # out of sample: the FP8-KV run of CAP-E1 (same traffic, 8 agents, twice the pool), same device model
    fp8 = RUNS / "cap-e1-o32granite-n8-fp8kv"
    if (fp8 / "manifest.json").exists():
        lv = live(fp8)
        dev, _ = device_from_calibration(lv["p_call_w"], lv["p_idle_w"])
        sc = sim_for(lv, dev, sessions, cut=True)
        res["fp8_check"] = dict(pool=lv["pool"], completed=lv["completed"], cut=lv["cut"],
                                live_energy_per_completed_j=lv["energy_per_completed_j"],
                                sim_cut_energy_per_session_j=sc["energy_per_session_j"], sim_cut_completed=sc["completed"],
                                gap=sc["energy_per_session_j"] / lv["energy_per_completed_j"] - 1,
                                calls_with_cache_hit=f"{lv['calls_with_cache_hit']}/{lv['calls']}")
    print(json.dumps({k: res.get(k) for k in ("rule", "fp8_check")}, indent=1, default=str))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()

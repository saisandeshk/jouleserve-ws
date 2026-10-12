"""P1F-3 (planning/OPTIONS_PLAN.md §5.1): RET-E1 and CAP-E1 redone on P1's clean Orin 32 granite sessions (P1F-2).
Written on 12 Oct before the runs' data existed (plan §6 rule 7).

    python -m analysis.p1f3      (WS; reads ~/work/runs/p1f3-ws-*; writes reports/2026-10-06-options/p1f3.json)

Points: bf16 at 25,358 tokens (N = 1, 4, 8; GPU0), FP8 KV at 50,716 (N = 4, 8; GPU1); 10-minute warm-up, 60-minute
window, the agent's window held at 25,358.
- Plan §6 metrics per point (analysis/device_runs.window): J per generated token over the window first, energy per
  completed session prorated, raw per session (biased), sessions per hour.
- FP8 against bf16 at N = 4, 8 and best against best: the WS side of CAP-J1's platform link (plan §5.2 rule 4).
- The simulator anchor, by RET-E1's method (analysis/ret_e1: the simulator replays each live run's session order on
  the 6 Oct WS calibration, with the live run's own call and idle power): it holds if live and simulated energy agree
  within +-15% per completed session (same span as live, RET-E1's rule) and within +-10% per generated token, at
  every point.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

from analysis.device_runs import capj1, window
from analysis.ret_e1 import device_from_calibration, live, sim_for
from analysis.sessions import REPO

RUNS = Path.home() / "work/runs"
OUT = REPO / "reports/2026-10-06-options/p1f3.json"


def main():
    sessions = [json.loads(l) for l in open(REPO / "data/replay/t_o32_granite.jsonl")]
    rows = []
    for d in sorted(glob.glob(str(RUNS / "p1f3-ws-*"))):
        m = Path(d) / "manifest.json"
        if not (m.exists() and "t_end_mono" in json.loads(m.read_text())):
            continue
        w = window(d)
        lv = live(d)
        dev, info = device_from_calibration(lv["p_call_w"], lv["p_idle_w"])
        sm, sc = sim_for(lv, dev, sessions), sim_for(lv, dev, sessions, cut=True)
        w["sim"] = {"per_session_gap": sc["energy_per_session_j"] / lv["energy_per_completed_j"] - 1
                    if lv["energy_per_completed_j"] else None,
                    "per_token_gap": sm["energy_per_out_token_j"] / lv["energy_per_out_token_j"] - 1
                    if lv["energy_per_out_token_j"] else None,
                    "live_completed": lv["completed"], "sim_cut_completed": sc["completed"],
                    "calls_with_cache_hit": f"{lv['calls_with_cache_hit']}/{lv['calls']}"}
        rows.append(w)
        print(f"{w['name']:40s} n={w['n']} kv={w['kv']} pool={w['pool']} J/tok {w['j_per_token'] or 0:.3f} "
              f"done {w['completed_in_window']} | sim gap/session {w['sim']['per_session_gap'] or 0:+.1%} "
              f"/token {w['sim']['per_token_gap'] or 0:+.1%}")
    res = {"points": rows, "capacity": capj1({"ws": rows}).get("ws")}
    ps = [r["sim"]["per_session_gap"] for r in rows if r["sim"]["per_session_gap"] is not None]
    pt = [r["sim"]["per_token_gap"] for r in rows if r["sim"]["per_token_gap"] is not None]
    res["sim_rule"] = {"points": len(rows), "max_abs_per_session": max(map(abs, ps)) if ps else None,
                       "max_abs_per_token": max(map(abs, pt)) if pt else None,
                       "holds": bool(ps and pt) and max(map(abs, ps)) <= 0.15 and max(map(abs, pt)) <= 0.10}
    OUT.write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: res[k] for k in ("capacity", "sim_rule")}, indent=1, default=str))


if __name__ == "__main__":
    main()

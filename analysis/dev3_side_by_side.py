"""DEV-3 check (planning/OPTIONS_PLAN.md §4.1): our Jetson sampler against P1's own, side by side on one unit.

    python -m analysis.dev3_side_by_side <ours: device_samples.jsonl> <P1's DeviceSampler output .jsonl> [--t0 W --t1 W]

P1's drone-harness sampler (a scratch copy of its samplers.py, run unmodified) records the rails but no total; its
total is rebuilt the way P1's traffic vitals define it (Orin: VDD_GPU_SOC + VDD_CPU_CV + VIN_SYS_5V0; Thor: VIN).
Both files are integrated by the same trapezoid rule over the common window (both carry the unit's wall clock).
Done when the energies agree within 1% and our median interval is 200 ms +- 10%.
"""
from __future__ import annotations

import argparse
import json

from jsw.telemetry.jetson import ORIN_TOTAL, board_energy, load


def p1_rows(path):
    rows = []
    for r in load(path):
        rails = {k[len("power_"):-len("_mW")]: v for k, v in r.items() if k.startswith("power_") and k.endswith("_mW")}
        if all(k in rails for k in ORIN_TOTAL):
            tot = sum(rails[k] for k in ORIN_TOTAL)
        elif "VIN" in rails:
            tot = rails["VIN"]
        else:
            continue
        rows.append({"t_wall": r["t_wall"], "power_total_mw": tot})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ours")
    ap.add_argument("p1")
    ap.add_argument("--t0", type=float)
    ap.add_argument("--t1", type=float)
    a = ap.parse_args()
    ours, p1 = load(a.ours), p1_rows(a.p1)
    t0 = max(ours[0]["t_wall"], p1[0]["t_wall"], a.t0 or 0)
    t1 = min(ours[-1]["t_wall"], p1[-1]["t_wall"], a.t1 or 1e18)
    eo, ep = board_energy(ours, t0, t1), board_energy(p1, t0, t1)
    gap = eo["energy_J"] / ep["energy_J"] - 1
    print(json.dumps({"window_s": t1 - t0, "ours_J": eo["energy_J"], "p1_J": ep["energy_J"], "gap": gap,
                      "ours_median_interval_s": eo["median_interval_s"], "p1_median_interval_s": ep["median_interval_s"],
                      "ours_gaps": eo["gaps"], "passes": abs(gap) <= 0.01 and abs(eo["median_interval_s"] - 0.2) <= 0.02},
                     indent=1))


if __name__ == "__main__":
    main()

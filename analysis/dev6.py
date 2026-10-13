"""DEV-6 (planning/OPTIONS_PLAN.md §4.1): are the three Orin 32s interchangeable? Written on 13 Oct before Orin-32-1's
and Orin-32-2's DEV-6 data was read (plan §6 rule 7; Orin-32-3's was read on 12 Oct).

    python -m analysis.dev6        (WS; reads ~/work/runs/dev6-*/; writes reports/2026-10-06-options/device/dev6.json)

Per unit (the latest dev6-<tag>-* run of each): the preflight's 10-minute idle power (board, P1's power field, with
the server loaded), and calibrate2's decode J/token and tokens/s per (context, batch) cell, median over repeats.
Rule (fixed in plan §4.1): the units are interchangeable if idle power and decode J/token agree within ±3%, read here
as every unit within ±3% of the units' mean, for idle power and for each decode cell measured on every unit. Else
comparisons stay within one unit.
"""
from __future__ import annotations

import glob
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

from analysis.device_runs import _preflight
from analysis.sessions import REPO

RUNS = Path.home() / "work/runs"
OUT = REPO / "reports/2026-10-06-options/device/dev6.json"
TOL = 0.03


def unit_summary(d: Path) -> dict:
    c = json.loads((d / "calib.json").read_text())
    cells = defaultdict(list)
    for r in c["decode"]:
        cells[(r["L"], r["batch"])].append(r)
    pre = _preflight(d, "before") or {}
    return {"run": d.name, "unit": c["device"]["unit"], "idle_W": pre.get("idle_W"), "preflight_before_ok": pre.get("ok"),
            "preflight_after": _preflight(d, "after"), "calib_idle_W": c.get("idle_w"),
            "decode": {f"L{L}_b{b}": {"j_per_tok": st.median(r["j_per_tok"] for r in rs),
                                      "tok_s": st.median(r["tok_s"] for r in rs), "reps": len(rs),
                                      "gaps": sum(len(r.get("gaps") or []) for r in rs)}
                       for (L, b), rs in sorted(cells.items())}}


def spread(vals: dict) -> dict:
    m = st.mean(vals.values())
    dev = {u: v / m - 1 for u, v in vals.items()}
    return {"mean": m, "dev": dev, "max_abs_dev": max(map(abs, dev.values())),
            "within": max(map(abs, dev.values())) <= TOL}


def main():
    latest = {}
    for d in sorted(glob.glob(str(RUNS / "dev6-*"))):
        if (Path(d) / "calib.json").exists():
            latest[Path(d).name.split("-")[1]] = Path(d)
    units = [unit_summary(d) for d in latest.values()]
    res = {"units": units, "checks": {}}
    if len(units) >= 2:
        res["checks"]["idle_W"] = spread({u["unit"]: u["idle_W"] for u in units if u["idle_W"]})
        common = set.intersection(*(set(u["decode"]) for u in units))
        for k in sorted(common):
            res["checks"][f"decode_{k}_j_per_tok"] = spread({u["unit"]: u["decode"][k]["j_per_tok"] for u in units})
        res["interchangeable"] = all(v["within"] for v in res["checks"].values())
        res["verdict"] = ("interchangeable (within ±3%)" if res["interchangeable"]
                          else "not interchangeable: comparisons stay within one unit")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, default=str))
    for u in units:
        print(u["unit"], u["run"], "idle", round(u["idle_W"] or 0, 2),
              {k: (round(v["j_per_tok"], 3), round(v["tok_s"], 2)) for k, v in u["decode"].items()})
    for k, v in res["checks"].items():
        print(k, "mean", round(v["mean"], 3), "max |dev|", f"{v['max_abs_dev']:.1%}", "within" if v["within"] else "OUT")
    print("verdict:", res.get("verdict"))


if __name__ == "__main__":
    main()

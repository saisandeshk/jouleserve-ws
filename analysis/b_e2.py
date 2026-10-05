"""B-E2 (OPTIONS_PLAN.md §2.4): the step-wise projections redone with P1's own model's step sizes.

    python -m analysis.b_e2      (WS: reads B-E1's runs; writes reports/2026-10-06-options/b_e2.json)

The 2026-10-03 projection (analysis/admission_figures.paradigm_compare) applied the Thor's gemma-26B rates and
board power to the token counts and real-time flights of step-wise missions run with Qwen3.5-9B and
K2-Horizon-7B, and compared them with P1's Reflexion measured on D1-D3. Here the same projection uses B-E1's
gemma-4-E4B missions (P1's weights), at two device prices:
- Thor, gemma-26B rates (the 2026-10-03 projection, so the numbers line up with its table);
- Orin 32, gemma-E4B rates fitted on P1's own E4B traffic calls (analysis/traffic_sim.fit), the device P1 runs
  this model on.
Success is reported both ways (delivered and returned; the strict delivery check).
"""
from __future__ import annotations

import json
import statistics as st

from analysis.admission_figures import _strict_pass, paradigm_compare
from analysis.admission_sim import load_aerogen_runs, thor_device
from analysis.sessions import REPO
from analysis.traffic_sim import fit

OUT = REPO / "reports/2026-10-06-options/b_e2.json"
ARMS = {"e4b_greedy": ["b-e1-e4b-think-greedy-d1", "b-e1-e4b-think-greedy-d23"],
        "e4b_sampled": ["b-e1-e4b-think-sampled-d1", "b-e1-e4b-think-sampled-d23"]}


def project(w, dev, tag):
    ms = [m for m in w.missions if tag in m.mid]
    es, ts = [], []
    for m in ms:
        llm = 0.0
        for i, c in enumerate(m.calls):
            pf = c.prompt - (max(w.shared, c.cached) if i else w.shared)
            llm += max(0, pf) / dev.prefill + c.out * dev.step(1, w.shared + c.prompt + c.out / 2)
        tot = llm + sum(m.waits)
        es.append(dev.p_active * llm + dev.p_idle * (tot - llm))
        ts.append(tot)
    ok = sum(m.success for m in ms)
    strict = sum(_strict_pass(m.mid) for m in ms)
    return dict(missions=len(ms), succeeded=ok, succeeded_strict=strict,
                kj_per_mission=st.mean(es) / 1e3 if es else None,
                kj_per_success=(sum(es) / ok / 1e3) if ok else None,
                kj_per_strict_success=(sum(es) / strict / 1e3) if strict else None,
                minutes_median=st.median(ts) / 60 if ts else None,
                llm_minutes_median=st.median(e for e in ts) / 60 if ts else None)


def main():
    devices = {"thor_gemma26b": thor_device(), "orin32_e4b": fit("t_o32_e4b")[0]}
    res = {"devices": {k: dict(prefill=d.prefill, p_active=d.p_active, p_idle=d.p_idle) for k, d in devices.items()},
           "stepwise_e4b_projected": {}}
    for arm, runs in ARMS.items():
        w = load_aerogen_runs(f"Step-wise, gemma-4-E4B ({arm})", runs, 32768)
        for dname, dev in devices.items():
            for tag, label in (("-d1/", "D1"), ("-d23/", "D2+D3")):
                res["stepwise_e4b_projected"][f"{arm} {label} @ {dname}"] = project(w, dev, tag)
    ref = paradigm_compare()                   # P1's Reflexion measured, and the 2026-10-03 step-wise projections
    res["p1_reflexion_measured"] = ref["p1_reflexion_measured"]
    res["stepwise_projected_2026_10_03"] = ref["stepwise_projected"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, default=str))
    for k, v in res["stepwise_e4b_projected"].items():
        print(f"{k:40s}", {x: (round(y, 1) if isinstance(y, float) else y) for x, y in v.items()})
    for k, v in res["p1_reflexion_measured"].items():
        print("P1 Reflexion", k, {x: (round(y, 1) if isinstance(y, float) else y) for x, y in v.items()})


if __name__ == "__main__":
    main()

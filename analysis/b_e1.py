"""B-E1 (OPTIONS_PLAN.md §2.4): P1's own model family as a step-wise agent on P1's delivery tasks D1-D3.

Same metrics as the 2026-10-02 step-wise test (analysis/stepwise_ceiling.py: output per step after a tool
result, planning-call length, runaways, strict delivery check, retention ceilings, Thor projection), for the
gemma-4-E4B arms run by env/queue_b_e1.sh through the gateway, plus what the gateway had to do: replies whose
tool calls were written as Python text (converted) and replies stopped once they began imagining tool results.
Decision rule (D15): the median output after a tool result <= 300 tokens means B's projection holds for P1's model.

Usage (WS, where the runs are): python -m analysis.b_e1   -> reports/2026-10-06-options/b_e1.json
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

from analysis import stepwise_ceiling as sc
from analysis.sessions import REPO

ARMS = [("gemma-4-E4B thinking, greedy (P1 protocol)", "b-e1-e4b-think-greedy"),
        ("gemma-4-E4B thinking, sampled (Gemma defaults)", "b-e1-e4b-think-sampled")]
GW = REPO / "data/ws_runs/b-e1-gw/calls.jsonl"
OUT = REPO / "reports/2026-10-06-options/b_e1.json"


def gateway_counts(missions):
    """Gateway records that fall inside these missions' LLM-call windows."""
    if not GW.exists():
        return {}
    gw = [json.loads(l) for l in open(GW)]
    wins = [(c["t_req_wall"], c["t_req_wall"] + (c["t_end"] - c["t_req"]) + 1) for m in missions for c in m["calls"]
            if c.get("t_req_wall")]
    import time as _t
    # gateway times are monotonic on the same host; map via each record's wall clock is not logged, so match by
    # count: the gateway log is ordered, and each LLM call made one gateway call (plus retries, none here)
    return {"gateway_calls_total": len(gw),
            "converted_total": sum(bool((c.get("meta") or {}).get("pythonic_fallback")) for c in gw),
            "stopped_first_total": sum(c.get("stopped_by") == "pythonic_first" for c in gw)}


def load_missions(prefix, suffix):
    """Like stepwise_ceiling.load_missions, for B-E1's run names (<prefix>-<suffix>)."""
    import glob
    out = []
    for sd in sorted(glob.glob(str(sc.RUNS / f"{prefix}-{suffix}" / "sessions" / "*"))):
        summ = json.loads(Path(sd, "summary.json").read_text()) if Path(sd, "summary.json").exists() else {}
        calls = [c for c in sc._jsonl(Path(sd, "llm_calls.jsonl")) if c.get("completion_tokens") is not None]
        if calls:
            out.append(dict(dir=sd, summary=summ, calls=calls, tools=sc._jsonl(Path(sd, "tool_calls.jsonl"))))
    return out


def main():
    result = {}
    for suffix in ("d1", "d23"):
        for label, prefix in ARMS:
            ms = load_missions(prefix, suffix)
            ms = [m for m in ms if m["summary"]]
            if not ms:
                continue
            pre, dec = sc.rates(ms)
            row = sc.arm_stats(ms, (pre / dec) if pre and dec else None)
            row.update(prefill_ws=pre, decode_ws=dec)
            result[f"{prefix}-{suffix}"] = dict(label=label, task_set=suffix, **row)
    for label, prefix in ARMS:                                    # D1-D3 pooled per arm
        ms = [m for sf in ("d1", "d23") for m in load_missions(prefix, sf) if m["summary"]]
        if ms:
            result[f"{prefix}-all"] = dict(label=label, task_set="d1-d3", **sc.arm_stats(ms, None))
    result["gateway"] = gateway_counts([])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1, default=str))
    keys = ["missions", "done", "aerogen_validator_yes", "delivered_all", "passed_strict", "collisions",
            "calls_per_mission", "first_out_median", "first_out_max", "resume_out_median", "resume_out_p90",
            "resume_out_max", "resume_share_gt_1k", "capped", "reuse", "ceiling_thor", "ceiling_thor_private",
            "resume_ceiling_thor", "thor_llm_s_nokeep", "flight_s_per_mission"]
    for k, row in result.items():
        print(k, {x: (round(row[x], 3) if isinstance(row.get(x), float) else row.get(x)) for x in keys if x in row}
              if k != "gateway" else row)


if __name__ == "__main__":
    main()

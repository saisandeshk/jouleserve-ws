"""CAP-E1 (OPTIONS_PLAN.md §2.4): does an FP8 KV cache cost quality on these agents, and what does its capacity buy live?

    python -m analysis.cap_e1      (WS; writes reports/2026-10-06-options/cap_e1.json)

Pairs, same workload and settings, bf16 KV against fp8_e5m2 KV (the FP8 type Ampere has):
- capacity: P1's Orin 32 granite traffic replayed by 8 agents on granite-4.2-8b (RET-E1's bf16 run vs CAP-E1's
  FP8 run): pool size, energy per completed session, sessions per hour, cache share;
- quality, A-E1's pilot prompts on gemma-4-E4B, greedy: finish rate, loops, valid programs, output tokens;
- quality, B-E1's D1 missions on gemma-4-E4B, greedy: strict pass, delivered, output after a tool result.
Decision rule (D15): no measurable degradation means capacity is a free configuration (a finding for P1, CAP
weakens as research); degradation means a run-time trade-off exists.
"""
from __future__ import annotations

import json
from pathlib import Path

from analysis import a_e1, b_e1
from analysis import stepwise_ceiling as sc
from analysis.ret_e1 import live
from analysis.sessions import REPO

RUNS = REPO / "data/ws_runs"
OUT = REPO / "reports/2026-10-06-options/cap_e1.json"


def done(d):
    m = Path(d) / "manifest.json"
    return m.exists() and "t_end_mono" in json.loads(m.read_text())


def server_failed(d):
    """The run finished but its server never answered (Gemma-4 with FP8 KV does not start on our A5000s in SGLang 0.5.20)."""
    m = json.loads((Path(d) / "manifest.json").read_text())
    return "error" in (m.get("server_info") or {})


def main():
    res = {}
    pairs = {"bf16": RUNS / "ret-e1-o32granite-n8-default", "fp8": RUNS / "cap-e1-o32granite-n8-fp8kv"}
    cap = {}
    for k, d in pairs.items():
        if done(d):
            lv = live(d)
            cap[k] = {x: lv[x] for x in ("pool", "completed", "cut", "errors", "energy_per_completed_j",
                                         "energy_per_out_token_j", "sessions_per_hour", "cache_share", "session_s_median",
                                         "p_call_w", "p_idle_w")}
    if len(cap) == 2 and cap["bf16"]["energy_per_completed_j"]:
        cap["fp8_vs_bf16_energy_per_session"] = cap["fp8"]["energy_per_completed_j"] / cap["bf16"]["energy_per_completed_j"] - 1
        cap["fp8_vs_bf16_sessions_per_hour"] = cap["fp8"]["sessions_per_hour"] / cap["bf16"]["sessions_per_hour"] - 1
    res["capacity_granite_n8"] = cap
    api = a_e1.known_api(REPO / "data/a_e1/prompts.jsonl")
    q = {}
    for k, d in {"bf16": RUNS / "a-e1-pilot-e4b-greedy", "fp8": RUNS / "cap-e1-e4b-fp8kv-controls"}.items():
        if done(d) and server_failed(d):
            q[k] = "not run: the server did not start (Gemma-4 FP8 KV on our A5000s, SGLang 0.5.20)"
        elif done(d):
            s = a_e1.summarize([d], REPO / "data/a_e1/prompts.jsonl")
            q[k] = {c.split("|", 1)[1]: {x: v[x] for x in ("n", "loops", "finish_rate", "program_valid", "generator_finished",
                                                           "tokens_median")} for c, v in s["cells"].items()}
    res["quality_e4b_a_e1_prompts"] = q
    m = {}
    for k, (prefix, suffix) in {"bf16": ("b-e1-e4b-think-greedy", "d1"),
                                "fp8": ("cap-e1-e4b-fp8kv-think-greedy", "d1")}.items():
        ms = [x for x in b_e1.load_missions(prefix, suffix) if x["summary"]]
        if ms:
            st = sc.arm_stats(ms, None)
            m[k] = {x: st[x] for x in ("missions", "delivered_all", "passed_strict", "collisions", "resume_out_median",
                                       "resume_out_p90", "first_out_median", "capped")}
    res["quality_e4b_d1"] = m
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str)[:4000])


if __name__ == "__main__":
    main()

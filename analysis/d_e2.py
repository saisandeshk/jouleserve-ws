"""D-E2 (OPTIONS_PLAN.md §2.4): is the vision burst worth more than 0.6% with several agents?

    python -m analysis.d_e2      (WS: ~/work/runs/d-e2-*; writes reports/2026-10-06-options/d_e2.json)

For every run of env/queue_d_e2.sh (P1's Orin 32 E4B traffic sessions with ask_vlm bursts, replayed on gemma-4-E4B
with real concurrent burst requests; pools 12,415 and ~63.5K tokens; N = 1, 4; policies default, pin, admit4,
both): energy per completed session (GPU energy over the replay window / completed sessions); for every agent
call that follows a burst, how much of the expected cached prefix (the previous prompt) it had to recompute;
the bursts' own duration (admission slows the tool); session time; and the ranking against the default.
Decision rule (D15): D's live case is small if the best policy stays within 5% of the default at 4 agents.
"""
from __future__ import annotations

import glob
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

from analysis.sessions import REPO
from jsw.runner.run import gpu_energy_j

RUNS = REPO / "data/ws_runs"
OUT = REPO / "reports/2026-10-06-options/d_e2.json"


def one(d):
    d = Path(d)
    man = json.loads((d / "manifest.json").read_text())
    if "t_end_mono" not in man:
        return None
    ev = [json.loads(l) for l in open(d / "events.jsonl")]
    calls = [json.loads(l) for l in open(d / "gw" / "calls.jsonl")]
    t0, t1 = man.get("t_replay_start") or man["t_start_mono"], man.get("t_replay_end") or man["t_end_mono"]
    E = gpu_energy_j(d, t0, t1)
    done = [e for e in ev if e["kind"] == "session_end" and e["status"] == "completed"]
    bursts = [e for e in ev if e["kind"] == "burst"]
    # the agent call right after each burst: compare its cached tokens with the previous agent prompt
    by_sid = defaultdict(list)
    for c in calls:
        by_sid[c["sid"]].append(c)
    after, miss_tok, exp_tok = 0, 0, 0
    burst_sids = {(b["sid"], b["step"]) for b in bursts}
    for sid, cs in by_sid.items():
        ag = sorted([c for c in cs if c["tag"] == "agent"], key=lambda c: c["t_req"])
        for i in range(1, len(ag)):
            if (sid, i - 1) in burst_sids:
                after += 1
                exp = ag[i - 1]["prompt_tokens"] or 0
                got = min(exp, ag[i]["cached_tokens"] or 0)
                exp_tok += exp
                miss_tok += exp - got
    agent = [c for c in calls if c["tag"] == "agent"]
    tool = [c for c in calls if c["tag"] == "tool"]
    return dict(name=d.name, n=man["args"]["n"], pool=(man.get("server_info") or {}).get("max_total_num_tokens"),
                policy=d.name.rsplit("-", 1)[1], span_s=t1 - t0, energy_j=E, completed=len(done),
                energy_per_completed_j=E / len(done) if done else None,
                bursts=len(bursts), burst_s_median=st.median(b["s"] for b in bursts) if bursts else None,
                calls_after_burst=after, prefix_recomputed_share=miss_tok / exp_tok if exp_tok else None,
                recomputed_tokens=miss_tok,
                agent_cache_share=sum(c["cached_tokens"] or 0 for c in agent) / max(1, sum(c["prompt_tokens"] or 0 for c in agent)),
                tool_held=sum(bool((c.get("meta") or {}).get("admitted_after_wait")) for c in tool),
                session_s_median=st.median(e["s"] for e in done) if done else None)


def main():
    rows = [r for r in (one(d) for d in sorted(glob.glob(str(RUNS / "d-e2-*")))) if r]
    groups = defaultdict(dict)
    for r in rows:
        groups[(r["pool"], r["n"])][r["policy"]] = r
    for (pool, n), g in sorted(groups.items()):
        base = (g.get("default") or {}).get("energy_per_completed_j")
        for p, r in g.items():
            r["vs_default"] = (r["energy_per_completed_j"] / base - 1) if base and r["energy_per_completed_j"] else None
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=1, default=str))
    for r in rows:
        print(f"{r['name']:28s} pool {r['pool']} n {r['n']} done {r['completed']:3d} E/session "
              f"{(r['energy_per_completed_j'] or 0) / 1e3:7.2f} kJ vs default {r['vs_default'] if r['vs_default'] is None else round(100 * r['vs_default'], 1)}% "
              f"| after-burst calls {r['calls_after_burst']} recomputed {r['prefix_recomputed_share']} | burst s {r['burst_s_median']} "
              f"| held {r['tool_held']}")


if __name__ == "__main__":
    main()

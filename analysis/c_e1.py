"""C-E1 (OPTIONS_PLAN.md §2.4): does tau2-bench give a retained-state opportunity?

    python -m analysis.c_e1 [run-dir]     (WS: ~/work/runs/c-e1; writes reports/2026-10-06-options/c_e1.json)

From the gateway's call log of env/queue_c_e1.sh: the agent's calls (session tau-agent-<domain>; the simulated
user's calls are left out, since a real deployment has a person there), grouped into conversations (a new one
starts when the prompt shrinks below the previous one's prompt). Per domain:
- calls per conversation, prompt at the first call and its growth per step, output per call (reasoning included);
- reuse (cached / prompt tokens) as the engine reported it;
- the ceiling P/(P + r*O) over every call after a conversation's first (P = its prompt tokens, an upper bound),
  at the WS's own r and at P1's Jetson values of r (52-312, reports/2026-10-05-p1-repo §2);
- the tasks' rewards from tau2's results file when present.
Decision rule (D15): >= 20% of LLM time at a Jetson r means an opportunity worth a full comparison; < 10% means
C collapses like P1's traffic agent.
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

from analysis.sessions import REPO

R_JETSON = {"Thor gemma (traffic)": 147, "Thor granite": 312, "Orin 64 gemma": 118, "Orin 32 E4B": 147,
            "Thor drone gemma": 63, "Thor drone tool calling": 52}
OUT = REPO / "reports/2026-10-06-options/c_e1.json"


def conversations(calls):
    convs, cur, last = [], [], None
    for c in sorted(calls, key=lambda c: c["t_req"]):
        p = c.get("prompt_tokens") or 0
        if cur and last is not None and p < last:
            convs.append(cur)
            cur = []
        cur.append(c)
        last = p
    if cur:
        convs.append(cur)
    return convs


def ceiling(convs, r):
    P = sum(c["prompt_tokens"] for cv in convs for c in cv[1:])
    O = sum(c["completion_tokens"] for cv in convs for c in cv[1:])
    return P / (P + r * O) if P + O else None


def rewards(run_dir, domain):
    f = Path(run_dir) / f"{domain}.json"
    if f.is_dir():                                   # tau2 writes <save-to>/results.json
        f = f / "results.json"
    if not f.exists():
        return None
    j = json.loads(f.read_text())
    sims = j.get("simulations") or j.get("results") or []
    rs = [((s.get("reward_info") or {}).get("reward")) for s in sims]
    rs = [x for x in rs if x is not None]
    return dict(tasks=len(sims), rewarded=len(rs), mean_reward=st.mean(rs) if rs else None,
                passed=sum(x >= 1 for x in rs))


def main():
    run_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "data/ws_runs/c-e1"
    calls = [json.loads(l) for l in open(run_dir / "gw" / "calls.jsonl")]
    calls = [c for c in calls if c.get("status") == 200 and c.get("completion_tokens") is not None]
    res = {"run": str(run_dir), "domains": {}}
    calib = REPO / "data/ws_runs/calib/gemma-e4b_tp1_gpu1.json"
    r_ws = None
    if calib.exists():
        c = json.loads(calib.read_text())
        pre = st.median(x["tok_s"] for x in c["prefill"] if x["L"] >= 4000)
        dec = 1 / min(x["step_s"] for x in c["decode"] if x["batch"] == 1)
        r_ws = pre / dec
    for dom in sorted({c["sid"].split("tau-agent-")[1] for c in calls if c["sid"].startswith("tau-agent-")}):
        ag = [c for c in calls if c["sid"] == f"tau-agent-{dom}"]
        convs = conversations(ag)
        outs = [c["completion_tokens"] for c in ag]
        growth = [b["prompt_tokens"] - a["prompt_tokens"] for cv in convs for a, b in zip(cv, cv[1:])]
        row = dict(agent_calls=len(ag), user_calls=sum(c["sid"] == f"tau-user-{dom}" for c in calls),
                   conversations=len(convs), calls_per_conversation=st.median(len(cv) for cv in convs),
                   first_prompt_median=st.median(cv[0]["prompt_tokens"] for cv in convs),
                   peak_prompt_median=st.median(max(c["prompt_tokens"] for c in cv) for cv in convs),
                   growth_per_step_median=st.median(growth) if growth else None,
                   out_median=st.median(outs), out_p90=sorted(outs)[int(0.9 * (len(outs) - 1))],
                   reasoning_share=sum(c.get("reasoning_chars") or 0 for c in ag) / max(1, sum(c.get("chars") or 0 for c in ag)),
                   reuse=sum(c.get("cached_tokens") or 0 for c in ag) / max(1, sum(c["prompt_tokens"] for c in ag)),
                   ceiling_ws=ceiling(convs, r_ws) if r_ws else None, r_ws=r_ws,
                   ceiling_jetson={k: ceiling(convs, r) for k, r in R_JETSON.items()},
                   rewards=rewards(run_dir, dom))
        cj = [v for v in row["ceiling_jetson"].values() if v is not None]
        row["verdict"] = ("opportunity (ceiling >= 20% at a Jetson r)" if cj and max(cj) >= 0.20 else
                          "collapses like traffic (ceiling < 10% at every Jetson r)" if cj and max(cj) < 0.10 else
                          "in between (10-20%)")
        res["domains"][dom] = row
        print(dom, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()
                               if k != "ceiling_jetson"}), {k: round(v, 3) for k, v in row["ceiling_jetson"].items()})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()

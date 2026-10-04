"""Step-wise agent on P1's delivery tasks: output tokens per step and the retention ceiling.

For every LLM call: P = prompt tokens, O = output tokens (reasoning included). The most a
retention policy can save is P / (P + r·O), with r = (cost of one output token) / (cost of
one prefilled token) on the target device. Calls are pooled token-weighted per arm.

Usage: python3 -m analysis.stepwise_ceiling   (reads data/ws_runs/, writes the report's JSON + figure)
"""
from __future__ import annotations

import glob
import json
import statistics as st
from pathlib import Path

from analysis.sessions import REPO

RUNS = REPO / "data/ws_runs"
P1 = {"P1 Reflexion": REPO / "data/p1_thor_drone", "P1 tool calling": REPO / "data/p1_thor_toolcalling"}
OUT = REPO / "reports/2026-10-02-stepwise-d1"
R_THOR = 1811 / 27.0      # Gemma-4-26B-A4B on the Thor: cold prefill / decode tokens per second
R_P1_ENERGY = 90.0        # sensitivity: P1's marginal energy price of a generated vs a prefilled token on
                          # the Thor, drone (EdgeAgentBench deck, 3 Oct 2026; average price 75, our fit 74)
ARMS = [  # (label, run-name prefix)
    ("Qwen3.5-9B thinking, greedy (P1 protocol)", "q_think_greedy"),
    ("Qwen3.5-9B thinking, sampled", "q_think_sampled"),
    ("Qwen3.5-9B no thinking, greedy", "q_nothink_greedy"),
    ("Qwen3.5-9B no thinking, sampled", "q_nothink_sampled"),
    ("K2-Horizon-7B high effort", "k2_high"),
    ("K2-Horizon-7B low effort", "k2_low"),
]


def _jsonl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def load_missions(prefix, suffix):
    out = []
    for sd in sorted(glob.glob(str(RUNS / f"{prefix}_{suffix}" / "sessions" / "*"))):
        summ = json.loads(Path(sd, "summary.json").read_text()) if Path(sd, "summary.json").exists() else {}
        calls = [c for c in _jsonl(Path(sd, "llm_calls.jsonl")) if c.get("completion_tokens") is not None]
        tools = _jsonl(Path(sd, "tool_calls.jsonl"))
        if calls:
            out.append(dict(dir=sd, summary=summ, calls=calls, tools=tools))
    return out


def rates(missions):
    """WS prefill rate from cold first calls (cache flushed, nothing cached) and decode rate."""
    pre = [c["prompt_tokens"] / c["ttft_s"] for m in missions for c in m["calls"][:1]
           if not c.get("cached_tokens") and c.get("ttft_s") and c["prompt_tokens"] > 4000]
    dec = [c["completion_tokens"] / c["decode_s"] for m in missions for c in m["calls"]
           if c.get("decode_s") and c["completion_tokens"] > 200]
    return (st.median(pre) if pre else None), (st.median(dec) if dec else None)


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else None


def arm_stats(missions, r_ws):
    calls = [c for m in missions for c in m["calls"]]
    P = sum(c["prompt_tokens"] for c in calls)
    O = sum(c["completion_tokens"] for c in calls)
    C = sum(c.get("cached_tokens") or 0 for c in calls)
    # private state: everything past the mission's first prompt (system + task are shared)
    Ppriv = sum(max(0, c["prompt_tokens"] - m["calls"][0]["prompt_tokens"]) for m in missions for c in m["calls"])
    outs = [c["completion_tokens"] for c in calls]
    checks = [m["summary"].get("delivery_check") or {} for m in missions]
    done = [m for m in missions if m["summary"].get("status") == "done"]
    llm_s = [sum(c["t_end"] - c["t_req"] for c in m["calls"]) for m in missions]
    flight_s = [m["summary"].get("flight_time_s") or 0 for m in missions]
    peak = [max(c["prompt_tokens"] + c["completion_tokens"] for c in m["calls"]) for m in missions]
    row = dict(
        missions=len(missions), done=len(done),
        passed_strict=sum(bool(k.get("valid")) for k in checks),
        delivered_all=sum(len(k.get("delivered", [])) == len(k.get("stops", [0])) for k in checks if k),
        collisions=sum(bool(k.get("collision")) for k in checks),
        aerogen_validator_yes=sum((m["summary"].get("validator") or {}).get("valid") == "YES" for m in missions),
        calls=len(calls), calls_per_mission=len(calls) / len(missions),
        out_median=st.median(outs), out_mean=O / len(calls), out_p90=pct(outs, 0.9), out_max=max(outs),
        share_out_gt_1k=sum(o > 1000 for o in outs) / len(outs),
        share_out_gt_4k=sum(o > 4000 for o in outs) / len(outs),
        capped=sum(c.get("finish_reason") == "length" for c in calls),
        prompt_median=st.median(c["prompt_tokens"] for c in calls),
        first_prompt=st.median(m["calls"][0]["prompt_tokens"] for m in missions),
        peak_ctx_median=st.median(peak), peak_ctx_max=max(peak),
        reuse=C / P,
        ceiling_thor=P / (P + R_THOR * O), ceiling_thor_private=Ppriv / (P + R_THOR * O),
        ceiling_r90=P / (P + R_P1_ENERGY * O), ceiling_r90_private=Ppriv / (P + R_P1_ENERGY * O),
        r_ws=r_ws, ceiling_ws=(P / (P + r_ws * O)) if r_ws else None,
        llm_s_per_mission_ws=st.median(llm_s), flight_s_per_mission=st.median(flight_s),
        # Thor projection (P1's model speed): nothing kept vs everything kept
        thor_llm_s_nokeep=st.median(sum(c["prompt_tokens"] / 1811 + c["completion_tokens"] / 27 for c in m["calls"])
                                    for m in missions),
    )
    row["flight_share_thor"] = row["flight_s_per_mission"] / (row["flight_s_per_mission"] + row["thor_llm_s_nokeep"])
    # First call = planning before any tool wait; resume calls follow a tool result and are the
    # ones a retention decision affects.
    first = [m["calls"][0]["completion_tokens"] for m in missions]
    res = [(m, c) for m in missions for c in m["calls"][1:]]
    ro = [c["completion_tokens"] for _, c in res]
    rP = sum(c["prompt_tokens"] for _, c in res)
    rO = sum(ro)
    rPpriv = sum(max(0, c["prompt_tokens"] - m["calls"][0]["prompt_tokens"]) for m, c in res)
    row.update(
        first_out_median=st.median(first), first_out_max=max(first),
        first_share_of_output=sum(first) / O,
        resume_calls=len(ro), resume_out_median=st.median(ro) if ro else None,
        resume_out_p90=pct(ro, 0.9), resume_out_max=max(ro) if ro else None,
        resume_out_mean=(rO / len(ro)) if ro else None,
        resume_share_gt_1k=(sum(o > 1000 for o in ro) / len(ro)) if ro else None,
        resume_ceiling_thor=(rP / (rP + R_THOR * rO)) if ro else None,
        resume_ceiling_thor_private=(rPpriv / (rP + R_THOR * rO)) if ro else None,
        resume_ceiling_r90=(rP / (rP + R_P1_ENERGY * rO)) if ro else None,
    )
    return row


def p1_calls():
    """(prompt, output) tokens of every LLM call in P1's Thor sweeps."""
    out = {}
    for label, root in P1.items():
        xs = []
        for f in glob.glob(str(root / "*/*/instance_*/run_*/iterations.jsonl")):
            xs += [(d.get("prompt_tokens") or 0, d.get("completion_tokens") or 0)
                   for d in _jsonl(f) if d.get("kind") == "llm" and d.get("t_phase_end")]
        out[label] = xs
    return out


def p1_outputs():
    return {k: [o for _, o in v] for k, v in p1_calls().items()}


def figure(per_arm_outs, p1):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # one hue family per model; lighter = the second setting; P1 in neutral dashes
    style = {
        "Qwen3.5-9B thinking, greedy (P1 protocol)": ("#1f5fae", "-"),
        "Qwen3.5-9B thinking, sampled": ("#7fb0e8", "-"),
        "Qwen3.5-9B no thinking, greedy": ("#137f59", "-"),
        "Qwen3.5-9B no thinking, sampled": ("#6fd3a8", "-"),
        "K2-Horizon-7B high effort": ("#c4511f", "-"),
        "K2-Horizon-7B low effort": ("#f2a477", "-"),
        "P1 Reflexion (Thor)": ("#222222", "--"),
        "P1 tool calling (Thor)": ("#8a8a8a", "--"),
    }
    fig, ax = plt.subplots(figsize=(8.5, 4.4), dpi=150)
    series = list(per_arm_outs.items()) + [(k + " (Thor)", v) for k, v in p1.items()]
    for label, xs in series:
        if not xs:
            continue
        col, ls = style.get(label, ("#555555", "-"))
        xs = sorted(max(1, x) for x in xs)
        ys = [(i + 1) / len(xs) for i in range(len(xs))]
        ax.step(xs, ys, where="post", color=col, lw=2, ls=ls, label=f"{label}, n={len(xs)}")
    ax.axvline(300, color="#999", lw=1, ls=":")
    ax.text(330, 0.03, "300 tokens: decoding them on the Thor costs as much\nas re-prefilling a 20K-token context",
            fontsize=7, color="#555")
    ax.set_xscale("log")
    ax.set_xlim(1, 6e4)
    ax.set_xlabel("Output tokens per LLM call (reasoning included, log scale)")
    ax.set_ylabel("Share of calls")
    ax.set_title("After a tool result, step-wise agents write ~60-100 tokens; P1's agents write thousands\n"
                 "(step-wise: calls after a tool result, D1 missions on the WS; P1: all calls, Thor sweeps)", fontsize=9.5)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7, loc="upper left", frameon=False)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    (OUT / "figures").mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "figures/output_per_step_cdf.png")


def main():
    result, per_arm_outs = {}, {}
    k2_pre = json.loads((RUNS / "calib_k2_tp1_gpu0.json").read_text()) if (RUNS / "calib_k2_tp1_gpu0.json").exists() else {}
    for suffix in ("d1", "d23"):
        for label, prefix in ARMS:
            ms = load_missions(prefix, suffix)
            if not ms:
                continue
            pre, dec = rates(ms)
            if prefix.startswith("k2"):
                pre = 4106.0          # calibrated cold prefill (jsw/costs/calibrate.py), K2 on one A5000
            else:
                # Qwen: cold first calls of the thinking arms, whose first streamed token is
                # reasoning, so TTFT is prefill (the tool parser buffers no-thinking output)
                pre = rates([m for pf in ("q_think_greedy", "q_think_sampled") for sf in ("d1", "d23")
                             for m in load_missions(pf, sf)])[0]
            r_ws = (pre / dec) if pre and dec else None
            row = arm_stats(ms, r_ws)
            llm = sum(c["t_end"] - c["t_req"] for m in ms for c in m["calls"])
            cached = sum(c.get("cached_tokens") or 0 for m in ms for c in m["calls"])
            row.update(prefill_ws=pre, decode_ws=dec, measured_saving_ws=((cached / pre) / (llm + cached / pre)) if pre else None)  # share of LLM time with nothing kept
            result[f"{prefix}_{suffix}"] = dict(label=label, task_set=suffix, **row)
            if suffix == "d1":
                per_arm_outs[label] = [c["completion_tokens"] for m in ms for c in m["calls"][1:]]
    p1 = p1_outputs()
    for k, calls in p1_calls().items():
        xs = [o for _, o in calls]
        P, O = sum(p for p, _ in calls), sum(xs)
        # P1's prompts are rebuilt per role call: the whole prompt counts as P (an upper bound)
        result[k] = dict(label=k, calls=len(xs), out_median=st.median(xs), out_p90=pct(xs, 0.9),
                         share_out_gt_1k=sum(x > 1000 for x in xs) / len(xs),
                         ceiling_thor=P / (P + R_THOR * O), ceiling_r90=P / (P + R_P1_ENERGY * O),
                         ceiling_r8=P / (P + 8 * O))  # sensitivity: r at batch 16 on the WS (energy)
    # aerogen on its own tasks (2026-10-01, K2-Horizon-7B, one session)
    for prefix in ("e1_low", "e1_medium", "e1_high"):
        ms = load_missions(prefix, "n1")
        if ms:
            result[f"{prefix}_n1"] = dict(label=f"aerogen own tasks, K2 {prefix[3:]} effort",
                                          task_set="aerogen", **arm_stats(ms, 4106.0 / 36.5))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stepwise.json").write_text(json.dumps(result, indent=1))
    figure(per_arm_outs, p1)
    keys = ["missions", "passed_strict", "collisions", "calls_per_mission", "first_out_median", "first_out_max",
            "first_share_of_output", "resume_out_median", "resume_out_p90", "resume_out_max", "resume_share_gt_1k",
            "capped", "first_prompt", "peak_ctx_median", "reuse", "ceiling_thor", "ceiling_thor_private",
            "resume_ceiling_thor", "resume_ceiling_thor_private", "ceiling_r90", "ceiling_r90_private", "ceiling_ws", "measured_saving_ws", "flight_s_per_mission",
            "thor_llm_s_nokeep", "flight_share_thor"]
    for name, row in result.items():
        print(name, {k: (round(row[k], 3) if isinstance(row.get(k), float) else row.get(k)) for k in keys if k in row})


if __name__ == "__main__":
    main()

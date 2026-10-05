"""Figures for the 2026-10-05 report on P1's repository (drone and traffic).

Reads opportunity.json, caps.json and traffic_sim.json in reports/2026-10-05-p1-repo/ (from
analysis.p1_opportunity, analysis.p1_caps and analysis.traffic_sim) and writes figures/.

Usage: python3 -m analysis.p1_repo_figures
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from analysis.p1_repo import CONFIGS  # noqa: E402
from analysis.report_figures import BASE, C1, C2, C3, C4, INK2, MUTED, _style  # noqa: E402
from analysis.sessions import REPO  # noqa: E402

OUT = REPO / "reports/2026-10-05-p1-repo"
SHORT = {"d_thor_gemma_rfx": "Drone · Thor · gemma-26B · Reflexion", "d_thor_gemma_tc": "Drone · Thor · gemma-26B · tool calling",
         "d_o64_devstral_tc": "Drone · Orin 64 · Devstral-24B", "d_o32_e4b_tc": "Drone · Orin 32 · gemma-E4B",
         "t_thor_gemma": "Traffic · Thor · gemma-26B", "t_thor_granite": "Traffic · Thor · granite-8B",
         "t_thor_qwen36": "Traffic · Thor · Qwen3.6-35B", "t_o64_gemma": "Traffic · Orin 64 · gemma-26B",
         "t_o64_granite": "Traffic · Orin 64 · granite-8B", "t_o32_granite": "Traffic · Orin 32 · granite-8B",
         "t_o32_e4b": "Traffic · Orin 32 · gemma-E4B", "t_o32_qwenvl": "Traffic · Orin 32 · Qwen2.5-VL-7B"}
KEYS = [c.key for c in CONFIGS]


def _rows(ax):
    ax.set_yticks(range(len(KEYS)), [SHORT[k] for k in KEYS])
    ax.set_ylim(len(KEYS) - 0.5, -0.5)
    ax.axhline(3.5, color=BASE, lw=1)


def fig_opportunity(op, path):
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 5.6), sharey=True, gridspec_kw=dict(width_ratios=[1.25, 1]))
    for i, k in enumerate(KEYS):
        v = op[k]
        meas = v["measured_saving"]
        est = (v.get("prefix_reuse") or {}).get("value_if_cached") if meas is None else None
        ceil = v["ceiling"]
        lo = meas if meas is not None else est
        if lo is not None and ceil is not None:
            a.plot([100 * lo, 100 * ceil], [i, i], color=BASE, lw=2, zorder=1)
        if meas is not None:
            a.plot(100 * meas, i, "o", color=C1, ms=8, mec="white", mew=1.5, zorder=3)
        if est is not None:
            a.plot(100 * est, i, "o", color="white", ms=8, mec=C1, mew=2, zorder=3)
        if ceil is not None:
            a.plot(100 * ceil, i, "o", color=C2, ms=8, mec="white", mew=1.5, zorder=3)
        g50, g90 = v["gap_median_s"], v["gap_p90_s"]
        b.plot([g50, g90], [i, i], color=BASE, lw=2, zorder=1)
        b.plot(g50, i, "o", color=C1, ms=8, mec="white", mew=1.5, zorder=3)
        b.plot(g90, i, "o", color=C3, ms=8, mec="white", mew=1.5, zorder=3)
    _rows(a)
    a.set_xlabel("share of LLM time (%)")
    a.set_title("What keeping a session's state saves", loc="left", fontweight="bold")
    a.plot([], [], "o", color=C1, label="saved by the prefix cache (measured)")
    a.plot([], [], "o", color="white", mec=C1, mew=2, label="if the cache had worked (from prompt text)")
    a.plot([], [], "o", color=C2, label="ceiling P/(P+r·O) at the configuration's own r")
    a.legend(fontsize=8, loc="center right", frameon=False)
    _style(a, "x")
    b.set_xscale("log")
    b.set_xlabel("idle gap between two LLM calls (s, log)")
    b.set_title("How long the state sits idle", loc="left", fontweight="bold")
    b.plot([], [], "o", color=C1, label="median")
    b.plot([], [], "o", color=C3, label="90th percentile")
    b.legend(fontsize=8, loc="center left", frameon=False)
    _style(b, "x")
    fig.suptitle("P1's runs, one agent per device (measured; traffic completed-only, ungraded)", x=0.01, ha="left",
                 fontsize=9.5, color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_caps(cp, path):
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 6.4), sharey=True)
    kinds = [("loop", "repetition loop (text)", C2), ("not_loop", "not a loop (text)", C1), ("no_text", "text not recorded", BASE)]
    for i, k in enumerate(KEYS):
        x = 0.0
        for kk, _, col in kinds:
            w = 100 * cp[k]["capped_llm_share_by_kind"][kk]
            a.barh(i, w, left=x, color=col, height=0.62, edgecolor="white", linewidth=1.5)
            x += w
        sr = cp[k]["stop_rules"]
        for j, (rule, col, mk) in enumerate([("loop", C2, "o"), ("second_consecutive_cap", C3, "s"), ("first_cap", C4, "D")]):
            b.plot(100 * sr[rule]["saved_share"], i + (j - 1) * 0.22, mk, color=col, ms=7, mec="white", mew=1.2)
    _rows(a)
    a.set_xlabel("share of LLM time in calls that hit their token limit (%)")
    a.set_title("Capped calls, and whether they loop", loc="left", fontweight="bold")
    from matplotlib.patches import Patch
    a.legend(handles=[Patch(color=col, label=lab) for _, lab, col in kinds], fontsize=8, loc="upper center",
             bbox_to_anchor=(0.5, -0.1), ncol=3, frameon=False)
    _style(a, "x")
    b.set_xlabel("energy saved, upper bound (% of the configuration's energy)")
    b.set_title("What a stop rule would save", loc="left", fontweight="bold")
    b.plot([], [], "o", color=C2, label="online loop stop (stops no finished call*)")
    b.plot([], [], "s", color=C3, label="stop the run at a second consecutive capped call")
    b.plot([], [], "D", color=C4, label="stop the run at its first capped call (P1's bound)")
    b.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=1, frameon=False)
    _style(b, "x")
    fig.suptitle("P1's runs (measured). *one false stop each on Traffic · Thor · gemma-26B and Traffic · Orin 32 · gemma-E4B;"
                 " the loop stop acts only on calls whose text was recorded", x=0.01, ha="left", fontsize=9.5, color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_sim(sim, path):
    cells = sim["cells"]
    keys = ["t_thor_gemma", "t_thor_granite", "t_o32_e4b", "t_o64_gemma", "t_o64_granite", "t_o32_granite"]
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.4))
    for ax, k in zip(axes.flat, keys):
        get = lambda s, f: [next(c[f] for c in cells if c["scenario"] == k and c["pool_scale"] == s and c["n"] == n) / 1e3
                            for n in (1, 2, 4, 8)]
        ns = [1, 2, 4, 8]
        ax.plot(ns, get(1.0, "e_inf"), color=MUTED, lw=1.5, ls="--", label="unlimited memory (bound)")
        ax.plot(ns, get(1.0, "e_default"), color=C1, lw=2, marker="o", ms=6, mec="white", label="SGLang default, real KV pool")
        ax.plot(ns, get(1.0, "e_best_any"), color=C2, lw=1.5, marker="o", ms=4, mec="white", label="best of 12 policies, real pool")
        ax.plot(ns, get(2.0, "e_default"), color=C3, lw=2, marker="s", ms=5, mec="white", label="SGLang default, pool x2 (FP8 KV)")
        ax.set_xscale("log", base=2)
        ax.set_xticks(ns, [str(n) for n in ns])
        ax.minorticks_off()
        ax.set_ylim(bottom=0)
        pool = sim["devices"][k]["kv_pool_tokens"]
        ax.set_title(f"{SHORT[k].replace('Traffic · ', '')}  (pool {pool / 1e3:.0f}K tokens)", loc="left", fontsize=9.5,
                     fontweight="bold")
        _style(ax, "y")
    for ax in axes[1]:
        ax.set_xlabel("traffic agents sharing one device")
    for ax in axes[:, 0]:
        ax.set_ylabel("board energy per completed task (kJ)")
    axes[0, 0].legend(fontsize=7.5, loc="upper right", frameon=False)
    fig.suptitle("Simulated from P1's traffic traces (mean of 3 seeds, 24 h each): the default matches every policy;"
                 " small KV pools cap consolidation", x=0.01, ha="left", fontsize=9.5, color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    (OUT / "figures").mkdir(parents=True, exist_ok=True)
    op = json.loads((OUT / "opportunity.json").read_text())
    cp = json.loads((OUT / "caps.json").read_text())
    sim = json.loads((OUT / "traffic_sim.json").read_text())
    fig_opportunity(op, OUT / "figures/opportunity.png")
    fig_caps(cp, OUT / "figures/caps.png")
    fig_sim(sim, OUT / "figures/traffic_sim.png")


if __name__ == "__main__":
    main()

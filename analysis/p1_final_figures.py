"""Figures on P1's final data (repository at 0cc2311a, 10 Oct 2026, the submitted state), for the options comparison.

    python -m analysis.p1_final_figures        (reads P1's committed summaries in data/edge-agent-bench if present)

Writes reports/2026-10-06-options/figures/p1final_{prefill,orin_rerun,evictions}.png. Inputs are P1's own committed
summary numbers (analysis/outputs/figdata/*.numbers.json) and counts read from P1's grading files; the 7 Oct values are
from P1's repository at f6aabe4 (docs/DATA_INVENTORY.md, paper macros, traffic/grading/overrides.csv).
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from analysis.report_figures import C1, C2, INK2, MUTED, _style  # noqa: E402
from analysis.sessions import REPO  # noqa: E402

P1 = REPO / "data/edge-agent-bench/analysis/outputs/figdata"
F = REPO / "reports/2026-10-06-options/figures"

REASONING = {"gemma4-e4b": True, "gemma4-26b-a4b": True, "granite4.2-8b": True, "qwen3.8-27b": True,
             "qwen3.6-35b-a3b": True, "qwen2.5-vl-7b": False, "ministral3-8b": False, "devstral-24b": False}
DEV = {"thor": "Thor", "orin64": "Orin 64", "orin32": "Orin 32"}
MOD = {"gemma4-e4b": "gemma-E4B", "gemma4-26b-a4b": "gemma-26B", "granite4.2-8b": "granite-8B", "qwen3.8-27b": "Qwen3.8-27B",
       "qwen3.6-35b-a3b": "Qwen3.6-35B", "qwen2.5-vl-7b": "Qwen2.5-VL", "ministral3-8b": "Ministral-8B",
       "devstral-24b": "Devstral-24B"}

# Orin traffic configurations: share of runs with a failed tool (sandbox image missing or detection-store disk full).
# 7 Oct = runs still faulted in P1's repository at f6aabe4 (our 7 Oct audit of overrides.csv); 10 Oct = 0cc2311a, where
# every faulted run of these configurations is replaced by a re-run (P1's paper: 776 superseded, 142 left, all in two
# Reflexion arms that are not shown here).
FAULTED_7OCT = {"Orin 32 granite": 70.4, "Orin 64 Devstral": 57.1, "Orin 64 granite": 56.1, "Orin 32 gemma-E4B": 47.6,
                "Orin 64 gemma-26B": 36.5, "Orin 32 Qwen2.5-VL": 22.6, "Orin 32 Qwen2.5-VL (Reflexion)": 15.5,
                "Orin 32 Ministral": 9.9}
# Pass rates (traffic tool calling): 7 Oct from P1's DATA_INVENTORY.md at f6aabe4; 10 Oct from traffic/grading/grades.csv
# at 0cc2311a with P1's supersede rule (re-run replaces the faulted original per task; overflows are never replaced).
PASS = {"Orin 32 granite": (16.4, 51.3), "Orin 32 gemma-E4B": (33.7, 73.0), "Orin 64 granite": (22.2, 58.7),
        "Orin 64 gemma-26B": (31.0, 44.8)}
# Context-window overflow (share of runs), P1's paper macros at f6aabe4 and 0cc2311a.
OVERFLOW = {"Orin 64 gemma-26B": (17.5, 24.2), "Orin 32 granite": (10.6, 21.2), "Orin 64 granite": (14.3, 19.0)}


def _load(name):
    p = P1 / f"{name}.numbers.json"
    return json.loads(p.read_text()) if p.exists() else None


def _label(cell):
    dom, dev, par, mod = cell.split("/")
    tag = " · Reflexion" if par == "reflexion" else ""
    return f"{dom.capitalize()} · {DEV[dev]} · {MOD[mod]}{tag}"


def fig_prefill():
    d = _load("D2_prefill_decode_share")
    if not d:
        return
    rows = sorted(((cell, v["prefill_time_share_pct"]) for cell, v in d.items()), key=lambda r: r[1])
    rows.sort(key=lambda r: r[1])
    fig, ax = plt.subplots(figsize=(9, 7.2))
    for i, (cell, pct) in enumerate(rows):
        mod = cell.split("/")[3]
        col = C1 if REASONING[mod] else C2
        ax.barh(i, pct, color=col, height=0.7)
        note = "  prefix cache off" if cell == "drone/orin64/tool_calling/devstral-24b" else ""
        ax.text(pct + 0.3, i, f"{pct:.1f}%{note}", va="center", fontsize=8.5, color=INK2)
    ax.axvspan(0.67, 3.94, color="#e9eef7", zorder=0)
    ax.set_yticks(range(len(rows)), [_label(c) for c, _ in rows], fontsize=8.5)
    ax.set_xlabel("Prefill share of LLM time (%), P1's measured runs, one agent per device")
    ax.set_xlim(0, 30)
    ax.bar(0, 0, color=C1, label="reasoning model")
    ax.bar(0, 0, color=C2, label="non-reasoning model")
    ax.legend(loc="lower right", frameon=True, fontsize=9)
    ax.text(6.5, 3, "shaded band: 0.7-3.9%,\n18 of the 22 configurations", fontsize=9, color=INK2, va="center")
    _style(ax)
    fig.tight_layout()
    fig.savefig(F / "p1final_prefill.png", dpi=160)
    plt.close(fig)


def fig_orin_rerun():
    fig, axs = plt.subplots(1, 3, figsize=(13, 4.2), gridspec_kw={"width_ratios": [1.5, 1, 1]})
    ax = axs[0]
    names = list(FAULTED_7OCT)[::-1]
    ax.barh(range(len(names)), [FAULTED_7OCT[n] for n in names], color=MUTED, height=0.6, label="7 Oct (what we replayed)")
    for i, n in enumerate(names):
        ax.text(FAULTED_7OCT[n] + 1, i, f"{FAULTED_7OCT[n]:.0f}% → 0%", va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(range(len(names)), names, fontsize=8.5)
    ax.set_xlim(0, 95)
    ax.set_xlabel("Runs with a failed tool (%)")
    ax.set_title("(a) Tool faults: all re-run by 10 Oct", fontsize=10, loc="left")
    _style(ax)
    for ax, data, title, xl in ((axs[1], PASS, "(b) Pass rate", "Runs passed (%)"),
                                (axs[2], OVERFLOW, "(c) Context-window overflow", "Runs ended by overflow (%)")):
        names = list(data)[::-1]
        for i, n in enumerate(names):
            a, b = data[n]
            ax.plot([a, b], [i, i], color=MUTED, lw=1.5, zorder=1)
            ax.scatter([a], [i], color=MUTED, s=40, zorder=2)
            ax.scatter([b], [i], color=C1, s=40, zorder=3)
            ax.text(b + (3 if data is PASS else 1.2), i, f"{b:.0f}%",
                    va="center", fontsize=8.5, color=INK2)
        ax.set_yticks(range(len(names)), names, fontsize=8.5)
        ax.set_xlim(0, max(b for _, b in data.values()) * 1.25)
        ax.set_ylim(-0.6, len(names) - 0.4)
        ax.set_xlabel(xl)
        ax.set_title(title, fontsize=10, loc="left")
        _style(ax)
    axs[1].scatter([], [], color=MUTED, label="7 Oct (P1's repository at f6aabe4, the data our Orin results replayed)")
    axs[1].scatter([], [], color=C1, label="10 Oct (P1's final data, 0cc2311a)")
    fig.legend(*axs[1].get_legend_handles_labels(), loc="upper right", ncol=2, fontsize=8.5, frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(F / "p1final_orin_rerun.png", dpi=160)
    plt.close(fig)


def fig_evictions():
    d = _load("B5_context_capacity")
    if not d:
        return
    rows = [(cell, 100 * v["kv_eviction_run_share"], v["kv_pool_tokens_min"]) for cell, v in d.items()
            if cell.startswith("drone/")]
    rows.sort(key=lambda r: r[1])
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    for i, (cell, pct, pool) in enumerate(rows):
        col = C2 if cell == "drone/thor/reflexion/gemma4-26b-a4b" else C1
        ax.barh(i, pct, color=col, height=0.65)
        ax.text(pct + 1, i, f"{pct:.0f}%  (pool {pool / 1000:.0f}K)", va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(range(len(rows)), [_label(c).replace("Drone · ", "") for c, _, _ in rows], fontsize=8.5)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Drone runs with a KV eviction (%), one agent per device, cache flushed per run")
    ax.text(98, 0.2, "Thor Reflexion: 46 of its 48 evicting runs\ncontain a capped (looping) call (P5, 5 Oct)",
            ha="right", va="bottom", fontsize=8.5, color=C2)
    _style(ax)
    fig.tight_layout()
    fig.savefig(F / "p1final_evictions.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    F.mkdir(parents=True, exist_ok=True)
    fig_prefill()
    fig_orin_rerun()
    fig_evictions()

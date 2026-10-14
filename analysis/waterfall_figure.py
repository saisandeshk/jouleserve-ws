"""Figure for the energy waterfall (analysis/waterfall.py): one 100% bar per configuration, traffic and drone panels.

Encoding: hue says whether the energy went to runs that failed (orange) or passed (blue); lightness separates the
buckets inside each group; grey is the rest (prefill, tool phases, vision tool, harness). Rows are sorted by the
share spent on failed runs. Right of each bar: energy per success as run, and the pass rate.

Usage: python -m analysis.waterfall_figure  -> reports/2026-10-14-waterfall/waterfall.png
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from analysis.sessions import REPO  # noqa: E402

OUT = REPO / "reports/2026-10-14-waterfall"
SEGS = [  # (label, buckets, colour)
    ("Failed runs: after a warning sign", ["failed_after_sign"], "#d9541e"),
    ("Failed runs: no warning sign", ["failed_before_sign"], "#f5b08c"),
    ("Passing runs: degenerate decode", ["degenerate"], "#184f95"),
    ("Passing runs: one-at-a-time decode cost (k = 4)", ["batch1_cost"], "#3987e5"),
    ("Passing runs: decode at k = 4", ["decode_floor"], "#9ec5f4"),
    ("Passing runs: prefill, tools, vision tool, other", ["prefill", "tool_wait", "vision_tool", "other"], "#cfcdc6"),
]
INK, MUTED, SURFACE = "#1b1b1a", "#5c5b57", "#fcfcfb"


def label(c):
    agent = "" if c["agent"] == "tool calling" else " · Reflexion"
    return f"{c['device']} · {c['model']}{agent}"


def panel(ax, rows, title):
    rows = sorted(rows, key=lambda c: (c["buckets_J"].get("failed_after_sign", 0) +
                                       c["buckets_J"].get("failed_before_sign", 0)) / c["total_J"])
    for i, c in enumerate(rows):
        left = 0.0
        for _, keys, col in SEGS:
            w = 100 * sum(c["buckets_J"].get(k, 0.0) for k in keys) / c["total_J"]
            if w > 0:
                ax.barh(i, w, left=left, height=0.62, color=col, edgecolor=SURFACE, linewidth=1.0)
            left += w
        fail = 100 * (c["buckets_J"].get("failed_after_sign", 0) + c["buckets_J"].get("failed_before_sign", 0)) \
            / c["total_J"]
        ax.text(fail / 2, i, f"{fail:.0f}%", va="center", ha="center", fontsize=8, color=INK)
        es = c["e_per_success_J"] / 1e3
        ax.text(101.5, i, f"{es:,.0f} kJ/success · {100 * c['passes'] / c['runs']:.0f}% pass",
                va="center", ha="left", fontsize=8, color=MUTED)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([label(c) for c in rows], fontsize=8.5, color=INK)
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_title(title, loc="left", fontsize=10.5, color=INK, fontweight="bold", pad=6)
    ax.tick_params(axis="x", colors=MUTED, labelsize=8)
    ax.tick_params(axis="y", length=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#d6d4cd")
    ax.set_axisbelow(True)
    ax.grid(axis="x", color="#ebe9e3", linewidth=0.8)


def main():
    W = json.loads((OUT / "waterfall.json").read_text())["configs"]
    tr = [c for c in W if c["domain"] == "traffic"]
    dr = [c for c in W if c["domain"] == "drone"]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10.5, 9.6), gridspec_kw=dict(height_ratios=[len(tr), len(dr)]),
                                 facecolor=SURFACE)
    for a in (a1, a2):
        a.set_facecolor(SURFACE)
    panel(a1, tr, f"Traffic agent: {len(tr)} configurations")
    panel(a2, dr, f"Drone agents: {len(dr)} configurations")
    a2.set_xlabel("Share of the configuration's board energy (%)", fontsize=8.5, color=MUTED)
    handles = [plt.Rectangle((0, 0), 1, 1, color=col) for _, _, col in SEGS]
    fig.legend(handles, [l for l, _, _ in SEGS], loc="upper left", ncol=2, fontsize=8, frameon=False,
               bbox_to_anchor=(0.01, 0.995))
    fig.suptitle("Where P1's board energy went: runs that failed take most of it", x=0.01, y=1.035, ha="left",
                 fontsize=12.5, color=INK, fontweight="bold")
    fig.text(0.01, -0.01, "P1's final data (0cc2311a), P1's selection rule and grades; board energy per run and per "
             "phase. Number in the bar: share spent on failed runs. One-at-a-time cost priced with the boards' "
             "cost curves at 4 requests (measured for gemma-26B on Thor and dense models on the Orin 32; a proxy "
             "elsewhere).", fontsize=7.5, color=MUTED, ha="left", va="top", wrap=True)
    fig.tight_layout(rect=(0, 0, 0.84, 0.95))
    fig.savefig(OUT / "waterfall.png", dpi=170, bbox_inches="tight", facecolor=SURFACE)
    print("wrote", OUT / "waterfall.png")


if __name__ == "__main__":
    main()

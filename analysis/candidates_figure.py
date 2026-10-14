"""Figure: energy per success against the number of candidates k, one line per load (agents on the board), for each
bank in candidates_bank.json. Values are relative to one sampled answer at one agent (k = 1, A = 1) of the same bank;
infeasible (memory) or unmeasured points are left out.

Usage: python -m analysis.candidates_figure -> reports/2026-10-15-candidates/candidates.png
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from analysis.sessions import REPO  # noqa: E402

OUT = REPO / "reports/2026-10-15-candidates"
COL = {1: "#2a78d6", 2: "#eb6834", 4: "#1baf7a", 8: "#eda100", 16: "#e87ba4"}   # validated categorical order
INK, MUTED, SURFACE, GRID = "#1b1b1a", "#5c5b57", "#fcfcfb", "#ebe9e3"


def main():
    banks = json.loads((OUT / "candidates_bank.json").read_text())
    banks = [b for b in banks if "controls" not in b["label"]]
    fig, axes = plt.subplots(1, len(banks), figsize=(5.2 * len(banks), 4.2), facecolor=SURFACE, sharey=False)
    for ax, b in zip(axes, banks):
        ax.set_facecolor(SURFACE)
        g = b["grid"]
        base = g["1x1"]["energy_per_success_J"]
        for A in (1, 2, 4, 8, 16):
            pts = [(v["k"], v["energy_per_success_J"] / base) for v in g.values()
                   if v["A"] == A and v["feasible"] and v["energy_per_success_J"]]
            if not pts:
                continue
            pts.sort()
            xs, ys = zip(*pts)
            ax.plot(xs, ys, color=COL[A], lw=2, marker="o", ms=5)
            ax.annotate(f"{A} agent{'s' if A > 1 else ''}", (xs[-1], ys[-1]), xytext=(6, 0), textcoords="offset points",
                        va="center", fontsize=8, color=INK)
        ax.axhline(1.0, color=MUTED, lw=0.8, ls=(0, (3, 3)))
        ax.set_xscale("log", base=2)
        ax.set_xticks([1, 2, 4, 8])
        ax.set_xticklabels(["1", "2", "4", "8"])
        ax.set_xlim(0.8, 13)
        ax.set_xlabel("candidates per call (k)", fontsize=8.5, color=MUTED)
        ax.set_title(b["label"].replace("Thor-1 gemma-26B, hard prompts", "Thor, gemma-26B (mixture of experts)")
                     .replace("Orin-32-1 gemma-E4B", "Orin 32, gemma-E4B (dense)"),
                     loc="left", fontsize=10, color=INK, fontweight="bold")
        ax.tick_params(colors=MUTED, labelsize=8)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.spines["left"].set_color("#d6d4cd")
        ax.spines["bottom"].set_color("#d6d4cd")
        ax.grid(axis="y", color=GRID, lw=0.8)
    axes[0].set_ylabel("energy per success, relative to one answer at one agent", fontsize=8.5, color=MUTED)
    fig.suptitle("Parallel candidates pay on a dense model and not on a mixture of experts; the best k falls with load",
                 x=0.01, ha="left", fontsize=11.5, color=INK, fontweight="bold")
    fig.text(0.01, -0.04, "Computed from the mentor's drone sample banks (8 sampled programs per prompt, each flown and "
             "graded) and the boards' measured energy per decode step. First-of-k: the shortest answer that finished "
             "wins. Points left out where k candidates for every agent do not fit the KV pool, or the width was not "
             "measured (more than 16 streams). Dashed line: one sampled answer at one agent.", fontsize=7.3,
             color=MUTED, ha="left", va="top", wrap=True)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(OUT / "candidates.png", dpi=170, bbox_inches="tight", facecolor=SURFACE)
    print("wrote", OUT / "candidates.png")


if __name__ == "__main__":
    main()

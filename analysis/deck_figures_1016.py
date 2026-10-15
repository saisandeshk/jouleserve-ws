"""Figures for the combined deck section of 16 Oct (slides 70 onward), in the deck's style: off-white ground, IBM Plex
Sans, one blue accent and orange for waste. Each figure's size in inches is its display width on the slide / 100, drawn
at 200 dpi with every font at 18 pt or more, so text shows at about 25 px on the 1920x1080 slide.

Inputs (all committed): reports/2026-10-14-waterfall/waterfall.json, reports/2026-10-15-candidates/{candidates_bank.json,
costcurve_granite_thor2.txt, cand_traffic_granite.json, cand_traffic_gemma.json}.

Usage: python3 analysis/deck_figures_1016.py <dir with IBMPlexSans-*.ttf> -> reports/2026-10-16-deck/figures/*.png
"""
from __future__ import annotations

import glob
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(REPO, "reports", "2026-10-16-deck", "figures")
BG, INK, MUTED, GRID = "#FAFAF7", "#1B2430", "#5F6B78", "#E3E6EA"
BLUE, BLUE_L, ORANGE, ORANGE_L, GREY, GREY_L = "#2A78D6", "#9CC1EE", "#E07B39", "#F3BE96", "#8A94A3", "#D5DAE0"
FS = 18


def setup(font_dir):
    for f in glob.glob(os.path.join(font_dir, "IBMPlexSans-*.ttf")):
        font_manager.fontManager.addfont(f)
    plt.rcParams.update({"font.family": "IBM Plex Sans", "font.size": FS, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": INK, "ytick.color": INK, "axes.titlesize": FS, "axes.labelsize": FS,
                         "xtick.labelsize": FS, "ytick.labelsize": FS, "legend.fontsize": FS, "figure.facecolor": BG,
                         "axes.facecolor": BG, "savefig.facecolor": BG})
    os.makedirs(OUT, exist_ok=True)


def fig(w_px, h_px):
    f, ax = plt.subplots(figsize=(w_px / 100, h_px / 100))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=GRID, lw=1)
    ax.set_axisbelow(True)
    return f, ax


def save(f, name):
    p = os.path.join(OUT, name)
    f.savefig(p, dpi=200)
    plt.close(f)
    print("wrote", p)


def short(c):
    dev = {"Thor": "Thor", "Orin 64": "Orin 64", "Orin 32": "Orin 32"}[c["device"]]
    m = c["model"].replace("gemma-26B", "gemma-26B").replace("Qwen2.5-VL-7B", "Qwen-VL-7B").replace("Devstral-24B", "Devstral")
    m = m.replace("Qwen3.6-35B-A3B", "Qwen3.6").replace("Qwen3.8-27B", "Qwen3.8").replace("Ministral-8B", "Ministral")
    return f"{dev} · {m}" + (" · R" if c["agent"] == "Reflexion" else "")


def waterfall():
    w = json.load(open(os.path.join(REPO, "reports/2026-10-14-waterfall/waterfall.json")))
    cats = [("failed", "runs that fail", ORANGE), ("degenerate", "runaway decode in passing runs", ORANGE_L),
            ("batch1_cost", "decoding one request at a time", BLUE_L), ("useful", "decode and prefill a pass needed", BLUE),
            ("waits", "tool waits and the rest", GREY_L)]
    rows = []
    for c in w["configs"]:
        b, T = c["buckets_J"], c["total_J"]
        v = {"failed": b.get("failed_before_sign", 0) + b.get("failed_after_sign", 0), "degenerate": b.get("degenerate", 0),
             "batch1_cost": b.get("batch1_cost", 0), "useful": b.get("decode_floor", 0) + b.get("prefill", 0),
             "waits": b.get("tool_wait", 0) + b.get("vision_tool", 0) + b.get("other", 0)}
        rows.append((c["domain"], short(c), {k: 100 * x / T for k, x in v.items()}))
    order = [r for r in rows if r[0] == "traffic"] + [r for r in rows if r[0] == "drone"]
    order = sorted([r for r in order if r[0] == "traffic"], key=lambda r: -r[2]["failed"]) + \
        sorted([r for r in order if r[0] == "drone"], key=lambda r: -r[2]["failed"])
    f, ax = fig(1000, 620)
    f.subplots_adjust(left=0.135, right=0.99, top=0.9, bottom=0.27)
    xs = list(range(len(order)))
    xs = [x + (1 if r[0] == "drone" else 0) for x, r in zip(xs, order)]       # a gap between the two families
    bottom = [0.0] * len(order)
    for key, lab, col in cats:
        vals = [r[2][key] for r in order]
        ax.bar(xs, vals, bottom=bottom, color=col, width=0.8, label=lab, edgecolor=BG, linewidth=0.6)
        bottom = [a + b for a, b in zip(bottom, vals)]
    ax.set_xticks([])
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_ylabel("share of board energy")
    nt = sum(1 for r in order if r[0] == "traffic")
    ax.text((nt - 1) / 2, 103, "traffic · 17 configurations", ha="center", va="bottom", color=INK, fontsize=FS)
    ax.text(nt + 1 + (len(order) - nt - 1) / 2, 103, "drones · 8", ha="center", va="bottom", color=INK, fontsize=FS)
    ax.set_xlim(-0.7, xs[-1] + 0.7)
    f.legend(*ax.get_legend_handles_labels(), loc="lower center", bbox_to_anchor=(0.53, 0.0), ncol=2, frameon=False,
             handlelength=1.1, columnspacing=1.4, labelspacing=0.35)
    save(f, "waterfall.png")


def costcurve():
    bank = {b["label"]: b for b in json.load(open(os.path.join(REPO, "reports/2026-10-15-candidates/candidates_bank.json")))}
    moe = bank["Thor-1 gemma-26B, hard prompts"]["step_energy_J"]
    e4b = bank["Orin-32-1 gemma-E4B"]["step_energy_J"]
    ks = [1, 2, 4, 8, 16]
    rel = lambda d: [d[str(k)] / d["1"] for k in ks]
    gr = {}
    for line in open(os.path.join(REPO, "reports/2026-10-15-candidates/costcurve_granite_thor2.txt")):
        p = line.split()
        if len(p) > 6 and p[0] == "ctx":
            gr.setdefault(int(p[1]), {})[int(p[3])] = float(p[7])
    series = [("one after another", ks, GREY, "--", 2.2),
              ("gemma-26B, MoE, Thor", rel(moe), ORANGE, "-", 3.4),
              ("granite-8B, dense, 16K", [gr[16384][k] for k in ks], BLUE, ":", 3.0),
              ("granite-8B, dense, 4K", [gr[4096][k] for k in ks], BLUE, "-", 3.4),
              ("E4B, dense, Orin", rel(e4b), "#2C8C5A", "-", 3.4)]
    f, ax = fig(1060, 470)
    f.subplots_adjust(left=0.1, right=0.6, top=0.95, bottom=0.17)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log", base=2)
    nudge = {"granite-8B, dense, 4K": 5, "E4B, dense, Orin": -7}
    for lab, ys, col, ls, lw in series:
        ax.plot(ks, ys, color=col, ls=ls, lw=lw, marker="o", ms=7 if ls != "--" else 5)
        txt = f"{lab}  {ys[-1]:.2f}×" if ls != "--" else f"{lab}  16×"
        ax.annotate(txt, (16, ys[-1]), xytext=(12, nudge.get(lab, 0)), textcoords="offset points", va="center",
                    color=col if ls != "--" else MUTED, fontsize=FS, annotation_clip=False)
    ax.axvline(4, color=MUTED, lw=1, ls=(0, (2, 4)))
    ax.text(4.25, 10.5, "4 streams", color=MUTED, fontsize=FS)
    ax.set_xticks(ks)
    ax.set_xticklabels([str(k) for k in ks])
    ax.set_yticks([1, 2, 4, 8, 16])
    ax.set_yticklabels(["1×", "2×", "4×", "8×", "16×"])
    ax.minorticks_off()
    ax.set_xlabel("streams decoding together")
    ax.set_ylabel("energy per step")
    ax.grid(axis="x", color=GRID, lw=1)
    save(f, "costcurve.png")


def candidates():
    d = {m: json.load(open(os.path.join(REPO, f"reports/2026-10-15-candidates/cand_traffic_{m}.json")))["arms"]
         for m in ("granite", "gemma")}
    keys = [("G (P1 greedy, recorded)", "P1, greedy (recorded)", GREY_L),
            ("S1 (one sampled answer)", "one sampled answer", BLUE_L), ("F4 (first-of-4)", "first of 4", BLUE)]
    f, ax = fig(1000, 560)
    f.subplots_adjust(left=0.11, right=0.99, top=0.97, bottom=0.25)
    groups = [("granite", "granite-8B (dense)"), ("gemma", "gemma-26B (mixture of experts)")]
    width = 0.26
    for gi, (m, glab) in enumerate(groups):
        for ki, (k, lab, col) in enumerate(keys):
            a = d[m][k]
            x = gi + (ki - 1) * (width + 0.03)
            v = a["energy_per_success_J"] / 1e3
            ax.bar(x, v, width=width, color=col, label=lab if gi == 0 else None, edgecolor=BG)
            ax.text(x, v + 3, f"{v:.0f} kJ\n{a['passes']}/{a['runs']}", ha="center", va="bottom", color=INK, fontsize=FS)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([g[1] for g in groups])
    ax.set_ylabel("kJ per success")
    ax.set_ylim(0, 205)
    f.legend(*ax.get_legend_handles_labels(), loc="lower center", bbox_to_anchor=(0.54, 0.0), ncol=3, frameon=False,
             handlelength=1.1, columnspacing=1.2)
    save(f, "candidates_traffic.png")


if __name__ == "__main__":
    setup(sys.argv[1])
    waterfall()
    costcurve()
    candidates()

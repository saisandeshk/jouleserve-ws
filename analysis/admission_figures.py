"""Figures and summary numbers for the admission/retention simulation report.

Reads reports/2026-10-03-admission-sim/sim.json (from analysis.admission_sim) and writes the
figures plus summary.json, which also holds the like-for-like comparison on P1's delivery
tasks (P1 Reflexion measured on the Thor vs. the step-wise agent projected onto the Thor).

Usage: python3 -m analysis.admission_figures
"""
from __future__ import annotations

import glob
import json
import statistics as st

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from analysis.admission_sim import OUT, REPO, thor_device, workloads  # noqa: E402
from analysis.report_figures import BASE, C1, C2, C3, C4, INK2, MUTED, SURF, _style  # noqa: E402

NS = (1, 2, 4, 8, 16)
SERIES = [("stepwise_qwen_think", "Step-wise, Qwen3.5 thinking", C1),
          ("stepwise_k2_high", "Step-wise, K2 high effort", C2),
          ("p1_reflexion", "P1 Reflexion", C3),
          ("p1_toolcalling", "P1 tool calling", C4)]


def cell(cells, scen, wl, b, n):
    return next(c for c in cells if c["scenario"] == scen and c["workload"] == wl and c["budget_gib"] == b and c["n"] == n)


def _x(ax):
    ax.set_xscale("log", base=2)
    ax.set_xticks(NS, [str(n) for n in NS])
    ax.minorticks_off()


def fig_scaling(cells, path):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for wl, lab, col in SERIES:
        cs = [cell(cells, "thor_gemma", wl, 16, n) for n in NS]
        kw = dict(color=col, lw=2, marker="o", ms=6, markeredgecolor=SURF, markeredgewidth=1.5, label=lab)
        axes[0].plot(NS, [c["e_inf"] / 1e3 for c in cs], **kw)
        axes[1].plot(NS, [c["inf_slow_p95"] for c in cs], **kw)
    axes[0].set_yscale("log")
    axes[0].set_yticks([5, 10, 20, 50, 100, 200], ["5", "10", "20", "50", "100", "200"])
    axes[0].set_ylabel("Board energy per successful mission (kJ, log)")
    axes[0].set_title("Energy per success falls as drones share the box")
    axes[1].axhline(1.5, color=MUTED, lw=1, ls="--")
    axes[1].text(1.05, 1.58, "1.5x", color=MUTED, fontsize=8)
    axes[1].set_ylabel("p95 mission time / mission time alone")
    axes[1].set_title("P1's agents saturate the Thor with one drone")
    for ax in axes:
        _x(ax)
        ax.set_xlabel("Drones sharing one Thor")
        _style(ax, "y")
    axes[0].legend(fontsize=8, loc="lower left")
    fig.suptitle("Unlimited state memory, Gemma-4-26B-A4B costs on the Thor (simulated, 12 h per point, 3 seeds)",
                 x=0.01, ha="left", fontsize=9.5, color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig_headroom(cells, path):
    rows = [("stepwise_qwen_think", "Step-wise, Qwen3.5 thinking"), ("p1_toolcalling", "P1 tool calling")]
    budgets = (1, 2, 4, 8)
    fig, axes = plt.subplots(len(rows), len(budgets), figsize=(12, 6.2), sharex=True)
    for i, (wl, lab) in enumerate(rows):
        top = 0
        for j, b in enumerate(budgets):
            ax = axes[i][j]
            cs = [cell(cells, "thor_gemma", wl, b, n) for n in NS]
            ok = [c["default_fail_share"] <= 0.01 for c in cs]
            d = [c["e_default"] / 1e3 if o else None for c, o in zip(cs, ok)]
            best = [c["e_best_any"] / 1e3 if o else None for c, o in zip(cs, ok)]
            inf = [c["e_inf"] / 1e3 for c in cs]
            ax.plot(NS, inf, color=MUTED, lw=1.5, ls="--", label="unlimited memory (bound)")
            ax.plot(NS, d, color=C1, lw=2, marker="o", ms=6, markeredgecolor=SURF, markeredgewidth=1.5,
                    label="SGLang default")
            ax.plot(NS, best, color=C2, lw=2, marker="o", ms=4, markeredgecolor=SURF, markeredgewidth=1,
                    label="best of 12 policies")
            top = max(top, max(x for x in d + inf if x))
            if i == 0:
                ax.set_title(f"{b} GiB for state", fontsize=10)
            if j == 0:
                ax.set_ylabel(f"{lab}\nkJ per successful mission")
            if i == len(rows) - 1:
                ax.set_xlabel("Drones per box")
            _x(ax)
            _style(ax, "y")
        for ax in axes[i]:
            ax.set_ylim(0, top * 1.08)
    h, l = axes[0][0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, fontsize=9, bbox_to_anchor=(0.5, -0.03))
    fig.suptitle("The gap to unlimited memory is capacity: no policy closes it (Thor, Gemma state layout; "
                 "cells where >1% of missions cannot fit are left out)", x=0.01, ha="left", fontsize=9.5, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig_retention(cells, path):
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for wl, lab, col in SERIES:
        ys = [cell(cells, "thor_gemma", wl, 16, n)["retention_value"] * 100 for n in NS]
        ax.plot(NS, ys, color=col, lw=2, marker="o", ms=6, markeredgecolor=SURF, markeredgewidth=1.5, label=lab)
        ax.annotate(f"{ys[-1]:.0f}%", (16, ys[-1]), xytext=(6, 0), textcoords="offset points", va="center",
                    fontsize=8, color=INK2)
    _x(ax)
    ax.set_xlim(0.85, 22)
    ax.set_ylim(bottom=0)
    ax.axhline(0, color=BASE, lw=1)
    ax.set_xlabel("Drones sharing one Thor")
    ax.set_ylabel("Energy per success saved by keeping state (%)")
    ax.set_title("Keeping state matters more as the box fills up", fontsize=10.5)
    ax.text(0.01, -0.22, "Default (keep while memory allows) vs. dropping state at every tool wait; 16 GiB for state.",
            transform=ax.transAxes, fontsize=7.5, color=INK2)
    _style(ax, "y")
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def paradigm_compare():
    """P1's own D1-D3: P1 Reflexion measured on the Thor vs. the step-wise agent projected onto
    the Thor (one drone; Gemma's prefill/decode rates and board power applied to the step-wise
    missions' token counts and real-time flights)."""
    out = {"p1_reflexion_measured": {}, "stepwise_projected": {}}
    runs = {}
    for f in glob.glob(str(REPO / "data/p1_thor_drone/*/*/instance_*/run_*/run_meta.json")):
        d = json.loads(open(f).read())
        if d["task_id"].startswith("D"):
            runs.setdefault(d["task_id"].split("_")[0], []).append(d)
    for t, rs in sorted(runs.items()):
        e = [r["workflow_energy_J"] for r in rs]
        ok = sum(r["final_result"] == "pass" for r in rs)
        out["p1_reflexion_measured"][t] = dict(
            runs=len(rs), passed=ok, kj_per_run=st.mean(e) / 1e3, kj_per_success=(sum(e) / ok / 1e3) if ok else None,
            minutes_median=st.median(r["workflow_time_s"] for r in rs) / 60,
            llm_share=sum(r["llm_time_s"] for r in rs) / sum(r["workflow_time_s"] for r in rs))
    thor = thor_device()
    for key in ("stepwise_qwen_think", "stepwise_qwen_nothink", "stepwise_k2_high", "stepwise_k2_low"):
        w = workloads()[key]()
        for tag, label in (("_d1/", "D1"), ("_d23/", "D2+D3")):
            ms = [m for m in w.missions if tag in m.mid]
            es, ts = [], []
            for m in ms:
                llm = 0.0
                for i, c in enumerate(m.calls):
                    pf = c.prompt - (max(w.shared, c.cached) if i else w.shared)
                    llm += max(0, pf) / thor.prefill + c.out * thor.step(1, w.shared + c.prompt + c.out / 2)
                tot = llm + sum(m.waits)
                es.append(thor.p_active * llm + thor.p_idle * (tot - llm))
                ts.append(tot)
            ok = sum(m.success for m in ms)
            out["stepwise_projected"][f"{key} {label}"] = dict(
                missions=len(ms), succeeded=ok, kj_per_mission=st.mean(es) / 1e3,
                kj_per_success=(sum(es) / ok / 1e3) if ok else None, minutes_median=st.median(ts) / 60)
    return out


def main():
    d = json.loads((OUT / "sim.json").read_text())
    cells = d["cells"]
    (OUT / "figures").mkdir(parents=True, exist_ok=True)
    fig_scaling(cells, OUT / "figures/scaling.png")
    fig_headroom(cells, OUT / "figures/headroom.png")
    fig_retention(cells, OUT / "figures/retention_value.png")
    ok = [c for c in cells if c["default_fail_share"] <= 0.01 and c["inf_fail_share"] <= 0.01]
    summary = dict(
        paradigm=paradigm_compare(),
        by_scenario={s: dict(cells=len([c for c in ok if c["scenario"] == s]),
                             found_gt_5pct=sum(c["found_vs_default"] > 0.05 for c in ok if c["scenario"] == s),
                             found_max=max(c["found_vs_default"] for c in ok if c["scenario"] == s),
                             bound_gt_10pct=sum(c["bound_vs_default"] > 0.10 for c in ok if c["scenario"] == s),
                             adaptive_vs_best_fixed_max=max(c["adaptive_vs_best_fixed"] for c in ok if c["scenario"] == s),
                             value_exact_max=max(c["value_exact_vs_default"] for c in ok if c["scenario"] == s))
                     for s in sorted({c["scenario"] for c in ok})})
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()

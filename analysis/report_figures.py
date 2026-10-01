"""Figures and numbers for reports/2026-10-01-workload-opportunity.

Inputs:  data/p1_thor_drone, data/p1_thor_toolcalling (P1 Thor traces),
         data/ws_runs/<run>/ (aerogen runs + calibration copied back from the WS).
Outputs: reports/2026-10-01-workload-opportunity/figures/*.png and report_data.json.

Usage: python3 -m analysis.report_figures
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from analysis.sessions import (REPO, load_aerogen, load_p1, pooled, session_metrics,  # noqa: E402
                               thor_prefill_rate)

OUT = REPO / "reports/2026-10-01-workload-opportunity"
FIG = OUT / "figures"
WS = REPO / "data/ws_runs"

# Reference palette (dataviz skill), light mode; validated for these 4 slots in this order.
C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, MUTED, GRID, BASE, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "font.family": "sans-serif", "font.size": 10, "text.color": INK,
    "axes.edgecolor": BASE, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "grid.linestyle": "-",
    "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 11,
    "axes.titleweight": "semibold", "axes.titlelocation": "left", "legend.frameon": False,
})


def _style(ax, grid_axis="x"):
    ax.grid(True, axis=grid_axis)
    ax.grid(False, axis="y" if grid_axis == "x" else "x")
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def calibration(path: Path) -> dict:
    cal = json.loads(path.read_text())
    toks = np.array([r["cold"]["prompt_tokens"] for r in cal["prefill"]])
    secs = np.array([r["cold"]["s"] for r in cal["prefill"]])
    joules = np.array([r["cold"]["j"] for r in cal["prefill"]])
    slope, icpt = np.polyfit(toks, secs, 1)
    jslope, jicpt = np.polyfit(toks, joules, 1)
    big = toks > 6000
    return dict(raw=cal, prefill_tok_s=float(np.median(toks[big] / secs[big])),
                prefill_fit_s=(float(icpt), float(slope)), prefill_fit_j=(float(jicpt), float(jslope)),
                j_per_prefill_tok=float(np.median(joules[big] / toks[big])),
                idle_w=cal["idle_w"], decode=cal["decode"])


def energy_between(nvml_rows, t0, t1):
    """GPU energy (J) between two monotonic times, from the cumulative NVML counter."""
    xs = [r for r in nvml_rows if "energy_mj" in r]
    ts = np.array([r["t_mono"] for r in xs])
    es = np.array([r["energy_mj"] for r in xs]) / 1000.0
    if len(ts) < 2 or t1 <= ts[0] or t0 >= ts[-1]:
        return None
    return float(np.interp(t1, ts, es) - np.interp(t0, ts, es))


def load_ws_run(name, cal):
    d = WS / name
    if not (d / "sessions").exists():
        return None
    sessions = load_aerogen(d, name, cal["prefill_tok_s"])
    nvml = [json.loads(l) for l in open(d / "nvml.jsonl")] if (d / "nvml.jsonl").exists() else []
    man = json.loads((d / "manifest.json").read_text())
    return dict(name=name, dir=d, sessions=sessions, nvml=nvml, manifest=man)


def run_summary(run, cal):
    # Every mission that ran spends energy; errored missions (e.g. context outgrew a capped
    # pool) are charged to the run, and energy is reported per completed and per
    # successful mission.
    ss = list(run["sessions"])
    done = [s for s in ss if s.status == "done"]
    if not done:
        return None
    p = pooled(done, cal["prefill_tok_s"])
    # Energy: whole-run GPU energy divided by missions (concurrency shares the GPU), plus
    # the per-mission idle share for single-session runs.
    man = run["manifest"]
    e_run = energy_between(run["nvml"], min(s.t0 for s in ss), max(s.t1 for s in ss))
    span = max(s.t1 for s in ss) - min(s.t0 for s in ss)
    ms = [session_metrics(s, cal["prefill_tok_s"]) for s in ss]
    uncached = sum(m["prompt"] - m["cached"] for m in ms)
    # Tokens that were in the previous call's context but had to be prefilled again.
    reprefill = 0
    for s in ss:
        for a, b in zip(s.calls, s.calls[1:]):
            reusable = a["prompt"] + a["completion"]
            reprefill += max(0, min(b["prompt"], reusable) - b["cached"])
    # Energy the GPU spends while *no* call is running (all sessions waiting on tools).
    iv = sorted((c["t0"], c["t1"]) for s in ss for c in s.calls)
    busy, c0, c1 = [], None, None
    for a, b in iv:
        if c1 is None or a > c1:
            if c1 is not None:
                busy.append((c0, c1))
            c0, c1 = a, b
        else:
            c1 = max(c1, b)
    if c1 is not None:
        busy.append((c0, c1))
    e_busy = sum(energy_between(run["nvml"], a, b) or 0 for a, b in busy)
    busy_s = sum(b - a for a, b in busy)
    p.update(
        call_power_w=(e_busy / busy_s) if busy_s else None,
        idle_power_w=((e_run - e_busy) / (span - busy_s)) if e_run and span > busy_s else None,
        idle_energy_share=(1 - e_busy / e_run) if e_run else None,
        busy_time_share=sum(b - a for a, b in busy) / span if span else None,
        concurrency=man["args"]["concurrency"], effort=man["args"]["effort"],
        missions=len(ss), completed=len(done), errored=len(ss) - len(done),
        succeeded=sum(1 for s in done if s.success), energy_j=e_run, span_s=span,
        energy_per_mission_j=(e_run / len(done)) if e_run else None,
        energy_per_success_j=(e_run / max(1, sum(1 for s in done if s.success))) if e_run else None,
        missions_per_hour=len(done) / span * 3600,
        uncached_tokens_per_mission=uncached / len(ss),
        reprefill_tokens_per_mission=reprefill / len(ss),
        reprefill_j_per_mission=reprefill / len(ss) * cal["j_per_prefill_tok"],
        mission_s_p50=st.median(m["total_s"] for m in ms),
    )
    return p


ROW_ORDER = [("P1 Reflexion · basic (B)", "P1"), ("P1 Reflexion · advanced (A)", "P1"),
             ("P1 Reflexion · AeroEval (D/F)", "P1"), ("P1 tool-calling · basic (B)", "P1"),
             ("P1 tool-calling · advanced (A)", "P1"), ("aerogen · low effort (WS)", "AG"),
             ("aerogen · medium effort (WS)", "AG"), ("aerogen · high effort (WS)", "AG")]


def fig_time_split(rows, path):
    fig, ax = plt.subplots(figsize=(8.6, 0.46 * len(rows) + 1.3))
    names = [r["label"] for r in rows]
    y = np.arange(len(rows))[::-1]
    left = np.zeros(len(rows))
    segs = [("decode", "share_decode", C1), ("tool wait", "share_tool", C2),
            ("prefill", "share_prefill", C3), ("other", "share_other", C4)]
    for lab, key, col in segs:
        v = np.array([r[key] for r in rows]) * 100
        ax.barh(y, v, left=left, height=0.56, color=col, label=lab, edgecolor=SURF, linewidth=2)
        left += v
    for yi, r in zip(y, rows):
        ax.text(101.5, yi, f"p50 session {r['session_s_p50'] / 60:.1f} min", va="center",
                fontsize=8.5, color=INK2)
    ax.set_yticks(y, names)
    ax.set_xlim(0, 100)
    ax.set_xlabel("share of session wall time (%)")
    ax.set_title("Where session time goes")
    ax.legend(ncol=4, loc="upper left", bbox_to_anchor=(0, -0.16 - 0.02 * (7 - len(rows))), fontsize=9)
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig_retention(rows, path):
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 0.42 * len(rows) + 1.7), sharey=True)
    fig.subplots_adjust(left=0.2, right=0.98, wspace=0.28, top=0.88, bottom=0.2)
    y = np.arange(len(rows))[::-1]
    panels = [("reuse", "Prompt tokens served from cache", "%", 1),
              ("paused_mem_share", "KV memory-time held while waiting", "%", 1),
              ("retention_saving", "LLM time saved by keeping state", "%", 1)]
    for ax, (key, title, unit, _) in zip(axes, panels):
        v = np.array([r[key] for r in rows]) * 100
        cols = [C1 if r["family"] == "P1" else C2 for r in rows]
        ax.barh(y, v, height=0.56, color=cols)
        for yi, vi in zip(y, v):
            ax.text(vi + 1.5, yi, f"{vi:.1f}{unit}" if vi < 10 else f"{vi:.0f}{unit}",
                    va="center", fontsize=8.5, color=INK)
        ax.set_xlim(0, 118)
        ax.set_xticks([0, 50, 100], ["0", "50", "100 %"])
        ax.set_title(title, fontsize=10)
        _style(ax)
    axes[0].set_yticks(y, [r["label"] for r in rows])
    from matplotlib.patches import Patch
    axes[0].legend(handles=[Patch(color=C1, label="P1 drone agent (Thor, Gemma-4-26B)"),
                            Patch(color=C2, label="aerogen tool-calling agent (WS, K2-Horizon-7B)")],
                   loc="upper left", bbox_to_anchor=(0, -0.1), ncol=2, fontsize=9)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _timeline(ax, s, title, xmax_min=None):
    t0 = s.t0
    for c in s.calls:
        ax.plot([(c["t0"] - t0) / 60, (c["t1"] - t0) / 60],
                [c["prompt"] / 1000, (c["prompt"] + c["completion"]) / 1000],
                color=C1, lw=2, solid_capstyle="round")
    for a, b in zip(s.calls, s.calls[1:]):
        held = (a["prompt"] + a["completion"]) / 1000
        ax.plot([(a["t1"] - t0) / 60, (b["t0"] - t0) / 60], [held, held], color=C2, lw=2,
                solid_capstyle="round")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("time since session start (min)")
    ax.set_ylabel("context held (K tokens)")
    if xmax_min:
        ax.set_xlim(0, xmax_min)
    ax.set_ylim(bottom=0)
    _style(ax, "y")


def fig_timelines(p1_session, ag_session, path):
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 3.6), sharey=True)
    _timeline(axes[0], p1_session, f"P1 Reflexion, task {p1_session.task} (Thor)")
    _timeline(axes[1], ag_session, f"aerogen, task {ag_session.task} (WS, low effort)")
    from matplotlib.lines import Line2D
    axes[0].legend(handles=[Line2D([], [], color=C1, lw=2, label="LLM call (prompt → prompt + output)"),
                            Line2D([], [], color=C2, lw=2, label="between calls (tool running, state held)")],
                   loc="upper left", bbox_to_anchor=(0, -0.2), ncol=2, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig_cdf(groups, path):
    fig, axes = plt.subplots(1, len(groups), figsize=(5.2 * len(groups), 3.3), sharey=True, sharex=True)
    axes = np.atleast_1d(axes)
    for ax, (title, sessions) in zip(axes, groups):
        calls = np.sort([c["t1"] - c["t0"] for s in sessions for c in s.calls])
        waits = np.sort([w["t1"] - w["t0"] for s in sessions for w in s.waits if w["t1"] - w["t0"] > 0.5])
        for arr, col, lab, ha in [(calls, C1, "LLM call", "right"), (waits, C2, "tool wait (> 0.5 s)", "left")]:
            if len(arr):
                ax.plot(arr, np.arange(1, len(arr) + 1) / len(arr), color=col, lw=2, label=lab)
                med = float(np.median(arr))
                ax.plot([med], [0.5], "o", color=col, ms=7, markeredgecolor=SURF, markeredgewidth=2)
                ax.text(med * (0.8 if ha == "right" else 1.25), 0.5, f"p50 {med:.0f} s", color=INK2,
                        fontsize=8.5, ha=ha, va="center")
        ax.set_xscale("log")
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("duration (s, log scale)")
        _style(ax, "both")
    axes[0].set_ylabel("fraction of events ≤ x")
    axes[0].legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig_calibration(cal, path):
    raw = cal["raw"]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.4))
    ax = axes[0]
    toks = np.array([r["cold"]["prompt_tokens"] for r in raw["prefill"]]) / 1000
    for key, col, lab in [("cold", C1, "cold (nothing cached)"), ("warm", C2, "warm (prefix cached)")]:
        ax.plot(toks, [r[key]["s"] for r in raw["prefill"]], "o", color=col, ms=5, label=lab,
                markeredgecolor=SURF, markeredgewidth=1.5)
    ax.set_xlabel("prompt length (K tokens)")
    ax.set_ylabel("time to first token (s)")
    ax.set_title("Prefill cost, K2-Horizon-7B on one A5000", fontsize=10)
    ax.legend(loc="upper left", fontsize=9)
    _style(ax, "both")
    ax = axes[1]
    b = [d["batch"] for d in raw["decode"]]
    jpt = [d["j_per_tok"] for d in raw["decode"]]
    ax.plot(b, jpt, color=C1, lw=2, marker="o", ms=6, markeredgecolor=SURF, markeredgewidth=1.5)
    for bi, ji in zip(b, jpt):
        ax.text(bi, ji * 1.08, f"{ji:.2f} J", ha="center", fontsize=8.5, color=INK2)
    ax.set_xscale("log", base=2)
    ax.set_xticks(b, [str(x) for x in b])
    ax.set_xlabel("concurrent decodes (batch size)")
    ax.set_ylabel("GPU energy per output token (J)")
    ax.set_title("Decode energy per token vs batch size", fontsize=10)
    ax.set_ylim(0, max(jpt) * 1.25)
    _style(ax, "y")
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig_concurrency(groups, path):
    """groups: [(label, [summary...]), ...] - grouped bars over concurrency N."""
    ns = sorted({x["concurrency"] for _, g in groups for x in g})
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.4))
    panels = [("reuse", "Prompt tokens served from cache (%)", 100, "{:.0f}"),
              ("reprefill_tokens_per_mission", "Re-prefilled tokens per mission (K)", 1e-3, "{:.1f}"),
              ("energy_per_mission_j", "GPU energy per mission (kJ)", 1e-3, "{:.1f}")]
    w = 0.36
    cols = [C1, C2]
    for ax, (key, title, scale, fmt) in zip(axes, panels):
        vmax = 0
        for gi, (lab, g) in enumerate(groups):
            by_n = {x["concurrency"]: x for x in g}
            xs = [i + (gi - (len(groups) - 1) / 2) * w for i, n in enumerate(ns) if n in by_n]
            vs = [(by_n[n][key] or 0) * scale for n in ns if n in by_n]
            ax.bar(xs, vs, width=w * 0.92, color=cols[gi], label=lab)
            for xi, vi in zip(xs, vs):
                ax.text(xi, vi, fmt.format(vi), ha="center", va="bottom", fontsize=8, color=INK)
            vmax = max([vmax] + vs)
        ax.set_xticks(range(len(ns)), [f"N={n}" for n in ns])
        ax.set_title(title, fontsize=10)
        ax.set_ylim(0, vmax * 1.2 if vmax > 0 else 1)
        _style(ax, "y")
    axes[0].legend(loc="upper left", bbox_to_anchor=(0, -0.12), ncol=len(groups), fontsize=9)
    fig.suptitle("aerogen on one A5000 (K2-Horizon-7B, KV pool 25.4K tokens), closed-loop sessions",
                 x=0.01, ha="left", fontsize=10, color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig_pool(runs, path):
    """KV pool over time: memory used by running requests vs retained (evictable) cache, the
    pool capacity, and below it queued requests and cumulative evicted tokens."""
    fig, axes = plt.subplots(2, len(runs), figsize=(12, 5.2), sharex="col",
                             gridspec_kw={"height_ratios": [2, 1]})
    for j, (run, title) in enumerate(runs):
        rows = [json.loads(l) for l in open(run["dir"] / "sglang_metrics.jsonl")]
        rows = [r for r in rows if "m" in r]
        t0 = rows[0]["t_mono"]
        t = np.array([(r["t_mono"] - t0) / 60 for r in rows])
        g = lambda k: np.array([r["m"].get(k, np.nan) for r in rows], dtype=float)
        used, evict = g("sglang:kv_used_tokens") / 1000, g("sglang:kv_evictable_tokens") / 1000
        cap = float(np.nanmax(g("sglang:max_total_num_tokens"))) / 1000
        ev_key = next(k for k in rows[-1]["m"] if k.startswith("sglang:evicted_tokens_total"))
        evicted = g(ev_key)
        first = evicted[~np.isnan(evicted)][0] if np.any(~np.isnan(evicted)) else 0.0
        evicted = (np.nan_to_num(evicted, nan=first) - first) / 1000
        n = run["manifest"]["args"]["concurrency"]
        queue_any = np.nanmax(g("sglang:num_queue_reqs")) > 0
        title = (f"N={n} sessions, {float(np.nanmax(g('sglang:max_total_num_tokens'))) / 1000:.1f}K-token pool: "
                 + ("requests queue for memory" if queue_any else "no queueing"))
        ax = axes[0][j]
        ax.fill_between(t, 0, used, color=C1, alpha=0.85, lw=0, label="in use by running requests")
        ax.fill_between(t, used, used + evict, color=C2, alpha=0.35, lw=0, label="retained cache (waiting sessions + shared prompt)")
        ax.axhline(cap, color=INK2, lw=1)
        ax.text(t[-1], cap * 1.02, f"pool {cap:.1f}K", ha="right", va="bottom", fontsize=8.5, color=INK2)
        ax.set_ylim(0, cap * 1.15)
        ax.set_title(title, fontsize=10)
        if j == 0:
            ax.set_ylabel("KV tokens (K)")
        _style(ax, "y")
        ax = axes[1][j]
        ax.plot(t, g("sglang:num_queue_reqs"), color=C2, lw=1.5, label="queued requests")
        ax2max = max(1.0, float(np.nanmax(g("sglang:num_queue_reqs"))))
        ax.set_ylim(0, ax2max * 1.3 + 0.5)
        ax.text(0.99, 0.92, f"{evicted[-1]:.0f}K tokens evicted in total", transform=ax.transAxes,
                ha="right", va="top", fontsize=8.5, color=INK2)
        ax.set_xlabel("time since run start (min)")
        if j == 0:
            ax.set_ylabel("queued requests")
        _style(ax, "y")
    h, l = axes[0][0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, fontsize=9, bbox_to_anchor=(0.5, -0.04), frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    data = {}
    R = load_p1(REPO / "data/p1_thor_drone", "P1 Reflexion")
    T = load_p1(REPO / "data/p1_thor_toolcalling", "P1 tool-calling")
    thor_rate = thor_prefill_rate(R + T)
    data["thor_prefill_tok_s"] = thor_rate
    cal = calibration(WS / "calib_k2_tp1_gpu0.json")
    data["ws_calibration"] = {k: v for k, v in cal.items() if k != "raw"}

    rows = []
    for label, fam, S, cls in [
        (ROW_ORDER[0][0], "P1", R, "B"), (ROW_ORDER[1][0], "P1", R, "A"), (ROW_ORDER[2][0], "P1", R, "D/F"),
        (ROW_ORDER[3][0], "P1", T, "B"), (ROW_ORDER[4][0], "P1", T, "A")]:
        ss = [s for s in S if s.cls == cls]
        if ss:
            p = pooled(ss, thor_rate)
            rows.append(dict(label=label, family=fam, **p))
    ws_runs = {}
    for name, label in [("e1_low_n1", ROW_ORDER[5][0]), ("e1_medium_n1", ROW_ORDER[6][0]),
                        ("e1_high_n1", ROW_ORDER[7][0])]:
        run = load_ws_run(name, cal)
        if run:
            ws_runs[name] = run
            ss = [s for s in run["sessions"] if s.status == "done"]
            if ss:
                rows.append(dict(label=label, family="AG", **pooled(ss, cal["prefill_tok_s"])))
    for r in rows:
        # Share of LLM time that keeping state saves, relative to recomputing every prompt.
        rate = thor_rate if r["family"] == "P1" else cal["prefill_tok_s"]
        r["retention_saving"] = r["ceiling_of_llm"] / (1 + r["ceiling_of_llm"])
        r["prefill_rate_used"] = rate
    data["rows"] = rows

    fig_time_split(rows, FIG / "time_split.png")
    fig_retention(rows, FIG / "retention_value.png")
    fig_calibration(cal, FIG / "ws_costs.png")
    p1_example = next(s for s in R if s.task == "A6" and "instance_1__run_1" in s.sid)
    if "e1_low_n1" in ws_runs:
        ag = [s for s in ws_runs["e1_low_n1"]["sessions"] if s.success]
        ag_example = max(ag, key=lambda s: len(s.calls)) if ag else None
        if ag_example:
            fig_timelines(p1_example, ag_example, FIG / "timelines.png")
        fig_cdf([("P1 Reflexion (Thor, all classes)", R),
                 ("aerogen (WS, low effort)", ws_runs["e1_low_n1"]["sessions"])], FIG / "durations_cdf.png")

    groups = []
    for effort, names in [("low", ["e1_low_n1", "e2_low_n2", "e2_low_n4", "e2_low_n8"]),
                          ("high", ["e1_high_n1", "e2_high_n2", "e2_high_n4"])]:
        g = []
        for name in names:
            run = ws_runs.get(name) or load_ws_run(name, cal)
            if run:
                ws_runs[name] = run
                sm = run_summary(run, cal)
                if sm:
                    sm["run"] = name
                    g.append(sm)
        data[f"concurrency_{effort}"] = g
        if g:
            groups.append((f"{effort} reasoning effort", g))
    if any(len(g) >= 2 for _, g in groups):
        pr = [(ws_runs.get(n) or load_ws_run(n, cal), n) for n in ["e2_low_n8", "e2_low_n4_kv16k"]]
        pr = [(r, lab) for r, lab in pr if r and (r["dir"] / "sglang_metrics.jsonl").exists()]
        if pr:
            fig_pool(pr, FIG / "pool_timeline.png")
            for r, _ in pr:
                rows_m = [json.loads(l) for l in open(r["dir"] / "sglang_metrics.jsonl")]
                rows_m = [x for x in rows_m if "m" in x]
                k = next(k for k in rows_m[-1]["m"] if k.startswith("sglang:evicted_tokens_total"))
                data.setdefault("pool_runs", {})[r["name"]] = {
                    "evicted_tokens": rows_m[-1]["m"][k] - rows_m[0]["m"].get(k, 0),
                    "queue_max": max(x["m"].get("sglang:num_queue_reqs", 0) for x in rows_m),
                    "queue_mean": st.mean(x["m"].get("sglang:num_queue_reqs", 0) for x in rows_m),
                    "retracted": max(v for x in rows_m for kk, v in x["m"].items() if kk.startswith("sglang:num_retracted_reqs"))}
    (OUT / "report_data.json").write_text(json.dumps(data, indent=1, default=float))
    print(json.dumps({"rows": [(r["label"], round(r["reuse"], 3), round(r["retention_saving"], 4),
                                round(r["paused_mem_share"], 3)) for r in rows],
                      "concurrency": [(c["run"], c["missions"], round(c["reuse"], 3),
                                       round(c["reprefill_tokens_per_mission"]),
                                       c["energy_per_mission_j"], c["idle_energy_share"])
                                      for k in ("concurrency_low", "concurrency_high")
                                      for c in data.get(k, [])]}, indent=1))


if __name__ == "__main__":
    main()

"""Figures for the options comparison (reports/2026-10-06-options/figures/), from the experiments' JSON files.

    python -m analysis.options_figures      (skips any experiment whose JSON is not there yet)
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from analysis.report_figures import C1, C2, C3, C4, INK2, MUTED, _style  # noqa: E402
from analysis.sessions import REPO  # noqa: E402

D = REPO / "reports/2026-10-06-options"
F = D / "figures"


def _load(name):
    p = D / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def fig_a_e1():
    a = _load("a_e1")
    if not a:
        return
    # one panel per model: the 26B through llama.cpp, and gemma-4-E4B
    cells = {}
    for k, v in a["cells"].items():
        run, rest = k.split("|", 1)
        if "g26b" in run:
            cells["26B · " + rest] = v
        elif "e4b" in run:
            cells["E4B · " + rest] = v
    return _fig_a_e1_panels(cells)


def _fig_a_e1_panels(cells):
    groups = [("thor_rfx", "loop", "Thor Reflexion:\nlooped on P1's device"),
              ("thor_rfx", "control", "Thor Reflexion:\nfinished on P1's device"),
              ("thor_tc", "loop", "Thor tool calling:\nlooped on P1's device"),
              ("thor_tc", "control", "Thor tool calling:\nfinished on P1's device"),
              ("o32_e4b", "loop", "Orin 32 E4B:\nlooped on P1's device"), ("o32_e4b", "control", "Orin 32 E4B:\nfinished")]
    groups = [g for g in groups if any(k.endswith(f"|{g[0]}|{g[1]}") for k in cells)]
    order = ["26B · greedy", "26B · sampled:0", "E4B · greedy", "E4B · sampled:0", "E4B · sampled:1"]
    colors = {"26B · greedy": C2, "26B · sampled:0": C1, "E4B · greedy": C4, "E4B · sampled:0": C3, "E4B · sampled:1": C3}
    names = {"26B · greedy": "gemma-4-26B (4-bit, llama.cpp), greedy = P1's protocol",
             "26B · sampled:0": "gemma-4-26B, Gemma's default sampling",
             "E4B · greedy": "gemma-4-E4B (SGLang), greedy", "E4B · sampled:0": "gemma-4-E4B, sampling (2 seeds)"}
    fig, ax = plt.subplots(figsize=(10, 4.2))
    seen, x = set(), 0.0
    ticks = []
    for src, kind, label in groups:
        present = [a for a in order if f"{a}|{src}|{kind}" in cells]
        w = 0.8 / max(1, len(present))
        for j, a in enumerate(present):
            c = cells[f"{a}|{src}|{kind}"]
            xi = x + (j - (len(present) - 1) / 2) * w
            lo, hi = c["loop_ci"] or (c["loop_rate"], c["loop_rate"])
            ax.bar(xi, max(c["loop_rate"], 0.004), w * 0.88, color=colors[a],
                   label=names.get(a) if names.get(a) and a not in seen else None)
            ax.errorbar([xi], [c["loop_rate"]], yerr=[[c["loop_rate"] - lo], [hi - c["loop_rate"]]], fmt="none",
                        ecolor=INK2, lw=0.7, capsize=2)
            ax.text(xi, hi + 0.02, f"{c['loops']}/{c['n']}", ha="center", fontsize=7, color=INK2)
            seen.add(a)
        ticks.append((x, label))
        x += 1.0
    ax.set_xticks([t for t, _ in ticks], [l for _, l in ticks], fontsize=8)
    ax.set_ylabel("share of calls that loop (95% CI)")
    ax.set_ylim(0, 1.08)
    ax.set_title("A-E1: P1's recorded prompts replayed on the WS: does sampling remove the loops?", loc="left",
                 fontweight="bold")
    _style(ax, "y")
    ax.legend(fontsize=7.5, frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(F / "a_e1_loops.png", dpi=160)
    plt.close(fig)


def fig_b():
    b, b2 = _load("b_e1"), _load("b_e2")
    if not b or not b2:
        return
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.6), gridspec_kw={"width_ratios": [1, 1.2]})
    rows = [(k, v) for k, v in b.items() if k.endswith("-all")]
    labels = ["E4B greedy" if "greedy" in k else "E4B sampled" for k, _ in rows]
    a1.bar(range(len(rows)), [v["resume_out_median"] for _, v in rows], 0.5, color=C1, label="median")
    a1.bar(range(len(rows)), [v["resume_out_p90"] for _, v in rows], 0.5, color=C1, alpha=0.35, label="p90")
    a1.axhline(300, color=C2, lw=1, ls="--")
    a1.text(len(rows) - 0.6, 310, "B-E1 rule: 300", color=C2, fontsize=8, ha="right")
    a1.set_xticks(range(len(rows)), labels)
    a1.set_ylabel("output tokens after a tool result")
    a1.set_title("Steps stay short", loc="left", fontweight="bold")
    a1.legend(fontsize=8, frameon=False)
    _style(a1, "y")
    p1 = b2["p1_reflexion_measured"]
    proj = b2["stepwise_e4b_projected"]
    bars = [("P1 Reflexion D1\n(measured)", p1["D1"]["kj_per_success"], C2),
            ("P1 Reflexion D2\n(measured)", p1["D2"]["kj_per_success"], C2),
            ("E4B step-wise D1\n(projected, strict)", proj["e4b_greedy D1 @ thor_gemma26b"]["kj_per_strict_success"], C1),
            ("E4B step-wise D2+D3\n(projected, strict)", proj["e4b_greedy D2+D3 @ thor_gemma26b"]["kj_per_strict_success"], C1)]
    a2.bar(range(len(bars)), [x[1] or 0 for x in bars], 0.55, color=[x[2] for x in bars])
    for i, x in enumerate(bars):
        a2.text(i, (x[1] or 0) + 8, f"{x[1]:.0f}", ha="center", fontsize=8, color=INK2)
    a2.set_xticks(range(len(bars)), [x[0] for x in bars], fontsize=7.5)
    a2.set_ylabel("kJ per success (Thor prices)")
    a2.set_title("Energy per success, P1's delivery tasks", loc="left", fontweight="bold")
    _style(a2, "y")
    fig.tight_layout()
    fig.savefig(F / "b_e1_e2.png", dpi=160)
    plt.close(fig)


def fig_ret():
    r = _load("ret_e1")
    if not r or not r.get("live"):
        return
    rows = sorted(r["live"], key=lambda x: (x["no_reuse"], x["n"]))
    fig, ax = plt.subplots(figsize=(7, 3.4))
    xs = range(len(rows))
    ax.bar([x - 0.2 for x in xs], [(x["energy_per_completed_j"] or 0) / 1e3 for x in rows], 0.38, color=C1, label="live (WS)")
    ax.bar([x + 0.2 for x in xs], [x["sim"]["energy_per_session_j"] / 1e3 for x in rows], 0.38, color=MUTED, label="simulator")
    ax.set_xticks(list(xs), [f"N={x['n']}" + (" no reuse" if x["no_reuse"] else "") for x in rows])
    ax.set_ylabel("kJ per completed session (GPU)")
    ax.set_title("RET-E1: P1's Orin 32 granite traffic, live vs simulated", loc="left", fontweight="bold")
    _style(ax, "y")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(F / "ret_e1.png", dpi=160)
    plt.close(fig)


def fig_d():
    d = _load("d_e2")
    if not d:
        return
    pols = ["default", "pin", "admit4", "both"]
    groups = sorted({(r["pool"], r["n"]) for r in d})
    fig, ax = plt.subplots(figsize=(8, 3.4))
    w = 0.2
    for j, p in enumerate(pols):
        ys = []
        for g in groups:
            r = next((x for x in d if (x["pool"], x["n"]) == g and x["policy"] == p), None)
            ys.append((r["energy_per_completed_j"] or 0) / 1e3 if r else 0)
        ax.bar([i + (j - 1.5) * w for i in range(len(groups))], ys, w * 0.9, color=[MUTED, C1, C4, C3][j], label=p)
    ax.set_xticks(range(len(groups)), [f"pool {g[0]:,}\nN={g[1]}" for g in groups], fontsize=8)
    ax.set_ylabel("kJ per completed session (GPU)")
    ax.set_title("D-E2: vision bursts, P1's Orin 32 E4B traffic on gemma-4-E4B", loc="left", fontweight="bold")
    _style(ax, "y")
    ax.legend(fontsize=8, frameon=False, ncol=4)
    fig.tight_layout()
    fig.savefig(F / "d_e2.png", dpi=160)
    plt.close(fig)


def fig_c():
    c = _load("c_e1")
    if not c or not c.get("domains"):
        return
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    doms = list(c["domains"])
    rs = list(next(iter(c["domains"].values()))["ceiling_jetson"])
    w = 0.8 / len(rs)
    for j, rname in enumerate(rs):
        ax.bar([i + (j - (len(rs) - 1) / 2) * w for i in range(len(doms))],
               [c["domains"][d]["ceiling_jetson"][rname] or 0 for d in doms], w * 0.9,
               color=[C1, C2, C3, C4, MUTED, INK2][j % 6], label=rname)
    ax.axhline(0.20, color=C2, lw=1, ls="--")
    ax.axhline(0.10, color=MUTED, lw=1, ls=":")
    ax.set_xticks(range(len(doms)), [f"tau2 {d}" for d in doms])
    ax.set_ylabel("most kept state could save\n(share of LLM time)")
    ax.set_title("C-E1: tau2-bench with gemma-4-E4B, at each Jetson's price", loc="left", fontweight="bold")
    _style(ax, "y")
    ax.legend(fontsize=7, frameon=False, ncol=2)
    fig.tight_layout()
    fig.savefig(F / "c_e1.png", dpi=160)
    plt.close(fig)


def main():
    F.mkdir(parents=True, exist_ok=True)
    for f in (fig_a_e1, fig_b, fig_ret, fig_d, fig_c):
        try:
            f()
            print("ok", f.__name__)
        except Exception as e:      # one figure's missing field should not stop the others
            print("skip", f.__name__, repr(e)[:200])


if __name__ == "__main__":
    main()

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


TRAFFIC = [k for k in KEYS if k.startswith("t_")]


def fig_context_growth(path):
    """N1: prompt tokens at each call of every traffic run, against the context window."""
    from analysis.p1_repo import load
    fig, axes = plt.subplots(2, 4, figsize=(13, 6.2), sharex=True)
    for ax, k in zip(axes.flat, TRAFFIC):
        runs = load(k)
        win = max(r["ctx"] or 0 for r in runs)
        for r in runs:
            ys = [c["prompt"] / 1e3 for c in r["calls"]]
            if not ys:
                continue
            col = C2 if r["status"] == "input_ceiling" else C1
            ax.plot(range(1, len(ys) + 1), ys, color=col, lw=0.8, alpha=0.35 if col == C1 else 0.6)
        ax.axhline(win / 1e3, color=INK2, lw=1.2, ls="--")
        ax.text(21.5, win / 1e3, f"window {win / 1e3:.0f}K", ha="right", va="bottom", fontsize=8, color=INK2)
        ax.set_title(SHORT[k].replace("Traffic · ", ""), loc="left", fontsize=9.5, fontweight="bold")
        ax.set_yscale("log")
        ax.set_ylim(2, 130)
        ax.set_yticks([2, 5, 10, 20, 50, 100], ["2K", "5K", "10K", "20K", "50K", "100K"])
        ax.minorticks_off()
        ax.set_xlim(0.5, 22)
        _style(ax, "y")
    for ax in axes[1]:
        ax.set_xlabel("LLM call in the run")
    for ax in axes[:, 0]:
        ax.set_ylabel("prompt tokens (log)")
    axes[0, 0].plot([], [], color=C1, label="run (completed or gave up)")
    axes[0, 0].plot([], [], color=C2, label="run ended by window overflow")
    axes[0, 0].legend(fontsize=7.5, loc="upper left", frameon=False)
    fig.suptitle("Traffic contexts only grow: every prompt repeats the previous one and adds a tool result (P1's runs, measured)",
                 x=0.01, ha="left", fontsize=9.5, color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_vlm_burst(path, key="t_o64_gemma", task="special-vehicle", inst="A_kamath_mon_peak", rep=3):
    """N2: one run on Orin 64: the KV pool from the vitals (tokens of running requests, and cached tokens
    no request is using), running requests, the agent's calls and the vision tool's windows."""
    import gzip, os
    from analysis.p1_repo import load
    r = next(x for x in load(key) if x["task"] == task and x["instance"] == inst and x["rep"] == rep)
    t0, t1 = r["calls"][0]["t0"] - 5, r["calls"][-1]["t1"] + 5
    ts, used, cached, q = [], [], [], []
    pool = None
    with gzip.open(os.path.join(r["vitals_dir"], "vitals.jsonl.gz"), "rt") as f:
        for line in f:
            if '"kv_num_running_reqs"' not in line:
                continue
            v = json.loads(line)
            t = v.get("t_monotonic")
            if t is None or not t0 <= t <= t1:
                continue
            ts.append(t - t0)
            used.append((v.get("kv_used_tokens") or 0) / 1e3)
            cached.append((v.get("kv_evictable_tokens") or 0) / 1e3)
            q.append(v.get("kv_num_running_reqs") or 0)
            pool = v.get("kv_max_total_num_tokens") or pool
    fig, (a, b) = plt.subplots(2, 1, figsize=(12, 6.0), sharex=True, gridspec_kw=dict(height_ratios=[1.7, 1]))
    for ax in (a, b):
        for c in r["calls"]:
            ax.axvspan(c["t0"] - t0, c["t1"] - t0, color=C1, alpha=0.10, lw=0)
        for t in r["tools"]:
            if t["tool"] == "ask_vlm":
                ax.axvspan(t["t0"] - t0, t["t1"] - t0, color=C4, alpha=0.16, lw=0)
    a.stackplot(ts, used, cached, colors=[C1, BASE], step="post", alpha=0.9,
                labels=["tokens of running requests", "cached tokens no request is using (evictable)"])
    a.axhline(pool / 1e3, color=INK2, lw=1.2, ls="--")
    a.text(ts[-1], pool / 1e3 + 0.25, f"KV pool {pool / 1e3:.1f}K tokens", ha="right", va="bottom", fontsize=8.5, color=INK2)
    for i, c in enumerate(r["calls"]):
        b.text(c["t0"] - t0 + 2, 4.2, f"call {i + 1}: {c['prompt'] / 1e3:.1f}K prompt,\n{c['cached'] / 1e3:.1f}K from cache",
               fontsize=8, color=C1, va="center")
    # the moment the burst's requests push the agent's paused context out of the pool
    k = next(i for i, (t, cc) in enumerate(zip(ts, cached)) if t > 100 and cc < 0.1)
    a.annotate("the agent's paused context (7.2K tokens)\nis evicted to make room for the burst", xy=(ts[k], 9.4),
               xytext=(ts[k] + 120, 15.2), fontsize=8.5, color=INK2, va="center",
               arrowprops=dict(arrowstyle="->", color=INK2, lw=1))
    a.set_ylabel("KV pool (thousand tokens)")
    a.set_ylim(0, pool / 1e3 * 1.32)
    a.set_title("The vision tool's burst takes the pool; the agent's paused context is evicted and recomputed",
                loc="left", fontweight="bold")
    a.legend(fontsize=8, loc="upper left", frameon=False, ncol=1)
    b.step(ts, q, where="post", color=C3, lw=1.6)
    b.set_ylabel("running requests")
    b.set_ylim(0, 6.8)
    b.set_xlabel("seconds into the run (blue: the agent's LLM calls; yellow: ask_vlm)")
    for ax in (a, b):
        _style(ax, "y")
    fig.suptitle(f"Traffic · Orin 64 · gemma-26B, task '{task}', instance {inst[0]}, repeat {rep} (P1's vitals, 1 s KV samples)",
                 x=0.01, ha="left", fontsize=9.5, color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_cap_raster(path):
    """N3: runs that hit a cap, call by call: caps come in chains on gemma."""
    from analysis.p1_repo import load
    from matplotlib.patches import Patch
    keys = ["t_thor_gemma", "t_o32_e4b"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.4))
    for ax, k in zip(axes, keys):
        runs = [r for r in load(k) if any(c["capped"] for c in r["calls"])]
        runs.sort(key=lambda r: (-sum(c["capped"] for c in r["calls"]), len(r["calls"])))
        for y, r in enumerate(runs):
            for x, c in enumerate(r["calls"]):
                ax.add_patch(plt.Rectangle((x + 0.08, y + 0.1), 0.84, 0.8, color=C2 if c["capped"] else BASE, lw=0))
            ax.text(len(r["calls"]) + 0.4, y + 0.5, "completed" if r["ok"] else r["status"].replace("_", " "),
                    fontsize=6.5, va="center", color=INK2 if r["ok"] else C2)
        ax.set_xlim(0, 25)
        ax.set_ylim(len(runs), 0)
        ax.set_yticks([])
        ax.set_xlabel("LLM call in the run")
        n_after = sum(1 for r in runs for a_, b_ in zip(r["calls"], r["calls"][1:]) if a_["capped"] and b_["capped"])
        n_cap = sum(c["capped"] for r in runs for c in r["calls"])
        ax.set_title(f"{SHORT[k].replace('Traffic · ', '')}: {len(runs)} runs with a capped call;\n"
                     f"{n_after} of {n_cap} capped calls follow a capped call", loc="left", fontsize=9.5, fontweight="bold")
        _style(ax, "x")
    axes[1].legend(handles=[Patch(color=C2, label="call hit its 8,000-token cap"), Patch(color=BASE, label="call finished")],
                   fontsize=8, loc="lower right", frameon=False)
    fig.suptitle("A cap inside a tool call drops the call; the agent retries and caps again (P1's traffic runs, measured)",
                 x=0.01, ha="left", fontsize=9.5, color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def energy_map():
    """Where each configuration's measured board energy goes (shares of run energy)."""
    from analysis.p1_repo import load
    out = {}
    for k in KEYS:
        runs = load(k)
        E = sum(r["energy_J"] for r in runs)
        acc = dict(capped_decode=0.0, other_decode=0.0, prefill=0.0, vision_tool=0.0, other_tools=0.0)
        tool_w = {}
        for r in runs:
            for t in r["tools"]:
                if t["energy"] is not None and t["t1"] > t["t0"]:
                    tool_w.setdefault(t["tool"], []).append(t["energy"] / (t["t1"] - t["t0"]))
        med = {n: sorted(v)[len(v) // 2] for n, v in tool_w.items()}
        for r in runs:
            for c in r["calls"]:
                e = c["energy"] or 0.0
                dur = max(1e-9, c["t1"] - c["t0"])
                pf = e * min(1.0, c["ttft"] / dur)
                acc["prefill"] += pf
                acc["capped_decode" if c["capped"] else "other_decode"] += e - pf
            for t in r["tools"]:
                e = t["energy"] if t["energy"] is not None else med.get(t["tool"], 0.0) * (t["t1"] - t["t0"])
                # Devstral's validate_drone_code runs an LLM call inside the tool: count that energy once.
                for c in r["calls"]:
                    a, b = max(t["t0"], c["t0"]), min(t["t1"], c["t1"])
                    if b > a:
                        e -= (c["energy"] or 0.0) * (b - a) / max(1e-9, c["t1"] - c["t0"])
                acc["vision_tool" if t["tool"] == "ask_vlm" else "other_tools"] += max(0.0, e)
        tot = sum(acc.values())
        shares = {a: v / E for a, v in acc.items()}
        shares["rest"] = max(0.0, 1 - tot / E)
        out[k] = shares
    return out


def fig_energy_map(em, path):
    """N4: shares of measured board energy by phase, per configuration."""
    parts = [("capped_decode", "decode in capped calls", C2), ("other_decode", "other decode", C1),
             ("prefill", "prefill", C3), ("vision_tool", "vision tool (ask_vlm)", C4),
             ("other_tools", "other tools", BASE), ("rest", "between calls", "#e1e0d9")]
    fig, ax = plt.subplots(figsize=(12, 5.6))
    for i, k in enumerate(KEYS):
        x = 0.0
        for p, _, col in parts:
            w = 100 * em[k][p]
            ax.barh(i, w, left=x, color=col, height=0.62, edgecolor="white", linewidth=1.2)
            x += w
    _rows(ax)
    ax.set_xlim(0, 100)
    ax.set_xlabel("share of the configuration's measured board energy (%)")
    ax.set_title("Where the energy goes: decode, and on Thor gemma mostly in capped calls", loc="left", fontweight="bold")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=c, label=l) for _, l, c in parts], fontsize=8, loc="upper center",
              bbox_to_anchor=(0.45, -0.12), ncol=6, frameon=False)
    _style(ax, "x")
    fig.suptitle("P1's runs (measured). Prefill and decode split each call's energy by its time to first token.",
                 x=0.01, ha="left", fontsize=9.5, color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_summary(op, em, path):
    """N5: what kept state could save against the energy spent in capped calls."""
    fig, ax = plt.subplots(figsize=(10, 6.2))
    for k in KEYS:
        x = 100 * (op[k]["ceiling"] or 0)
        y = 100 * em[k]["capped_decode"]
        dr = k.startswith("d_")
        ax.plot(x, y, "D" if dr else "o", color=C2 if dr else C1, ms=9, mec="white", mew=1.5, zorder=3)
        dx, dy, ha = {"d_o32_e4b_tc": (6, -12, "left"), "t_o32_granite": (6, 6, "left"), "t_o64_granite": (-7, -3, "right"),
                      "t_thor_qwen36": (6, -10, "left"), "t_o64_gemma": (6, 4, "left")}.get(k, (6, 4, "left"))
        lab = SHORT[k].split(" · ", 1)[1] if not k.startswith("d_o") else SHORT[k]
        ax.annotate(lab, (x, y), xytext=(dx, dy), textcoords="offset points", fontsize=8, color=INK2, ha=ha)
    ax.set_xlim(-1, 36)
    ax.set_ylim(-2, 75)
    ax.set_xlabel("most that keeping state could save: ceiling, % of LLM time")
    ax.set_ylabel("board energy spent decoding capped calls (%)")
    ax.set_title("The energy is in runaway decodes, not in kept state", loc="left", fontweight="bold")
    ax.plot([], [], "D", color=C2, label="drone")
    ax.plot([], [], "o", color=C1, label="traffic")
    ax.legend(fontsize=8.5, loc="upper right", frameon=False)
    _style(ax, "both")
    fig.suptitle("P1's runs, one agent per device (measured; ceilings are upper bounds)", x=0.01, ha="left", fontsize=9.5, color=INK2)
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
    fig_context_growth(OUT / "figures/context_growth.png")
    fig_vlm_burst(OUT / "figures/vlm_burst.png")
    fig_cap_raster(OUT / "figures/cap_chains.png")
    em = energy_map()
    (OUT / "energy_map.json").write_text(json.dumps(em, indent=1))
    fig_energy_map(em, OUT / "figures/energy_map.png")
    fig_summary(op, em, OUT / "figures/summary.png")


if __name__ == "__main__":
    main()

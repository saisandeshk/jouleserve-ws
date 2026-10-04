"""Runaway calls in P1's drone runs: are they repetition loops, and what would stopping them save?

For P1's Reflexion sweep (143 runs, 16 tasks) and tool-calling sweep (104 runs, 12 CLGSCE tasks),
both Gemma-4-26B-A4B on the Thor at temperature 0 (measured traces, read-only copies):

1. Loops. Every LLM call's text (reasoning, then output) is replayed through an online loop
   detector: zlib-compress the last W characters every 1,000 characters, and flag the call when
   the compressed size stays below 10% of the window for 3 checks in a row, at W = 4,000 or
   16,000 characters (whichever fires first). Ordinary reasoning and code compress to 25-35%;
   a repeating loop to a few percent.
2. Savings, an upper bound in the style of analysis/p1_runaway.py: the decode time a call would
   not have spent past the stop point, at the board's 71.9 W while a call runs, as a share of the
   sweep's measured board energy, assuming the rest of each run goes as recorded (every capped
   call ended at the token limit with no usable answer). The token position of a flag is taken
   proportional to its character position. A flag on a call that finished on its own counts as
   a false stop.
3. Cross-checks against P1's own drone findings (EdgeAgentBench deck, 3 Oct 2026): pass rate,
   share of LLM time in capped calls, pass rate with and without a capped call, energy of failed
   runs, prefix-cache share, the energy price of a generated
   vs a prefilled token (regression of each call's energy on its token counts, no intercept),
   and how KV-cache evictions line up with capped calls. A capped call is one that ended at its
   output-token limit (finish reason "length"): 32,768 tokens for generate and reflect calls, 8,192 or
   4,096 for some validator calls.

Usage: python3 -m analysis.p1_loops   (writes reports/2026-10-04-drone-runaways/loops.json + figure)
"""
from __future__ import annotations

import ast
import glob
import json
import statistics as st
import zlib

import numpy as np

from analysis.sessions import REPO

SOURCES = {"reflexion": REPO / "data/p1_thor_drone", "toolcalling": REPO / "data/p1_thor_toolcalling"}
CLGSCE = {"B5", "B13", "B29", "B37", "A3", "A5", "A6", "A7", "A8", "A9", "A16", "A20"}
P_ACTIVE_W = 71.9
WINDOWS, THRESHOLD, PERSIST, STEP = (4000, 16000), 0.10, 3, 1000
OUT = REPO / "reports/2026-10-04-drone-runaways"


def _ratio(t: str) -> float:
    b = t.encode()
    return len(zlib.compress(b)) / max(1, len(b))


def detect(text: str) -> float | None:
    """Share of the call's text at which the online detector fires, or None."""
    best = None
    for w in WINDOWS:
        run = 0
        for end in range(w, len(text) + 1, STEP):
            run = run + 1 if _ratio(text[end - w:end]) < THRESHOLD else 0
            if run >= PERSIST:
                pos = end / len(text)
                best = pos if best is None else min(best, pos)
                break
    return best


def min_window_ratio(text: str, w: int = 16000) -> float | None:
    """Lowest compressibility of any w-character window (for the figure)."""
    if len(text) < w:
        return None
    return min(_ratio(text[e - w:e]) for e in range(w, len(text) + 1, 4 * STEP))


def _d(x):
    return x if isinstance(x, dict) else ast.literal_eval(x) if x else {}


def load(root):
    runs = []
    for f in sorted(glob.glob(str(root / "*/*/instance_*/run_*/run_meta.json"))):
        meta = json.loads(open(f).read())
        calls = []
        for line in open(f.replace("run_meta.json", "iterations.jsonl")):
            r = json.loads(line)
            if r.get("kind") != "llm" or not r.get("completion_tokens"):
                continue
            text = (r.get("reasoning_text") or "") + (r.get("output_text") or "")
            out = float(r["completion_tokens"])
            calls.append(dict(
                out=out, text=text, finish=r.get("finish_reason"), capped=r.get("finish_reason") == "length",
                rate=float(r.get("decode_tokens_per_s") or 28), prompt=float(r.get("prompt_tokens") or 0),
                cached=float(r.get("cached_tokens") or 0), ttft=float(r.get("ttft_s") or 0),
                s=float(r["t_phase_end"]) - float(r["t_phase_start"]),
                energy=r.get("iter_energy_J")))
        runs.append(dict(meta=meta, calls=calls))
    return runs


def stop_savings(runs, flags):
    """Energy share saved by three stop rules (upper bounds), and the calls each would cut that
    finished on their own."""
    E = sum(r["meta"]["workflow_energy_J"] for r in runs)
    res = {}
    for rule in ("loop", "cut16k", "loop_or_cut16k"):
        saved_s, false_stops, false_tok = 0.0, 0, 0.0
        for r in runs:
            for c in r["calls"]:
                stops = []
                if rule in ("loop", "loop_or_cut16k") and flags[id(c)] is not None:
                    stops.append(flags[id(c)] * c["out"])
                if rule in ("cut16k", "loop_or_cut16k") and c["out"] > 16384:
                    stops.append(16384.0)
                if not stops:
                    continue
                at = min(stops)
                if c["capped"]:
                    saved_s += (c["out"] - at) / c["rate"]
                else:
                    false_stops += 1
                    false_tok += c["out"] - at
        res[rule] = dict(saved_energy_share=saved_s * P_ACTIVE_W / E, saved_hours=saved_s / 3600,
                         finished_calls_stopped=false_stops, finished_tokens_lost=false_tok)
    return res


def price_ratio(runs):
    """J per prefilled, cached and generated token: least squares on each call's measured energy."""
    rows = [(c["prompt"] - c["cached"], c["cached"], c["out"], c["energy"])
            for r in runs for c in r["calls"] if c["energy"]]
    X = np.array([r[:3] for r in rows])
    y = np.array([r[3] for r in rows])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    if (coef <= 0).any():  # too few prefilled tokens to separate their price (P1: "not identifiable")
        return dict(calls=len(rows), identifiable=False)
    gen_share = float((X[:, 2] * coef[2]).sum() / (X @ coef).sum())
    return dict(calls=len(rows), identifiable=True, j_per_prefilled=float(coef[0]), j_per_cached=float(coef[1]),
                j_per_generated=float(coef[2]), generated_over_prefilled=float(coef[2] / coef[0]),
                generated_share_of_llm_energy=gen_share)


def cross_check(runs):
    """P1's drone numbers, recomputed from the same traces."""
    n = len(runs)
    ok = [r["meta"]["final_result"] == "pass" for r in runs]
    has_cap = [any(c["capped"] for c in r["calls"]) for r in runs]
    E = [r["meta"]["workflow_energy_J"] for r in runs]
    calls = [c for r in runs for c in r["calls"]]
    llm = sum(c["s"] for c in calls)
    ev = [(_d(r["meta"].get("server_summary")).get("evicted_tokens_in_run") or 0) > 0 for r in runs]
    return dict(
        runs=n, passed=sum(ok),
        capped_share_of_llm_time=sum(c["s"] for c in calls if c["capped"]) / llm,
        runs_with_capped_call=sum(has_cap),
        pass_rate_with_capped_call=sum(o for o, h in zip(ok, has_cap) if h) / max(1, sum(has_cap)),
        pass_rate_without=sum(o for o, h in zip(ok, has_cap) if not h) / max(1, n - sum(has_cap)),
        failed_share_of_runs=1 - sum(ok) / n,
        failed_share_of_energy=sum(e for e, o in zip(E, ok) if not o) / sum(E),
        cached_share_of_prompt_tokens=sum(c["cached"] for c in calls) / sum(c["prompt"] for c in calls),
        prefill_share_of_llm_time=sum(min(c["ttft"], c["s"]) for c in calls) / llm,
        runs_with_kv_eviction=sum(ev), evicting_runs_with_capped_call=sum(e and h for e, h in zip(ev, has_cap)),
        price=price_ratio(runs))


def figure(data, path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from analysis.report_figures import C1, C2, C3, INK2, MUTED, SURF, _style

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    ax = axes[0]
    rng = np.random.default_rng(0)
    for i, (k, lab) in enumerate((("reflexion", "Reflexion"), ("toolcalling", "Tool calling"))):
        for capped, col, dy in ((False, MUTED, 0.17), (True, C2, -0.17)):
            xs = [x for x, c in data[k]["min_window_ratio"] if c == capped and x is not None]
            ax.scatter(xs, i + dy + rng.uniform(-0.07, 0.07, len(xs)), s=9, color=col, alpha=0.6, linewidths=0,
                       label=("hit its token limit" if capped else "finished on its own") if i == 0 else None)
    ax.axvline(THRESHOLD, color=INK2, lw=1, ls="--")
    ax.text(THRESHOLD + 0.005, 1.45, "detector\nthreshold", fontsize=8, color=INK2, va="top")
    ax.set_yticks([0, 1], ["Reflexion", "Tool calling"])
    ax.set_ylim(-0.5, 1.5)
    ax.set_xlabel("compressed ÷ raw size of the call's most repetitive 16K characters\n(calls with at least 16K characters of text)")
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    ax.set_title("(a) Capped calls are loops; finished calls are not", loc="left", fontsize=10)
    ax = axes[1]
    for k, lab, col in (("reflexion", "Reflexion", C1), ("toolcalling", "Tool calling", C3)):
        xs = sorted(data[k]["flag_tokens_capped"])
        ax.step(xs, np.arange(1, len(xs) + 1) / len(xs), where="post", color=col, lw=2, label=f"{lab} (n={len(xs)})")
    ax.axvline(16384, color=MUTED, lw=1, ls=":")
    ax.text(16384 + 300, 0.05, "fixed\n16K cut", fontsize=8, color=MUTED)
    ax.set_xlim(0, 32768)
    ax.set_xticks([0, 8192, 16384, 24576, 32768], ["0", "8K", "16K", "24K", "32K"])
    ax.set_xlabel("output tokens when the loop detector fires")
    ax.set_ylabel("share of capped calls")
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.set_title("(b) Where an online loop stop would cut", loc="left", fontsize=10)
    for ax in axes:
        _style(ax, "x")
    fig.patch.set_facecolor(SURF)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURF)


def main():
    out, figdata = {}, {}
    for k, root in SOURCES.items():
        runs = load(root)
        flags = {id(c): (detect(c["text"]) if len(c["text"]) >= WINDOWS[0] else None) for r in runs for c in r["calls"]}
        capped = [c for r in runs for c in r["calls"] if c["capped"]]
        finished = [c for r in runs for c in r["calls"] if not c["capped"]]
        fl = [flags[id(c)] for c in capped if flags[id(c)] is not None]
        scopes = {"all": runs, "clgsce12": [r for r in runs if r["meta"]["task_id"] in CLGSCE]}
        out[k] = dict(
            detector=dict(windows_chars=WINDOWS, threshold=THRESHOLD, persist_checks=PERSIST, step_chars=STEP),
            calls=sum(len(r["calls"]) for r in runs), capped_calls=len(capped),
            capped_finish_reasons=sorted({c["finish"] for c in capped}),
            capped_flagged=len(fl), finished_calls_flagged=sum(flags[id(c)] is not None for c in finished),
            flag_share_median=st.median(fl), flag_tokens_median=st.median(f * c["out"] for c in capped
                                                                         if (f := flags[id(c)]) is not None),
            savings={s: stop_savings(rs, flags) for s, rs in scopes.items()},
            cross_check=cross_check(runs))
        figdata[k] = dict(min_window_ratio=[(min_window_ratio(c["text"]), c["capped"])
                                            for r in runs for c in r["calls"]],
                          flag_tokens_capped=[f * c["out"] for c in capped if (f := flags[id(c)]) is not None])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "loops.json").write_text(json.dumps(out, indent=1))
    (OUT / "figures").mkdir(exist_ok=True)
    figure(figdata, OUT / "figures/loops.png")
    for k, v in out.items():
        s = v["savings"]
        print(f"{k}: capped {v['capped_calls']}/{v['calls']}, flagged {v['capped_flagged']}, finished calls flagged "
              f"{v['finished_calls_flagged']}; flag at {v['flag_share_median']:.0%} of the call "
              f"(~{v['flag_tokens_median']:.0f} tokens)")
        for scope, d in s.items():
            print(f"   {scope}: " + "; ".join(f"{rule} saves {x['saved_energy_share']:.0%} (false stops "
                                              f"{x['finished_calls_stopped']})" for rule, x in d.items()))
        print("   cross-check:", json.dumps({a: (round(b, 3) if isinstance(b, float) else b)
                                              for a, b in v["cross_check"].items() if a != "price"}))
        print("   price:", json.dumps({a: round(b, 4) if isinstance(b, float) else b
                                       for a, b in v["cross_check"]["price"].items()}))


if __name__ == "__main__":
    main()

"""Capped calls in every P1 configuration, drone and traffic: are they repetition loops, and what would
stopping them save? Extends analysis/p1_loops.py (P1's two Thor drone sweeps) to the repo's data.

For each configuration in analysis/p1_repo.py:
1. Capped calls (output at the call's token limit; see p1_repo): count, share of LLM time, by cap.
2. Loops, two detectors on the call's text:
   - ours, online (p1_loops.detect): zlib-compress the last 4,000 or 16,000 characters every 1,000
     characters; fire when below 10% of the window for 3 checks in a row;
   - P1's, offline (analysis/scripts/insights_why.py in their repo): calls of >= 2,000 tokens whose last
     6,000 characters compress below 10%.
   Traffic text is missing for some calls (traces rebuilt from tool records, or a cap inside a tool call
   whose partial body the parser dropped); those calls are counted as "no text", not as non-loops.
3. Stop rules, upper bounds on the configuration's measured energy (board energy, whole sweep), assuming
   the rest of each run goes as recorded:
   - loop stop: end a call where our detector fires; saves the call's decode energy past that point
     (the call's measured energy x its decode share x the share of its tokens past the stop);
     a fire on a call that finished on its own is a false stop;
   - half-cap cut: end every call at half its cap; false stops are finished calls longer than that;
   - P1's rule: stop the run when its first capped call ends; saves everything after it; runs lost are
     those that still passed (drone) or completed (traffic);
   - second consecutive cap: stop the run when a capped call follows a capped call (traffic agents retry
     a dropped tool call and cap again); runs lost as above.

Usage: python3 -m analysis.p1_caps   (writes reports/2026-10-05-p1-repo/caps.json)
"""
from __future__ import annotations

import json
import zlib
from concurrent.futures import ProcessPoolExecutor

from analysis.p1_loops import detect
from analysis.p1_repo import CONFIGS, load
from analysis.sessions import REPO

OUT = REPO / "reports/2026-10-05-p1-repo"


def p1_rule(c):
    """P1's offline loop rule: >= 2,000 tokens, last 6,000 characters compress below 10%."""
    t = c["text"] or ""
    if c["out"] < 2000 or len(t) <= 500:
        return None
    b = t[-6000:].encode()
    return len(zlib.compress(b, 9)) / len(b) < 0.10


def _flags(key):
    runs = load(key)
    return [[detect(c["text"]) if c["text"] and c["text_complete"] else None for c in r["calls"]] for r in runs]


def decode_j(c):
    """Measured energy of the call's decode phase (whole board, as P1 meters it)."""
    dur = max(1e-9, c["t1"] - c["t0"])
    e = c["energy"] if c["energy"] is not None else 0.0
    return e * min(1.0, c["decode"] / dur) if c["decode"] else e


def after(r, t, energy_of_rest):
    """Energy of everything in run r that starts at or after time t (LLM calls and tools)."""
    return sum(energy_of_rest(x) for x in r["calls"] + r["tools"] if x["t0"] >= t - 1e-6)


def analyse(key, flags):
    runs = load(key)
    E = sum(r["energy_J"] for r in runs)
    calls = [c for r in runs for c in r["calls"]]
    llm = sum(c["t1"] - c["t0"] for c in calls)
    capped = [c for c in calls if c["capped"]]
    caps = {}
    for c in capped:
        caps[str(c["cap"])] = caps.get(str(c["cap"]), 0) + 1
    fl = {id(c): f for r, fs in zip(runs, flags) for c, f in zip(r["calls"], fs)}
    with_text = [c for c in capped if c["text"] and c["text_complete"]]
    fin_text = [c for c in calls if not c["capped"] and c["text"] and c["out"] >= 2000]
    en = lambda x: x["energy"] or 0.0
    rules = {}
    # loop stop and half-cap cut
    for rule in ("loop", "half_cap"):
        saved, false_stops = 0.0, 0
        for c in calls:
            if rule == "loop":
                f = fl[id(c)]
                if f is None:
                    continue
                at = f * c["out"]
            else:
                if not c["cap"] or c["out"] <= c["cap"] / 2:
                    continue
                at = c["cap"] / 2
            if c["capped"]:
                saved += decode_j(c) * (c["out"] - at) / c["out"]
            else:
                false_stops += 1
        rules[rule] = dict(saved_share=saved / E, finished_calls_stopped=false_stops)
    # run-level rules
    for rule in ("first_cap", "second_consecutive_cap"):
        saved, lost, stopped = 0.0, 0, 0
        for r in runs:
            cs, stop_t = r["calls"], None
            for i, c in enumerate(cs):
                if c["capped"] and (rule == "first_cap" or (i and cs[i - 1]["capped"])):
                    stop_t = c["t1"]
                    break
            if stop_t is None:
                continue
            stopped += 1
            saved += after(r, stop_t, en)
            lost += bool(r["ok"])
        rules[rule] = dict(saved_share=saved / E, runs_stopped=stopped, ok_runs_lost=lost)
    loops_ours = [c for c in with_text if fl[id(c)] is not None]
    p1_flags = [p1_rule(c) for c in capped]
    p1_checked = [f for f in p1_flags if f is not None]
    # how repetitive the capped calls are that P1's rule misses (its last 6,000 characters)
    missed = sorted(len(zlib.compress(c["text"][-6000:].encode(), 9)) / max(1, len(c["text"][-6000:].encode()))
                    for c, f in zip(capped, p1_flags) if f is False)
    consecutive = sum(1 for r in runs for a, b in zip(r["calls"], r["calls"][1:]) if a["capped"] and b["capped"])
    kind_s = {"loop": 0.0, "not_loop": 0.0, "no_text": 0.0}
    for c in capped:
        k = "no_text" if not (c["text"] and c["text_complete"]) else "loop" if fl[id(c)] is not None else "not_loop"
        kind_s[k] += c["t1"] - c["t0"]
    return dict(
        runs=len(runs), calls=len(calls), capped=len(capped), caps=caps,
        capped_share_of_llm_time=sum(c["t1"] - c["t0"] for c in capped) / llm if llm else None,
        runs_with_cap=sum(any(c["capped"] for c in r["calls"]) for r in runs),
        ok_rate_with_cap=_rate(runs, True), ok_rate_without_cap=_rate(runs, False),
        capped_with_complete_text=len(with_text),
        loops_ours=len(loops_ours), finished_long_calls_with_text=len(fin_text),
        finished_flagged_ours=sum(fl[id(c)] is not None for c in fin_text),
        loop_fire_position_median=_median([fl[id(c)] for c in loops_ours]),
        loops_p1_rule=sum(p1_checked), capped_checked_p1_rule=len(p1_checked),
        p1_rule_missed_ratios=[round(x, 3) for x in missed],
        capped_after_capped=consecutive,
        capped_llm_share_by_kind={k: v / llm for k, v in kind_s.items()} if llm else None,
        stop_rules=rules)


def _rate(runs, with_cap):
    rs = [r for r in runs if any(c["capped"] for c in r["calls"]) == with_cap]
    return sum(r["ok"] for r in rs) / len(rs) if rs else None


def _median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    keys = [c.key for c in CONFIGS]
    with ProcessPoolExecutor(max_workers=12) as ex:
        flags = dict(zip(keys, ex.map(_flags, keys)))
    res = {c.key: dict(label=c.label, **analyse(c.key, flags[c.key])) for c in CONFIGS}
    (OUT / "caps.json").write_text(json.dumps(res, indent=1))
    for k, v in res.items():
        s = v["stop_rules"]
        print(f"{k:19s} capped {v['capped']:4d} ({(v['capped_share_of_llm_time'] or 0):.0%} LLM)  text {v['capped_with_complete_text']:3d}"
              f"  loops ours {v['loops_ours']:3d}  p1 {v['loops_p1_rule']}/{v['capped_checked_p1_rule']}"
              f"  fin flagged {v['finished_flagged_ours']}/{v['finished_long_calls_with_text']}  consec {v['capped_after_capped']}"
              f" | loop {s['loop']['saved_share']:.1%}/{s['loop']['finished_calls_stopped']}"
              f"  half {s['half_cap']['saved_share']:.1%}/{s['half_cap']['finished_calls_stopped']}"
              f"  first {s['first_cap']['saved_share']:.1%}/-{s['first_cap']['ok_runs_lost']}"
              f"  2nd {s['second_consecutive_cap']['saved_share']:.1%}/-{s['second_consecutive_cap']['ok_runs_lost']}")


if __name__ == "__main__":
    main()

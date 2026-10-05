"""Is there retained state worth managing in P1's drone and traffic runs? One row per configuration.

For every configuration in analysis/p1_repo.py (measured on P1's Jetsons, one agent per device):
- shape: calls per run, output tokens per call, prefill share of LLM time (time to first token over call
  time), the gap an agent's state sits idle between two calls, and the paused share of its KV
  memory-time (context held x gap, against context held x call time);
- value of kept state:
  * measured: the prefill time the prefix cache saved (cached tokens at the configuration's cold
    prefill rate) as a share of what LLM time would have been with nothing kept;
  * ceiling: P / (P + r * O) over every call after a run's first, with P all its prompt tokens (an
    upper bound: any prompt token could at best have been kept) and r the configuration's own
    measured time ratio (cold prefill tokens/s over decode tokens/s), and at r = 67 and 90 for
    comparison with the drone reports;
- memory: largest context per run against the KV pool and the context window, runs that overflowed;
- sharing: tokens common to every session's prompt (traffic opens with the current date and time, so
  sessions share almost nothing; the drone harness flushes the cache before every run);
- ask_vlm (traffic): the vision tool sends many requests to the agent's own server; from the vitals
  stream (1 s KV samples) the running requests and KV use during ask_vlm, and whether the agent's
  paused context survives it (cache miss on the next call).

The reported cached tokens are 0 on every call of the two Orin drone cells, although their server
reports cache hits (P1's open question Q-D7); their measured value is therefore not available.

Usage: python3 -m analysis.p1_opportunity   (writes reports/2026-10-05-p1-repo/opportunity.json)
"""
from __future__ import annotations

import gzip
import json
import os
import statistics as st

from analysis.p1_repo import CONFIGS, load
from analysis.sessions import REPO

OUT = REPO / "reports/2026-10-05-p1-repo"
NO_CACHE_REPORT = {"d_o64_devstral_tc", "d_o32_e4b_tc"}


def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    lo = int(k)
    return xs[lo] + (xs[min(lo + 1, len(xs) - 1)] - xs[lo]) * (k - lo)


def rates(runs):
    """Cold prefill and batch-1 decode tokens/s, from the configuration's own calls."""
    pre = [c["prompt"] / c["ttft"] for r in runs for c in r["calls"]
           if c["prompt"] > 2000 and c["cached"] < 0.02 * c["prompt"] and 0.1 < c["ttft"] < c["t1"] - c["t0"]]
    dec = [c["out"] / c["decode"] for r in runs for c in r["calls"] if c["out"] >= 256 and c["decode"] > 0]
    return (st.median(pre) if pre else None), (st.median(dec) if dec else None)


def tools_between(r, a, b):
    return [t["tool"] for t in r["tools"] if t["t0"] >= a["t1"] - 0.5 and t["t1"] <= b["t0"] + 0.5]


def row(key):
    runs = load(key)
    calls = [c for r in runs for c in r["calls"]]
    llm = sum(c["t1"] - c["t0"] for c in calls)
    prefill = sum(min(c["ttft"], c["t1"] - c["t0"]) for c in calls)
    pre_rate, dec_rate = rates(runs)
    later = [c for r in runs for c in r["calls"][1:]]
    P, O, C = sum(c["prompt"] for c in later), sum(c["out"] for c in later), sum(c["cached"] for c in calls)
    r_time = pre_rate / dec_rate if pre_rate and dec_rate else None
    saved_s = C / pre_rate if pre_rate else None
    gaps, gap_vlm, held_gap, held_call = [], [], 0.0, 0.0
    post = {"ask_vlm": [0, 0, 0, 0], "other": [0, 0, 0, 0]}   # calls, misses > 64 tokens, missed, expected
    for r in runs:
        cs = r["calls"]
        for a, b in zip(cs, cs[1:]):
            g = max(0.0, b["t0"] - a["t1"])
            gaps.append(g)
            between = tools_between(r, a, b)
            if "ask_vlm" in between:
                gap_vlm.append(g)
            held_gap += (a["prompt"] + a["out"]) * g
            # the next prompt repeats the previous one (append-only context); what the cache did not
            # return was recomputed
            if r["cfg"].startswith("t_"):
                k = post["ask_vlm" if "ask_vlm" in between else "other"]
                miss = max(0, min(a["prompt"], b["prompt"]) - b["cached"])
                k[0] += 1
                k[1] += miss > 64
                k[2] += miss
                k[3] += min(a["prompt"], b["prompt"])
        held_call += sum((c["prompt"] + c["out"] / 2) * (c["t1"] - c["t0"]) for c in cs)
    peaks = [max(c["prompt"] + c["out"] for c in r["calls"]) for r in runs if r["calls"]]
    pools = sorted({r["pool"] for r in runs if r["pool"]})
    ctxs = sorted({r["ctx"] for r in runs if r["ctx"]})
    E = sum(r["energy_J"] for r in runs)
    ok = [r for r in runs if r["ok"]]
    res = dict(
        runs=len(runs), ok=len(ok), ok_share=len(ok) / len(runs), kwh=E / 3.6e6,
        kj_per_ok_run=(E / len(ok) / 1e3) if ok else None,
        calls=len(calls), calls_per_run_median=st.median(len(r["calls"]) for r in runs),
        out_median=st.median(c["out"] for c in calls), out_p90=pct([c["out"] for c in calls], 0.9),
        later_out_median=st.median(c["out"] for c in later) if later else None,
        llm_h=llm / 3600, prefill_share_of_llm=prefill / llm,
        reuse=None if key in NO_CACHE_REPORT else C / max(1, sum(c["prompt"] for c in calls)),
        prefill_tok_s=pre_rate, decode_tok_s=dec_rate, r_time=r_time,
        measured_saving=None if key in NO_CACHE_REPORT or not saved_s else saved_s / (llm + saved_s),
        ceiling=P / (P + r_time * O) if r_time else None,
        ceiling_r67=P / (P + 67 * O), ceiling_r90=P / (P + 90 * O),
        gap_median_s=st.median(gaps) if gaps else None, gap_p90_s=pct(gaps, 0.9),
        gaps_over_10s=sum(g > 10 for g in gaps) / max(1, len(gaps)),
        gaps_over_60s=sum(g > 60 for g in gaps) / max(1, len(gaps)),
        gap_time_in_ask_vlm=sum(gap_vlm) / max(1e-9, sum(gaps)), ask_vlm_gap_median_s=st.median(gap_vlm) if gap_vlm else None,
        paused_share_of_kv_time=held_gap / max(1e-9, held_gap + held_call),
        peak_ctx_median=st.median(peaks), peak_ctx_p90=pct(peaks, 0.9), peak_ctx_max=max(peaks),
        kv_pool_tokens=pools, context_window=ctxs,
        overflow_share=sum(r["status"] == "input_ceiling" for r in runs) / len(runs),
        evicting_runs=sum((r["evicted"] or 0) > 0 for r in runs) if key.startswith("d_") else None,
    )
    if key.startswith("t_"):
        pairs = [(a, b) for r in runs for a, b in zip(r["calls"], r["calls"][1:])]
        grow = [b["prompt"] - a["prompt"] for a, b in pairs]
        dtool = sum(max(0, (b.get("toolout") or 0) - (a.get("toolout") or 0)) for a, b in pairs)
        res["prompt_never_shrinks"] = sum(g >= 0 for g in grow) / max(1, len(grow))
        res["growth_per_step_median"] = st.median(grow) if grow else None
        res["growth_from_tool_output"] = dtool / max(1, sum(max(0, g) for g in grow))
        res["cached_equals_previous_prompt"] = sum(abs(b["cached"] - a["prompt"]) <= 64 for a, b in pairs) / max(1, len(pairs))
        res["first_prompt_median"] = st.median(r["calls"][0]["prompt"] for r in runs if r["calls"])
        first = [r["calls"][0] for r in runs if r["calls"]]
        res["fixed_prompt_tokens_median"] = st.median((c.get("schema") or 0) + (c.get("scaffold") or 0) for c in first)
        res["after_tool_cache"] = {k: dict(calls=v[0], calls_missing_over_64=v[1], missed_tokens=v[2],
                                           missed_share=v[2] / max(1, v[3]),
                                           recompute_share_of_llm=(v[2] / pre_rate / llm) if pre_rate else None)
                                   for k, v in post.items()}
    return res


def ask_vlm_bursts(key):
    """Running requests and KV use on the agent's own server during ask_vlm, from the 1 s vitals."""
    runs = [r for r in load(key) if any(t["tool"] == "ask_vlm" for t in r["tools"])]
    by_dir = {}
    for r in runs:
        by_dir.setdefault(r["vitals_dir"], []).append(r)
    inside_reqs, inside_kv, outside_reqs, n_windows, pool = [], [], [], 0, None
    for d, rs in by_dir.items():
        wins = [(t["t0"], t["t1"]) for r in rs for t in r["tools"] if t["tool"] == "ask_vlm"]
        spans = [(r["calls"][0]["t0"], r["calls"][-1]["t1"]) for r in rs if r["calls"]]
        n_windows += len(wins)
        with gzip.open(os.path.join(d, "vitals.jsonl.gz"), "rt") as f:
            for line in f:
                if '"kv_num_running_reqs"' not in line:
                    continue
                v = json.loads(line)
                t, q = v.get("t_monotonic"), v.get("kv_num_running_reqs")
                if t is None or q is None:
                    continue
                pool = v.get("kv_max_total_num_tokens") or pool
                if any(a <= t <= b for a, b in wins):
                    inside_reqs.append(q)
                    inside_kv.append(v.get("kv_used_tokens") or 0)
                elif any(a <= t <= b for a, b in spans) and not any(a - 2 <= t <= b + 2 for a, b in wins):
                    outside_reqs.append(q)   # 2 s clear of any window (the KV samples are 1 s apart)
    if not inside_reqs:
        return None
    return dict(windows=n_windows, samples_inside=len(inside_reqs),
                running_reqs_inside_median=st.median(inside_reqs), running_reqs_inside_max=max(inside_reqs),
                share_inside_with_more_than_one=sum(q > 1 for q in inside_reqs) / len(inside_reqs),
                running_reqs_outside_max=max(outside_reqs) if outside_reqs else None,
                share_outside_with_more_than_one=(sum(q > 1 for q in outside_reqs) / len(outside_reqs)) if outside_reqs else None,
                kv_used_inside_max=max(inside_kv), kv_pool=pool,
                kv_used_inside_max_share_of_pool=(max(inside_kv) / pool) if pool else None)


def drone_prefix_reuse(key):
    """Share of each drone prompt that repeats an earlier prompt of the same run (longest common
    character prefix with any earlier call's rendered messages): what a working prefix cache could
    reuse. Used where the server reports no cached tokens (the Orin cells)."""
    import glob
    from analysis.p1_repo import BY_KEY, _root, jsonl
    reusable = total = 0.0
    tok_reusable = 0.0
    for f in sorted(glob.glob(os.path.join(_root(BY_KEY[key]), "*/instance_*/run_*/iterations.jsonl*"))):
        f = f[:-3] if f.endswith(".gz") else f
        prev = []
        for r in jsonl(f):
            if r.get("kind") != "llm" or not r.get("prompt_tokens"):
                continue
            s_ = json.dumps(r.get("prompt_messages") or [], sort_keys=True)
            best = max((len(os.path.commonprefix([s_, q])) for q in prev), default=0)
            reusable += best
            total += len(s_)
            tok_reusable += r["prompt_tokens"] * best / max(1, len(s_))
            prev.append(s_)
    return dict(reusable_char_share=reusable / max(1, total), reusable_tokens=tok_reusable)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {c.key: dict(label=c.label, **row(c.key)) for c in CONFIGS}
    for k in ("t_thor_gemma", "t_thor_qwen36", "t_o64_gemma", "t_o32_e4b"):
        res[k]["ask_vlm"] = ask_vlm_bursts(k)
    for k in ("d_thor_gemma_rfx", "d_o64_devstral_tc", "d_o32_e4b_tc"):
        pr = drone_prefix_reuse(k)
        v = res[k]
        llm_s = v["llm_h"] * 3600
        pr["value_if_cached"] = (pr["reusable_tokens"] / v["prefill_tok_s"]) / (llm_s + pr["reusable_tokens"] / v["prefill_tok_s"]) \
            if v["prefill_tok_s"] else None
        v["prefix_reuse"] = pr
    (OUT / "opportunity.json").write_text(json.dumps(res, indent=1))
    cols = ["runs", "ok_share", "calls_per_run_median", "out_median", "prefill_share_of_llm", "reuse",
            "r_time", "measured_saving", "ceiling", "ceiling_r67", "gap_median_s", "gap_p90_s",
            "paused_share_of_kv_time", "peak_ctx_p90", "overflow_share"]
    print("config".ljust(20), *[c[:12].rjust(12) for c in cols])
    for k, v in res.items():
        print(k.ljust(20), *[(f"{v[c]:.3g}" if isinstance(v[c], (int, float)) else str(v[c]))[:12].rjust(12) for c in cols])
    for k in ("t_thor_gemma", "t_thor_qwen36", "t_o64_gemma", "t_o32_e4b"):
        print(k, "after-tool cache:", res[k]["after_tool_cache"], "\n   ask_vlm:", res[k]["ask_vlm"])
    for k in ("d_thor_gemma_rfx", "d_o64_devstral_tc", "d_o32_e4b_tc"):
        print(k, "prefix reuse:", res[k]["prefix_reuse"], "prefill share", round(res[k]["prefill_share_of_llm"], 3))


if __name__ == "__main__":
    main()

"""Independent recheck of the mentor's drone-experiment slides (16 Oct 2026). Runs on the WS, reads the read-only copies in
~/work/mentor/p5osdi_20261016, never writes to a board.  Usage:
    ~/work/venv-analysis/bin/python recheck.py            # numbers -> recheck.json, then the four plots
Section 1 (this half) computes every number; section 2 (plots) draws the four figures from those numbers.
"""
import collections
import csv
import glob
import json
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = HERE
ROOT = os.path.expanduser("~/work/mentor/p5osdi_20261016")
T1 = ROOT + "/thor1/p5_osdi"
O1 = ROOT + "/orin32_1/p5_osdi"
O2 = ROOT + "/orin32_2/p5_osdi"
P1DRONES = os.path.expanduser("~/work/p1/edge-agent-bench/drones")

RUNS = {
    # key: (path, label, board, agent)
    "thor_w1_n4": (T1 + "/fleet/runs/w1_bf16_n4", "Reflexion (P1) 4 drones", "thor", "reflexion"),
    "thor_w1_n8": (T1 + "/fleet/runs/w1_bf16_n8", "Reflexion (P1) 8 drones", "thor", "reflexion"),
    "thor_w3f_n4": (T1 + "/fleet/runs/w3f_gemma_n4", "Step-wise final 4 drones", "thor", "stepwise"),
    "thor_w3f_n8": (T1 + "/fleet/runs/w3f_gemma_n8", "Step-wise final 8 drones", "thor", "stepwise"),
    "thor_w3_n4": (T1 + "/fleet/runs/w3_gemma_n4", "Step-wise fast-sim 4 drones", "thor", "stepwise"),
    "thor_w3_n8": (T1 + "/fleet/runs/w3_gemma_n8", "Step-wise fast-sim 8 drones", "thor", "stepwise"),
    "orin_w1_n2": (O1 + "/fleet/runs/w1_bf16_n2", "E4B tool-calling 2 drones", "orin", "toolcalling"),
    "orin_w1_n4": (O1 + "/fleet/runs/w1_bf16_n4", "E4B tool-calling 4 drones", "orin", "toolcalling"),
    "orin_w1_n8": (O1 + "/fleet/runs/w1_bf16_n8", "E4B tool-calling 8 drones", "orin", "toolcalling"),
    "orin_w3f_n2": (O1 + "/orinfleet/runs/w3f_e4b_n2", "E4B step-wise 2 drones", "orin", "stepwise"),
    "orin_w3f_n4": (O1 + "/orinfleet/runs/w3f_e4b_n4", "E4B step-wise 4 drones", "orin", "stepwise"),
    "orin_w3f_n8": (O1 + "/orinfleet/runs/w3f_e4b_n8", "E4B step-wise 8 drones", "orin", "stepwise"),
    "gr_w3_n2": (O2 + "/orinfleet/runs/w3_granite_n2", "granite step-wise 2 drones (earlier agent version)", "orin", "stepwise"),
    "gr_w3f_sf_n2": (O2 + "/orinfleet/runs/w3f_granite_sf_n2", "granite step-wise final 2 drones (stopped, 11 of 12)", "orin", "stepwise"),
    "gr_ss_n2": (O2 + "/orinfleet/runs/ss_granite_bf16_n2", "granite steady load 2 drones", "orin", "stepwise"),
    "gr_ss_n4": (O2 + "/orinfleet/runs/ss_granite_bf16_n4", "granite steady load 4 drones (running at copy)", "orin", "stepwise"),
}
THOR6 = ["thor_w1_n4", "thor_w1_n8", "thor_w3f_n4", "thor_w3f_n8", "thor_w3_n4", "thor_w3_n8"]
MOVE = ("step_fly_to", "step_fly_body")

OUT = {}


# ----------------------------------------------------------------------------------------------------------------- loading
def jl(path):
    out = []
    try:
        with open(path, errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        pass
    return out


STEP = re.compile(r"^\[STEP (\d+)\] (\S+) (\{.*?\}) -> (.*)$")


def parse_transcript(path):
    try:
        tr = open(path, errors="replace").read()
    except FileNotFoundError:
        return {"passed_line": None, "attempts": 0, "steps": [], "toolcall_agent": False}
    m = re.search(r"^PASSED = (True|False)", tr, re.M)
    att = [int(x) for x in re.findall(r"^\[SUPERVISOR\] attempt = (\d+)/", tr, re.M)]
    it = re.search(r"^ITERATIONS = (\d+)", tr, re.M)
    if it:
        att.append(int(it.group(1)))
    steps = []
    for line in tr.splitlines():
        s = STEP.match(line)
        if s:
            st = None
            mm = re.search(r'"state": \[([^\]]+)\]', s.group(4))
            if mm:
                st = [float(x) for x in mm.group(1).split(",")]
            steps.append({"n": int(s.group(1)), "name": s.group(2), "state": st})
        elif line.startswith("[STEP ") and "no tool call" in line:
            steps.append({"n": int(re.match(r"\[STEP (\d+)", line).group(1)), "name": "nudge", "state": None})
    return {"passed_line": None if not m else m.group(1) == "True", "attempts": max(att) if att else 0, "steps": steps,
            "toolcall_agent": "[P1_TOOLCALL]" in tr}


def energy_from_samples(dev, t0, t1):
    """Trapezoid over the 200 ms board samples in [t0, t1], the same rule as P1's run_one.energy_j
    (platform_total_power_mW, else power_VIN_mW)."""
    pts = [(r["t_mono"], r.get("platform_total_power_mW", r.get("power_VIN_mW"))) for r in dev]
    pts = [(t, p) for t, p in pts if p is not None and t0 <= t <= t1]
    return sum(0.5 * (p0 + p1) / 1000.0 * (u1 - u0) for (u0, p0), (u1, p1) in zip(pts, pts[1:]))


def load_run(key):
    path, label, board, agent = RUNS[key]
    R = {"key": key, "path": path, "label": label, "board": board, "agent": agent}
    R["meta"] = json.load(open(path + "/fleet_meta.json"))
    R["summary"] = json.load(open(path + "/fleet_summary.json")) if os.path.exists(path + "/fleet_summary.json") else None
    R["jobs"] = jl(path + "/fleet_runs.jsonl")
    R["n"] = R["meta"]["args"]["n"]
    R["t0"] = min(j["t_start"] for j in R["jobs"])
    R["t1"] = max(j["t_end"] for j in R["jobs"])
    missions = {}
    for j in R["jobs"]:
        k = (j["task"], j["inst"][-1], str(j["rep"]))
        d = f"{path}/{j['task']}/instance_{j['inst'][-1]}/run_{j['rep']}"
        calls = [c for c in jl(d + "/llm_calls.jsonl") if c.get("t_send_mono") is not None
                 and R["t0"] - 5 <= c["t_send_mono"] <= R["t1"] + 5]
        for c in calls:
            c["mission"] = f"{j['task']}i{j['inst'][-1]}"
            c["drone"] = j["drone"]
        calls.sort(key=lambda c: c["t_send_mono"])
        missions[k] = {"job": j, "dir": d, "tr": parse_transcript(d + "/transcript.log"), "calls": calls}
    R["missions"] = missions
    R["calls"] = sorted([c for m in missions.values() for c in m["calls"]], key=lambda c: c["t_send_mono"])
    R["kv"] = [x for x in jl(path + "/server_kv.jsonl") if R["t0"] - 1 <= x["t_mono"] <= R["t1"] + 1]
    R["energy_J"] = energy_from_samples(jl(path + "/device_samples.jsonl"), R["t0"], R["t1"])
    R["window_s"] = R["t1"] - R["t0"]
    return R


def kvarr(R, field):
    return np.array([x.get(field) or 0 for x in R["kv"]], dtype=float)


def pctl(v, qs=(10, 50, 90)):
    v = np.asarray(v, dtype=float)
    return [round(float(np.percentile(v, q)), 3) for q in qs] if len(v) else None


# ------------------------------------------------------------------------------------------------------ run-level numbers
def run_level(R):
    jobs = R["jobs"]
    passed = sum(1 for j in jobs if j["passed"])
    s = R["summary"]
    # sensitivity: P1's own limits (1,800 s per LLM call, 7,200 s per mission) applied after the fact
    ok_p1 = 0
    over = []
    for k, m in R["missions"].items():
        j = m["job"]
        if not j["passed"]:
            continue
        mx = max([c.get("e2e_s") or 0 for c in m["calls"]] or [0])
        if j["wall_s"] > 7200 or mx > 1800:
            over.append({"mission": f"{k[0]}i{k[1]}", "wall_min": round(j["wall_s"] / 60, 1), "longest_call_s": round(mx)})
        else:
            ok_p1 += 1
    d = {"label": R["label"], "n_drones": R["n"], "missions": len(jobs), "passed": passed,
         "passed_transcript_PASSED_line": sum(1 for m in R["missions"].values() if m["tr"]["passed_line"]),
         "complete_summary_file": s is not None, "window_s": round(R["window_s"], 1),
         "energy_kJ_recomputed": round(R["energy_J"] / 1000, 1),
         "kJ_per_success_recomputed": round(R["energy_J"] / passed / 1000, 3) if passed else None,
         "summary_energy_kJ": None if not s else round(s["energy_J"] / 1000, 1),
         "summary_kJ_per_success": None if not s else round(s["energy_per_success_kJ"], 3),
         "timed_out": sum(1 for j in jobs if j["timed_out"]), "tracebacks": sum(1 for j in jobs if j.get("traceback")),
         "sim_restarts": sum(1 for j in jobs if j.get("sim_restarted")),
         "passed_if_P1_limits_applied": ok_p1, "passes_over_P1_limits": over,
         "kJ_per_success_if_P1_limits": round(R["energy_J"] / ok_p1 / 1000, 3) if ok_p1 else None}
    return d


# ------------------------------------------------------------------------------------------------- T1: P1's own 1-drone runs
def t1_baseline():
    cfg = "edge_devices/final_sweep_thor/reflexion/gemma-4-26B-A4B-it"
    tasks = ["A3", "A6", "A7", "A8", "A9", "A16", "A20"]
    grades = {(r["task"], r["instance"], r["run"]): r for r in csv.DictReader(open(P1DRONES + "/grading/grades.csv"))
              if r["config"] == cfg}
    rows, per = [], collections.defaultdict(list)
    for t in tasks:
        for i in (1, 2, 3):
            for rn in (1, 2, 3):
                m = json.load(open(f"{P1DRONES}/{cfg}/{t}/instance_{i}/run_{rn}/run_meta.json"))
                g = grades[(t, f"instance_{i}", f"run_{rn}")]
                r = {"task": t, "inst": i, "run": rn, "pass": g["final_result"] == "pass", "harness_pass": m["final_result"] == "pass",
                     "E_J": m["workflow_energy_J"], "wall_s": m["workflow_time_s"]}
                rows.append(r)
                per[(t, i)].append(r)
    exp_pass = sum(np.mean([r["pass"] for r in v]) for v in per.values())
    exp_E = sum(np.mean([r["E_J"] for r in v]) for v in per.values())
    flat_E = sum(r["E_J"] for r in rows)
    flat_p = sum(r["pass"] for r in rows)
    # the same, but with P1's 7,200 s mission limit and 1,800 s call limit shown not to bind (P1's own runs)
    import gzip
    p1calls = 0
    mx = 0.0
    over = 0
    capped = []
    for t in tasks:
        for f in glob.glob(f"{P1DRONES}/{cfg}/{t}/instance_*/run_*/llm_calls.jsonl.gz"):
            for line in gzip.open(f, "rt"):
                r = json.loads(line)
                p1calls += 1
                e = r.get("e2e_s") or 0
                mx = max(mx, e)
                over += e > 1800
                if r.get("finish_reason") == "length" and (r.get("completion_tokens") or 0) >= 32000:
                    capped.append((e, r["completion_tokens"]))
    p1_call_times = {"calls": p1calls, "longest_call_s": round(mx), "calls_over_1800s": over, "capped_calls": len(capped),
                     "capped_call_e2e_s_min_median_max": [round(min(c[0] for c in capped)), round(float(np.median([c[0] for c in capped]))), round(max(c[0] for c in capped))] if capped else None,
                     "capped_call_tokens_per_s_median": round(float(np.median([c[1] / c[0] for c in capped])), 1) if capped else None}
    return {"p1_single_drone_call_times_on_these_63_runs": p1_call_times,
            "definition": "P1 Thor gemma-4-26B Reflexion, drones/edge_devices/final_sweep_thor/reflexion/gemma-4-26B-A4B-it, "
                          "runs run_1..run_3 of each (task, instance). Pass = P1's grades.csv final_result (equals the harness "
                          "final_result in all 63 runs). Energy = run_meta workflow_energy_J (board energy over the run).",
            "n_runs": len(rows), "runs_per_mission": sorted({len(v) for v in per.values()}),
            "expected_passes_of_21": round(exp_pass, 3), "expected_energy_kJ": round(exp_E / 1000, 1),
            "kJ_per_success": round(exp_E / exp_pass / 1000, 3),
            "check_pooled_all_63_runs": {"passes": flat_p, "energy_kJ": round(flat_E / 1000, 1),
                                          "kJ_per_pass": round(flat_E / flat_p / 1000, 2)},
            "harness_vs_grade_disagreements": sum(1 for r in rows if r["pass"] != r["harness_pass"]),
            "per_mission": {f"{k[0]}i{k[1]}": {"pass_rate": round(float(np.mean([r['pass'] for r in v])), 3),
                                                "mean_E_kJ": round(float(np.mean([r['E_J'] for r in v])) / 1000, 1),
                                                "max_wall_min": round(max(r['wall_s'] for r in v) / 60, 1)} for k, v in per.items()},
            "all_p1_runs_within_7200s_mission_limit": all(r["wall_s"] <= 7200 for r in rows)}


def b_task_agreement():
    cfg = "edge_devices/final_sweep_thor/reflexion/gemma-4-26B-A4B-it"
    c = collections.Counter()
    for r in csv.DictReader(open(P1DRONES + "/grading/grades.csv")):
        if r["config"] == cfg and r["task"][0] in "AB":
            c[(r["task"][0], r["final_result"] == r["harness_final_result"])] += 1
    return {f"{k[0]}_tasks_{'agree' if k[1] else 'disagree'}": v for k, v in sorted(c.items())}


# ------------------------------------------------------------------------------ T4/T5: capped calls, reuse, pool use, T6
def capped_and_reuse(R):
    C = R["calls"]
    resp = [c for c in C if c.get("completion_tokens") is not None]
    cap_any = [c for c in C if c.get("finish_reason") == "length"]
    cap = [c for c in cap_any if (c.get("completion_tokens") or 0) >= 32000]   # = every length-stop on Thor; Orin also has 1,024-token evaluator caps
    cap32 = cap
    tot_e = sum(c.get("e2e_s") or 0 for c in C)
    tot_o = sum(c.get("completion_tokens") or 0 for c in C)
    P = sum(c.get("prompt_tokens") or 0 for c in C)
    Cc = sum(c.get("cached_tokens") or 0 for c in C)
    sw = [c for c in C if c.get("role") != "evaluator" and c.get("prompt_tokens")]
    per = [(c.get("cached_tokens") or 0) / c["prompt_tokens"] for c in C if c.get("prompt_tokens")]
    d = {"calls": len(C), "calls_with_response": len(resp), "errored_calls": len(C) - len(resp),
         "calls_finish_length_any_cap": len(cap_any), "capped_calls_finish_length": len(cap), "capped_calls_ge32000_tokens": len(cap32),
         "capped_max_tokens_values": sorted({c.get("max_tokens") for c in cap}),
         "capped_share_of_calls": round(len(cap) / len(C), 4),
         "capped_share_of_output_tokens": round(sum(c["completion_tokens"] for c in cap) / tot_o, 4),
         "capped_share_of_llm_time": round(sum(c.get("e2e_s") or 0 for c in cap) / tot_e, 4),
         "llm_time_total_s": round(tot_e),
         "cache_reuse_token_weighted_all_calls": round(Cc / P, 4),
         "cache_reuse_token_weighted_stepcalls_only": round(sum(c.get("cached_tokens") or 0 for c in sw) / sum(c["prompt_tokens"] for c in sw), 4) if sw else None,
         "cache_reuse_per_call_mean": round(float(np.mean(per)), 4), "cache_reuse_per_call_median": round(float(np.median(per)), 4)}
    # time saved if a looping call is cut at 4,096 tokens (call time assumed proportional to its tokens; no resample cost)
    sv = sum((c.get("e2e_s") or 0) * (1 - 4096 / c["completion_tokens"]) for c in cap if c.get("completion_tokens"))
    d["llm_time_saved_if_capped_calls_cut_at_4096_tokens"] = round(sv / tot_e, 4)
    if cap:
        ee = [c.get("e2e_s") or 0 for c in cap]
        d["capped_call_e2e_s_min_median_max"] = [round(min(ee)), round(float(np.median(ee))), round(max(ee))]
        d["capped_call_tokens_per_s_median"] = round(float(np.median([c["completion_tokens"] / max(c.get("e2e_s") or 1, 1) for c in cap])), 1)
        d["capped_calls_over_1800s"] = sum(1 for e in ee if e > 1800)
    if R["kv"]:
        for f in ("full_token_usage", "swa_token_usage"):
            v = kvarr(R, f)
            d["pool_" + f] = {"mean": round(float(v.mean()), 3), "p95": round(float(np.percentile(v, 95)), 3), "max": round(float(v.max()), 3)}
        d["pool_tokens"] = int(R["kv"][-1].get("max_total_num_tokens") or 0)
        q = kvarr(R, "num_queue_reqs")
        rr = kvarr(R, "num_running_reqs")
        d["queue_gt0_time_share"] = round(float((q > 0).mean()), 4)
        d["queue_max"] = int(q.max())
        d["running_mean"] = round(float(rr.mean()), 2)
    return d


def decoding_table(keys):
    out = {}
    for k in keys:
        R = load_run(k)
        c = collections.Counter((x.get("temperature"), x.get("top_p"), x.get("top_k"), x.get("seed")) for x in R["calls"])
        mt = collections.Counter(x.get("max_tokens") for x in R["calls"])
        out[k] = {"recorded_(temperature,top_p,top_k,seed):calls": {str(t): n for t, n in c.items()},
                  "max_tokens_recorded": {str(t): n for t, n in mt.items()}}
        # what the agent asked for (its own banner line, step-wise agents only)
        req = collections.Counter()
        for m in R["missions"].values():
            try:
                for line in open(m["dir"] + "/transcript.log", errors="replace"):
                    mm = re.search(r"\[P5 PROMPT\].*thinking=(\w+); temperature=([\d.]+) top_p=([\d.]+) top_k=(\d+)", line)
                    if mm:
                        req[f"thinking={mm.group(1)} temperature={mm.group(2)} top_p={mm.group(3)} top_k={mm.group(4)}"] += 1
                        break
            except FileNotFoundError:
                pass
        out[k]["requested_by_stepwise_agent_banner:missions"] = dict(req)
    return out


# ---------------------------------------------------------------------------------- P3c: the loop detector (same text reappears)
def call_text(c):
    return (c.get("reasoning_content") or "") + (c.get("content") or "") + \
        "".join((t["function"]["arguments"] or "") for t in (c.get("tool_calls") or []))


def first_repeat(t, W, k):
    """End index of the first W-character block that appears for the k-th time (earlier copies at least W apart)."""
    seen = collections.defaultdict(list)
    for i in range(0, len(t) - W + 1):
        L = seen[t[i:i + W]]
        if len(L) >= k - 1 and i - L[-(k - 1)] >= W:
            return i + W
        if not L or i - L[-1] >= W:
            L.append(i)
    return None


def detector_eval(cap, oth, rules):
    res = {}
    for (W, k) in rules:
        r = {}
        for name, grp in (("capped_looping_calls", cap), ("other_long_calls", oth)):
            pos, hit = [], 0
            for c in grp:
                t = call_text(c)
                p = first_repeat(t, W, k)
                if p is not None:
                    hit += 1
                    pos.append(p * c["completion_tokens"] / max(len(t), 1))
            r[name] = {"flagged": hit, "of": len(grp), "trigger_tokens_p10_p50_p90_max": None if not pos else
                       [round(float(np.percentile(pos, 10))), round(float(np.percentile(pos, 50))),
                        round(float(np.percentile(pos, 90))), round(float(max(pos)))],
                       "_positions": pos if name == "capped_looping_calls" else None,
                       "_cap_pairs": None}
        res[f"block{W}chars_{k}x"] = r
    return res


# ------------------------------------------------------------------------------------------- step-wise tables (P1c, P2c)
def step_rows(R):
    rows, bad = [], []
    for k, m in R["missions"].items():
        calls = [c for c in m["calls"]]
        ev_t = [c["t_send_mono"] for c in calls if c.get("role") == "evaluator"]
        sw = [c for c in calls if c.get("role") != "evaluator" and c.get("completion_tokens") is not None]
        steps = m["tr"]["steps"]
        # Thor's tracer version has no tool_calls field: there a call that ended finish_reason=tool_calls matches any step
        names = [(c["tool_calls"][0]["function"]["name"] if c.get("tool_calls") else "nudge") if "tool_calls" in c
                 else ("ANY" if c.get("finish_reason") == "tool_calls" else "nudge") for c in sw]
        if len(sw) != len(steps) or not all(a == b["name"] or (a == "ANY" and b["name"] != "nudge") for a, b in zip(names, steps)):
            bad.append(f"{k[0]}i{k[1]}")
            continue
        prev = None
        prev_raw = None
        for i, (c, s) in enumerate(zip(sw, steps)):
            nxt = sw[i + 1] if i + 1 < len(sw) else None
            boundary = nxt is not None and any(c["t_end_mono"] <= t <= nxt["t_send_mono"] for t in ev_t)
            if i > 0 and any(sw[i - 1]["t_end_mono"] <= t <= c["t_send_mono"] for t in ev_t):
                prev = None
            d = None
            if s["name"] in MOVE and prev is not None and s["state"]:
                d = math.dist(prev[:3], s["state"][:3])
            d_raw = math.dist(prev_raw[:3], s["state"][:3]) if (s["name"] in MOVE and prev_raw is not None and s["state"]) else None
            if s["state"]:
                prev = s["state"]
                prev_raw = s["state"]
            rows.append({"mission": f"{k[0]}i{k[1]}", "i": i, "name": s["name"], "prompt": c["prompt_tokens"], "completion": c["completion_tokens"],
                         "gap": None if nxt is None or boundary else nxt["t_send_mono"] - c["t_end_mono"],
                         "next_prompt": None if nxt is None or boundary else nxt["prompt_tokens"], "dist": d,
                         "gap_raw": None if nxt is None else nxt["t_send_mono"] - c["t_end_mono"], "dist_raw": d_raw})
    return rows, bad


def p1c(rows_by_run, A=10.6, v=2.0, raw=False):
    out = {}
    allmv = []
    gk, dk = ("gap_raw", "dist_raw") if raw else ("gap", "dist")
    for k, rows in rows_by_run.items():
        mv = [dict(r, gap=r[gk], dist=r[dk]) for r in rows if r["name"] in MOVE and r[dk] is not None and r[dk] > 0.5 and r[gk] and r[gk] > 0]
        if not mv:
            out[k] = {"moves": 0}
            continue
        a0 = float(np.median([r["gap"] - r["dist"] / v for r in mv]))
        e_fit = [abs(r["gap"] - (a0 + r["dist"] / v)) / r["gap"] for r in mv]
        e_fix = [abs(r["gap"] - (A + r["dist"] / v)) / r["gap"] for r in mv]
        out[k] = {"moves": len(mv), "fitted_offset_s": round(a0, 2), "err_p50_p90_fitted_offset": pctl(e_fit, (50, 90)),
                  "err_p50_p90_fixed_10.6s": pctl(e_fix, (50, 90)), "share_within_4pct_fixed": round(float(np.mean(np.array(e_fix) <= 0.04)), 3),
                  "share_within_5pct_fixed": round(float(np.mean(np.array(e_fix) <= 0.05)), 3)}
        allmv += [(k, r) for r in mv]
    return out, allmv


# ---------------------------------------------------------------------------------------------------------------------- main
def main():
    runs = {k: load_run(k) for k in RUNS}
    OUT["_note"] = ("Recomputed on the WS from the read-only copies (made 16 Oct 00:20-00:25 IST). Energy = trapezoid of the 200 ms board "
                    "samples over [first mission start, last mission end], the rule of P1's run_one.energy_j.")
    OUT["runs"] = {k: run_level(R) for k, R in runs.items()}

    # T1
    OUT["T1_p1_baseline"] = t1_baseline()
    OUT["T1_p1_baseline"]["B_task_harness_vs_grade_agreement_in_P1_Thor_Reflexion"] = b_task_agreement()
    # T2/T3 come from OUT["runs"]
    # T4/T5
    OUT["T4_T5_per_run"] = {k: capped_and_reuse(runs[k]) for k in THOR6}
    OUT["T4_T5_orin_for_reference"] = {k: capped_and_reuse(runs[k]) for k in RUNS if RUNS[k][2] == "orin"}
    # T6
    OUT["T6_decoding"] = decoding_table([k for k in RUNS])
    # P3c
    calls = []
    for k in THOR6:
        for c in runs[k]["calls"]:
            c["run"] = k
            calls.append(c)
    cap = [c for c in calls if c.get("finish_reason") == "length"]
    oth = [c for c in calls if c.get("finish_reason") != "length" and (c.get("completion_tokens") or 0) >= 2000]
    det = detector_eval(cap, oth, [(200, 3), (200, 2), (300, 2), (500, 2), (100, 3), (300, 3), (500, 3), (1000, 2), (1000, 3), (2000, 2)])
    # savings if the detector (200 chars, 3x) stops each looping call where it fires
    pos = det["block200chars_3x"]["capped_looping_calls"]["_positions"]
    tot_e = {k: sum(c.get("e2e_s") or 0 for c in runs[k]["calls"]) for k in THOR6}
    sav = collections.defaultdict(float)
    capk = []
    for c in cap:
        p = first_repeat(call_text(c), 200, 3)
        t = len(call_text(c))
        ptok = p * c["completion_tokens"] / max(t, 1) if p else c["completion_tokens"]
        sav[c["run"]] += (c.get("e2e_s") or 0) * (1 - ptok / c["completion_tokens"])
        capk.append(ptok)
    det_pos = {k: det[k]["capped_looping_calls"].pop("_positions") for k in det}
    for k in det:
        det[k]["other_long_calls"].pop("_positions")
        det[k]["capped_looping_calls"].pop("_cap_pairs")
        det[k]["other_long_calls"].pop("_cap_pairs")
    OUT["P3c_loop_detector"] = {
        "population": "the 6 Thor runs (W1 n4/n8, step-wise final n4/n8, step-wise fast-sim n4/n8)",
        "looping_calls = calls that ended finish_reason=length (32,768 tokens)": len(cap),
        "other_long_calls = calls with >= 2,000 output tokens that finished normally": len(oth),
        "note": "her detector's exact rule is not in the data copy; these are my rules (a W-character block of the model's reasoning/answer/tool-call text appearing for the k-th time; trigger position converted from characters to tokens by the call's tokens-per-character ratio)",
        "rules": det,
        "share_of_llm_time_saved_if_detector_200chars_3x_stops_each_capped_call_where_it_fires": {k: round(sav[k] / tot_e[k], 4) for k in THOR6},
        "capped_calls_total_by_run": dict(collections.Counter(c["run"] for c in cap)),
    }
    # step tables
    sw_keys = ["thor_w3f_n4", "thor_w3f_n8", "orin_w3f_n2", "orin_w3f_n4", "orin_w3f_n8"]
    extra_keys = ["thor_w3_n4", "thor_w3_n8", "gr_w3f_sf_n2", "gr_ss_n2", "gr_ss_n4", "gr_w3_n2"]
    rows_by_run, bad = {}, {}
    for k in sw_keys + extra_keys:
        rows_by_run[k], bad[k] = step_rows(runs[k])
    p1c_all, mv_all = p1c({k: rows_by_run[k] for k in sw_keys})
    p1c_extra, _ = p1c({k: rows_by_run[k] for k in extra_keys})
    fx = np.array([abs(r["gap"] - (10.6 + r["dist"] / 2.0)) / r["gap"] for _, r in mv_all])
    p1c_raw, mv_raw = p1c({k: rows_by_run[k] for k in sw_keys}, raw=True)
    fr = np.array([abs(r["gap"] - (10.6 + r["dist"] / 2.0)) / r["gap"] for _, r in mv_raw])
    p1c_raw_all, mv_raw_all = p1c({k: rows_by_run[k] for k in sw_keys + ["gr_w3f_sf_n2", "gr_ss_n2", "gr_ss_n4"]}, raw=True)
    fa = np.array([abs(r["gap"] - (10.6 + r["dist"] / 2.0)) / r["gap"] for _, r in mv_raw_all])
    OUT["P1c_next_call_time"] = {
        "definition": "gap = (send time of the next LLM call) - (end time of the call that issued the move); move = step_fly_to/step_fly_body with "
                      "distance > 0.5 m (distance from the transcript states); calls separated by an evaluator call are excluded. "
                      "Prediction = 10.6 s + distance / 2 m/s. NB the 10 s is the hover the P5 tool server itself adds after every move "
                      "(P5_INSPECT_S=10, stepwise_mcp_server.py line 45) and 2 m/s is the simulator's flight speed.",
        "unaligned_missions_skipped": bad, "final_runs": p1c_all,
        "pooled_final_runs": {"moves": len(fx), "err_p50_p90_p100": pctl(fx, (50, 90, 100)),
                              "share_within_4pct": round(float((fx <= 0.04).mean()), 3), "share_within_5pct": round(float((fx <= 0.05).mean()), 3),
                              "share_within_10pct": round(float((fx <= 0.10).mean()), 3)},
        "other_step_runs": p1c_extra,
        "variant_her_definition_(gap_across_attempt_boundaries_allowed,_no_state_reset)": {
            "five_final_runs": {"per_run_moves": {k: v.get("moves") for k, v in p1c_raw.items()}, "moves": len(fr), "err_p50_p90": pctl(fr, (50, 90)),
                                "share_within_4pct": round(float((fr <= 0.04).mean()), 3)},
            "five_final_runs_plus_granite_final_and_steady_runs": {"per_run_moves": {k: v.get("moves") for k, v in p1c_raw_all.items()}, "moves": len(fa), "err_p50_p90": pctl(fa, (50, 90)),
                                                                   "share_within_4pct": round(float((fa <= 0.04).mean()), 3)}}}
    # P2c
    pairs = {}
    allpairs = []
    for k in sw_keys + extra_keys:
        pr = [(r["prompt"], r["next_prompt"], r["i"]) for r in rows_by_run[k] if r["next_prompt"] is not None]
        pairs[k] = pr
    def p2(keys, skip_first):
        d = []
        for k in keys:
            for p, n, i in pairs[k]:
                if skip_first and i == 0:
                    continue
                d.append((p, n))
        d = np.array(d, dtype=float)
        g = d[:, 1] - d[:, 0]
        med = float(np.median(g))
        pred_err = np.abs(d[:, 0] + med - d[:, 1]) / d[:, 1]
        naive_err = np.abs(d[:, 0] - d[:, 1]) / d[:, 1]
        gr_err = np.abs(g - med) / np.maximum(g, 1)
        return {"steps": len(d), "growth_tokens_p10_p25_p50_p75_p90": pctl(g, (10, 25, 50, 75, 90)), "median_growth": med,
                "err_of_prompt_pred_(prompt+median_growth)_p50_p90": pctl(pred_err, (50, 90)), "share_within_4pct": round(float((pred_err <= 0.04).mean()), 3),
                "naive_no_growth_err_p90": pctl(naive_err, (90,)), "naive_share_within_4pct": round(float((naive_err <= 0.04).mean()), 3),
                "err_of_growth_pred_p50_p90": pctl(gr_err, (50, 90)), "share_growth_within_4pct_of_growth": round(float((gr_err <= 0.04).mean()), 3),
                "share_growth_in_150_200": round(float(((g >= 150) & (g <= 200)).mean()), 3)}
    OUT["P2c_conversation_growth"] = {
        "definition": "growth = prompt_tokens of the next step call - prompt_tokens of this step call (same attempt, no evaluator call in between)",
        "pairs_by_run": {k: len(v) for k, v in pairs.items()},
        "final_runs_all_steps": p2(sw_keys, False), "final_runs_excluding_first_step": p2(sw_keys, True),
        "all_step_runs_all_steps": p2(sw_keys + extra_keys, False), "all_step_runs_excluding_first_step": p2(sw_keys + extra_keys, True)}
    # step counts
    OUT["step_call_counts"] = {k: len(rows_by_run[k]) for k in rows_by_run}

    # P4c: retries
    def resc(keys):
        out = {}
        for k in keys:
            R = runs[k]
            ms = list(R["missions"].values())
            fin = [m for m in ms if m["tr"]["passed_line"] is not None]
            r = sum(1 for m in fin if m["tr"]["passed_line"] and m["tr"]["attempts"] >= 2)
            out[k] = {"missions": len(ms), "finished_with_PASSED_line": len(fin), "passed_first_attempt": sum(1 for m in fin if m["tr"]["passed_line"] and m["tr"]["attempts"] == 1),
                      "rescued_by_a_retry": r, "rescue_share_of_missions": round(r / len(ms), 3),
                      "missions_with_a_failed_first_attempt": sum(1 for m in fin if m["tr"]["attempts"] >= 2 or not m["tr"]["passed_line"]),
                      "rescue_share_of_missions_with_failed_first_attempt": None}
            nf = out[k]["missions_with_a_failed_first_attempt"]
            out[k]["rescue_share_of_missions_with_failed_first_attempt"] = round(r / nf, 3) if nf else None
        return out
    small = ["orin_w1_n2", "orin_w1_n4", "orin_w1_n8", "orin_w3f_n2", "orin_w3f_n4", "orin_w3f_n8", "gr_w3_n2", "gr_w3f_sf_n2", "gr_ss_n2"]
    OUT["P4c_retry_rescue"] = {"definition": "rescue = mission whose PASSED line is True and whose last [SUPERVISOR] attempt number is >= 2",
                               "small_models": resc(small), "big_model_for_reference": resc(["thor_w1_n4", "thor_w1_n8", "thor_w3f_n4", "thor_w3f_n8"])}

    # O1 queue
    o1 = {}
    for k in ["orin_w1_n2", "orin_w1_n4", "orin_w1_n8"]:
        R = runs[k]
        t = np.array([x["t_mono"] for x in R["kv"]])
        dt = np.diff(t, append=t[-1])
        q = kvarr(R, "num_queue_reqs")
        u = kvarr(R, "token_usage")
        rr = kvarr(R, "num_running_reqs")
        tcalls = sum(1 for m in R["missions"].values() if m["tr"]["toolcall_agent"])
        o1[k] = {"missions": len(R["jobs"]), "passed": OUT["runs"][k]["passed"], "kJ_per_success": OUT["runs"][k]["kJ_per_success_recomputed"],
                 "missions_whose_transcript_is_P1_tool_calling_agent": tcalls,
                 "roles_in_llm_calls": dict(collections.Counter(c.get("role") for c in R["calls"])),
                 "queue_gt0_time_share": round(float(dt[q > 0].sum() / dt.sum()), 4),
                 "queue_gt0_and_pool_usage_ge90pct_time_share": round(float(dt[(q > 0) & (u >= 0.9)].sum() / dt.sum()), 4),
                 "pool_usage_ge90pct_time_share": round(float(dt[u >= 0.9].sum() / dt.sum()), 4),
                 "pool_usage_ge95pct_time_share": round(float(dt[u >= 0.95].sum() / dt.sum()), 4),
                 "queue_gt0_but_pool_usage_below_50pct_time_share": round(float(dt[(q > 0) & (u < 0.5)].sum() / dt.sum()), 4),
                 "queue_max": int(q.max()), "running_mean": round(float(rr.mean()), 2), "pool_tokens": int(R["kv"][-1]["max_total_num_tokens"]),
                 "kv_cache_dtype": R["meta"]["server"]["kv_cache_dtype"]}
    OUT["O1_e4b_w1"] = o1

    # O2 granite
    OUT["O2_granite"] = granite_numbers(runs)
    # O3
    OUT["O3_reread"] = reread_numbers(runs)
    json.dump(OUT, open(OUTDIR + "/recheck.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    return runs


def conv_series(R, drone_ids=None, dt_s=15.0):
    """Summed size of the live conversations (tokens), on a time grid. A mission's conversation is prompt_tokens of its latest
    call at call start, growing linearly to prompt+completion at call end, held until the next call, 0 after the mission ends."""
    t0, t1 = R["t0"], R["t1"]
    grid = np.arange(t0, t1, dt_s)
    tot = np.zeros(len(grid))
    per_drone = {}
    for k, m in R["missions"].items():
        calls = [c for c in m["calls"] if c.get("completion_tokens") is not None and c.get("role") != "evaluator"]
        j = m["job"]
        s = np.zeros(len(grid))
        for i, c in enumerate(calls):
            a, b = c["t_send_mono"], c["t_end_mono"]
            nxt = calls[i + 1]["t_send_mono"] if i + 1 < len(calls) else j["t_end"]
            p, q = c["prompt_tokens"], c["completion_tokens"]
            idx = (grid >= a) & (grid < b)
            s[idx] = p + q * (grid[idx] - a) / max(b - a, 1e-9)
            idx2 = (grid >= b) & (grid < nxt)
            s[idx2] = p + q
        tot += s
        per_drone.setdefault(j["drone"], np.zeros(len(grid)))
        per_drone[j["drone"]] += s
    return grid, tot, per_drone


def granite_numbers(runs):
    out = {"pools_in_the_data_copy": {}, "note": ""}
    for k in ["gr_w3_n2", "gr_w3f_sf_n2", "gr_ss_n2", "gr_ss_n4"]:
        R = runs[k]
        out["pools_in_the_data_copy"][k] = {"kv_cache_dtype": R["meta"]["server"]["kv_cache_dtype"], "max_total_num_tokens": R["meta"]["server"]["max_total_num_tokens"],
                                            "n_drones": R["n"], "missions": len(R["jobs"]), "complete": R["summary"] is not None}
    # any fp8 / 44.9K run anywhere in the three copies?
    found = []
    for f in glob.glob(ROOT + "/*/p5_osdi/**/fleet_meta.json", recursive=True):
        s = json.load(open(f)).get("server", {})
        if "fp8" in str(s.get("kv_cache_dtype")) or (s.get("max_total_num_tokens") or 0) > 40000 and "granite" in str(s.get("model_path")):
            found.append({"file": f.replace(ROOT + "/", ""), "kv_cache_dtype": s.get("kv_cache_dtype"), "pool": s.get("max_total_num_tokens"), "model": s.get("model_path")})
    out["fleet_meta_with_fp8_or_pool_over_40K_for_granite"] = found
    k = "gr_w3f_sf_n2"
    R = runs[k]
    grid, tot, per = conv_series(R)
    pool = R["meta"]["server"]["max_total_num_tokens"]
    live = tot > 0
    q = {}
    kvt = np.array([x["t_mono"] for x in R["kv"]])
    qq = kvarr(R, "num_queue_reqs")
    qi = np.interp(grid, kvt, qq) > 0
    out["w3f_granite_sf_n2_16bit"] = {"pool_tokens": pool, "conversation_sum_max": int(tot.max()),
                                      "share_of_time_sum_of_conversations_exceeds_pool": round(float((tot > pool)[live].mean()), 3),
                                      "share_of_time_with_both_drones_in_a_mission_and_sum_exceeds_pool": None,
                                      "per_drone_conversation_max": {int(d): int(v.max()) for d, v in per.items()},
                                      "queue_gt0_time_share": round(float(qi.mean()), 3),
                                      "max_prompt_tokens_any_call": max((c.get("prompt_tokens") or 0) for c in R["calls"]),
                                      "evicted_tokens": int(R["kv"][-1].get("evicted_tokens_total", 0) - R["kv"][0].get("evicted_tokens_total", 0))}
    both = np.zeros(len(grid), bool)
    pd_list = list(per.values())
    if len(pd_list) >= 2:
        both = (pd_list[0] > 0) & (pd_list[1] > 0)
    out["w3f_granite_sf_n2_16bit"]["share_of_time_with_both_drones_in_a_mission_and_sum_exceeds_pool"] = round(float((tot > pool)[both].mean()), 3) if both.any() else None
    out["w3f_granite_sf_n2_16bit"]["share_of_time_both_drones_in_a_mission"] = round(float(both.mean()), 3)
    return out


def reread_numbers(runs):
    out = {"definition": "server-side time-to-first-token (ttft_s, recorded only when one request finished its first token in the sampling window) "
                         "of calls whose uncached prompt (prompt_tokens - cached_tokens) is large; queue empty during the call (so no queueing is counted)."}
    for model, keys in (("gemma-4-E4B (Orin-32-1)", ["orin_w1_n2", "orin_w1_n4", "orin_w1_n8"]),
                        ("granite-4.2-8b (Orin-32-2)", ["gr_w3_n2", "gr_w3f_sf_n2", "gr_ss_n2", "gr_ss_n4"])):
        pts = []
        for k in keys:
            R = runs[k]
            kvt = np.array([x["t_mono"] for x in R["kv"]])
            rr = kvarr(R, "num_running_reqs")
            qq = kvarr(R, "num_queue_reqs")
            for c in R["calls"]:
                unc = (c.get("prompt_tokens") or 0) - (c.get("cached_tokens") or 0)
                if c.get("ttft_s") is None or unc < 6000:
                    continue
                m = (kvt >= c["t_send_mono"]) & (kvt <= c["t_end_mono"])
                if not m.any() or qq[m].max() > 0:
                    continue
                pts.append((unc, c["ttft_s"], float(rr[m].mean()), k))
        d = {"calls_used": len(pts)}
        if len(pts) >= 3:
            x = np.array([p[0] for p in pts], float)
            y = np.array([p[1] for p in pts], float)
            b, a = np.polyfit(x, y, 1)
            d.update({"fit_ttft_s_=_a_+_b*tokens": [round(float(a), 2), round(float(b), 5)],
                      "predicted_ttft_s_at_15000_uncached_tokens": round(float(a + b * 15000), 1),
                      "uncached_range": [int(x.min()), int(x.max())], "ttft_range_s": [round(float(y.min()), 1), round(float(y.max()), 1)],
                      "median_rate_tok_per_s": round(float(np.median(x / y))),
                      "solo_calls_only(mean running<=1.2)": None})
            solo = [(u, t) for u, t, r, _ in pts if r <= 1.2]
            if len(solo) >= 3:
                xs = np.array([p[0] for p in solo], float)
                ys = np.array([p[1] for p in solo], float)
                bs, as_ = np.polyfit(xs, ys, 1)
                d["solo_calls_only(mean running<=1.2)"] = {"n": len(solo), "predicted_ttft_s_at_15000": round(float(as_ + bs * 15000), 1),
                                                           "median_rate_tok_per_s": round(float(np.median(xs / ys)))}
            big = [(u, round(t, 1), round(r, 2)) for u, t, r, _ in pts if u >= 12000]
            d["observed_calls_with_>=12K_uncached_tokens(unc,ttft_s,mean_running)"] = big[:12]
        out[model] = d
    return out


# ====================================================================================================== section 2: the four plots
import matplotlib  # noqa: E402
import matplotlib.patches  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator  # noqa: E402

BG, INK, BLUE, ORANGE, GREY, GRID = "#FAFAF7", "#3D4752", "#2A78D6", "#E07B39", "#8A94A3", "#E6E8EB"
FS = 18          # every text element is >= 18 pt; figsize = display px / 100, so 18 pt = 25 px on the slide
DPI = 200


def setup_fonts():
    for f in glob.glob(os.path.expanduser("~/work/fonts/IBMPlexSans-*.ttf")):
        fm.fontManager.addfont(f)
    fam = "IBM Plex Sans" if any(x.name == "IBM Plex Sans" for x in fm.fontManager.ttflist) else "DejaVu Sans"
    plt.rcParams.update({"font.family": fam, "font.size": FS, "axes.labelsize": FS, "xtick.labelsize": FS, "ytick.labelsize": FS,
                         "text.color": INK, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
                         "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG, "axes.edgecolor": INK,
                         "axes.linewidth": 1.2, "axes.grid": False, "legend.fontsize": FS, "axes.unicode_minus": False})
    return fam


def style(ax, grid_y=True):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK)
    ax.tick_params(colors=INK, labelsize=FS, length=5, width=1.2)
    if grid_y:
        ax.yaxis.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
    ax.xaxis.grid(False)


def fig_px(w, h):
    return plt.figure(figsize=(w / 100, h / 100), dpi=DPI)


def plot_packing(OUT, path):
    fig = fig_px(1000, 620)
    ax = fig.add_axes([0.105, 0.17, 0.865, 0.79])
    style(ax)
    r = OUT["runs"]
    p1 = OUT["T1_p1_baseline"]
    S = [  # (series label at the right end, color, [(x, kJ, "passed/total")])
        ("Thor 26B\nReflexion (P1)", BLUE, [(1, p1["kJ_per_success"], f"{p1['expected_passes_of_21']:.1f}/21"),
                                              (4, r["thor_w1_n4"]["kJ_per_success_recomputed"], "16/21"),
                                              (8, r["thor_w1_n8"]["kJ_per_success_recomputed"], "17/21")]),
        ("Thor 26B\nstep-wise", ORANGE, [(4, r["thor_w3f_n4"]["kJ_per_success_recomputed"], "10/14"),
                                          (8, r["thor_w3f_n8"]["kJ_per_success_recomputed"], "11/14")]),
        ("Orin E4B\nP1 tool-calling", GREY, [(2, r["orin_w1_n2"]["kJ_per_success_recomputed"], "17/36"),
                                            (4, r["orin_w1_n4"]["kJ_per_success_recomputed"], "17/36"),
                                            (8, r["orin_w1_n8"]["kJ_per_success_recomputed"], "17/36")]),
    ]
    ax.set_xscale("log", base=2)
    ax.set_xlim(0.8, 19)
    ax.set_ylim(0, 150)
    ax.xaxis.set_major_locator(FixedLocator([1, 2, 4, 8]))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v)}"))
    ax.set_yticks([0, 50, 100, 150])
    for name, col, pts in S:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ax.plot(xs, ys, color=col, lw=3.2, marker="o", ms=11, mec=BG, mew=2, zorder=3)
        for x, y, t in pts:   # passed/total above each point, on a background-coloured halo so a crossing line never hides it
            ax.annotate(t, (x, y), xytext=(0, 11), textcoords="offset points", ha="center", va="bottom", fontsize=FS, color=INK,
                        zorder=5, bbox=dict(boxstyle="square,pad=0.12", fc=BG, ec="none"))
        ax.annotate(name, (pts[-1][0], pts[-1][1]), xytext=(34, 0), textcoords="offset points", ha="left", va="center",
                    fontsize=FS, color=INK, linespacing=1.15)
    ax.set_xlabel("drones per board")
    ax.set_ylabel("board energy per success (kJ)")
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def plot_loops(OUT, path):
    fig = fig_px(1000, 560)
    ax = fig.add_axes([0.105, 0.2, 0.88, 0.66])
    style(ax)
    order = [("thor_w1_n4", "Reflexion\n4 drones"), ("thor_w1_n8", "Reflexion\n8 drones"), ("thor_w3f_n4", "Step-wise\n4 drones"),
             ("thor_w3f_n8", "Step-wise\n8 drones"), ("thor_w3_n4", "Fast sim\n4 drones"), ("thor_w3_n8", "Fast sim\n8 drones")]
    xs = np.arange(len(order))
    w = 0.36
    for i, (k, lab) in enumerate(order):
        d = OUT["T4_T5_per_run"][k]
        a = 1.0 if i < 4 else 0.45
        c1, c2 = 100 * d["capped_share_of_calls"], 100 * d["capped_share_of_llm_time"]
        ax.bar(i - w / 2 - 0.01, c1, w, color=BLUE, alpha=a, zorder=3)
        ax.bar(i + w / 2 + 0.01, c2, w, color=ORANGE, alpha=a, zorder=3)
        ax.text(i - w / 2 - 0.01, c1 + 2, f"{c1:.0f}%", ha="center", va="bottom", fontsize=FS, color=INK)
        ax.text(i + w / 2 + 0.01, c2 + 2, f"{c2:.0f}%", ha="center", va="bottom", fontsize=FS, color=INK)
    ax.set_xticks(xs)
    ax.set_xticklabels([l for _, l in order])
    ax.set_xlim(-0.6, len(order) - 0.4)
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0", "25", "50", "75", "100%"])
    ax.axvline(3.5, color=GRID, lw=1.5, zorder=1)
    ax.text(4.5, 95, "earlier runs, 5x sim", ha="center", va="center", fontsize=FS, color=INK)
    # key above the axes
    fig.patches.append(matplotlib.patches.Rectangle((0.115, 0.915), 0.022, 0.04, transform=fig.transFigure, color=BLUE))
    fig.text(0.145, 0.915, "share of calls", fontsize=FS, color=INK, va="bottom")
    fig.patches.append(matplotlib.patches.Rectangle((0.37, 0.915), 0.022, 0.04, transform=fig.transFigure, color=ORANGE))
    fig.text(0.40, 0.915, "share of LLM time", fontsize=FS, color=INK, va="bottom")
    fig.text(0.985, 0.915, "calls cut off at 32,768 tokens", fontsize=FS, color=INK, va="bottom", ha="right")
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def plot_orin_wait(OUT, path):
    fig = fig_px(760, 520)
    ax = fig.add_axes([0.14, 0.26, 0.83, 0.50])
    style(ax)
    ks = ["orin_w1_n2", "orin_w1_n4", "orin_w1_n8"]
    nd = [2, 4, 8]
    xs = np.arange(3)
    w = 0.36
    for i, k in enumerate(ks):
        d = OUT["O1_e4b_w1"][k]
        a, b = 100 * d["queue_gt0_time_share"], 100 * d["queue_gt0_and_pool_usage_ge90pct_time_share"]
        ax.bar(i - w / 2 - 0.01, a, w, color=BLUE, zorder=3)
        ax.bar(i + w / 2 + 0.01, b, w, color=ORANGE, zorder=3)
        ax.text(i - w / 2 - 0.01, a + 2, f"{a:.0f}%", ha="center", va="bottom", fontsize=FS, color=INK)
        ax.text(i + w / 2 + 0.01, b + 2, f"{b:.0f}%", ha="center", va="bottom", fontsize=FS, color=INK)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{n} drones\n{OUT['O1_e4b_w1'][k]['kJ_per_success']:.1f} kJ" for n, k in zip(nd, ks)])
    ax.set_xlim(-0.6, 2.6)
    ax.set_ylim(0, 80)
    ax.set_yticks([0, 20, 40, 60, 80])
    ax.set_ylabel("share of time (%)")
    fig.patches.append(matplotlib.patches.Rectangle((0.14, 0.925), 0.03, 0.04, transform=fig.transFigure, color=BLUE))
    fig.text(0.18, 0.92, "a request is queued", fontsize=FS, color=INK, va="bottom")
    fig.patches.append(matplotlib.patches.Rectangle((0.14, 0.845), 0.03, 0.04, transform=fig.transFigure, color=ORANGE))
    fig.text(0.18, 0.84, "queued and the pool is 90% full", fontsize=FS, color=INK, va="bottom")
    fig.text(0.02, 0.02, "kJ = board energy per success", fontsize=FS, color=INK, va="bottom")
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def plot_orin_granite(runs, OUT, path):
    fig = fig_px(1500, 520)
    axl = fig.add_axes([0.065, 0.2, 0.43, 0.72])
    axr = fig.add_axes([0.565, 0.2, 0.43, 0.72])
    for ax in (axl, axr):
        style(ax)
        ax.set_ylim(0, 52)
        ax.set_yticks([0, 10, 20, 30, 40, 50])
        ax.set_xlabel("minutes into the run")
    axl.set_ylabel("KV tokens (thousands)")
    # left panel: the 16-bit run
    k = "gr_w3f_sf_n2"
    R = runs[k]
    grid, tot, per = conv_series(R, dt_s=20.0)
    tm = (grid - R["t0"]) / 60
    pool = R["meta"]["server"]["max_total_num_tokens"]
    kvt = np.array([x["t_mono"] for x in R["kv"]])
    q = np.interp(grid, kvt, kvarr(R, "num_queue_reqs")) > 0
    # shade where a request waited
    edges = np.flatnonzero(np.diff(np.concatenate([[0], q.astype(int), [0]])))
    for a, b in zip(edges[::2], edges[1::2]):
        axl.axvspan(tm[a], tm[min(b, len(tm) - 1)], color=ORANGE, alpha=0.22, lw=0, zorder=1)
    axl.step(tm, tot / 1000, where="post", color=BLUE, lw=2.2, zorder=3)
    axl.axhline(pool / 1000, color=INK, lw=2, ls=(0, (6, 4)), zorder=4)
    axl.set_xlim(0, tm[-1])
    axl.text(tm[-1] * 0.02, 51, f"16-bit KV cache, pool {pool / 1000:.1f}K (dashed)", ha="left", va="top", fontsize=FS, color=INK, fontweight="bold")
    axl.text(tm[-1] * 0.36, 40.5, "the two conversations, summed", ha="left", va="bottom", fontsize=FS, color=BLUE)
    axl.text(tm[-1] * 0.02, 2, "shaded: a request waits", ha="left", va="bottom", fontsize=FS, color=INK)
    # right panel: no FP8 run in the data copy
    axr.set_xlim(0, 1)
    axr.text(0.5, 0.52, "FP8 run not in the data copy", ha="center", va="center", fontsize=FS, color=INK, transform=axr.transAxes)
    axr.text(0.5, 0.40, "(Orin-32-2 copy of 16 Oct 00:25 has 16-bit runs only)", ha="center", va="center", fontsize=FS, color=GREY, transform=axr.transAxes)
    axr.text(0.02, 0.98, "FP8 KV cache", ha="left", va="top", fontsize=FS, color=INK, fontweight="bold", transform=axr.transAxes)
    axr.set_xticks([])
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def make_plots(runs):
    fam = setup_fonts()
    print("font family:", fam)
    plot_packing(OUT, OUTDIR + "/packing.png")
    plot_loops(OUT, OUTDIR + "/loops.png")
    plot_orin_wait(OUT, OUTDIR + "/orin_wait.png")
    plot_orin_granite(runs, OUT, OUTDIR + "/orin_granite.png")
    # the deck shows only the 16-bit panel (no FP8 granite run is in the data copy): the left 1,530 px
    from PIL import Image
    Image.open(OUTDIR + "/orin_granite.png").crop((0, 0, 1530, 1040)).save(OUTDIR + "/orin_granite_16bit.png")
    OUT["_plots"] = {"font_family": fam, "files": ["packing.png", "loops.png", "orin_wait.png", "orin_granite_16bit.png"]}


if __name__ == "__main__":
    _runs = main()
    make_plots(_runs)
    json.dump(OUT, open(OUTDIR + "/recheck.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("wrote recheck.json and the four PNGs in", OUTDIR)

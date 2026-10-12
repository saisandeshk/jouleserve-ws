"""A-J1 (planning/OPTIONS_PLAN.md §5.3): do P1's drone loops survive sampling on P1's own setup (bf16 gemma-4-26B-A4B-it,
P1's image and flags, Thor-1)? Analysis of jsw/workloads/loop_replay runs driven by env/jetson_loop_point.sh.
Written on 12 Oct while the pilot ran, before its data was read (plan §6 rule 7).

    python -m analysis.a_j1 <run-dir> [<run-dir> ...]      (WS; default ~/work/runs/aj1*-thor-*)
                                                           -> reports/2026-10-06-options/a_j1.json

Per arm (greedy = P1's protocol, stopped where the online detector fires; sampled:<seed> = Gemma-4's defaults, run to
their end) and per kind (loop: capped on P1's Thor; control: finished on its own after >= 2,000 tokens), A-E1's measures
(analysis/a_e1): the loop flag with a Wilson 95% interval, the finish reason, output size and time, the program's
validity (parses; calls only drone-API names P1's own finished programs use). Energy is the board's (P1's total power
field, jsw/telemetry/jetson.py), integrated per call and per arm over the unit-clock span of each (analysis/device_runs
Clock), plus the decode rate per call (streamed chunks over first-to-last chunk).
Decision rules (fixed in plan §5.3):
1. reproduction: greedy loops on >= 80% of the prompts that looped on P1's Thor; else the 4-bit result stands alone;
2. sampling removes the loops: the sampled arm loops on <= 10% of them (Wilson bounds reported) and, in the full set, the
   controls do not get worse (finish rate, valid programs);
3. the pilot (10 loop prompts, no controls) is indicative only: 0 of 10 still has a 95% upper bound of 28%.
"""
from __future__ import annotations

import glob
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

from analysis.a_e1 import api_calls, known_api, program, wilson
from analysis.device_runs import Clock, _jl, _preflight
from analysis.sessions import REPO
from jsw.telemetry.jetson import board_energy, load as load_samples

OUT = REPO / "reports/2026-10-06-options/a_j1.json"
RUNS = Path.home() / "work/runs"


def _texts(run_dir):
    import gzip
    msgs = {}
    for f in glob.glob(str(Path(run_dir) / "texts" / "*.json.gz")):
        with gzip.open(f, "rt") as fh:
            j = json.load(fh)
        msgs[(j["rec"]["arm"], j["rec"]["id"])] = j["message"]
    return msgs


def run_summary(run_dir, api):
    d = Path(run_dir)
    man = json.loads((d / "manifest.json").read_text())
    clk = Clock(man)
    samples = load_samples(d / "device" / "device_samples.jsonl")
    recs, msgs = _jl(d / "calls.jsonl"), _texts(d)
    gw = {(c.get("sid"), c.get("t_req")): c for c in _jl(d / "gw" / "calls.jsonl")}
    gw_by_sid = defaultdict(list)
    for c in gw.values():
        gw_by_sid[c.get("sid")].append(c)
    ev = _jl(d / "events.jsonl")
    wins = {}
    for e in ev:
        if e["kind"] == "arm_start":
            wins[e["arm"]] = [e["t_mono"], None]
        elif e["kind"] == "arm_end" and e["arm"] in wins:
            wins[e["arm"]][1] = e["t_mono"]
    arms = {}
    for arm, (t0, t1) in wins.items():
        if t1:
            e = board_energy(samples, clk.unit(t0), clk.unit(t1))
            arms[arm] = {"board_energy_kj": round(e["energy_J"] / 1000, 1), "wall_s": round(t1 - t0),
                         "mean_W": round(e["mean_W"], 1), "gaps": e["gaps"]}
    calls = []
    for r in recs:
        e = board_energy(samples, clk.unit(r["t0"]), clk.unit(r["t1"]))
        g = gw_by_sid.get(r.get("sid")) or []
        g = g[0] if len(g) == 1 else None
        rate = ((g["chunks"] - 1) / (g["t_last"] - g["t_first"])
                if g and g.get("t_first") and g.get("t_last") and g["t_last"] > g["t_first"] else None)
        code = program(msgs.get((r["arm"], r["id"])) or {}) if r["stopped_by"] != "loop" and not r["error"] else None
        names = api_calls(code) if code else None
        calls.append({**{k: r.get(k) for k in ("id", "task", "role", "kind", "arm", "finish_reason", "stopped_by",
                                               "error", "s", "completion_tokens", "est_tokens", "chars")},
                      "out_tokens": r["completion_tokens"] or r["est_tokens"] or round(r["chars"] / 3.2),
                      "recorded_tokens": r["recorded"]["completion_tokens"],
                      "recorded_s": r["recorded"].get("e2e_s"),
                      "board_energy_j": round(e["energy_J"], 1), "board_gaps": e["gaps"],
                      "decode_tok_s": round(rate, 2) if rate else None,
                      "program_parses": names is not None,
                      "program_valid": (bool(names) and names <= api) if names is not None and r["task"][:1] in "AB"
                      else (names is not None)})
    return {"run": d.name, "preflight_before": _preflight(d, "before"), "preflight_after": _preflight(d, "after"),
            "clock_offset_s": clk.offset, "clock_drift_s": clk.spread, "arms": arms, "calls": calls}


def cells(calls):
    out = {}
    by = defaultdict(list)
    for c in calls:
        by[(c["arm"], c["kind"])].append(c)
    for (arm, kind), cs in sorted(by.items()):
        n = len(cs)
        loops = sum(c["stopped_by"] == "loop" for c in cs)
        fin = sum(c["finish_reason"] in ("stop", "tool_calls") and c["stopped_by"] != "loop" for c in cs)
        capped = sum(c["finish_reason"] == "length" and c["stopped_by"] != "loop" for c in cs)
        gen = [c for c in cs if c["role"] == "generator" and c["stopped_by"] != "loop" and not c["error"]]
        rates = [c["decode_tok_s"] for c in cs if c["decode_tok_s"]]
        out[f"{arm}|{kind}"] = dict(
            n=n, errors=sum(bool(c["error"]) for c in cs), loops=loops, loop_rate=round(loops / n, 4),
            loop_ci=wilson(loops, n), finished=fin, finish_rate=round(fin / n, 4), capped_no_loop=capped,
            out_tokens_median=round(st.median(c["out_tokens"] for c in cs)),
            s_median=round(st.median(c["s"] for c in cs), 1),
            board_kj_total=round(sum(c["board_energy_j"] for c in cs) / 1000, 1),
            board_kj_median=round(st.median(c["board_energy_j"] for c in cs) / 1000, 2),
            decode_tok_s_median=round(st.median(rates), 2) if rates else None,
            generator_finished=len(gen), program_parses=sum(c["program_parses"] for c in gen),
            program_valid=sum(c["program_valid"] for c in gen),
            recorded_tokens_median=round(st.median(c["recorded_tokens"] for c in cs)))
    return out


def rules(cl, pilot):
    g = cl.get("greedy|loop")
    if not g:
        return {}
    sampled = [v for k, v in cl.items() if k.startswith("sampled") and k.endswith("|loop")]
    s_loops, s_n = sum(v["loops"] for v in sampled), sum(v["n"] for v in sampled)
    ctrl_g = cl.get("greedy|control")
    ctrl_s = [v for k, v in cl.items() if k.startswith("sampled") and k.endswith("|control")]
    reproduced = g["loop_rate"] >= 0.80
    s_rate = s_loops / s_n if s_n else None
    controls_ok = None
    if ctrl_g and ctrl_s:
        fin_s = sum(v["finished"] for v in ctrl_s) / sum(v["n"] for v in ctrl_s)
        val_s = sum(v["program_valid"] for v in ctrl_s) / max(1, sum(v["generator_finished"] for v in ctrl_s))
        val_g = ctrl_g["program_valid"] / max(1, ctrl_g["generator_finished"])
        controls_ok = fin_s >= ctrl_g["finish_rate"] - 0.05 and val_s >= val_g - 0.05
    verdict = ("not reproduced: the 4-bit result stands alone" if not reproduced else
               "sampling removes the loops" if s_rate is not None and s_rate <= 0.10 and controls_ok is not False else
               "sampling reduces but does not remove the loops" if s_rate is not None and s_rate < g["loop_rate"] else
               "sampling does not reduce the loops" if s_rate is not None else "sampled arm missing")
    return dict(greedy_loop_rate=g["loop_rate"], greedy_ci=g["loop_ci"], reproduction=reproduced,
                sampled_loop_rate=round(s_rate, 4) if s_rate is not None else None, sampled_ci=wilson(s_loops, s_n),
                controls_ok=controls_ok, verdict=verdict + (" (pilot: indicative only)" if pilot else ""))


def main():
    dirs = [Path(x) for x in sys.argv[1:]] or [Path(p) for p in sorted(glob.glob(str(RUNS / "aj1*-thor-*")))
                                               if (Path(p) / "calls.jsonl").exists()]
    api = known_api(REPO / "data/a_e1/prompts.jsonl")
    runs = [run_summary(d, api) for d in dirs]
    calls = [c for r in runs for c in r["calls"]]
    cl = cells(calls)
    pilot = not any(c["kind"] == "control" for c in calls)
    res = {"runs": [{k: v for k, v in r.items() if k != "calls"} for r in runs], "cells": cl,
           "rules": rules(cl, pilot), "calls": calls}
    OUT.write_text(json.dumps(res, indent=1, default=str))
    for k, v in cl.items():
        print(k, {x: v[x] for x in ("n", "loops", "loop_ci", "finished", "capped_no_loop", "out_tokens_median",
                                    "s_median", "board_kj_median", "decode_tok_s_median", "program_valid",
                                    "generator_finished", "errors")})
    print("arms:", [r["arms"] for r in runs])
    print("rules:", json.dumps(res["rules"], indent=1))


if __name__ == "__main__":
    main()

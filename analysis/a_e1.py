"""A-E1 (OPTIONS_PLAN.md §2.4): do Gemma-4's loops survive sampling? Analysis of jsw/workloads/loop_replay runs.

    python -m analysis.a_e1 <run-dir> [<run-dir> ...]   -> reports/2026-10-06-options/a_e1.json

Per arm (greedy = P1's protocol; sampled:<seed> = Gemma-4's defaults), per source (Thor Reflexion, Thor tool
calling, Orin 32 E4B) and per kind ("loop": the call looped to its cap on P1's device; "control": it finished on
its own after >= 2,000 tokens):
- loop rate: the online detector fired (the gateway stopped the call), with a Wilson 95% interval;
- other outcomes: finished (stop / tool_calls) or capped without a loop;
- output size (tokens, else characters / 3.2), time, and GPU energy per arm (NVML, every GPU of the run);
- validity of what came back: the program (Reflexion generator: a ```python block; tool calling: the
  execute_and_observe code argument) parses as Python and calls only drone-API names (aw.*) that P1's own
  finished programs use.
Decision rules (D15): reproduction check first (greedy loops on >= 50% of the prompts that looped on the Thor);
"sampling removes the loops" if sampled runs loop on <= 10% of them and the controls do not get worse.
"""
from __future__ import annotations

import ast
import glob
import gzip
import json
import math
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

from analysis.sessions import REPO
from jsw.runner.run import gpu_energy_j

OUT = REPO / "reports/2026-10-06-options/a_e1.json"
CODE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.S)


def wilson(k, n, z=1.96):
    if n == 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)


def program(msg):
    """The drone program in a reply, or None."""
    for tc in msg.get("tool_calls") or []:
        try:
            args = json.loads((tc.get("function") or {}).get("arguments") or "{}")
        except ValueError:
            continue
        for v in args.values():
            if isinstance(v, str) and ("aw." in v or "\n" in v):
                return v
    m = CODE.findall(msg.get("content") or "")
    return m[-1] if m else None


def api_calls(code):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    return {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name) and n.func.value.id == "aw"}


def known_api(prompts_file):
    """aw.* names in P1's own finished generator programs (the controls' recorded outputs are not in the prompt
    set, so take them from the prompts' examples and the API description instead)."""
    names = set()
    for line in open(prompts_file):
        r = json.loads(line)
        for m in r["request"]["messages"]:
            names |= set(re.findall(r"\baw\.([A-Za-z_][A-Za-z0-9_]*)\s*\(", str(m.get("content"))))
    return names


def load(run_dir):
    run_dir = Path(run_dir)
    recs = [json.loads(l) for l in open(run_dir / "calls.jsonl")]
    msgs = {}
    for f in glob.glob(str(run_dir / "texts" / "*.json.gz")):
        with gzip.open(f, "rt") as fh:
            j = json.load(fh)
        msgs[(j["rec"]["arm"], j["rec"]["id"])] = j["message"]
    ev = [json.loads(l) for l in open(run_dir / "events.jsonl")]
    wins = {}
    for e in ev:
        if e["kind"] == "arm_start":
            wins[e["arm"]] = [e["t_mono"], None]
        elif e["kind"] == "arm_end" and e["arm"] in wins:
            wins[e["arm"]][1] = e["t_mono"]
    energy = {a: gpu_energy_j(run_dir, t0, t1) for a, (t0, t1) in wins.items() if t1}
    return recs, msgs, energy, {a: (t1 - t0) if t1 else None for a, (t0, t1) in wins.items()}


def summarize(run_dirs, prompts_file):
    api = known_api(prompts_file)
    out = {"api_names": sorted(api), "runs": [str(d) for d in run_dirs], "cells": {}, "arms": {}}
    for d in run_dirs:
        recs, msgs, energy, wall = load(d)
        for arm, e in energy.items():
            out["arms"][f"{Path(d).name}:{arm}"] = {"gpu_energy_kj": round(e / 1000, 1) if e else None,
                                                    "wall_s": round(wall[arm] or 0)}
        cells = defaultdict(list)
        for r in recs:
            cells[(r["arm"], r["src"], r["kind"])].append(r)
        for (arm, src, kind), rs in sorted(cells.items()):
            n = len(rs)
            loops = sum(r["stopped_by"] == "loop" for r in rs)
            fin = sum(r["finish_reason"] in ("stop", "tool_calls") and r["stopped_by"] != "loop" for r in rs)
            capped = sum(r["finish_reason"] == "length" and r["stopped_by"] != "loop" for r in rs)
            errs = sum(bool(r["error"]) for r in rs)
            toks = [r["completion_tokens"] or r["est_tokens"] or r["chars"] / 3.2 for r in rs]
            valid = parsed = 0
            gen = [r for r in rs if r["role"] == "generator" and r["stopped_by"] != "loop" and not r["error"]]
            for r in gen:
                code = program(msgs.get((arm, r["id"])) or {})
                calls = api_calls(code) if code else None
                if calls is not None:
                    parsed += 1
                    # the aw.* API is CLGSCE's (tasks A*, B*); AeroEval (D*, F1) programs use Aerostack2: parse only
                    valid += (bool(calls) and calls <= api) if r["task"][:1] in "AB" else 1
            row = dict(n=n, errors=errs, loops=loops, loop_rate=round(loops / n, 4), loop_ci=wilson(loops, n),
                       finished=fin, finish_rate=round(fin / n, 4), capped_no_loop=capped,
                       tokens_median=round(st.median(toks)), tokens_mean=round(sum(toks) / n),
                       s_median=round(st.median(r["s"] for r in rs), 1),
                       generator_finished=len(gen), program_parses=parsed, program_valid=valid,
                       recorded_tokens_median=round(st.median(r["recorded"]["completion_tokens"] for r in rs)))
            out["cells"][f"{Path(d).name}|{arm}|{src}|{kind}"] = row
    # decision rules (D15)
    rules = {}
    runs = sorted({k.split("|")[0] for k in out["cells"]})
    for run, src in ((r, s_) for r in runs for s_ in ("thor_rfx", "thor_tc", "o32_e4b")):
        cells = {k.split("|", 1)[1]: v for k, v in out["cells"].items() if k.startswith(run + "|")}
        g = cells.get(f"greedy|{src}|loop")
        if not g:
            continue
        reproduced = g["loop_rate"] >= 0.5
        sampled = [v for k, v in cells.items() if k.startswith("sampled") and k.endswith(f"|{src}|loop")]
        s_loops = sum(v["loops"] for v in sampled)
        s_n = sum(v["n"] for v in sampled)
        ctrl_g = cells.get(f"greedy|{src}|control")
        ctrl_s = [v for k, v in cells.items() if k.startswith("sampled") and k.endswith(f"|{src}|control")]
        ctrl_s_fin = sum(v["finished"] for v in ctrl_s) / max(1, sum(v["n"] for v in ctrl_s))
        rules[f"{run}|{src}"] = dict(
            greedy_loop_rate_on_thor_loops=g["loop_rate"], reproduction_check=reproduced,
            sampled_loop_rate_on_thor_loops=round(s_loops / s_n, 4) if s_n else None,
            sampled_ci=wilson(s_loops, s_n),
            controls_finish_greedy=ctrl_g["finish_rate"] if ctrl_g else None,
            controls_finish_sampled=round(ctrl_s_fin, 4) if ctrl_s else None,
            verdict=("inconclusive: the stand-in does not reproduce P1's loops" if not reproduced else
                     "sampling removes the loops" if s_n and s_loops / s_n <= 0.10 and
                     (not ctrl_g or ctrl_s_fin >= ctrl_g["finish_rate"] - 0.05) else
                     "sampling reduces but does not remove the loops" if s_n and s_loops / s_n < g["loop_rate"] else
                     "sampling does not reduce the loops"))
    out["rules"] = rules
    return out


def main():
    dirs = [Path(x) for x in sys.argv[1:]] or [Path(p) for p in sorted(glob.glob(str(REPO / "data/ws_runs/a-e1-*")))
                                               if (Path(p) / "calls.jsonl").exists()]
    res = summarize(dirs, REPO / "data/a_e1/prompts.jsonl")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, default=str))
    for k, v in res["cells"].items():
        print(k, {x: v[x] for x in ("n", "loops", "loop_rate", "loop_ci", "finish_rate", "capped_no_loop",
                                    "tokens_median", "program_valid", "generator_finished", "errors")})
    print("arms:", res["arms"])
    print("rules:", json.dumps(res["rules"], indent=1))


if __name__ == "__main__":
    main()

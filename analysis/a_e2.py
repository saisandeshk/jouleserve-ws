"""A-E2 (OPTIONS_PLAN.md §2.4): after an online stop, does a retry finish usefully, and at what cost?

    python -m analysis.a_e2 <prefix>     e.g. a-e2-g26b-gguf  (WS; writes reports/2026-10-06-options/a_e2.json)

For each retry action (runs <prefix>-resample, -nudge, -budget of env/queue_a_e2.sh): the prompts that looped under
greedy decoding in A-E1, replayed greedy; the gateway stopped each where the loop detector fired (attempt 0) and
retried once (attempt 1). Per action:
- the retry finished (stop / tool_calls, not stopped again), and its program is valid (as in A-E1);
- tokens: attempt 0 up to the stop plus the retry, against the recorded call (P1's run to the 32,768-token cap);
- GPU energy of the action's window (NVML) per prompt.
Decision rule (D15): "stop and retry preserves runs" if >= 70% of retries end with a valid program at <= 50% of the
recorded call's cost (tokens as the proxy).
"""
from __future__ import annotations

import glob
import gzip
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

from analysis.a_e1 import api_calls, known_api, program, wilson
from analysis.sessions import REPO
from jsw.runner.run import gpu_energy_j

RUNS = REPO / "data/ws_runs"
OUT = REPO / "reports/2026-10-06-options/a_e2.json"


def one(run_dir, api):
    d = Path(run_dir)
    man = json.loads((d / "manifest.json").read_text())
    if "t_end_mono" not in man:
        return None
    recs = {r["id"]: r for r in (json.loads(l) for l in open(d / "calls.jsonl"))}
    gw = defaultdict(list)
    for l in open(d / "gw" / "calls.jsonl"):
        c = json.loads(l)
        gw[c["sid"]].append(c)
    msgs = {}
    for f in glob.glob(str(d / "texts" / "*.json.gz")):
        with gzip.open(f, "rt") as fh:
            j = json.load(fh)
        msgs[j["rec"]["id"]] = j["message"]
    rows = []
    for pid, r in recs.items():
        atts = sorted(gw.get(r["sid"], []), key=lambda c: c["attempt"])
        t0 = sum((a.get("completion_tokens") or a.get("chunks") or 0) for a in atts[:1])
        t1 = sum((a.get("completion_tokens") or a.get("chunks") or 0) for a in atts[1:])
        retried = len(atts) > 1
        last = atts[-1] if atts else {}
        fin = last.get("finish_reason") in ("stop", "tool_calls") and last.get("stopped_by") != "loop"
        code = program(msgs.get(pid) or {})
        calls = api_calls(code) if code else None
        valid = (bool(calls) and calls <= api) if r["task"][:1] in "AB" else calls is not None
        if r["role"] != "generator":
            valid = fin                     # reflector/evaluator replies: finishing is the outcome
        rows.append(dict(id=pid, role=r["role"], task=r["task"], retried=retried, finished=fin, valid=bool(valid),
                         tokens_stop=t0, tokens_retry=t1, tokens_total=t0 + t1,
                         recorded=r["recorded"]["completion_tokens"]))
    n = len(rows)
    ok = sum(x["finished"] and x["valid"] for x in rows)
    cheap = sum(x["finished"] and x["valid"] and x["tokens_total"] <= 0.5 * x["recorded"] for x in rows)
    E = gpu_energy_j(d, man.get("t_start_mono"), man.get("t_end_mono"))
    return dict(run=d.name, prompts=n, retried=sum(x["retried"] for x in rows),
                finished=sum(x["finished"] for x in rows), finished_valid=ok, finished_valid_ci=wilson(ok, n),
                finished_valid_under_half_cost=cheap,
                tokens_total_median=st.median(x["tokens_total"] for x in rows) if rows else None,
                tokens_stop_median=st.median(x["tokens_stop"] for x in rows) if rows else None,
                tokens_retry_median=st.median(x["tokens_retry"] for x in rows) if rows else None,
                recorded_median=st.median(x["recorded"] for x in rows) if rows else None,
                gpu_kj_per_prompt=(E / n / 1e3) if E and n else None,
                rule_met=(cheap / n >= 0.70) if n else None, rows=rows)


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else "a-e2"
    api = known_api(REPO / "data/a_e1/prompts.jsonl")
    res = {}
    for d in sorted(glob.glob(str(RUNS / f"{prefix}-*"))):
        r = one(d, api)
        if r:
            res[Path(d).name] = r
            print(Path(d).name, {k: v for k, v in r.items() if k != "rows"})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    old = json.loads(OUT.read_text()) if OUT.exists() else {}
    old.update(res)
    OUT.write_text(json.dumps(old, indent=1, default=str))


if __name__ == "__main__":
    main()

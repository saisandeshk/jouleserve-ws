"""A-E4 (OPTIONS_PLAN.md §2.4): what are traffic's capped calls? (P1's traces only; no replay is possible.)

    python -m analysis.a_e4        -> reports/2026-10-06-options/a_e4.json

For the traffic configurations where capped calls hold the energy (Thor gemma 38% of board energy, Orin 32 E4B
33%; reports/2026-10-05-p1-repo §5) and the others for contrast: every call that reached 99% of its granted output
budget, matched to its assistant turn in the trace. Per capped call: was the cap inside a tool call (the parser
dropped the partial call: arguments "{}") or inside the reasoning; which tool it was writing; how much reasoning
preceded it; what came next (another capped call, a completed call, the end of the run). Per run: chains of
consecutive caps and their share of the run's LLM energy; and whether the run completed anyway.
"""
from __future__ import annotations

import glob
import json
import os
import statistics as st
from collections import Counter

from analysis import p1_repo
from analysis.sessions import REPO

OUT = REPO / "reports/2026-10-06-options/a_e4.json"
CONFIGS = ("t_thor_gemma", "t_o32_e4b", "t_thor_granite", "t_o64_gemma", "t_o64_granite", "t_o32_granite")


def calls_with_turns(cfg):
    """Every LLM call of every traffic run of a configuration, with its assistant turn when aligned."""
    out = []
    for rd in sorted(glob.glob(os.path.join(p1_repo._root(p1_repo.BY_KEY[cfg]), "*", "run*"))):
        for tf in sorted(glob.glob(os.path.join(rd, "2026*.json"))):
            t = json.load(open(tf))
            b = t.get("benchmark") or {}
            lc = [c for c in (b.get("llm_calls") or []) if "error" not in c and c.get("output_tokens") is not None]
            turns = [x for x in (t.get("turns") or []) if x.get("role") == "assistant"]
            aligned = len(turns) == len(lc) > 0
            run = []
            for i, c in enumerate(lc):
                granted = (c.get("token_budget") or {}).get("granted_max_tokens") or 8000
                cap = min(8000, granted)
                a = turns[i] if aligned else {}
                req = a.get("requested_tool_calls") or []
                run.append(dict(out=int(c["output_tokens"]), cap=cap, capped=int(c["output_tokens"]) >= 0.99 * cap,
                                guard=granted < 8000, energy=c.get("iter_energy_j") or 0.0,
                                reasoning_tokens=c.get("reasoning_tokens"),
                                tools=[r.get("name") for r in req],
                                args_empty=[(r.get("arguments") in ("{}", {}, None, "")) for r in req],
                                content_chars=len(str(a.get("content") or "")), aligned=aligned))
            out.append(dict(run=os.path.basename(tf), calls=run, completed=not t.get("stopped_at_step_limit")
                            and bool(t.get("answer"))))
    return out


def summarize(cfg):
    runs = calls_with_turns(cfg)
    calls = [c for r in runs for c in r["calls"]]
    capped = [c for c in calls if c["capped"]]
    E = sum(c["energy"] for c in calls)
    kinds = Counter()
    tools = Counter()
    for c in capped:
        if not c["aligned"]:
            kinds["no_turn_text"] += 1
        elif c["guard"]:
            kinds["context_guard"] += 1
        elif c["tools"] and all(c["args_empty"]):
            kinds["inside_tool_call_dropped"] += 1
            tools.update(t for t in c["tools"] if t)
        elif c["tools"]:
            kinds["tool_call_kept"] += 1
            tools.update(t for t in c["tools"] if t)
        elif (c["reasoning_tokens"] or 0) >= 0.99 * c["cap"]:
            kinds["inside_reasoning"] += 1
        else:
            kinds["inside_answer_text"] += 1
    nxt = Counter()
    chains, chain_energy = [], 0.0
    for r in runs:
        cs, i = r["calls"], 0
        for j, c in enumerate(cs):
            if c["capped"]:
                nxt["capped" if j + 1 < len(cs) and cs[j + 1]["capped"] else "end_of_run" if j + 1 == len(cs)
                    else "uncapped"] += 1
        while i < len(cs):
            if cs[i]["capped"]:
                j = i
                while j < len(cs) and cs[j]["capped"]:
                    j += 1
                chains.append(j - i)
                if j - i >= 2:
                    chain_energy += sum(c["energy"] for c in cs[i + 1:j])      # the repeats after the first cap
                i = j
            else:
                i += 1
    with_cap = [r for r in runs if any(c["capped"] for c in r["calls"])]
    return dict(config=cfg, runs=len(runs), calls=len(calls), capped=len(capped),
                capped_energy_share=sum(c["energy"] for c in capped) / E if E else None,
                capped_kind=dict(kinds), tools_in_capped_calls=dict(tools.most_common(8)),
                after_a_cap=dict(nxt), chains=dict(Counter(chains)), longest_chain=max(chains) if chains else 0,
                repeat_cap_energy_share=chain_energy / E if E else None,
                runs_with_cap=len(with_cap), completed_with_cap=sum(r["completed"] for r in with_cap),
                completed_without_cap=sum(r["completed"] for r in runs if r not in with_cap),
                runs_without_cap=len(runs) - len(with_cap),
                reasoning_tokens_before_dropped_call_median=st.median(
                    [c["reasoning_tokens"] for c in capped if c["tools"] and all(c["args_empty"]) and c["reasoning_tokens"]]
                    or [0]))


def main():
    res = {cfg: summarize(cfg) for cfg in CONFIGS}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, default=str))
    for k, v in res.items():
        print(k, json.dumps({x: (round(y, 3) if isinstance(y, float) else y) for x, y in v.items() if x != "config"}))


if __name__ == "__main__":
    main()

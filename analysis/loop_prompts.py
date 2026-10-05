"""Prompt set for A-E1/A-E2 (OPTIONS_PLAN.md §2.4): P1's recorded drone calls, replayable exactly.

Reads every LLM call of P1's Thor gemma-26B drone sweeps (Reflexion from P1's repository, tool calling from our
copy) and of the Orin 32 gemma-E4B drone cell, with the full request as P1 sent it (messages, tools,
tool_choice, max_tokens, decoding settings) and what came back (text, tokens, finish reason). Each call gets
our online loop detector's verdict on its recorded text, and a kind:
- "loop":     capped at its token limit (32,768 for generator/reflector calls) and flagged as a loop;
- "cap_other": capped but not flagged (e.g. the 1,024-token evaluator calls);
- "control":  finished on its own after at least 2,000 output tokens (the finished long calls of p1_caps).
Writes data/a_e1/prompts.jsonl (git-ignored: P1's prompts are unpublished) and prints counts, which must match
reports/2026-10-05-p1-repo §5: Reflexion 121 loops of 122 capped, 173 controls; tool calling 127 loops at
32,768, 194 controls; E4B 5 capped generator calls.

Usage: python3 -m analysis.loop_prompts
"""
from __future__ import annotations

import glob
import gzip
import json
import os
from collections import Counter

from analysis.p1_repo import P1, REPO
from jsw.policies.loop_detector import detect_offline

SOURCES = {
    "thor_rfx": P1 / "drones/final_sweep_thor/reflexion/gemma-4-26B-A4B-it",
    "thor_tc": REPO / "data/p1_thor_toolcalling/gemma-4-26B-A4B-it-toolcalling",
    "o32_e4b": None,  # resolved below (directory name differs)
}
OUT = REPO / "data/a_e1/prompts.jsonl"


def _jsonl(p):
    op = gzip.open if str(p).endswith(".gz") else open
    with op(p, "rt") as f:
        return [json.loads(x) for x in f if x.strip()]


def _call_text(c):
    args = "".join(((t.get("function") or {}).get("arguments") or "") for t in (c.get("tool_calls") or []))
    return (c.get("reasoning_content") or "") + (c.get("content") or "") + args


def _runs(root):
    for meta_p in sorted(glob.glob(str(root / "*/instance_*/run_*/run_meta.json"))):
        d = os.path.dirname(meta_p)
        lc = glob.glob(os.path.join(d, "llm_calls.jsonl*"))
        if not lc:
            continue
        yield json.load(open(meta_p)), d, _jsonl(lc[0])


def build():
    roots = dict(SOURCES)
    roots["o32_e4b"] = next(iter(glob.glob(str(P1 / "drones/final_sweep_orin32/*/*"))), None)
    rows, counts = [], Counter()
    for src, root in roots.items():
        if not root:
            continue
        for meta, d, calls in _runs(type(REPO)(root)):
            for c in calls:
                out = int(c.get("completion_tokens") or 0)
                capped = c.get("finish_reason") == "length"
                text = _call_text(c)
                fired = detect_offline(text) if text else None
                kind = ("loop" if capped and fired is not None else "cap_other" if capped
                        else "control" if out >= 2000 and text else None)
                if kind is None:
                    continue
                counts[(src, kind)] += 1
                if capped:
                    counts[(src, f"capped@{c.get('max_tokens')}")] += 1
                rows.append(dict(
                    id=f"{src}/{os.path.relpath(d, root)}/{c.get('call_seq')}", src=src, kind=kind,
                    task=meta.get("task_id"), run_ok=meta.get("final_result") == "pass", role=c.get("role"),
                    request=dict(messages=c["messages"], tools=c.get("tools"), tool_choice=c.get("tool_choice"),
                                 max_tokens=c.get("max_tokens"), extra_body=c.get("extra_body")),
                    recorded=dict(prompt_tokens=c.get("prompt_tokens"), completion_tokens=out,
                                  finish_reason=c.get("finish_reason"), e2e_s=c.get("e2e_s"),
                                  text_chars=len(text), fired_char=fired, temperature=c.get("temperature"),
                                  top_k=c.get("top_k"), seed=c.get("seed")),
                ))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return rows, counts


if __name__ == "__main__":
    rows, counts = build()
    for k in sorted(counts):
        print(k, counts[k])
    print(len(rows), "rows ->", OUT, f"({OUT.stat().st_size / 1e6:.1f} MB)")

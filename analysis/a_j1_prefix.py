"""A-J1 diagnostic (not one of plan §5.3's rules; added 12 Oct after the pilot): is greedy decoding repeatable on P1's
setup? For each replayed call, the length of the text it shares from the start with P1's recorded output, and, for a
prompt run in several of our runs, with our own earlier output of the same arm. Prints character counts only (P1's
text stays out of the repo).

    python -m analysis.a_j1_prefix <run-dir> [<run-dir> ...]     (WS; P1's clone read-only)
                                                                -> reports/2026-10-06-options/a_j1_prefix.json
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import sys
from pathlib import Path

from analysis.loop_prompts import SOURCES, _call_text, _jsonl
from analysis.sessions import REPO

OUT = REPO / "reports/2026-10-06-options/a_j1_prefix.json"


def _common(a: str, b: str) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def _p1_text(cid: str) -> str:
    src, rel = cid.split("/", 1)
    d, seq = rel.rsplit("/", 1)
    lc = glob.glob(os.path.join(str(SOURCES[src]), d, "llm_calls.jsonl*"))
    return _call_text(next(c for c in _jsonl(lc[0]) if str(c.get("call_seq")) == seq))


def _ours(run_dir):
    for f in sorted(glob.glob(str(Path(run_dir) / "texts" / "*.json.gz"))):
        with gzip.open(f, "rt") as fh:
            j = json.load(fh)
        m = j["message"]
        yield j["rec"], (m.get("reasoning_content") or "") + (m.get("content") or "")


def main():
    rows, seen = [], {}
    p1_cache = {}
    for run in sys.argv[1:]:
        for rec, text in _ours(run):
            cid, arm = rec["id"], rec["arm"]
            if cid not in p1_cache:
                p1_cache[cid] = _p1_text(cid)
            a = p1_cache[cid]
            row = dict(run=Path(run).name, id=cid, arm=arm, outcome=rec["stopped_by"] or rec["finish_reason"],
                       ours_chars=len(text), p1_chars=len(a), common_with_p1=_common(a, text))
            if (cid, arm) in seen:
                row["common_with_our_earlier"] = _common(seen[(cid, arm)], text)
            seen[(cid, arm)] = text
            rows.append(row)
            print(row)
    g = [r for r in rows if r["arm"] == "greedy"]
    summary = dict(greedy_calls=len(g),
                   greedy_identical_to_p1=sum(r["common_with_p1"] >= min(r["ours_chars"], r["p1_chars"]) for r in g),
                   greedy_common_with_p1_median=sorted(r["common_with_p1"] for r in g)[len(g) // 2] if g else None,
                   greedy_repeats=[r for r in g if "common_with_our_earlier" in r])
    OUT.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()

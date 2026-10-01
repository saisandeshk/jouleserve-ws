"""P1 cache-miss anomaly: same-role calls that repeat an earlier prompt almost exactly
(size within 5%, > 4K tokens) yet get < 50% of the earlier prompt from cache.

Usage: python3 -m analysis.p1_cache_misses
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

from analysis.sessions import REPO

ROOT = REPO / "data/p1_thor_drone"


def main():
    cls = lambda t: "B" if t.startswith("B") else ("A" if t.startswith("A") else "D/F")
    S = collections.defaultdict(collections.Counter)
    for f in ROOT.glob("*/*/*/*/iterations.jsonl"):
        c = cls(f.parts[-4])
        L = [json.loads(l) for l in open(f)]
        llm = sorted([d for d in L if d["kind"] == "llm" and d.get("t_phase_start")], key=lambda d: d["t_phase_start"])
        last = {}
        for d in llm:
            S[c]["llm_s"] += d["t_phase_end"] - d["t_phase_start"]
            r, p, ca = d["role"], d["prompt_tokens"] or 0, d["cached_tokens"] or 0
            if r in last and p > 4000:
                pp, pcomp = last[r]
                if abs(p - pp) / pp < 0.05:
                    S[c]["same_role_resumes"] += 1
                    if ca < 0.5 * pp:
                        S[c]["misses"] += 1
                        S[c]["miss_ttft_s"] += d["ttft_s"] or 0
                        S[c]["miss_after_32k_decode"] += pcomp >= 32000
            last[r] = (p, d["completion_tokens"] or 0)
    for c in ["B", "A", "D/F"]:
        s = S[c]
        print(f"{c}: resumes={s['same_role_resumes']} misses={s['misses']} "
              f"after_32k_decode={s['miss_after_32k_decode']} "
              f"miss_prefill_share_of_llm={s['miss_ttft_s'] / s['llm_s']:.2%}")


if __name__ == "__main__":
    main()

"""Print a quick per-session view of an aerogen run directory (LLM calls and tool calls).

Usage: python -m jsw.workloads.aerogen_peek <run_dir> [--calls]
"""
import json
import sys
from pathlib import Path


def rows(p):
    return [json.loads(l) for l in open(p)] if p.exists() else []


def main():
    run = Path(sys.argv[1])
    show_calls = "--calls" in sys.argv
    for s in sorted((run / "sessions").glob("*")):
        llm, tools = rows(s / "llm_calls.jsonl"), rows(s / "tool_calls.jsonl")
        summ = json.loads((s / "summary.json").read_text()) if (s / "summary.json").exists() else {}
        wait = sum(t["dur_s"] for t in tools)
        llm_s = sum((c.get("t_end") or 0) - c["t_req"] for c in llm)
        P = sum(c.get("prompt_tokens") or 0 for c in llm)
        C = sum(c.get("cached_tokens") or 0 for c in llm)
        maxp = max([c.get("prompt_tokens") or 0 for c in llm] or [0])
        val = (summ.get("validator") or {}).get("valid")
        print(f"{s.name}: status={summ.get('status', 'running')} stop={summ.get('stop_reason')} "
              f"valid={val} llm_calls={len(llm)} tool_calls={len(tools)} llm_s={llm_s:.0f} "
              f"tool_wait_s={wait:.0f} max_prompt={maxp} cached/prompt={C / max(P, 1):.1%} "
              f"err={summ.get('error', '')[:120]}")
        if show_calls:
            ev = sorted([("L", c["t_req"], c) for c in llm] + [("T", t["t_start"], t) for t in tools],
                        key=lambda x: x[1])
            for kind, _, r in ev:
                if kind == "L":
                    print(f"   LLM {r['call_index']:3d} prompt={r.get('prompt_tokens')} "
                          f"cached={r.get('cached_tokens')} compl={r.get('completion_tokens')} "
                          f"ttft={r.get('ttft_s') or 0:.2f} dec={r.get('decode_s') or 0:.2f} "
                          f"reas={r.get('reasoning_chars')} -> {r.get('tool_names')} "
                          f"{r.get('finish_reason')} {r.get('error', '')[:100]}")
                else:
                    print(f"   TOOL {r['seq']:3d} {r['tool']:<18} {r['dur_s']:7.2f}s {r['status']}")


if __name__ == "__main__":
    main()

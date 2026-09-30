"""Load P1 Thor traces and aerogen WS runs into one session model, and compute the
retained-state metrics used in the workload-opportunity report.

A session is a list of LLM calls and tool waits on one clock:
  call: t0, t1, prompt, cached, completion, prefill_s, role
  wait: t0, t1, tool
Metrics (per session, then pooled per workload class):
  - time split: prefill / decode / tool wait / other (other = session time minus the rest)
  - reuse: cached prompt tokens / prompt tokens
  - KV memory-time split: active (during calls) vs paused (between calls, state held)
  - retention ceiling: prefill time that perfect retention avoids = cached tokens /
    cold-prefill throughput, as a share of LLM time
"""
from __future__ import annotations

import json
import statistics as st
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


@dataclass
class Session:
    workload: str
    cls: str
    task: str
    sid: str
    t0: float
    t1: float
    success: bool | None
    calls: list = field(default_factory=list)
    waits: list = field(default_factory=list)


def _jsonl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def p1_class(task: str) -> str:
    return "B" if task.startswith("B") else "A" if task.startswith("A") else "D/F"


def load_p1(root: Path, workload: str) -> list[Session]:
    out = []
    for meta_p in sorted(root.glob("*/*/instance_*/run_*/run_meta.json")):
        d = meta_p.parent
        meta = json.loads(meta_p.read_text())
        it = _jsonl(d / "iterations.jsonl")
        s = Session(workload, p1_class(meta["task_id"]), meta["task_id"], meta["run_id"],
                    meta["t_start_mono"], meta["t_end_mono"],
                    {"pass": True, "fail": False, "partial": False}.get(meta.get("final_result")))
        for r in it:
            if r.get("kind") == "llm" and r.get("t_phase_start") and r.get("t_phase_end"):
                s.calls.append(dict(t0=r["t_phase_start"], t1=r["t_phase_end"],
                                    prompt=r.get("prompt_tokens") or 0,
                                    cached=r.get("cached_tokens") or 0,
                                    completion=r.get("completion_tokens") or 0,
                                    prefill_s=r.get("ttft_s") or 0.0, role=r.get("role")))
            elif r.get("kind") == "mcp" and r.get("t_phase_start") and r.get("t_phase_end"):
                s.waits.append(dict(t0=r["t_phase_start"], t1=r["t_phase_end"], tool=r.get("tool_name")))
        s.calls.sort(key=lambda c: c["t0"])
        s.waits.sort(key=lambda w: w["t0"])
        if s.calls:
            out.append(s)
    return out


def load_aerogen(run_dir: Path, workload: str, prefill_tok_s: float) -> list[Session]:
    """`prefill_tok_s`: cold prefill throughput of the serving GPU, used to split each
    call's time into prefill and decode (client TTFT is not a clean prefill measure
    because the tool-call parser buffers output until the call is complete)."""
    out = []
    for sd in sorted((run_dir / "sessions").glob("*")):
        summ_p = sd / "summary.json"
        if not summ_p.exists():
            continue
        summ = json.loads(summ_p.read_text())
        llm = _jsonl(sd / "llm_calls.jsonl")
        tools = _jsonl(sd / "tool_calls.jsonl")
        valid = (summ.get("validator") or {}).get("valid")
        s = Session(workload, workload, f"t{summ['task_index']}", sd.name, summ["t_start"],
                    summ["t_end"], None if summ.get("status") != "done" else valid == "YES")
        for r in llm:
            if r.get("t_end") is None or r.get("prompt_tokens") is None:
                continue
            uncached = (r["prompt_tokens"] or 0) - (r.get("cached_tokens") or 0)
            dur = r["t_end"] - r["t_req"]
            s.calls.append(dict(t0=r["t_req"], t1=r["t_end"], prompt=r["prompt_tokens"],
                                cached=r.get("cached_tokens") or 0,
                                completion=r.get("completion_tokens") or 0,
                                prefill_s=min(dur, uncached / prefill_tok_s), role="agent"))
        for t in tools:
            s.waits.append(dict(t0=t["t_start"], t1=t["t_end"], tool=t["tool"]))
        if s.calls:
            out.append(s)
    return out


def session_metrics(s: Session, prefill_tok_s: float) -> dict:
    llm_s = sum(c["t1"] - c["t0"] for c in s.calls)
    prefill_s = sum(min(c["prefill_s"], c["t1"] - c["t0"]) for c in s.calls)
    tool_s = sum(w["t1"] - w["t0"] for w in s.waits)
    total = max(s.t1 - s.t0, llm_s + tool_s)
    active = paused = 0.0
    for i, c in enumerate(s.calls):
        dur = c["t1"] - c["t0"]
        active += (c["prompt"] + c["completion"] / 2) * dur
        if i + 1 < len(s.calls):
            gap = max(0.0, s.calls[i + 1]["t0"] - c["t1"])
            paused += (c["prompt"] + c["completion"]) * gap
    P = sum(c["prompt"] for c in s.calls)
    C = sum(c["cached"] for c in s.calls)
    return dict(
        total_s=total, llm_s=llm_s, prefill_s=prefill_s, decode_s=llm_s - prefill_s,
        tool_s=tool_s, other_s=max(0.0, total - llm_s - tool_s),
        n_calls=len(s.calls), n_waits=len(s.waits),
        prompt=P, cached=C, completion=sum(c["completion"] for c in s.calls),
        peak_ctx=max(c["prompt"] + c["completion"] for c in s.calls),
        active_tok_s=active, paused_tok_s=paused,
        ceiling_s=C / prefill_tok_s,
    )


def pooled(sessions: list[Session], prefill_tok_s: float) -> dict:
    ms = [session_metrics(s, prefill_tok_s) for s in sessions]
    tot = lambda k: sum(m[k] for m in ms)
    med = lambda k: st.median(m[k] for m in ms)
    succ = [s.success for s in sessions if s.success is not None]
    # Real waits only: bookkeeping tools (connect, arm, get_pose, validate) return in ms.
    waits = [w["t1"] - w["t0"] for s in sessions for w in s.waits if w["t1"] - w["t0"] > 0.5]
    calls = [c["t1"] - c["t0"] for s in sessions for c in s.calls]
    return dict(
        n=len(ms), success_rate=(sum(succ) / len(succ)) if succ else None,
        session_s_p50=med("total_s"), calls_p50=med("n_calls"), waits_p50=med("n_waits"),
        share_prefill=tot("prefill_s") / tot("total_s"), share_decode=tot("decode_s") / tot("total_s"),
        share_tool=tot("tool_s") / tot("total_s"), share_other=tot("other_s") / tot("total_s"),
        prefill_of_llm=tot("prefill_s") / tot("llm_s"),
        reuse=tot("cached") / max(tot("prompt"), 1),
        paused_mem_share=tot("paused_tok_s") / max(tot("paused_tok_s") + tot("active_tok_s"), 1e-9),
        ceiling_of_llm=tot("ceiling_s") / tot("llm_s"),
        peak_ctx_p50=med("peak_ctx"), peak_ctx_max=max(m["peak_ctx"] for m in ms),
        wait_s_p50=st.median(waits) if waits else None, call_s_p50=st.median(calls),
        completion_per_call=tot("completion") / max(sum(m["n_calls"] for m in ms), 1),
        prompt_per_call=tot("prompt") / max(sum(m["n_calls"] for m in ms), 1),
    )


def thor_prefill_rate(sessions: list[Session]) -> float:
    """Median cold-prefill throughput on the Thor: calls with >2K prompt and no cache hit."""
    rates = [c["prompt"] / c["prefill_s"] for s in sessions for c in s.calls
             if c["prompt"] > 2000 and c["cached"] < 16 and c["prefill_s"] > 0.2]
    return st.median(rates)

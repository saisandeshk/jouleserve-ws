"""P1's EdgeAgentBench repository (read-only clone in data/edge-agent-bench, HEAD 3c47ebc, 4 Oct 2026)
in one call-level model, for both domains.

Configurations (one device, model and agent each):
- drone: the repo's three cells (Thor gemma-4-26B-A4B Reflexion, Orin 64 Devstral-24B FP8 tool calling,
  Orin 32 gemma-4-E4B tool calling) plus our own read-only copy of P1's Thor gemma tool-calling sweep
  (data/p1_thor_toolcalling, 104 runs to 2026-10-03 16:16), which the repo does not hold;
- traffic: the eight tool-calling cells (main run directories only; P1 also drops `*_topup` and
  `*_ceilretry`). Traffic is ungraded: a run is "ok" when it completed without a harness failure.

Each run is a dict: cfg, task, instance, rep, ok, status, energy_J, time_s, pool (KV-pool tokens),
ctx (context window), evicted (drone: tokens evicted during the run), calls, tools. A call is a dict:
t0, t1, prompt, cached, out, reasoning, ttft, decode, energy, capped, cap, role, text (None when not
recorded), text_complete. A tool is: t0, t1, tool, energy.

A capped call ended at its output-token limit: drone finish reason "length" (caps 32,768, 8,192, 4,096
or 1,024 by role); traffic has no finish reason, so output >= 99% of the granted budget (8,000, or less
when Orin 64's context guard lowered it). Traffic text comes from the trace's assistant turns, aligned
1:1 with the calls when the counts agree; when the cap hits inside a tool call the parser drops the
partial call, so that text is incomplete.

Usage: from analysis.p1_repo import CONFIGS, load   (parsed runs are cached in data/p1_cache/)
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import pickle
import re
from dataclasses import dataclass

from analysis.sessions import REPO

P1 = REPO / "data/edge-agent-bench"
CACHE = REPO / "data/p1_cache"
DRONE_CAP_ROLES = ("generator", "reflector")


@dataclass(frozen=True)
class Cfg:
    key: str
    domain: str
    device: str
    model: str
    agent: str
    root: str   # run root: <root>/<task>/instance_<i>/run_<r> (drone) or <root>/<instance>/run<r> (traffic)

    @property
    def label(self):
        return f"{self.domain.capitalize()} · {self.device} · {self.model}" + (
            f" · {self.agent}" if self.domain == "drone" else "")


CONFIGS = [
    Cfg("d_thor_gemma_rfx", "drone", "Thor", "gemma-26B", "Reflexion",
        "drones/final_sweep_thor/reflexion/gemma-4-26B-A4B-it"),
    Cfg("d_thor_gemma_tc", "drone", "Thor", "gemma-26B", "tool calling",
        str(REPO / "data/p1_thor_toolcalling/gemma-4-26B-A4B-it-toolcalling")),
    Cfg("d_o64_devstral_tc", "drone", "Orin 64", "Devstral-24B", "tool calling",
        "drones/final_sweep_orin64/tool_calling/devstral"),
    Cfg("d_o32_e4b_tc", "drone", "Orin 32", "gemma-E4B", "tool calling",
        "drones/final_sweep_orin32/tool_calling/gemma-4-E4B-it"),
    Cfg("t_thor_gemma", "traffic", "Thor", "gemma-26B", "tool calling",
        "traffic/final_sweep_thor/tool_calling/gemma-4-26B-A4B-it"),
    Cfg("t_thor_granite", "traffic", "Thor", "granite-8B", "tool calling",
        "traffic/final_sweep_thor/tool_calling/granite-4.2-8b"),
    Cfg("t_thor_qwen36", "traffic", "Thor", "Qwen3.6-35B-A3B", "tool calling",
        "traffic/final_sweep_thor/tool_calling/Qwen3.6-35B-A3B-FP8"),
    Cfg("t_o64_gemma", "traffic", "Orin 64", "gemma-26B", "tool calling",
        "traffic/final_sweep_orin_64/tool_calling/gemma-4-26B-A4B-it"),
    Cfg("t_o64_granite", "traffic", "Orin 64", "granite-8B", "tool calling",
        "traffic/final_sweep_orin_64/tool_calling/granite-4.2-8b"),
    Cfg("t_o32_granite", "traffic", "Orin 32", "granite-8B", "tool calling",
        "traffic/final_sweep_orin_32/tool_calling/granite-4.2-8b"),
    Cfg("t_o32_e4b", "traffic", "Orin 32", "gemma-E4B", "tool calling",
        "traffic/final_sweep_orin_32/tool_calling/gemma-4-E4B-it"),
    Cfg("t_o32_qwenvl", "traffic", "Orin 32", "Qwen2.5-VL-7B", "tool calling",
        "traffic/final_sweep_orin_32/tool_calling/Qwen2.5-VL-7B-Instruct"),
]
BY_KEY = {c.key: c for c in CONFIGS}


def _root(cfg):
    return cfg.root if os.path.isabs(cfg.root) else str(P1 / cfg.root)


def jsonl(path):
    """Rows of a .jsonl file, or of its .gz twin (the repo gzips every .jsonl)."""
    for p in (path, path + ".gz", path[:-3] if path.endswith(".gz") else None):
        if p and os.path.exists(p):
            op = gzip.open if p.endswith(".gz") else open
            with op(p, "rt") as f:
                return [json.loads(l) for l in f if l.strip()]
    return []


def _d(x):
    if isinstance(x, dict):
        return x
    try:
        return json.loads(x) if x else {}
    except (TypeError, ValueError):
        import ast
        return ast.literal_eval(x)


# ----------------------------------------------------------------------------- drone

def _drone_run(meta_p):
    d = os.path.dirname(meta_p)
    meta = json.load(open(meta_p))
    it = jsonl(os.path.join(d, "iterations.jsonl"))
    lc = jsonl(os.path.join(d, "llm_calls.jsonl"))
    rows = [r for r in it if r.get("kind") == "llm"]
    aligned = len(rows) == len(lc) and all(a.get("completion_tokens") == b.get("completion_tokens")
                                           for a, b in zip(rows, lc))
    calls, tools = [], []
    for i, r in enumerate(rows):
        if not r.get("t_phase_end") or r.get("completion_tokens") is None:
            continue
        x = lc[i] if aligned else {}
        args = "".join(((t.get("function") or {}).get("arguments") or "") for t in (x.get("tool_calls") or []))
        out = int(r["completion_tokens"])
        capped = r.get("finish_reason") == "length"
        calls.append(dict(
            t0=float(r["t_phase_start"]), t1=float(r["t_phase_end"]), prompt=int(r.get("prompt_tokens") or 0),
            cached=int(r.get("cached_tokens") or 0), out=out, reasoning=None, ttft=float(r.get("ttft_s") or 0),
            decode=float(r.get("decode_s") or 0), energy=r.get("iter_energy_J"), capped=capped,
            cap=x.get("max_tokens") or (out if capped else None), role=r.get("role"),
            text=(r.get("reasoning_text") or "") + (r.get("output_text") or "") + args, text_complete=True))
    for r in it:
        if r.get("kind") == "mcp" and r.get("t_phase_end"):
            tools.append(dict(t0=float(r["t_phase_start"]), t1=float(r["t_phase_end"]), tool=r.get("tool_name"),
                              energy=r.get("iter_energy_J")))
    si, ss = _d(meta.get("server_info")), _d(meta.get("server_summary"))
    res = meta.get("final_result")
    return dict(task=meta["task_id"], instance=meta.get("instance"), rep=meta.get("run_number"),
                ok=res == "pass", status=res, energy_J=float(meta["workflow_energy_J"]),
                time_s=float(meta["workflow_time_s"]), pool=si.get("max_total_num_tokens"),
                ctx=si.get("context_length"), evicted=ss.get("evicted_tokens_in_run") or 0,
                flushed=meta.get("cache_flushed_before_run"), calls=calls, tools=tools)


# ----------------------------------------------------------------------------- traffic

def _traffic_dir(rd):
    calls_by_run, tools_by_run = {}, {}
    for tf in sorted(glob.glob(os.path.join(rd, "2026*.json"))):
        rid = os.path.basename(tf)[:-5]
        t = json.load(open(tf))
        b = t.get("benchmark") or {}
        ok_calls = [c for c in (b.get("llm_calls") or []) if "error" not in c and c.get("output_tokens") is not None]
        turns = [x for x in (t.get("turns") or []) if x.get("role") == "assistant"]
        aligned = len(turns) == len(ok_calls) > 0
        calls = []
        for i, c in enumerate(ok_calls):
            out = int(c["output_tokens"])
            granted = (c.get("token_budget") or {}).get("granted_max_tokens") or 8000
            cap = min(8000, granted)
            capped = out >= 0.99 * cap
            text, complete = None, False
            if aligned:
                a = turns[i]
                args = [r.get("arguments") for r in (a.get("requested_tool_calls") or [])]
                text = "\n".join([str(a.get("reasoning") or ""), str(a.get("content") or "")] +
                                 [x if isinstance(x, str) else json.dumps(x) for x in args if x])
                # a cap inside a tool call drops its body (arguments "{}"): only the reasoning survives
                complete = not capped or (c.get("reasoning_tokens") or 0) >= 0.99 * cap
            calls.append(dict(
                t0=float(c["t_phase_start"]), t1=float(c["t_phase_end"]), prompt=int(c.get("input_tokens") or 0),
                cached=int(c.get("cached_input_tokens") or 0), out=out, reasoning=c.get("reasoning_tokens"),
                ttft=float(c.get("ttft_s") or 0), decode=float(c.get("decode_s") or 0), energy=c.get("iter_energy_j"),
                capped=capped, cap=cap, role="agent", text=text, text_complete=complete,
                schema=c.get("prompt_schema_tokens"), scaffold=c.get("prompt_scaffold_tokens"),
                toolout=c.get("prompt_tooloutput_tokens")))
        calls_by_run[rid] = calls
        tools_by_run[rid] = [dict(t0=float(x["t_phase_start"]), t1=float(x["t_phase_end"]), tool=x.get("tool"),
                                  energy=x.get("iter_energy_j"))
                             for x in (b.get("tool_calls") or []) if x.get("t_phase_end") is not None]
    return calls_by_run, tools_by_run


def _traffic_runs(cfg):
    runs = []
    for rd in sorted(glob.glob(os.path.join(_root(cfg), "*", "run*"))):
        m = re.match(r"run(\d+)(_.+)?$", os.path.basename(rd))
        if not m or m.group(2):
            continue
        calls_by_run, tools_by_run = _traffic_dir(rd)
        for r in jsonl(os.path.join(rd, "runs.jsonl")):
            rid = r.get("run_id")
            if rid not in calls_by_run:
                continue  # 32 rows have no trace (P1 counts them; they carry no calls)
            en = r.get("workflow_energy_j")
            en = en if en is not None else r.get("workflow_energy_j_reconstructed")
            runs.append(dict(task=r.get("task_id"), instance=os.path.basename(os.path.dirname(rd)), rep=int(m.group(1)),
                             ok=r.get("failure_class") is None, status=r.get("failure_class") or "completed",
                             energy_J=float(en or 0), time_s=float(r.get("workflow_time_s") or 0),
                             pool=r.get("max_total_num_tokens"), ctx=r.get("context_length"), evicted=None,
                             flushed=r.get("cache_flushed_before_run"), calls=calls_by_run[rid],
                             tools=tools_by_run[rid], vitals_dir=rd))
    return runs


# ----------------------------------------------------------------------------- entry point

def load(key, refresh=False):
    """Runs of one configuration (see CONFIGS), parsed once and cached."""
    cfg = BY_KEY[key]
    CACHE.mkdir(parents=True, exist_ok=True)
    cp = CACHE / f"{key}.pkl"
    if cp.exists() and not refresh:
        return pickle.loads(cp.read_bytes())
    if cfg.domain == "drone":
        runs = [_drone_run(p) for p in sorted(glob.glob(os.path.join(_root(cfg), "*/instance_*/run_*/run_meta.json")))]
    else:
        runs = _traffic_runs(cfg)
    for r in runs:
        r["cfg"] = key
        r["calls"].sort(key=lambda c: c["t0"])
        r["tools"].sort(key=lambda t: t["t0"])
    cp.write_bytes(pickle.dumps(runs))
    return runs


if __name__ == "__main__":
    for c in CONFIGS:
        rs = load(c.key, refresh=True)
        n = sum(len(r["calls"]) for r in rs)
        print(f"{c.key:20s} runs {len(rs):4d}  calls {n:5d}  ok {sum(r['ok'] for r in rs):4d}  "
              f"capped {sum(x['capped'] for r in rs for x in r['calls']):4d}  "
              f"kWh {sum(r['energy_J'] for r in rs) / 3.6e6:.2f}")

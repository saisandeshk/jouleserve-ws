"""Memory-budget simulator: N drones' agent sessions sharing one edge box.

Question: when N concurrent agent sessions share one device's state budget, how much energy
per successful mission does SGLang's default leave on the table, and how much of it does a
controller that only uses online observations recover?

Model (token-driven, discrete events, fluid within an event):
- Workloads are recorded missions. Per LLM call: prompt, cached and output tokens. Between
  calls: the tool wait, at real time (step-wise runs were paced 50x; their flight times come
  from the sim clock). Missions are drawn at random, with replacement, for N closed-loop
  drone slots: when a mission ends, that drone starts the next one.
- Device: cold prefill rate, decode step time as a function of batch (and context), and power
  while any call runs vs. while none runs (GPU power on the WS, board power on the Thor).
  Calls prefill FCFS one at a time; decode waits while a prefill runs (SGLang without mixed
  chunks).
- Memory: one byte budget for retained state. Per model: bytes per token of full-attention KV,
  a fixed block per session (Gemma's sliding-window KV, Qwen3.5's recurrent-state slot) and
  extra working state per running call. The shared system prompt is stored once. A session's
  private state is evicted whole: without its fixed block it cannot resume from cache.
- A running call grows by one token per decode step. When memory runs out, paused state is
  evicted first (in the policy's order), then running calls are retracted (fewest decoded
  tokens first) and later recompute prompt + decoded tokens (SGLang 0.5.20 monolithic mode).
- A call that cannot fit even alone fails its mission (SGLang rejects it).

Metric: energy per successful mission in steady state = (energy per hour) / (successful
missions completed per hour), over the window [warm, horizon].

Policies (serving decisions only; the agents and the model are fixed):
  default    SGLang-like: FCFS; admit while memory minus a reserve of 0.3 x min(4096, left)
             tokens per running call allows; LRU eviction of paused state; retraction
  drop       default, but discard a session's state at every tool wait
  keep       default, but paused state is pinned (never evicted); running calls are retracted
  cap<k>     default with at most k calls running at once (KAIROS-style concurrency cap)
  value      default admission + value-per-byte eviction (online wait estimates)
  value_exact  default admission + value-per-byte eviction with exact wake times
  adaptive   budget-aware admission (projected peak of running calls, from an online p90 of
             output length per call position) + value-per-byte eviction (re-prefill saved
             per byte-second, wait predicted per tool by an online EWMA). Uses only what a
             gateway observes while running.
  oracle     adaptive with exact output lengths and exact wake times (clairvoyant variant;
             not an optimum: exact reservations under-admit long decodes)
  compress   default, but paused state is stored at half size (e.g. FP8 instead of bf16) and
             expanded on resume; quality effects are not modelled
  inf        unlimited memory at the same N: a bound for every memory policy

Usage: python3 -m analysis.admission_sim [validate|grid|all]
"""
from __future__ import annotations

import glob
import heapq
import json
import math
import random
import statistics as st
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from analysis.sessions import REPO, load_p1

WS_RUNS = REPO / "data/ws_runs"
OUT = REPO / "reports/2026-10-03-admission-sim"
GiB = 1024 ** 3


# ----------------------------------------------------------------------------- workloads

@dataclass
class Call:
    prompt: int
    cached: int
    out: int


@dataclass
class Mission:
    mid: str
    calls: list
    waits: list           # len(calls) - 1, seconds
    tools: list           # tool name per wait (None when unknown)
    success: bool
    t0: float = 0.0       # start time in the recorded run


@dataclass
class Workload:
    name: str
    missions: list
    shared: int           # system-prompt tokens common to every session
    max_tokens: int


def _jsonl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def _success_aerogen(summ):
    dc = summ.get("delivery_check")
    if isinstance(dc, dict) and dc.get("stops"):
        # All stops delivered and back at the depot. The strict check also fails flights through
        # buildings, which aerogen's kinematic sim does not model (step-wise report, item 5).
        return len(dc.get("delivered", [])) == len(dc["stops"]) and bool(dc.get("returned"))
    return (summ.get("validator") or {}).get("valid") == "YES"


def load_aerogen_runs(name, runs, max_tokens, margin=150, include_errored=False):
    """aerogen-driver runs (WS). Tool waits at real time: for paced runs the per-tool flight
    time is the difference of the cumulative sim clock (`sim_t`)."""
    ms = []
    for run in runs:
        for sd in sorted(glob.glob(str(WS_RUNS / run / "sessions" / "*"))):
            sp = Path(sd, "summary.json")
            if not sp.exists():
                continue
            summ = json.loads(sp.read_text())
            if summ.get("status") != "done" and not include_errored:
                continue
            calls = sorted((c for c in _jsonl(Path(sd, "llm_calls.jsonl"))
                            if c.get("completion_tokens") is not None and c.get("t_end")), key=lambda c: c["t_req"])
            tools = sorted(_jsonl(Path(sd, "tool_calls.jsonl")), key=lambda t: t["t_start"])
            if len(calls) < 2:
                continue
            last_sim, real = 0.0, []
            for t in tools:
                if t.get("sim_t") is not None:
                    real.append(max(0.0, t["sim_t"] - last_sim))
                    last_sim = t["sim_t"]
                else:
                    real.append(t["dur_s"])
            waits, names = [], []
            for a, b in zip(calls, calls[1:]):
                idx = [k for k, t in enumerate(tools) if a["t_end"] - 1e-3 <= t["t_start"] < b["t_req"]]
                measured = sum(tools[k]["dur_s"] for k in idx)
                gap = max(0.0, b["t_req"] - a["t_end"])
                waits.append(max(0.0, gap - measured) + sum(real[k] for k in idx))
                names.append(max(idx, key=lambda k: real[k], default=None) is not None
                             and tools[max(idx, key=lambda k: real[k])]["tool"] or None)
            ms.append(Mission(f"{run}/{Path(sd).name}",
                              [Call(c["prompt_tokens"], c.get("cached_tokens") or 0, c["completion_tokens"]) for c in calls],
                              waits, names, summ.get("status") == "done" and _success_aerogen(summ),
                              float(summ.get("t_start") or calls[0]["t_req"])))
    shared = max(0, min(m.calls[0].prompt for m in ms) - margin)
    return Workload(name, ms, shared, max_tokens)


def load_p1_workload(name, root):
    ms = []
    for s in load_p1(root, name):
        calls = [Call(c["prompt"], c["cached"], c["completion"]) for c in s.calls]
        waits = [max(0.0, b["t0"] - a["t1"]) for a, b in zip(s.calls, s.calls[1:])]
        ms.append(Mission(s.sid, calls, waits, [None] * len(waits), bool(s.success)))
    # Prompts are rebuilt per role call; cross-session sharing of P1's system text is not
    # modelled (shared = 0), so every session's prefix counts as its own state.
    return Workload(name, ms, 0, 32768)


def workloads():
    return {
        "stepwise_qwen_think": lambda: load_aerogen_runs(
            "Step-wise, Qwen3.5-9B thinking (P1 D1-D3)", ["q_think_sampled_d1", "q_think_sampled_d23"], 32768),
        "stepwise_qwen_nothink": lambda: load_aerogen_runs(
            "Step-wise, Qwen3.5-9B no thinking (P1 D1-D3)", ["q_nothink_sampled_d1", "q_nothink_sampled_d23"], 32768),
        "stepwise_qwen_think_greedy": lambda: load_aerogen_runs(
            "Step-wise, Qwen3.5-9B thinking, greedy (P1 D1-D3)", ["q_think_greedy_d1", "q_think_greedy_d23"], 32768),
        "stepwise_k2_high": lambda: load_aerogen_runs(
            "Step-wise, K2 high effort (P1 D1-D3)", ["k2_high_d1", "k2_high_d23"], 16384),
        "stepwise_k2_low": lambda: load_aerogen_runs(
            "Step-wise, K2 low effort (P1 D1-D3)", ["k2_low_d1", "k2_low_d23"], 16384),
        "aerogen_k2_low": lambda: load_aerogen_runs(
            "aerogen own tasks, K2 low effort", ["e1_low_n1"], 16384),
        "p1_reflexion": lambda: load_p1_workload("P1 Reflexion (Gemma, Thor)", REPO / "data/p1_thor_drone"),
        "p1_toolcalling": lambda: load_p1_workload("P1 tool calling (Gemma, Thor)", REPO / "data/p1_thor_toolcalling"),
    }


# ----------------------------------------------------------------------------- devices, layouts

@dataclass
class Layout:
    name: str
    tok: float      # bytes per token of full-attention KV
    fixed: float    # bytes per session that must stay resident to resume from cache
    work: float     # extra bytes per running call


LAYOUTS = {
    # 30 layers: 25 sliding-window (window 1024, 8 KV heads x 256) + 5 full (2 KV heads x 512);
    # bytes per token from P1's run_meta kv_config, window from the model config.
    "gemma": Layout("Gemma-4-26B-A4B: 25 sliding-window + 5 full-attention layers", 20480, 1024 * 204800, 0),
    # 8 full-attention layers (32 KiB/token); one recurrent-state slot ~54 MB (WS server log:
    # 0.96 GiB for 19 slots). SGLang 0.5.20 holds 5 slots per running request.
    "qwen35": Layout("Qwen3.5-9B: 24 linear-attention + 8 full-attention layers", 32768, 54e6, 4 * 54e6),
    "k2": Layout("K2-Horizon-7B: dense, 144 KiB/token", 147456, 0, 0),
    "gemma_fp8": Layout("Gemma-4-26B-A4B with an FP8 KV cache", 10240, 1024 * 102400, 0),
}


@dataclass
class Device:
    name: str
    prefill: float          # cold prefill tokens/s
    p_active: float         # W while any call runs
    p_idle: float           # W while no call runs
    kind: str               # "ws" (calibrated table) or "moe" (bandwidth model)
    table: list = field(default_factory=list)   # [(batch, s per step)]
    t1: float = 0.0         # s per step at batch 1 (moe)

    def step(self, b, ctx_sum):
        if b <= 0:
            return 0.0
        if self.kind == "ws":
            # calibrated at ~120-token prompts; add the KV read of the real contexts (K2:
            # 144 KiB/token at the bandwidth implied by ~15.2 GB of weights per batch-1 step)
            return self._table(b) + ctx_sum * 147456 * self._table(1) / 15.2e9
        return self.t1 * _moe_bytes(b, ctx_sum) / _moe_bytes(1, 12000)


    def _table(self, b):
        bs = self.table
        if b <= bs[0][0]:
            return bs[0][1]
        for (b0, s0), (b1, s1) in zip(bs, bs[1:]):
            if b <= b1:
                return s0 + (s1 - s0) * (b - b0) / (b1 - b0)
        (b0, s0), (b1, s1) = bs[-2], bs[-1]
        return s1 + (s1 - s0) * (b - b1) / (b1 - b0)


# Gemma-4-26B-A4B decode is bandwidth-bound: per step it reads the non-expert weights
# (attention, dense MLP, tied LM head: ~4.5 GB in bf16), every distinct expert any token in the
# batch routes to (128 experts, top-8, 11.9 MB each per layer x 30 layers; uniform routing, so
# correlated routing would make batching cheaper than this), and each request's KV.
def _moe_bytes(b, ctx_sum):
    distinct = 128 * (1 - (1 - 8 / 128) ** b)
    return 4.5e9 + distinct * 30 * 11.9e6 + 20480 * ctx_sum + b * 1024 * 204800


def ws_device():
    cal = json.loads((WS_RUNS / "calib_k2_tp1_gpu0.json").read_text())
    data = json.loads((REPO / "reports/2026-10-01-workload-opportunity/report_data.json").read_text())["ws_calibration"]
    table = [(d["batch"], d["wall_s"] / (d["tokens"] / d["batch"])) for d in cal["decode"]]
    p_dec = st.mean(d["avg_power_w"] for d in cal["decode"])
    return Device("WS A5000 (K2-Horizon-7B, measured)", data["prefill_tok_s"], p_dec, data["idle_w"], "ws", table)


def thor_device(decode_tok_s=27.0):
    # Board power from 178 P1 runs (VIN): 71.9 W while an LLM call runs, 38.6 W otherwise
    # (least squares over workflow energy = a * LLM time + b * other time; 0.4% median error).
    return Device("Thor (Gemma-4-26B-A4B; P1 rates, board power)", 1811.0, 71.9, 38.6, "moe", t1=1 / decode_tok_s)


# ----------------------------------------------------------------------------- simulator

POLICIES = {
    "default": dict(adm="sglang", ret="lru"),
    "drop": dict(adm="sglang", ret="lru", drop=True),
    "keep": dict(adm="sglang", ret="lru", pin=True),
    "cap1": dict(adm="sglang", ret="lru", cap=1),
    "cap2": dict(adm="sglang", ret="lru", cap=2),
    "cap4": dict(adm="sglang", ret="lru", cap=4),
    "cap8": dict(adm="sglang", ret="lru", cap=8),
    "value": dict(adm="sglang", ret="value"),
    "value_exact": dict(adm="sglang", ret="exact"),
    "adaptive": dict(adm="budget", ret="value"),
    "oracle": dict(adm="exact", ret="exact"),
    "compress": dict(adm="sglang", ret="lru", compress=0.5),
    "inf": dict(adm="none", ret="lru", inf=True),
}
FIXED_RULES = ["default", "drop", "keep", "cap1", "cap2", "cap4", "cap8"]
SGLANG_RATIO, SGLANG_CLIP = 0.3, 4096


class Sess:
    __slots__ = ("slot", "m", "i", "t_ms", "held", "held_tok", "res", "pf", "dec", "decoded",
                 "phase", "last_use", "wake", "tool", "retracted", "reprefill", "retract_tok",
                 "queued_s", "q_since", "failed", "seq")

    def __init__(self, slot):
        self.slot = slot
        self.m = None


class Predictor:
    """Online estimates a gateway can keep: output length per call position, wait per tool."""

    def __init__(self):
        self.out = {"first": deque(maxlen=256), "step": deque(maxlen=256)}
        self.wait = {}

    def out_p90(self, first):
        xs = self.out["first" if first else "step"]
        if len(xs) < 8:
            return 2048 if first else 256
        return sorted(xs)[int(0.9 * (len(xs) - 1))]

    def remaining(self, first, decoded):
        return max(self.out_p90(first) - decoded, 0.25 * decoded, 32)

    def wait_est(self, tool):
        return self.wait.get(tool or "gap", 30.0)

    def see_wait(self, tool, w):
        k = tool or "gap"
        self.wait[k] = w if k not in self.wait else 0.7 * self.wait[k] + 0.3 * w


def standalone_s(m, wl, dev):
    S, t = wl.shared, 0.0
    for i, c in enumerate(m.calls):
        pf = c.prompt - (max(S, c.cached) if i else S)
        t += max(0, pf) / dev.prefill + c.out * dev.step(1, S + c.prompt + c.out / 2)
    return t + sum(m.waits)


def simulate(wl, dev, lay, budget_gib, n, policy, horizon=8 * 3600.0, warm=1800.0, seed=0,
             plan=None, stagger=20.0, standalone=None):
    P = POLICIES[policy]
    rng = random.Random(seed)
    B = math.inf if P.get("inf") or budget_gib is None else budget_gib * GiB
    S, tok, fixed, work = wl.shared, lay.tok, lay.fixed, lay.work
    shared_b = S * tok + (fixed if S else 0)
    cap = P.get("cap", 10 ** 9)
    pred = Predictor()
    if standalone is None:
        standalone = {}
    if plan is not None:            # a fixed mission sequence, taken by whichever drone frees first
        horizon, warm = math.inf, 0.0
        plan = deque(plan)

    sess = [Sess(k) for k in range(n)]
    heap, seq = [], [0]
    queue = deque()
    running = []                   # admission order; prefill FCFS by this order
    paused = set()
    rec = []                       # finished missions
    stats = dict(busy=0.0, win_busy=0.0, win_t0=None, forced=0, batch_area=0.0, dec_time=0.0)

    def push(t, kind, s):
        seq[0] += 1
        heapq.heappush(heap, (t, seq[0], kind, s))

    comp = P.get("compress", 1.0)

    def held_b(s):
        return comp * (fixed + s.held_tok * tok) if s.held else 0.0

    def run_b(s):
        return fixed + work + s.res * tok

    def used():
        return shared_b + sum(run_b(s) for s in running) + sum(held_b(s) for s in paused) \
            + sum(held_b(s) for s in queue)

    def call(s):
        return s.m.calls[s.i]

    def reserve_left(r):
        a = P["adm"]
        if a == "sglang":
            return SGLANG_RATIO * max(0.0, min(SGLANG_CLIP, wl.max_tokens) - r.decoded) * tok
        if a == "budget":
            return 1.1 * pred.remaining(r.i == 0, r.decoded) * tok
        if a == "exact":
            return max(0.0, call(r).out - r.decoded) * tok
        return 0.0

    def own_reserve(s):
        a = P["adm"]
        if a == "sglang":
            return SGLANG_RATIO * min(SGLANG_CLIP, wl.max_tokens) * tok
        if a == "budget":
            return 1.1 * pred.remaining(s.i == 0, s.decoded) * tok
        if a == "exact":
            return max(0.0, call(s).out - s.decoded) * tok
        return 0.0

    def priv(s):
        return max(0, call(s).prompt - S)

    def need_b(s):
        if s.held:
            # resuming expands compressed state back to full size
            return work + max(0, priv(s) - s.held_tok) * tok + (1 - comp) * (fixed + s.held_tok * tok)
        return fixed + work + (priv(s) + (s.decoded if s.retracted else 0)) * tok

    def evict_order(t, exclude):
        cands = [v for v in list(paused) + list(queue) if v.held and v is not exclude]
        if P.get("pin"):
            return []
        r = P["ret"]
        if r == "lru":
            return sorted(cands, key=lambda v: v.last_use)
        if r == "value":
            def val(v):
                rem = 0.0 if v in queue else max(0.0, pred.wait_est(v.tool) - (t - v.last_use))
                return (v.held_tok / dev.prefill) / (held_b(v) * max(1.0, rem))
            return sorted(cands, key=val)
        def val_exact(v):
            rem = 0.0 if v in queue else max(0.0, v.wake - t)
            return (v.held_tok / dev.prefill) / (held_b(v) * max(1.0, rem))
        return sorted(cands, key=val_exact)

    def admissible(s, t):
        if len(running) >= cap:
            return False
        if B == math.inf:
            return True
        free = B - used() - sum(reserve_left(r) for r in running)
        evictable = sum(held_b(v) for v in evict_order(t, s))
        # with nothing running, the engine admits a call that fits without its reserve
        return free + evictable >= need_b(s) + (own_reserve(s) if running else 0.0)

    def drop_state(v):
        v.held = False
        v.held_tok = 0

    def admit(s, t):
        c = call(s)
        if s.retracted:
            pf = priv(s) + s.decoded
            s.retract_tok += pf
        elif s.held or s.i == 0:
            pf = c.prompt - (max(S, c.cached) if s.i else S)
        else:
            pf = c.prompt - S
            s.reprefill += max(0, max(S, c.cached) - S)
        need = need_b(s)
        if B != math.inf:
            for v in evict_order(t, s):
                if B - used() >= need:
                    break
                drop_state(v)
        s.held, s.held_tok = False, 0
        s.res = priv(s) + (s.decoded if s.retracted else 0)
        s.retracted = False
        s.pf = max(0, pf)
        s.dec = c.out - s.decoded
        s.phase = "prefill" if s.pf > 0 else "decode"
        running.append(s)

    def drain(t):
        while queue:
            s = queue[0]
            if admissible(s, t):
                queue.popleft()
                s.queued_s += t - s.q_since
                admit(s, t)
            elif not running and P.get("pin") and B != math.inf:
                # deadlock guard under pinning: nothing runs, so drop the oldest pinned state
                vs = sorted((v for v in list(paused) + list(queue) if v.held and v is not s), key=lambda v: v.last_use)
                if not vs:
                    break
                drop_state(vs[0])
                stats["forced"] += 1
            else:
                break

    def fail_mission(s, t):
        s.failed = True
        if s in running:
            running.remove(s)
        if s in queue:
            queue.remove(s)
        end_mission(s, t)

    def request(s, t):
        c = call(s)
        if shared_b + fixed + work + (priv(s) + c.out) * tok > B:
            fail_mission(s, t)
            return
        s.q_since = t
        queue.append(s)

    def start_mission(s, t):
        if plan is not None:
            if not plan:
                s.m = None
                return
            s.m = plan.popleft()
        else:
            s.m = wl.missions[rng.randrange(len(wl.missions))]
        s.i, s.t_ms, s.held, s.held_tok, s.res, s.decoded = 0, t, False, 0, 0, 0
        s.retracted, s.reprefill, s.retract_tok, s.queued_s, s.failed = False, 0, 0, 0.0, False
        s.tool = None
        request(s, t)

    def end_mission(s, t):
        s.held, s.held_tok, s.res = False, 0, 0
        key = id(s.m)
        if key not in standalone:
            standalone[key] = standalone_s(s.m, wl, dev)
        rec.append(dict(t0=s.t_ms, t1=t, ok=(s.m.success and not s.failed), failed=s.failed,
                        reprefill=s.reprefill, retract=s.retract_tok, queued=s.queued_s,
                        slow=(t - s.t_ms) / max(1.0, standalone[key])))
        if t < horizon:
            # via the event heap (no recursion when missions fail at once); a failed mission
            # costs the drone a minute before it relaunches
            push(t + (60.0 if s.failed else 0.0), "start", s)

    def finish_call(s, t):
        running.remove(s)
        c = call(s)
        pred.out["first" if s.i == 0 else "step"].append(c.out)
        s.decoded, s.res = 0, 0
        s.i += 1
        s.last_use = t
        if s.i >= len(s.m.calls):
            end_mission(s, t)
            return
        wait = s.m.waits[s.i - 1]
        s.tool = s.m.tools[s.i - 1]
        s.held = not P.get("drop")
        s.held_tok = max(0, c.prompt - S) + c.out
        s.wake = t + wait
        paused.add(s)
        push(t + wait, "wake", s)

    def retract(t):
        dec = [r for r in running if r.phase == "decode"]
        if len(running) <= 1 or not dec:
            return False
        v = min(dec, key=lambda r: r.decoded)
        running.remove(v)
        v.res, v.retracted, v.held, v.held_tok = 0, True, False, 0
        v.q_since = t
        queue.appendleft(v)
        return True

    def overflow(t, slack):
        for v in evict_order(t, None):
            if B - used() >= slack:
                return
            drop_state(v)
        while B - used() < slack and retract(t):
            pass
        if B - used() > 1e-3:
            return
        # One call left and no room to grow.
        pinned = sorted((v for v in list(paused) + list(queue) if v.held), key=lambda v: v.last_use)
        for v in pinned:            # only non-empty under pinning: give up pinned state
            drop_state(v)
            stats["forced"] += 1
            if B - used() >= slack:
                return
        if B - used() <= 1e-3 and running:
            fail_mission(max(running, key=lambda r: r.res), t)

    for k in range(n):
        push(k * stagger, "start", sess[k])

    t = 0.0
    while True:
        drain(t)
        pf_head = next((r for r in running if r.phase == "prefill"), None)
        decs = [r for r in running if r.phase == "decode"] if pf_head is None else []
        dt_int = math.inf
        step = 0.0
        if pf_head is not None:
            dt_int = pf_head.pf / dev.prefill
        elif decs:
            ctx = sum(S + call(r).prompt + r.decoded for r in decs)
            step = dev.step(len(decs), ctx)
            dt_int = min(r.dec for r in decs) * step
            if B != math.inf:
                rate = len(decs) * tok / step
                free = B - used()
                dt_int = min(dt_int, max(0.0, free) / rate if rate > 0 else math.inf)
        t_ext = heap[0][0] if heap else math.inf
        if dt_int == math.inf and t_ext == math.inf:
            if queue and not running:
                # the head can never be admitted (pinned state held by sessions that are
                # themselves queued, or no room at all): its mission fails
                fail_mission(queue[0], t)
                continue
            break
        t_next = min(t + dt_int, t_ext)
        if plan is None and t_next > horizon:
            t_next = horizon
        dt = t_next - t
        if running and dt > 0:
            stats["busy"] += dt
            a, b = max(t, warm), min(t_next, horizon)
            if b > a:
                stats["win_busy"] += b - a
            if decs:
                stats["batch_area"] += len(decs) * dt
                stats["dec_time"] += dt
        if pf_head is not None:
            pf_head.pf -= dev.prefill * dt
        elif decs and step > 0:
            k = dt / step
            for r in decs:
                r.dec -= k
                r.decoded += k
                r.res += k
        t = t_next
        if plan is None and t >= horizon:
            break
        # internal transitions
        if pf_head is not None and pf_head.pf <= 1e-6:
            pf_head.phase = "decode"
            if pf_head.dec <= 1e-6:
                finish_call(pf_head, t)
        for r in [r for r in decs if r.dec <= 1e-6 and r in running]:
            finish_call(r, t)
        if B != math.inf and decs and B - used() <= 1e-3:
            overflow(t, slack=64 * len(decs) * tok)
        while heap and heap[0][0] <= t + 1e-9:
            _, _, kind, s = heapq.heappop(heap)
            if kind == "start":
                start_mission(s, t)
            elif kind == "wake":
                paused.discard(s)
                pred.see_wait(s.tool, t - s.last_use)
                request(s, t)
        if plan is not None and not running and not queue and not heap and not paused:
            break

    win = (horizon - warm) if plan is None else t
    lo = warm if plan is None else 0.0
    done = [r for r in rec if lo <= r["t1"] <= (horizon if plan is None else math.inf)]
    ok = sum(r["ok"] for r in done)
    energy = dev.p_active * stats["win_busy"] + dev.p_idle * (win - stats["win_busy"]) if plan is None \
        else dev.p_active * stats["busy"] + dev.p_idle * (t - stats["busy"])
    nd = max(1, len(done))
    slows = sorted(r["slow"] for r in done) or [float("nan")]
    return dict(
        policy=policy, n=n, budget_gib=budget_gib, seed=seed, span_s=t, missions=len(done),
        succeeded=ok, failed=sum(r["failed"] for r in done),
        energy_j=energy, energy_per_success_j=energy / ok if ok else math.inf,
        energy_per_mission_j=energy / nd, missions_per_hour=len(done) / win * 3600,
        reprefill_tok=sum(r["reprefill"] for r in done) / nd,
        retract_tok=sum(r["retract"] for r in done) / nd,
        queued_s=sum(r["queued"] for r in done) / nd,
        slow_p50=slows[len(slows) // 2], slow_p95=slows[min(len(slows) - 1, int(0.95 * len(slows)))],
        busy_share=(stats["win_busy"] / win) if plan is None else stats["busy"] / t,
        mean_batch=stats["batch_area"] / stats["dec_time"] if stats["dec_time"] else 0.0,
        forced=stats["forced"])


# ----------------------------------------------------------------------------- validation

LIVE = ["e2_low_n2", "e2_low_n4", "e2_low_n8", "e2_low_n4_kv16k", "e2_low_n4_kv13k"]


def validate():
    """Replay each live WS concurrency run (K2 low, aerogen tasks, real-time flights) with its
    own missions in their recorded order, its N, stagger and KV pool, under the default
    policy, with the run's measured call and between-call GPU power. Compares re-prefilled
    tokens, energy and missions per hour with the live run."""
    from analysis.report_figures import WS, calibration, load_ws_run, run_summary
    from analysis.sim_validate import excess_reprefill
    cal = calibration(WS / "calib_k2_tp1_gpu0.json")
    base = ws_device()
    rows = []
    for name in LIVE:
        run = load_ws_run(name, cal)
        live = run_summary(run, cal) if run else None
        if not live:
            continue
        man = run["manifest"]
        n, stagger = man["args"]["concurrency"], man["args"]["stagger_s"]
        pool = int(man["server_info"]["max_total_num_tokens"])
        wl = load_aerogen_runs(name, [name], 16384, include_errored=True)
        plan = sorted(wl.missions, key=lambda m: m.t0)
        dev = Device(base.name, base.prefill, live["call_power_w"], live["idle_power_w"], "ws", base.table)
        r = simulate(wl, dev, LAYOUTS["k2"], pool * LAYOUTS["k2"].tok / GiB, n, "default",
                     plan=plan, stagger=stagger)
        rows.append(dict(run=name, n=n, pool_tokens=pool, missions=len(plan),
                         live_reprefill_tok=excess_reprefill(run["sessions"]),
                         sim_reprefill_tok=r["reprefill_tok"] + r["retract_tok"],
                         live_energy_per_mission_j=live["energy_j"] / len(plan),
                         sim_energy_per_mission_j=r["energy_per_mission_j"],
                         live_missions_per_hour=len(plan) / live["span_s"] * 3600,
                         sim_missions_per_hour=r["missions"] / r["span_s"] * 3600,
                         live_errored=live["errored"], sim_failed=r["failed"]))
        x = rows[-1]
        print(f"{name:16s} N={n} pool={pool:5d} | re-prefill/mission live {x['live_reprefill_tok']:6.0f} sim "
              f"{x['sim_reprefill_tok']:6.0f} | energy/mission live {x['live_energy_per_mission_j']:6.0f} sim "
              f"{x['sim_energy_per_mission_j']:6.0f} J | missions/h live {x['live_missions_per_hour']:5.1f} sim "
              f"{x['sim_missions_per_hour']:5.1f} | errored live {x['live_errored']} sim {x['sim_failed']}")
    return rows


# ----------------------------------------------------------------------------- grid

# P1 missions run 10-110 min, so they need a longer window for the same number of missions
HORIZON = {"p1": 72 * 3600.0, "other": 24 * 3600.0}
WARM, SEEDS = 2 * 3600.0, (0, 1, 2, 3, 4)
NS = (1, 2, 4, 8, 16)

# (scenario, device, layout, workloads, budgets in GiB)
SCENARIOS = [
    ("thor_gemma", "thor", "gemma",
     ["stepwise_qwen_think", "stepwise_qwen_nothink", "stepwise_k2_high", "aerogen_k2_low",
      "p1_reflexion", "p1_toolcalling"], (1, 2, 4, 8, 16)),
    # H3: same device and timing, other state layouts (hybrid recurrent; dense)
    ("thor_qwen35", "thor", "qwen35", ["stepwise_qwen_think", "stepwise_k2_high", "p1_reflexion"], (1, 2, 4, 8, 16)),
    ("thor_dense", "thor", "k2", ["stepwise_qwen_think", "stepwise_k2_high", "p1_reflexion"], (2, 4, 8, 16, 32)),
    # Sensitivity: Thor with dense-model batching (decode step time grows as on the WS)
    ("thor_densebatch_gemma", "thor_densebatch", "gemma", ["stepwise_qwen_think", "p1_reflexion", "p1_toolcalling"],
     (1, 2, 4, 8, 16)),
    # WS, K2: closest to the live runs (3.5 GiB = the one-GPU pool of 25.4K tokens)
    ("ws_k2", "ws", "k2", ["aerogen_k2_low", "stepwise_k2_low", "stepwise_k2_high"], (1.5, 2.5, 3.5, 6, 10)),
    # Capacity reference: all KV in FP8 (half the bytes per token and per window)
    ("thor_gemma_fp8", "thor", "gemma_fp8", ["stepwise_qwen_think", "stepwise_k2_high", "p1_toolcalling"], (1, 2, 4, 8, 16)),
]

_W, _D = {}, {}


def _device(name):
    if name not in _D:
        if name == "thor":
            _D[name] = thor_device()
        elif name == "ws":
            _D[name] = ws_device()
        elif name == "thor_densebatch":
            ws = ws_device()
            t1 = 1 / 27.0
            _D[name] = Device("Thor, dense-model batching (sensitivity)", 1811.0, 71.9, 38.6, "ws",
                              [(b, s * t1 / ws.table[0][1]) for b, s in ws.table])
    return _D[name]


def _workload(name):
    if name not in _W:
        _W[name] = workloads()[name]()
    return _W[name]


def _job(args):
    scen, dev, lay, wl, budget, n, pol, seed = args
    h = HORIZON["p1" if wl.startswith("p1") else "other"]
    r = simulate(_workload(wl), _device(dev), LAYOUTS[lay], budget, n, pol, horizon=h, warm=WARM, seed=seed)
    r.update(scenario=scen, workload=wl, layout=lay, device=dev)
    return r


def grid(procs=20):
    from multiprocessing import Pool
    jobs = [(scen, dev, lay, wl, b, n, pol, seed)
            for scen, dev, lay, wls, budgets in SCENARIOS for wl in wls for b in budgets for n in NS
            for pol in POLICIES for seed in SEEDS]
    print(f"{len(jobs)} simulations")
    with Pool(procs) as p:
        rows = p.map(_job, jobs, chunksize=8)
    return rows


def summarize(rows):
    """Mean over seeds per (scenario, workload, budget, n, policy), then headroom per cell."""
    from collections import defaultdict
    acc = defaultdict(list)
    for r in rows:
        acc[(r["scenario"], r["workload"], r["budget_gib"], r["n"], r["policy"])].append(r)
    mean = {}
    for k, rs in acc.items():
        m = {f: st.mean(x[f] for x in rs) for f in ("energy_per_success_j", "energy_per_mission_j", "missions_per_hour",
                                                     "reprefill_tok", "retract_tok", "queued_s", "slow_p50",
                                                     "slow_p95", "busy_share", "mean_batch", "failed", "succeeded")}
        m["fail_share"] = sum(x["failed"] for x in rs) / max(1, sum(x["missions"] for x in rs))
        mean[k] = m
    cells = []
    for (scen, wl, b, n) in sorted({k[:4] for k in mean}, key=lambda k: (k[0], k[1], k[2], k[3])):
        g = {p: mean[(scen, wl, b, n, p)] for p in POLICIES if (scen, wl, b, n, p) in mean}
        E = {p: g[p]["energy_per_success_j"] for p in g}
        d = E["default"]
        fixed = {p: E[p] for p in FIXED_RULES}
        best_fixed = min(fixed, key=fixed.get)
        ok_lat = {p: E[p] for p in FIXED_RULES if g[p]["slow_p95"] <= 1.1 * g["default"]["slow_p95"]}
        best_fixed_lat = min(ok_lat, key=ok_lat.get)
        best_any = min((p for p in E if p != "inf"), key=E.get)
        cells.append(dict(
            scenario=scen, workload=wl, budget_gib=b, n=n,
            e_default=d, e_inf=E["inf"], e_oracle=E["oracle"], e_adaptive=E["adaptive"],
            best_fixed=best_fixed, e_best_fixed=fixed[best_fixed],
            best_fixed_lat=best_fixed_lat, e_best_fixed_lat=ok_lat[best_fixed_lat],
            best_any=best_any, e_best_any=E[best_any],
            bound_vs_default=1 - E["inf"] / d,                      # most any memory policy could save
            found_vs_default=1 - E[best_any] / d,                   # best policy we found
            adaptive_vs_default=1 - E["adaptive"] / d,
            adaptive_vs_best_fixed=1 - E["adaptive"] / fixed[best_fixed],
            oracle_vs_best_fixed=1 - E["oracle"] / fixed[best_fixed],
            value_vs_default=1 - E["value"] / d, value_exact_vs_default=1 - E["value_exact"] / d,
            retention_value=1 - d / E["drop"],      # what keeping state is worth vs dropping it at every wait
            compress_vs_default=1 - E["compress"] / d,
            default_fail_share=g["default"]["fail_share"], inf_fail_share=g["inf"]["fail_share"],
            default_slow_p95=g["default"]["slow_p95"], adaptive_slow_p95=g["adaptive"]["slow_p95"],
            inf_slow_p95=g["inf"]["slow_p95"],
            default_reprefill=g["default"]["reprefill_tok"], default_retract=g["default"]["retract_tok"],
            default_busy=g["default"]["busy_share"], default_batch=g["default"]["mean_batch"],
            policies=g))
    return cells


def main(what="all"):
    OUT.mkdir(parents=True, exist_ok=True)
    out = {}
    if what in ("validate", "all"):
        out["validation"] = validate()
    if what in ("grid", "all"):
        rows = grid()
        out["cells"] = summarize(rows)
        out["meta"] = dict(horizon_s=HORIZON, warm_s=WARM, seeds=SEEDS, ns=NS,
                           scenarios=[dict(name=s, device=d, layout=l, workloads=w, budgets_gib=b)
                                      for s, d, l, w, b in SCENARIOS],
                           layouts={k: vars(v) for k, v in LAYOUTS.items()},
                           sglang_reserve=dict(ratio=SGLANG_RATIO, clip=SGLANG_CLIP),
                           workloads={k: dict(name=_workload(k).name, missions=len(_workload(k).missions),
                                              shared=_workload(k).shared,
                                              success=sum(m.success for m in _workload(k).missions) / len(_workload(k).missions))
                                      for k in workloads()})
    (OUT / "sim.json").write_text(json.dumps(_round(out), separators=(",", ":"), default=float))
    return out


def _round(x, sig=4):
    if isinstance(x, float):
        return float(f"{x:.{sig}g}") if math.isfinite(x) else None
    if isinstance(x, dict):
        return {k: _round(v, sig) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_round(v, sig) for v in x]
    return x


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")

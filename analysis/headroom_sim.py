"""Trace-driven headroom estimate: N concurrent agent sessions sharing one KV pool.

Replays single-session traces (LLM calls and tool waits, measured with no memory
pressure) as N closed-loop session slots on one GPU, and compares retention policies at a
fixed KV budget. It is a memory-and-energy model, not an engine model:

- An LLM call needs its whole context (prompt + output) resident while it runs. Its
  duration is the measured duration plus the prefill of any reusable tokens that were
  dropped while the session waited (at the calibrated cold-prefill rate).
- Between calls a session may keep its context resident, or not (policy).
- When a call needs memory, the policy chooses which waiting sessions to drop. If the
  active calls alone leave no room, the call queues (FCFS) until memory frees up.
- GPU energy = active power while at least one call runs + idle power otherwise. This
  matches the WS calibration (power is ~flat from batch 1 to 16, so overlapping calls
  share it) and ignores the small per-step slowdown from batching.

Policies:
  lru   drop the least-recently-used waiting session first (the shape of SGLang's default)
  drop  drop a session's state at every tool start (discard-on-pause)
  keep  never drop waiting state; calls queue until memory frees (pin-until-resume), with
        a deadlock guard that drops LRU state when nothing else can make progress
  eta   drop the waiting session that will resume last (needs the remaining tool time,
        which a gateway that proxies the tool knows exactly for a paced flight)

Usage: python3 -m analysis.headroom_sim
"""
from __future__ import annotations

import heapq
import json
import statistics as st
from dataclasses import dataclass, field
from pathlib import Path

from analysis.sessions import REPO, load_aerogen

POLICIES = ["lru", "drop", "keep", "eta"]


@dataclass
class Step:
    kind: str          # "call" or "wait"
    dur: float         # measured duration (s)
    ctx: int = 0       # tokens resident during the call (prompt + completion)
    reusable: int = 0  # prompt tokens served from cache in the measured run


def to_steps(s) -> list[Step]:
    steps = []
    for i, c in enumerate(s.calls):
        steps.append(Step("call", c["t1"] - c["t0"], c["prompt"] + c["completion"], c["cached"]))
        if i + 1 < len(s.calls):
            steps.append(Step("wait", max(0.0, s.calls[i + 1]["t0"] - c["t1"])))
    return steps


@dataclass(eq=False)
class Sess:
    slot: int
    steps: list
    t_start: float
    i: int = 0
    held: int = 0
    last_use: float = 0.0
    resume_at: float = 0.0
    reprefill_tok: int = 0
    queued_s: float = 0.0
    q_since: float = 0.0
    t_end: float = 0.0
    failed: bool = False


def share_prefix(traces, shared):
    """Sessions share the first `shared` prompt tokens (system prompt + tool schemas), which
    the radix cache stores once and every call touches, so it never becomes an eviction
    victim. Only the private suffix competes for the rest of the pool."""
    out = []
    for steps in traces:
        out.append([Step(x.kind, x.dur, max(0, x.ctx - shared), max(0, x.reusable - shared))
                    if x.kind == "call" else x for x in steps])
    return out


def simulate(traces, n, pool, policy, prefill_tok_s, active_w, idle_w, total_missions,
             shared=0, stagger_s=20.0, seed=0, shuffle=True):
    import random
    rng = random.Random(seed)
    traces = share_prefix(traces, shared)
    pool = pool - shared
    order = list(range(len(traces)))
    if shuffle:
        rng.shuffle(order)
    per_slot = [total_missions // n + (1 if k < total_missions % n else 0) for k in range(n)]
    events, seq = [], [0]
    active: dict = {}          # Sess -> tokens resident during its call
    waiting: set = set()       # Sess between calls (may hold state)
    queue: list = []           # Sess whose next call is waiting for memory (FCFS)
    done, intervals = [], []
    started = [0] * n
    nxt = [0]
    forced = [0]

    def push(t, kind, s):
        seq[0] += 1
        heapq.heappush(events, (t, seq[0], kind, s))

    def used():
        return sum(active.values()) + sum(x.held for x in waiting)

    def can_start(s):
        ctx = s.steps[s.i].ctx
        if policy == "keep":
            return pool - used() + s.held >= ctx
        return pool - sum(active.values()) >= ctx   # every other waiter can be dropped

    def start_call(s, t):
        step = s.steps[s.i]
        own = s.held
        waiting.discard(s)
        s.held = 0
        deficit = step.ctx - (pool - used())
        if deficit > 0:
            order = sorted(waiting, key=lambda x: -x.resume_at) if policy == "eta" \
                else sorted(waiting, key=lambda x: x.last_use)
            for v in order:
                if deficit <= 0:
                    break
                if v.held:
                    deficit -= v.held
                    v.held = 0
        missing = max(0, step.reusable - own)
        s.reprefill_tok += missing
        dur = step.dur + missing / prefill_tok_s
        active[s] = step.ctx
        intervals.append((t, t + dur))
        push(t + dur, "call_end", s)

    def request_call(s, t):
        if s.steps[s.i].ctx > pool:
            # The call cannot fit even alone (SGLang rejects it): the mission fails here.
            waiting.discard(s)
            s.held, s.failed, s.t_end = 0, True, t
            done.append(s)
            if started[s.slot] < per_slot[s.slot]:
                new_mission(s.slot, t)
            drain(t)
            return
        if not queue and can_start(s):
            start_call(s, t)
        else:
            s.q_since = t
            queue.append(s)

    def drain(t):
        while queue and can_start(queue[0]):
            s = queue.pop(0)
            s.queued_s += t - s.q_since
            start_call(s, t)

    def new_mission(slot, t):
        s = Sess(slot, traces[order[nxt[0] % len(order)]], t_start=t)
        nxt[0] += 1
        started[slot] += 1
        request_call(s, t)

    for k in range(n):
        push(k * stagger_s, "mission_start", k)
    t = 0.0
    while events or queue:
        if not events:
            # Deadlock guard (only reachable under "keep"): drop LRU waiting state.
            victims = sorted((x for x in waiting if x.held), key=lambda x: x.last_use)
            if not victims:
                raise RuntimeError("stuck with nothing to drop")
            victims[0].held = 0
            forced[0] += 1
            drain(t)
            continue
        t, _, kind, s = heapq.heappop(events)
        if kind == "mission_start":
            new_mission(s, t)
            continue
        if kind == "call_end":
            ctx = active.pop(s)
            s.i += 1
            s.last_use = t
            if s.i >= len(s.steps):
                s.t_end = t
                done.append(s)
                if started[s.slot] < per_slot[s.slot]:
                    new_mission(s.slot, t)
            else:
                wait = s.steps[s.i]
                s.i += 1
                s.held = 0 if policy == "drop" else ctx
                s.resume_at = t + wait.dur
                waiting.add(s)
                push(t + wait.dur, "wait_end", s)
            drain(t)
        else:
            request_call(s, t)

    busy, c0, c1 = 0.0, None, None
    for a, b in sorted(intervals):
        if c1 is None or a > c1:
            if c1 is not None:
                busy += c1 - c0
            c0, c1 = a, b
        else:
            c1 = max(c1, b)
    if c1 is not None:
        busy += c1 - c0
    energy = busy * active_w + (t - busy) * idle_w
    m = len(done)
    ok = [x for x in done if not x.failed] or done
    return dict(policy=policy, n=n, pool=pool + shared, shared=shared, missions=m, span_s=t,
                failed=sum(x.failed for x in done),
                missions_per_hour=len(ok) / t * 3600, energy_per_mission_j=energy / len(ok),
                reprefill_tok_per_mission=sum(x.reprefill_tok for x in done) / m,
                queued_s_per_mission=sum(x.queued_s for x in done) / m,
                mission_s_p50=st.median(x.t_end - x.t_start for x in ok),
                busy_share=busy / t, forced_drops=forced[0])


def shared_prefix_estimate(sessions, margin=150):
    """Longest prompt prefix common to all sessions ~ shortest first-call prompt minus the
    task text and template tail (`margin` tokens, conservative)."""
    return max(0, min(s.calls[0]["prompt"] for s in sessions) - margin)


def main(run="e1_low_n1", pools=(25427,), ns=(1, 2, 4, 8, 16), total=None, shared=None):
    data = json.loads((REPO / "reports/2026-10-01-workload-opportunity/report_data.json").read_text())
    cal = data["ws_calibration"]
    rate, idle_w = cal["prefill_tok_s"], cal["idle_w"]
    active_w = st.mean(d["avg_power_w"] for d in cal["decode"])
    sessions = [s for s in load_aerogen(REPO / "data/ws_runs" / run, run, rate) if s.success is not None]
    traces = [to_steps(s) for s in sessions]
    total = total or 4 * len(traces)
    shared = shared_prefix_estimate(sessions) if shared is None else shared
    print(f"shared prefix estimate: {shared} tokens")
    print(f"{len(traces)} traces from {run}; {total} missions per config; active {active_w:.0f} W, "
          f"idle {idle_w:.0f} W, prefill {rate:.0f} tok/s")
    rows = []
    for pool in pools:
        for n in ns:
            for policy in POLICIES:
                r = simulate(traces, n, pool, policy, rate, active_w, idle_w, total, shared=shared)
                rows.append(r)
                print(f"pool={pool} N={n} {policy:<4} missions/h={r['missions_per_hour']:6.1f} "
                      f"J/mission={r['energy_per_mission_j']:7.0f} reprefill/mission={r['reprefill_tok_per_mission']:7.0f} "
                      f"queued/mission={r['queued_s_per_mission']:6.1f}s p50={r['mission_s_p50']:6.0f}s "
                      f"busy={r['busy_share']:.2f} forced={r['forced_drops']}")
    out = REPO / "reports/2026-10-01-workload-opportunity/headroom_sim.json"
    out.write_text(json.dumps(rows, indent=1))
    return rows


if __name__ == "__main__":
    main()

# P5 thesis: draft for discussion (TH-1)

**14 Oct 2026, draft 1.** It is built on the energy waterfall
([`../reports/2026-10-14-waterfall/README.md`](../reports/2026-10-14-waterfall/README.md)) and follows ENERGY_PLAN §3–§5.
Sandesh and the mentor decide whether to adopt it; nothing in it is agreed yet.

## The claim, in one paragraph

On edge boards, an LLM agent's energy per successful task is set by two things the serving system controls but never
looks at.

**What P1's logs show** (25 edge configurations, board energy):
- **Work spent on episodes that fail:** runs that fail take 13–98% of board energy (median 69%).
- **Decoding one request at a time:** inside passing runs it costs up to 36% more than decoding 4 at once.
- **Fixed settings capture only part of each:**
  - a stop rule tuned per configuration;
  - packing several agents on one board.

  The best fixed setting differs by model, task and load. It leaves at least 15% of energy per success between itself
  and the oracle in 24 of 25 configurations.

**What P5 proposes:** a serving layer that estimates, while each episode runs, how likely it is to succeed, and uses
that estimate to spend the board's scarce capacity: batch slots and KV memory. It would:
- stop or rescue episodes headed for failure;
- give capacity first to episodes likely to succeed;
- spend spare width on candidate answers when the board is lightly loaded.

## Why a fixed setting cannot do this (Q1)

The value of letting an episode continue depends on two quantities that change while it runs:
- **Its chance of success.** It falls as it loops, repeats capped calls, retries, or approaches the window.
- **The value of the capacity it holds.** That is near zero on an idle board, and high when other agents wait or the
  pool is full.

A fixed energy budget or a fixed number of agents tracks neither. P1's logs already show the first half:
- **The best rule varies:** the best stop rule that keeps the pass rate is a warning sign in some configurations and an
  energy budget in others. Its multiple ranges from 1.5× to 12× a passing run's median.
- **One rule underperforms:** the single rule that keeps the pass rate everywhere often gives far less than the
  per-configuration best.
- **P1 itself:** P1's paper concludes from its offline attempt budgets that "reductions require task-specific
  decisions".

The second half, load, is absent from P1's logs, because P1 ran one agent per board.

## Why it matters on an edge board

- **Small windows turn capacity into failure.** On the Orins, 19–28% of granite and gemma-26B traffic runs end in a
  window overflow.
  - The overflow happens in one jump: a single tool output, a median 10.5K tokens, pushes the next request past a
    26,624- or 12,288-token window.
  - The serving layer sees it coming the moment the tool returns.
- **One-at-a-time decoding is the least efficient point on a Jetson.** Energy per token at 4 requests is 0.45× (Thor,
  26B) and 0.26× (Orin 32, dense models) that of one request.
  - A doomed 32K-token call holds a Thor's decoder for about 20 minutes.
- **No host tier, and energy is the budget.** Unified memory has nothing to spill to.

## The mechanism (sketch)

1. **Online success estimate per episode.** It uses signals the serving layer already sees:
   - repetition (the loop detector);
   - consecutive capped calls;
   - context headroom against the window;
   - repeated or failing tool calls;
   - energy spent against the task's history.
2. **Actions, chosen by the estimate and the board's load:**
   - **stop:** end the episode early;
   - **rescue:**
     - resample a looping call;
     - fit an oversized tool output into the window instead of failing;
     - hand the task to a stronger model;
   - **schedule:** give batch slots and KV to the episodes most likely to succeed;
   - **widen:** run k candidate answers for an at-risk step when the board has spare width. This is the mentor's
     first-of-k.
3. **Objective:** board energy per success, at an unchanged pass rate, at each load.

## The baseline it must beat (B*)

- P1 as run;
- plus model-card sampling;
- plus the best fixed stop rule per configuration;
- plus the best fixed number of agents per box, with FP8 KV where the pool binds;
- plus, for comparison, P1's attempt budget and a Continuum-style program-aware scheduler.

## What we have, and what is missing

| Question | Status | Where |
| --- | --- | --- |
| Is failure the biggest bucket? | Yes in 22 of 25 configurations (median 69%); P1's headline too | waterfall |
| Can a fixed rule capture it? (Q1) | Partly; the best rule varies by configuration | `stop_bounds.json` |
| Is there room beyond B*? (Q2 bound) | ≥ 15% to the oracle in 24 of 25, an upper bound | `stop_bounds.json` |
| Can an online estimate capture that room without losing passes? | **Not tested.** Next: a predictor on P1's logs, trained and scored on different tasks | WF-3b |
| Do rescues turn failures into passes? | Partly: on a 4-bit stand-in, one resample recovered 17 of 17 looping calls (A-E2). The mentor's banks show sampled programs pass on hard prompts. Overflow rescue is not tested | live traffic agent (TRF-3) |
| Does success-aware capacity beat fixed packing under load? | **Not tested.** Next: the simulator driven by P1's episodes and the measured cost curves, then a live fleet | WF-4 (new) |

## Overlaps and risks

- **P1 owns the observation and the offline policies.**
  - The observation: failed runs consume most energy.
  - The offline policies: attempt budgets and step cutoffs.
  - P5's part would be the online, capacity-aware mechanism with several agents per board. P1 has no multi-agent
    result. The split must be agreed with P1.
- **Prior work to position against:**
  - AgentStop (energy-motivated early stop of local agents);
  - Fail-Fast Restart-Smart (stop and restart);
  - Continuum and Autellix (program-aware scheduling, latency);
  - KAIROS (energy).

  The novelty has to be the combination: online success estimation driving capacity decisions on a unified-memory
  edge board, judged by energy per success.
- **The oracle gap may not be predictable.** Failures may only show after most of their energy is spent. WF-3b
  answers this first. If an online estimate captures less than 15% beyond B*, the stop and rescue part weakens. What
  remains is the capacity and widening part (the mentor's first-of-k), or the fallback, a limit study.
- **Gaming the metric:** refusing hard tasks lowers energy per success. Every result keeps the pass rate fixed (at
  most 5% of passes lost, as in WF-3).

## Decisions this draft needs

1. **Sandesh and the mentor:** adopt this shape, or keep the mentor's 13 Oct framing (first-of-k with load-elastic k) as
   the core, with this as its success model?
2. **With P1 (through Sandesh):** the split.
   - P1 keeps the measurement and the offline policies.
   - P5 takes the online, multi-agent mechanism.
3. **The professor, at the next meeting:** is "success-aware capacity allocation on edge boards" the proposal he was
   asking for?

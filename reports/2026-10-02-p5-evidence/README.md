# JouleServe (P5): drone workload evidence and options

**2026-10-03 · Sai Sandesh (P5)**, prepared with Claude Code.

This is the repo copy of the Claude Doc
[JouleServe (P5): drone workload evidence and options](https://claude.ai/code/artifact/474eee56-2e2f-44f9-8b97-f7bb51b588c7),
which is private until Sandesh shares it.
- It merges three detailed reports, which remain the reference for methods:
  [`2026-10-01-workload-opportunity`](../2026-10-01-workload-opportunity/README.md),
  [`2026-10-01-p1-task-overview`](../2026-10-01-p1-task-overview/README.md) and
  [`2026-10-02-stepwise-d1`](../2026-10-02-stepwise-d1/README.md).
- The doc's two charts appear here as a table and a figure.
- It was fact-checked against the sources on 2026-10-02, and updated on 2026-10-03 with the
  many-drones simulation and P1's refreshed tool-calling sweep
  ([`2026-10-03-admission-sim`](../2026-10-03-admission-sim/README.md)).

P1's drone agents, as built today, leave an edge serving system almost no retained state to
manage: keeping it could save at most 2.1% of their LLM time. A step-wise agent on P1's own
delivery tasks does create state worth keeping. But a simulation of 1–16 drones per box
(2026-10-03) shows that SGLang's default already keeps it: no memory policy beats the default by
more than about 10% of energy per successful mission.

The large levers are elsewhere. The agent design changes energy per success 5–13× on P1's
delivery tasks, and runaway thinking takes 57–70% of P1's LLM time. We now lean towards option
A, decode-side energy on P1's agents, with option B's finding reported to P1. The professor and
P1's mentor make that call.

## Summary

1. **P1's agents leave nothing to manage.**
   - They write a whole flight program per attempt, run it in one tool call, and start every
     LLM call from a fresh prompt.
   - Thinking decodes take 86–99% of their LLM time per task.
   - Pooled over all calls, any retention policy could save at most 2.1% (Reflexion, 143 runs)
     or 0.6% (tool calling, 104 runs) of it.
2. **The cause is the agent design, not the task.**
   - Bigger P1 tasks lower the ceiling, because they add thinking and 32K-capped calls (70% of
     tool-calling LLM time).
   - By the same mechanism, the large AeroEval missions P1 dropped should not change this under
     P1's agents. That is argued, not measured.
3. **A step-wise agent creates the opportunity.**
   - aerogen flies one action per tool call and keeps one growing conversation.
   - On its own tasks, 93% of prompt tokens came from cache, and kept state saved 33% of LLM
     time on the workstation.
4. **The deciding test passed.**
   - The test ran P1's own delivery tasks D1–D3: 108 missions with Qwen3.5-9B (thinking on and
     off) and K2-Horizon-7B (low and high effort).
   - Steps after a tool wait are short: median 55–99 output tokens, p90 ≤ 394.
   - Thinking concentrates in the first, planning call.
5. **Most of that value is the shared prompt.**
   - At the Thor's speeds, kept state could save 20–72% of a mission's LLM time, but each
     drone's private history is only 3–16% of it.
   - The rest is each mission's first prompt (9–11K tokens, mostly the system prompt every
     drone shares), which SGLang's radix cache already keeps.
6. **A memory controller does not beat SGLang's default.**
   - In a simulation of 1–16 drones per box, no policy beats the default by more than about 10%
     of energy per successful mission, short of the 15% bar.
   - Keeping state is worth 19–29% at 16 step-wise drones, but the radix cache already keeps it.
   - Under tight memory the loss is capacity, which no policy recovers.
7. **The agent design is the big lever.** On P1's delivery tasks a step-wise agent uses 5–13×
   less energy per success than P1's Reflexion agent, and one Thor serves 4–16 step-wise drones
   instead of 2.
8. **Runaway thinking is where P1's energy goes.**
   - On the 12 CLGSCE tasks, calls that hit the 32K cap take 57% (Reflexion) and 70% (tool
     calling) of LLM time, and none produced a usable answer.
   - On those tasks the tool-calling agent spends 2.9× Reflexion's energy per success.

**The most kept state could save** (P / (P + r·O) as a share of LLM time, at the Thor's r ≈ 67;
the doc's summary chart):

| Agent | Data | Ceiling | Of which: each drone's private history |
| --- | --- | --- | --- |
| P1 Reflexion | Thor, 143 runs | 2.1% | none (prompts rebuilt each call) |
| P1 tool calling | Thor, 104 runs | 0.6% | none (prompts rebuilt each call) |
| aerogen on its own tasks, K2-Horizon-7B low effort | WS, 15 missions | 50% | 13% |
| Step-wise on P1's D1: Qwen3.5-9B, no thinking, greedy | WS, 6 missions | 71% | 7.7% |
| Step-wise on P1's D1: Qwen3.5-9B, no thinking, sampled | WS, 9 missions | 68% | 10% |
| Step-wise on P1's D1: Qwen3.5-9B, thinking, sampled | WS, 9 missions | 53% | 11% |
| Step-wise on P1's D1: K2-Horizon-7B, low effort | WS, 9 missions | 49% | 9.9% |
| Step-wise on P1's D1: K2-Horizon-7B, high effort | WS, 9 missions | 36% | 16% |
| Step-wise on P1's D1: Qwen3.5-9B, thinking, greedy (one runaway) | WS, 6 missions | 20% | 2.9% |

- **What the symbols mean** (defined under
  [When kept state is worth anything](#when-kept-state-is-worth-anything)): P is the reused
  prompt tokens, O the output tokens, and r the cost of one output token over one prefilled
  token.
- **The private part** is what a retention policy decides about under memory pressure. The rest
  is the shared prompt, which the radix cache keeps once.
- **D1 only.** D2 and D3 give 42–72%.

## What P5 asks

P5 (JouleServe) asks how an edge LLM serving system should manage the state an agent session
holds while it waits for a tool. The goal is to minimise **energy per successful task** on
Jetson Orin and Thor.

- **The state:** the KV cache, plus the sliding-window or recurrent state of hybrid models such
  as Gemma-4 and Qwen3.8.
- **The choices:** keep it, drop it and recompute it later, offload or compress it, or change
  admission so that idle state does not block active work.
- **Where a contribution must come from:**
  - Generic "keep KV across tool pauses" is published: INFERCEPT, Continuum, TokenCake,
    Adaptive KV Retention and CacheScout, plus KAIROS for energy.
  - What the edge changes is still open: unified memory, shared bandwidth and power, thermal
    state, hybrid models, and physical tool waits of 10 s to 10 min.
- **Dependence on P1:**
  - P5 uses the devices and workloads of P1 (EdgeAgentBench: closed-loop drone and traffic
    tasks on Orin and Thor), and possibly P1's trajectory predictor.
  - The devices stay with P1 until its deadline, so P5 works on a 2×A5000 workstation ("the WS")
    in the meantime.

**Why prior work does not settle it.** P1's agents sit outside the regime the published
systems target, on both reuse and output length.

| | Published KV-retention systems | P1's drone agents |
| --- | --- | --- |
| Context | Grows across turns (ReAct, tool calling, chat) | Rebuilt for every role call |
| Output per call | Tens to hundreds of tokens, reasoning off | Thinking on, up to 32,768 tokens |
| Tool waits | Real tools take ms to ~2 s; long waits are injected (17 s to ~30 min) | Simulated flights: median 17 s (basic), 72 s (advanced), 113 s (AeroEval); up to ~15 min |
| Load | Tens to hundreds of concurrent sessions | One session per device |
| Hardware | Datacenter GPUs with host DRAM over PCIe | Jetson AGX Thor, unified memory |

## When kept state is worth anything

Keeping a paused session's state saves only the prefill of its next call. So the most any
retention policy can save on one call is:

```
saving ≤ P / (P + r · O)
```

- **P** is the prompt tokens of the next call that repeat state already cached. How the agent
  builds its prompts sets it.
- **O** is the output tokens of the next call, reasoning included. How much the model thinks
  sets it.
- **r** is the cost of one output token over one prefilled token.
  - On the Thor it is about 67: cold prefill runs at 1,811 tokens/s against decode at ~27
    tokens/s, for Gemma-4-26B-A4B in P1's traces.
  - On an A5000 it is about 108–127, depending on model and concurrency.
  - r is a time ratio at batch 1. Batching makes each decoded token cheaper, which lowers r and
    raises every ceiling; at batch 16 on the WS the energy ratio is about 8.

The task enters neither P nor O. It sets how many calls and waits there are, and how long each
wait lasts. On the Thor, re-prefilling a 20K-token context costs as much as decoding ~300
tokens.

**What counts as an opportunity.** Two things must hold:
- the best action changes with conditions a controller can observe (state size, wait length,
  memory pressure, reuse), within the realistic range;
- the best fixed rule, SGLang's default included, loses meaningfully to an adaptive one.

If the default already matches an oracle, a controller adds nothing.

In practice, kept state is worth managing only when four things hold together:

1. the context accumulates across tool calls, which means step-wise control;
2. there are many physical waits per mission, of tens of seconds to minutes;
3. each step's output is short, so prefill is a real share of LLM time;
4. memory is contended: several drones per device, or perception and simulator models sharing
   it.

How the workloads in this report meet those four conditions:

| Condition | P1's agents | aerogen on its own tasks | Step-wise agent on P1's D1–D3 |
| --- | --- | --- | --- |
| Context accumulates | No: prompts rebuilt per role call | Yes | Yes |
| Many physical waits | No: at most 3 flights per run | Yes: ~14 LLM calls per mission, 88% of mission time in flight | Yes: 13–22 LLM calls per mission |
| Short steps | No: median 538–3,406 output tokens per call | Yes: median 44 after a wait | Yes: median 55–99 after a wait |
| Memory contended | No: one session per device | Only with a capped pool | Not yet tested (at most 2 sessions) |

![A P1 session and an aerogen mission on one clock](../2026-10-01-workload-opportunity/figures/timelines.png)

- **Left:** a P1 Reflexion session is one long decode ramp and a short wait. The next call
  starts from a smaller, rebuilt prompt.
- **Right:** an aerogen mission holds a growing context through every flight leg, and each
  step appends a little to it.

## P1's drone workloads

P1's drone set is 16 tasks: 12 CLGSCE tasks in AirSim and 4 AeroEval tasks in Aerostack2 +
Gazebo. Each is run on 3 instances × 3 runs, which is 144 runs per model.

- **CLGSCE** (headless AirSim, deterministic validator):
  - basic: B5, B13, B29, B37 (runs of 1–3 min);
  - advanced: A3, A5, A6, A7, A8, A9, A16, A20, which are geometric patterns such as squares and
    figure-eights with 5–9 m legs.
- **AeroEval** (an LLM code validator, then a Gazebo flight check): D1 ordered three-stop
  delivery, D2 delivery via a checkpoint, D3 two out-and-back deliveries, F1 farm perimeter
  survey.

**The AeroEval family.**
- There are 5 original AeroEval missions. P1 wrote 6 variants on 2026-09-04, giving 9 distinct
  missions, of which P1 kept 4.
- I could not find a list of exactly 8.
- Flight times are estimates from the task text at 2 m/s, except D1's measured mission.

| Mission | Origin | In P1's sweep | Needs perception | Real flight time (est.) |
| --- | --- | --- | --- | --- |
| Ordered three-stop delivery | AeroEval delivery, P1 variant | D1 | no | ~13 min (P1's README: a ~770 s mission over a 645 m route) |
| Delivery via a checkpoint | P1 variant | D2 | no | ~5 min |
| Two out-and-back deliveries | P1 variant | D3 | no | ~10 min |
| Farm perimeter survey (14–26 m plot) | AeroEval farm survey | F1 | camera recording only | ~1 min |
| Farm lawnmower survey | P1 variant | no | no | ~15–20 min |
| Concentric circles (radii 75 to 30 m) | P1 variant | no | no | ~24 min |
| Radio towers: search 180 × 240 m, inspect each | AeroEval | no | tower detection | 20+ min |
| Powerline cable following | AeroEval | no | cable detection | open-ended |
| Search 8 × 4 m, then track a person | AeroEval | no | person detection and tracking | open-ended |

- **P1 kept the small missions** and dropped the large-area and perception ones.
- **P1's Gazebo stack** has worlds only for delivery and the small farm plot, and it runs at 10×
  real time.

**aerogen is related to AeroEval, but it is not P1's workload.**

| | AeroEval (the lab's original) | P1's AeroEval agent | aerogen_mcp (mayankarya) |
| --- | --- | --- | --- |
| What the model produces | One complete drone program | One complete Aerostack2 program per attempt | One tool call per flight action (20 tools) |
| Context across steps | Rebuilt per stage | Rebuilt per role call | One growing conversation |
| Tasks | 5 missions | D1–D3, F1 | 5 samples of its own, in the radio-tower world |
| Simulator | None (static validation) | Gazebo at 10× real time | Kinematic sim, or real Aerostack2 |

The mentor is right that aerogen's tasks are not P1's. Our aerogen runs measure the step-wise
paradigm; the deciding test below runs that paradigm on P1's own tasks.

## P1's agents as they run today

Any retention policy could save at most 0.3–14% of LLM time per task, and 0.3–3.2% on every
task longer than 10 minutes.
- **The bound** here is the measured prefill share of LLM time. It exceeds 4% only on the
  1–3-minute basic tasks.
- **What was actually saved:** the cache hits seen saved ≤ 0.9% per task class, and at most 2.1%
  on any one task (B37).
- **Data:** Thor traces of Gemma-4-26B-A4B on SGLang 0.5.16, one session at a time, cache
  flushed before each run, thinking on, up to 32,768 output tokens per call.

| Task | Reflexion: passed | Reflexion: min per run | Reflexion: bound | Reflexion: 32K-capped calls | Tool calling: passed | Tool calling: min per run | Tool calling: bound | Tool calling: 32K-capped calls |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B5 | 9/9 | 1.2 | 9.9% | 0 | 9/9 | 1.6 | 10.4% | 0 |
| B13 | 9/9 | 1.0 | 14.0% | 0 | 9/9 | 1.4 | 10.4% | 0 |
| B29 | 9/9 | 1.8 | 6.1% | 0 | 9/9 | 1.6 | 8.5% | 0 |
| B37 | 6/9 | 2.8 | 6.5% | 0 | 6/9 | 2.8 | 8.6% | 0 |
| A3 | 9/9 | 2.9 | 4.0% | 0 | 9/9 | 5.2 | 3.2% | 0 |
| A5 | 9/9 | 10.0 | 1.2% | 3 | 9/9 | 4.5 | 3.6% | 0 |
| A6 | 9/9 | 7.3 | 1.7% | 0 | 2/9 | 78.8 | 0.5% | 22 |
| A7 | 8/9 | 36.4 | 1.0% | 6 | 0/9 | 71.5 | 0.7% | 17 |
| A8 | 7/9 | 27.8 | 0.9% | 5 | 6/9 | 61.8 | 0.8% | 17 |
| A9 | 9/9 | 31.8 | 1.0% | 11 | 1/9 | 96.6 | 0.3% | 38 |
| A16 | 1/9 | 68.6 | 0.8% | 21 | 7/8 | 31.1 | 0.9% | 6 |
| A20 | 9/9 | 7.6 | 1.9% | 0 | 3/6 | 102.4 | 0.3% | 27 |
| D1 ordered delivery | 5/9 | 67.5 | 2.2% | 22 | not in sweep | | | |
| D2 checkpoint | 3/8 | 19.5 | 3.2% | 2 | not in sweep | | | |
| D3 out-and-back | 0/9 | 57.0 | 2.3% | 18 | not in sweep | | | |
| F1 farm survey | 0/9 | 72.6 | 2.1% | 27 | not in sweep | | | |

- **Reflexion:** P1's final sweep, 143 of 144 runs. One D2 run is missing from our copy.
- **Tool calling:** 104 of the 108 runs of P1's sweep (the 12 CLGSCE tasks, 3 instances × 3
  runs; the last 4 were still running), as of 2026-10-03 16:16.

**Why the bound is so small:**

- **P is small.**
  - Each attempt writes the whole flight program, and one tool call executes it.
  - Every role call (generator, evaluator, reflector) starts a new prompt.
  - Only 0–53% of prompt tokens come from cache, and the high end is mostly a retry of the same
    prompt.
- **O is large.** Thinking decodes take 71–94% of session wall time and 86–99% of LLM time per
  task. A generator call writes a median of ~8K tokens.
- **Bigger tasks make it worse.**
  - In the tool-calling sweep, 127 of 571 LLM calls hit the 32K cap. Those calls take 70% of
    all LLM time (43.0 of 61.1 h), and 30 of the 34 failures include one.
  - In Reflexion, 115 of 1,030 calls hit the cap.
- **The AeroEval runs rarely fly.** D1 flew 8 times in 9 runs and F1 never did, because the LLM
  code validator rejected the programs first.
- **There is no memory pressure.**
  - There is one session per device, and its context (≤ 55K tokens) fits P1's 80K-token pool,
    so keeping everything is free.
  - Concurrency does not change the picture either: in simulation with 1–16 drones per Thor,
    P1's agents gain at most 1.6% from kept state (see
    [Many drones on one box](#many-drones-on-one-box-does-a-memory-controller-help)).

**One anomaly to check on the devices.**
- In the Reflexion runs, most same-role calls that repeat an earlier prompt missed the cache:
  73 of 116 for advanced tasks and 105 of 182 for AeroEval. These misses often came right after
  a 32K decode.
- Our guess is that Gemma's sliding-window state is lost after long decodes, a hybrid-model
  effect.
- It costs 0.3–1.1% of LLM time.

**P1's two agents on the same 12 CLGSCE tasks** (Thor, measured): the tool-calling agent spends
2.9× the energy per success of Reflexion, and runaway thinking is the reason.

| | Reflexion | Tool calling |
| --- | --- | --- |
| Runs, passed | 108, 94 (87%) | 104, 70 (67%) |
| Board energy per run / per success | 69 / 79 kJ | 155 / 231 kJ |
| Long advanced tasks (A6–A9, A20): passed, median time | 42 of 45, 10 min | 12 of 42, 87 min |
| Calls that hit the 32K cap | 46 of 403, 57% of LLM time | 127 of 571, 70% of LLM time |
| Had those calls stopped at 16K tokens | 27% less board energy | 34% less board energy |

- Every capped call ended at the token limit, so none produced a usable answer.
- The last row is an upper bound from the traces: the decode time those calls spent past 16K
  tokens, at the board's 71.9 W, assuming the rest of each run goes as recorded. A fixed 16K
  cut would also stop 14 (Reflexion) and 32 (tool calling) calls that finished on their own.

## Step-wise agents (1): aerogen on its own tasks

aerogen_mcp flies one action per tool call (takeoff, go_to_point, hover, run_inference and 16
more) and keeps one growing conversation per mission.
- We ran it on the WS on 2026-10-01 with K2-Horizon-7B, its kinematic sim paced to real flight
  time.
- The agent logic is unchanged. We added a 6-line pacing hook.
- At runtime we removed the random prompt prefix the agent adds to defeat cloud caching. Every
  concurrency result depends on that removal.

**One session** (low effort, 15 missions):
- 88% of mission time is waiting on flights, and 93% of prompt tokens come from cache.
- 29% of the GPU energy is drawn while no call runs: about 10 W between calls against 181 W
  during them.
- Kept state saved 33% of LLM time: 12% from each mission's private history, the rest from the
  9.1K-token system prompt all sessions share. At the Thor's r the ceiling would be 50% (13%
  private).
- Medium and high effort used 2.3–2.5× the GPU energy per mission. Their contexts reached a
  median peak of 17–19K tokens, and one task's outgrew the one-GPU pool.

**Many sessions on one GPU.**
- The runs were live, at low effort, with 10–15 missions per run and one run per
  configuration.
- Energy is GPU energy from NVML.
- 1, 2 and 4 sessions ran on GPU1; 8 sessions and the capped pools ran on GPU0.

| Sessions on one GPU | Completed / errored / passed | GPU energy per completed mission | GPU energy per passed mission | Missions per hour | Re-prefilled tokens per mission |
| --- | --- | --- | --- | --- | --- |
| 1 | 15 / 0 / 11 | 20.4 kJ | 27.8 kJ | 5.4 | ~0 |
| 2 | 7 / 3 / 6 | 34.3 kJ | 40.0 kJ | 6.9 | 3.2K |
| 4 | 14 / 1 / 9 | 20.5 kJ | 31.9 kJ | 17.5 | 4.8K |
| 8 | 14 / 1 / 11 | 9.9 kJ | 12.6 kJ | 30.9 | 1.8K |
| 4, pool capped at 16.4K | 12 / 3 / 6 | 22.4 kJ | 44.8 kJ | 17.8 | 20.5K |
| 4, pool capped at 13.3K | 10 / 5 / 7 | 22.4 kJ | 32.0 kJ | 17.9 | 10.6K |

- **Eight sessions used 2.2× less GPU energy per passed mission than one** (27.8 to 12.6 kJ), at
  the same median mission time.
  - They ran on different GPUs, and GPU0 (8 sessions) idles higher than GPU1 (1 session).
  - So the comparison is, if anything, conservative.
- **Live energy swings with the missions drawn.**
  - The 2- and 4-session runs drew long missions, some of which outgrew the pool.
  - Replaying the same missions at every N, the simulator shows 2.5–3.5× less energy from 1 to
    16 sessions.
- **The KV budget bounds the gain.**
  - On the full 25.4K-token pool, the shared prompt kept pressure low.
  - Capping the pool at 16.4K brought queueing and 20.5K re-prefilled tokens per mission.
  - Missions whose context outgrows the pool fail at any concurrency.

![Simulated energy per mission against sessions per GPU, by policy](../2026-10-01-workload-opportunity/figures/headroom.png)

**What the simulation says about policies.**
- **How far to trust it:**
  - replaying each live run's own missions, its memory model lands within 7–25% of live
    re-prefill at 2 and 4 sessions, and 2× low at 8 sessions, where re-prefill is small;
  - its energy is within −23% to +38% of the live runs;
  - the chart and the policy results replay a fixed sample (the 15 single-session missions), so
    read them as rankings, not levels.
- **The results:**
  - dropping state at every wait costs 6–11% more energy than LRU on the full pool;
  - keeping all state until resume stalls missions: 44 min instead of 10 at 8 sessions;
  - an eviction oracle that knows exact flight times is no better than LRU (within 0–6%).

So eviction order is not a contribution: SGLang's default already gets most of the value.
Admission was simulated on 2026-10-03 and does not beat the default either (see
[Many drones on one box](#many-drones-on-one-box-does-a-memory-controller-help)).

## Step-wise agents (2): the deciding test on P1's delivery tasks

A step-wise agent on P1's own tasks keeps its steps short in every configuration tested: after
a tool wait, the model writes a median of 55–99 output tokens. The rule was set before the
test:
- a few hundred tokens, and option B holds;
- thousands, and it does not.

**Setup** (WS, 2026-10-02):

- **Agent:** aerogen's agent loop, unchanged. It was given P1's D1–D3 task texts verbatim (3
  instances each, with P1's node remaps) and the delivery-world and navigation files that P1's
  AeroEval agent uses.
- **Models:**
  - Qwen3.5-9B (hybrid: 8 full-attention and 24 linear-attention layers), thinking on and off,
    with greedy decoding (P1's protocol, temperature 0) and with the model card's sampling;
  - K2-Horizon-7B at low and high reasoning effort.
- **Missions:** 108, on the kinematic sim at 50× real time. Token counts do not depend on
  pacing.
- **Strict checker,** using P1's Gazebo geometry:
  - stops visited in order;
  - a descent and a 10 s hold at each stop;
  - no flight through a building below its 20 m roof.

![Output tokens per call](../2026-10-02-stepwise-d1/figures/output_per_step_cdf.png)

- **Under the 300-token line:** in every D1 configuration, 90–98% of the steps after a tool wait
  stay under it. The thinking goes into the one planning call before the first flight.
- **What the curves count:** the P1 curves count all of P1's calls; the step-wise curves count
  only the calls after a tool result.

**D1, per configuration:**

| Configuration | Missions | Delivered all / strict pass | LLM calls per mission | Planning call: longest output | Prompt: first → peak (median) | Prompt reuse | Ceiling after a wait (Thor r) | Ceiling on the WS (mission) | Measured saving on the WS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3.5-9B thinking, greedy (P1's protocol) | 6 | 2 / 0 | 13.7 | 24,236 (runaway) | 11.3K → 18.0K | 92% | 57% | 13% | 11% |
| Qwen3.5-9B thinking, sampled | 9 | 6 / 2 | 21.6 | 1,998 | 11.3K → 17.6K | 96% | 57% | 37% | 34% |
| Qwen3.5-9B no thinking, greedy | 6 | 4 / 0 | 20.0 | 28 | 11.3K → 15.7K | 94% | 71% | 58% | 53% |
| Qwen3.5-9B no thinking, sampled | 9 | 7 / 5 | 21.7 | 97 | 11.3K → 15.7K | 96% | 67% | 53% | 48% |
| K2-Horizon-7B high effort | 9 | 5 / 5 | 17.8 | 12,159 | 9.4K → 18.3K | 82% | 72% | 24% | 14% |
| K2-Horizon-7B low effort | 9 | 6 / 4 | 15.1 | 2,178 | 9.4K → 12.9K | 97% | 62% | 35% | 33% |

The measured saving sits 1–9 points under the WS ceiling in every configuration, which checks
the ceiling against what the cache actually did.

**What the test shows:**

- **Steps after a wait are short everywhere.**
  - Over D1–D3 the median is 55–99 tokens, and the p90 is at most 394.
  - Only 17 of 1,649 such steps exceed 1K tokens: 6 are final mission summaries, the rest
    mid-mission re-plans.
- **Thinking concentrates in the planning call.**
  - Before the drone moves, the model plans the whole mission.
  - With thinking on, that call writes a median of 546–5,147 tokens (21–82% of all output);
    without thinking, 28.
  - K2's long plans are genuine (waypoints, tool order), not loops.
- **Greedy thinking can run away.**
  - One greedy planning call ran to 24K tokens and filled the KV pool, so both greedy missions
    of that instance never flew. This is the same failure mode as P1's capped calls.
  - Qwen3.5 thinking with sampling showed no runaway in 21 missions; its longest planning call
    was 3,816 tokens.
- **What kept state is worth**, at the Thor's r:
  - 56–72% of the LLM time after a wait, and 20–72% of a mission's.
  - Each drone's private history is 3–16% of a mission's LLM time, or 6–33% of the post-wait
    time.
  - K2 at high effort has the most, because its long plan stays in the conversation.
- **Flights would dominate a mission.** At the Thor's speed with nothing kept, a drone would be
  flying for 49–85% of its mission. This is a projection from the sim clock and the token
  counts.
- **A thinking budget would complement retention.** The planning call carries most of the
  decode, so option A's lever (a budget for long thinking) applies here too.
- **The hybrid model reuses its state.** Qwen3.5's cache reused both KV and recurrent state
  across steps: 92–96% of prompt tokens came from cache.
- **The agent is not mission-ready in P1's world.**
  - 72% of missions delivered every package, but only 27% pass the strict check.
  - 56% collide, because the sim has no buildings and the model flies diagonals through them.
  - Token counts are unaffected, but a building-aware sim comes first if B is chosen.
- **D2 and D3 agree** (60 more missions): post-wait medians of 55–99 tokens and mission
  ceilings of 42–72%.

## Many drones on one box: does a memory controller help?

No. In a simulation of 1–16 drones sharing one box, no memory policy beats SGLang's default by
more than about 10% of energy per successful mission, short of the 15% bar suggested on
2026-10-02. This answers the open hypothesis left by the aerogen runs.

**Setup** (2026-10-03, [`2026-10-03-admission-sim`](../2026-10-03-admission-sim/README.md)):

- **Workloads:** recorded missions replayed by N drones, each starting a new mission when one
  ends: the step-wise D1–D3 runs, aerogen's own tasks, and P1's Reflexion and tool-calling
  traces.
- **Thor costs** from P1's runs: prefill 1,811 and decode 27 tokens/s; board power 71.9 W while
  a call runs and 38.6 W otherwise. Gemma's experts make batching weak: a 16-request decode step
  takes about 5.3× as long as one.
- **Memory:** state budgets of 1–16 GiB in Gemma's layout (20 KiB per token plus a 200 MiB
  sliding window per session), with Qwen3.5 and dense layouts as checks. 12 policies, unlimited
  memory as the bound, 5 seeds per point.
- **Validation:** LLM time within 2–3% of 887 Thor calls; energy per mission within −8% to +10%
  of the five live WS runs with 2–8 sessions.

![Default against the best policy and unlimited memory](../2026-10-03-admission-sim/figures/headroom.png)

The doc's chart shows the top row of this figure (step-wise Qwen3.5 thinking).

**What the policies recover** (best case on the Thor, Gemma layout; the gap to unlimited memory
reaches 60% at 1 GiB and 16 drones):

| Policy | Best gain over the default |
| --- | --- |
| Eviction order by value per byte, online | 3% (6% with exact wake times) |
| Budget-aware admission | 5% for step-wise agents; up to 52% worse on P1's long decodes |
| Concurrency caps of 1–8 calls | 0.2% |
| Paused state stored at half size | 10% |
| FP8 KV cache for all state (a configuration) | 10–34% at 1–4 GiB |

- **Keeping state matters more as the box fills, but the default already keeps it.**
  - Dropping state at every wait costs step-wise agents 4–7% more energy per success with one
    drone, and 19–29% more at 16.
  - With 8 GiB for state, the default matches unlimited memory up to 16 step-wise drones (P1's
    agents need 16 GiB).
- **P1's agents gain nothing from kept state** at any drone count (0–1.3%), and at most 1.6%
  even with dense-model batching. The earlier estimate that batching could lift their ceiling to
  about 15% does not hold.
- **On the Thor, decode throughput binds before memory.** P1's agents keep it 94–98% busy with
  one drone; step-wise agents saturate it at about 8.
- **Realistic budgets:** a Thor running Gemma in bf16 has tens of GB free (P1's runs used 75 GB
  in total), which is ample. Tight budgets mean an Orin 64 GB with Gemma in bf16, or dense-KV
  models.

**The agent design is the big lever** (Thor costs; the first three rows are P1's D1–D3 only):

| | P1 Reflexion (measured) | Step-wise agent (projected) |
| --- | --- | --- |
| Board energy per run | 82–277 kJ | 20–43 kJ |
| Board energy per success | 219–499 kJ (D3: no passes) | 22–68 kJ |
| Median mission time | 19–72 min, 91–97% of it LLM | 9–15 min |
| Drones per Thor within 1.5× p95 mission time | 2 | 4–16 |
| Energy per success, 1 → 16 drones | 3.1–3.2× lower | 4.7–8.5× lower |

The two sides differ in models (Gemma against the Qwen3.5 and K2 stand-ins), simulators and
success checks. P1's Gazebo flights run at 10× real time, which only flatters P1's side.

**Not tested yet:** longer missions, memory that changes over time (co-located models), Gemma's
own step-wise token counts, mixed agents on one box, and power modes. The simulated default also
loses less under pressure than live SGLang, which understates headroom by a few percent at most.

## Serving costs and what changes on the edge

Decode is the energy sink and batching is the lever.
- On one A5000, decode energy per output token falls 14× from 1 to 16 concurrent requests,
  while GPU power stays near 205 W.
- Memory held by paused sessions cannot hold more concurrent decodes.

| Quantity | Measured on the WS (one A5000, SGLang 0.5.20) |
| --- | --- |
| K2-Horizon-7B cold prefill | 4,106 tokens/s at 8–20K tokens, ≈ 0.05 J per token |
| The same prompt fully cached | 0.10–0.16 s to first token |
| K2-Horizon-7B decode energy per output token | 5.36 J at batch 1 (38 tokens/s); 0.38 J at batch 16 (539 tokens/s) |
| Power with no request | 10–20 W idle; 20–32 W between calls under concurrency |
| K2-Horizon-7B KV state | 144 KiB per token; a 25,427-token pool (3.5 GiB) at mem fraction 0.88 |
| Qwen3.5-9B (hybrid) | prefill 4,646 tokens/s, decode ~38 tokens/s; a 35.5K-token pool; at most 3 concurrent requests (recurrent-state slots) |

Re-prefilling a dropped 12K-token aerogen context costs ~3 s and ~600 J. That is about 60% of
the decode energy of a mean low-effort step (~186 tokens), and 2.3× that of a median one (49
tokens).

**What changes on Orin and Thor:**

- **Speed:**
  - Orin has about 4× less memory bandwidth than the A5000, so decode is slower and the same
    flight is relatively shorter.
  - On the Thor, r is about 67 for P1's MoE model, against about 108–127 on the WS.
- **Memory:**
  - Unified memory has no host tier, so "offload to CPU" is a copy inside the same DRAM.
  - That leaves keep, drop and recompute, compress, or NVMe.
  - Simulators and perception models compete with KV for that memory (H4).
- **Energy:** Jetson rails measure the whole board (CPU, DRAM, simulator), so idle power during
  waits is a board-level number.
- **Models:**
  - P1's models are hybrid (Gemma-4 sliding window, Qwen3.8 linear attention), with separate
    state pools and reuse at checkpoint granularity.
  - On the WS, K2-Horizon-7B is the dense baseline and Qwen3.5-9B the hybrid stand-in.

## Options left for P5

The simulation answers the memory-controller question for these workloads: SGLang's default is
within about 10% of every policy tried. On P1's agents there is nothing to manage at all;
dropping all state at every wait would cost at most 3.2% of LLM time on any task longer than 10
minutes. What remains is a choice of what P5 studies, and the professor makes it.

| Option | What P5 studies | Evidence for | Against |
| --- | --- | --- | --- |
| **A. Decode-side energy on P1's agents (our lean)** | Stopping runaway thinking, thinking budgets, admitting and batching long decodes on the Thor | Calls that hit the 32K cap take 57% (Reflexion) and 70% (tool calling) of LLM time on the 12 CLGSCE tasks, and none produced a usable answer. Stopping them at 16K tokens would save about 27–34% of board energy (upper bound from the traces). P1's agents keep the Thor busy with a single drone | No longer about kept state. The effect on mission success is unmeasured. Reasoning-length control is an active research area we have not reviewed yet |
| B. A step-wise agent on P1's tasks | The agent design itself | 5–13× less energy per success on P1's delivery tasks, and 4–16 drones per Thor instead of 2. Post-wait steps stay short with two stand-in models | The win belongs to the agent, which is P1's territory; a memory controller on top adds at most about 10% (simulated). Not P1's agent, and success needs a building-aware sim |
| C. Standard benchmarks (τ²-bench, BFCL) with injected waits | The original question on another workload | Easy comparison with prior work, including Adaptive KV Retention | The same capacity and compute limits probably apply (not simulated). Loses the drone story; every wait is synthetic |
| D. Memory that changes over time | Admission and retention when co-located models (perception, VLM, the simulator) take and release unified memory | The one memory-side case the simulation could not test. Under tight memory the default loses up to 60% to capacity | Untested. Needs a device, or a co-located workload emulated on the WS |

- **P1's agents stay in every option** as the case where a controller must not make things
  worse.
- **Option letters:** A–C are as on 2026-10-02 (the 2026-10-01 report's A is B here, its C is
  A, and its A + τ²-bench is C). D is new.

**Why A now.** It is where P1's measured energy goes, on P1's device, with P1's agents
unchanged. B's finding still matters, but as a result to hand to P1 (their agent design costs
5–13× per success), not as a serving controller. D is the alternative if P5 should stay on
retained state.

**Where A could be wrong:**

1. **Success.** A cut or a budget may cost missions. All 173 capped calls ended at the token
   limit, but a fixed 16K cut would also stop 14 (Reflexion) and 32 (tool calling) calls that
   finished on their own.
2. **Novelty.** Thinking budgets and early exit are studied for datacenter reasoning models.
   What the edge adds (board power, weak batching on a mixture of experts, one drone saturating
   the device) has to carry the contribution.
3. **Scope.** It drops P5's original question about retained state. The professor may prefer D.

## Decisions needed

- [ ] **Direction (professor):** option A (decode-side energy), B (the agent design, reported to
  P1), C, or D (memory that changes over time). The simulation rules out a memory controller on
  fixed budgets for these workloads.
- [ ] **Scope (professor):** leave retained state for decode-side energy (A), or stay on it with
  co-located models (D)?
- [ ] **Report to P1 (P1's mentor):** on the same 12 tasks their tool-calling agent spends 2.9×
  Reflexion's energy per success, and capped thinking calls take 57–70% of their LLM time; a
  step-wise agent uses 5–13× less energy per success on their delivery tasks.
- [ ] **P1's paradigms (P1's mentor):** is a step-wise agent with flight-level tools in P1's
  scope? P1's tool-calling and ReAct agents both act on whole programs.
- [ ] **Workload (P1's mentor):** may P5 run P1's AeroEval tasks with a step-wise agent (D1–D3
  and F1, then lawnmower and circles), keeping P1's agents as the contrast?
- [ ] **The 8 AeroEval tasks (P1's mentor):** which 8 are meant? We found 5 original missions and
  6 P1 variants.
- [ ] **aerogen (mayankarya):** permission to use and extend aerogen_mcp. Until then it stays a
  private copy on the WS.
- [ ] **Deployment assumption:** how many drones one edge box serves, which sets the memory
  pressure, and the go/no-go thresholds for the next stage.
- [ ] **Timeline:** P1's deadline, when the devices return, and the ISP milestones.

## Next steps

**Either way:**

1. Refresh P1's numbers when the last 4 tool-calling runs finish (expected around 21:00 on
   2026-10-03).
2. When the WS is reachable again, run one live memory-pressure test to anchor the simulator.

**If A:**

1. From P1's traces, find what predicts a runaway early (output length so far, repetition), and
   replay a stop rule's savings and misses.
2. Review the reasoning-budget and early-exit literature.
3. Measure batching of long decodes on the WS, and on the Thor when it is free.

**If B, as a finding for P1:** a building-aware sim guard, the large farm tasks (lawnmower,
concentric circles), and Gemma-4-26B-A4B's output per step on a device.

**If C:** stand up τ²-bench on the WS, one GPU as the agent and one as the user simulator, with
waits drawn from P1's measured flight times.

**If D:** emulate a co-located model that takes and releases memory on the WS, and extend the
simulator to a budget that changes over time.

## Data, methods and limitations

Every number in this report comes from one of these sources:

| Source | What | When |
| --- | --- | --- |
| P1 Thor traces | Reflexion final sweep (143 runs) and tool-calling sweep (104 of 108 runs); Gemma-4-26B-A4B; read-only copies | Reflexion to 2026-10-01; tool calling to 2026-10-03 16:16 |
| WS runs: aerogen | K2-Horizon-7B on aerogen's own 5 tasks, real-time pacing: one session (15 missions at low effort, 5 each at medium and high) and 1–8 sessions per GPU | 2026-10-01 |
| WS runs: the deciding test | Qwen3.5-9B and K2-Horizon-7B on P1's D1–D3, 108 missions, 50× pacing | 2026-10-02 |
| WS calibration | K2-Horizon-7B prefill and decode time and energy against length and batch | 2026-10-01 |
| Simulation | The traces above replayed as 1–16 drones per box on Thor and WS costs, 12 policies, 5 seeds (`analysis/admission_sim.py`) | 2026-10-03 |

**Reproduce.**
- `python3 -m analysis.stepwise_ceiling` writes `../2026-10-02-stepwise-d1/stepwise.json`:
  - the D1–D3 numbers;
  - the pooled P1 ceilings (`"P1 Reflexion"`, `"P1 tool calling"`, including the r = 8
    sensitivity);
  - aerogen's own-task ceilings (`e1_*_n1`).
- `python3 -m analysis.p1_per_task` writes the per-task table
  (`../2026-10-01-p1-task-overview/per_task.json`).
- The aerogen concurrency and simulation numbers come from the 2026-10-01 report's
  `report_data.json` and `sim_validation.json`.
- `python3 -m analysis.admission_sim all` and `python3 -m analysis.admission_figures` write the
  many-drones simulation (`../2026-10-03-admission-sim/`); `python3 -m analysis.p1_runaway`
  writes P1's two-agent comparison (`p1_agents.json` there).

**Where P1's code is on the Thor** (read-only):

- P1's AeroEval agent: `/home/yash/aeroeval_gazebo_subagents/`;
- the AeroEval task sets: its `vendor/CLGSCE/aerodaas_integration/task_sets/`;
- P1's task wiring: `/home/yash/final_sweep/_harness/instances.py`;
- aerogen and the original AeroGen: `/media/ssd/drone/aeroeval/` (mayankarya's).

**What the evidence does not show:**

- **P1's own model per step.** Qwen3.5-9B and K2-Horizon-7B stand in for Gemma-4-26B-A4B, which
  does not fit on one A5000 in bf16.
- **Physical realism.**
  - aerogen's kinematic sim has no buildings or physics.
  - P1's Gazebo runs at 10× real time.
  - Only delivery missions were tested.
- **Memory pressure on P1's tasks.** Live runs of the deciding test had at most 2 sessions per
  GPU. Memory pressure with up to 16 drones is simulated, not yet measured live.
- **Energy scope.** WS energy is NVML GPU energy; board, CPU and DRAM energy are not measured.
  On a Jetson the rails cover the whole board.
- **Ceilings are time shares at batch 1.** Batching lowers r, but on the Thor Gemma's experts make
  it weak, and in simulation P1's agents gain at most 1.6% from kept state at any drone count.
- **Statistics.**
  - There was one run per concurrency configuration and 6–12 missions per test configuration,
    with no confidence intervals.
  - Greedy repeats were identical, so each greedy configuration has 3 distinct trajectories.
- **The simulators.** The 2026-10-01 one is within −23% to +38% of live energy and gives rankings
  only. The 2026-10-03 one is within −8% to +10% of live energy and 2–3% of measured LLM time,
  but under capped pools its default re-prefills about half of what live SGLang did.
- **The shared prompt.** Removing aerogen's anti-cache prompt prefix is what lets sessions share
  the system prompt; a deployed agent would not carry it.

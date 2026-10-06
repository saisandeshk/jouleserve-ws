# Does a thinking model keep its steps short? A step-wise agent on P1's delivery tasks

> **Update 2026-10-06** ([`2026-10-06-options`](../2026-10-06-options/README.md), B-E1/B-E2). Measured with P1's own model, gemma-4-E4B (33 missions, thinking on):
> after a tool result it writes a median 63 tokens greedy and 68 sampled; it passes the strict check 9 of 11 times
> greedy and 7 of 13 sampled (27% for the models here). Projected at Thor gemma-26B prices: 26-27 kJ per strict
> success greedy, 35-40 sampled, against P1's Reflexion 284-499 kJ measured.
>
> **Update 2026-10-05** ([`2026-10-05-p1-repo`](../2026-10-05-p1-repo/README.md)). P1's own traffic agent is an accumulating-context agent too, with
> steps of a median 424–999 output tokens (more than the 55–99 here, because its models think at every
> step). Its kept state is worth 1–4% of LLM time.
>
> **Update 2026-10-03.** `stepwise.json` and the figure were regenerated with 104 of the 108
> runs of P1's tool-calling sweep (median 3,406 output tokens per call, 63% over 1K); the text
> below quotes the first 35 runs (median 3,802). Many drones per box are simulated in
> [`2026-10-03-admission-sim`](../2026-10-03-admission-sim/README.md).
>
> **Update 2026-10-04.** `stepwise.json` also holds every ceiling at r = 90, P1's marginal energy
> price of a generated vs a prefilled token on the Thor (the text uses r = 67, a time ratio). At
> r = 90 the mission ceilings are 16–66% (private state 2–13%) and the post-wait ceilings 48–66%:
> [`2026-10-04-drone-runaways`](../2026-10-04-drone-runaways/README.md).

**2026-10-02 · Sai Sandesh (P5)**, prepared with Claude Code.

This is the deciding test from the task overview
([`../2026-10-01-p1-task-overview/README.md`](../2026-10-01-p1-task-overview/README.md) §6–7).

- **Option B** (a step-wise agent on P1's tasks) is worth proposing only if the model's output
  per step stays short. On the Thor, decoding ~300 tokens costs as much as re-prefilling a
  20K-token context.
- **Decision rule:**
  - if the steps stay at a few hundred tokens, B holds;
  - if they run to thousands, A or C is the honest direction.

All numbers are WS measurements from 2026-10-02 unless marked otherwise. Data:
[`stepwise.json`](stepwise.json); figure: [`figures/`](figures/).

## Answer

1. **The steps stay short in every configuration, so B holds by the rule.**
   - **Coverage:** 108 missions over P1's D1, D2 and D3 (3 instances each); two models; thinking
     on and off; P1's greedy protocol and sampled decoding.
   - **After a tool result,** the model writes a median of **55–99 output tokens**, the p90 is
     ≤ 394, and at most 2.6% of steps exceed 1K tokens.
   - **For comparison,** P1's own agents write a median of 538 (Reflexion) and 3,802 (tool
     calling) tokens per call on the Thor, and 40–63% of their calls exceed 1K.
2. **Thinking concentrates in the first call, which plans the mission before the drone
   moves.**
   - **With thinking on,** that call writes a median of 545–5,147 tokens, and 21–82% of all
     output tokens. Without thinking it writes 28.
   - **K2 at high effort plans the longest:** 2.7K–5.1K tokens, up to 12K. Its reasoning
     samples show genuine planning (waypoints, tool order), not loops.
   - **The one failure was a runaway.** One greedy thinking call (Qwen, D1 instance 3) ran away
     to 24K tokens and filled the KV pool, so both of that instance's greedy missions never
     flew. This is the failure mode behind P1's 32K-capped calls.
3. **What retention could be worth** at the Thor's prefill/decode ratio (r ≈ 67):
   - at most **56–72% of the LLM time of the steps after a tool wait**;
   - **20–72% of a whole mission's LLM time**, because the planning call dilutes it. Without the
     runaway arm the range is 36–72%.
4. **Most of that value is the shared prompt, not per-session state.**
   - **The prompt is shared:** the 9–11K-token system prompt plus task is the same for every
     drone, and the radix cache already keeps one copy for all sessions.
   - **Each mission's private state is smaller.** That is the growing history, and what a
     retention policy must decide about under memory pressure. It is worth **3–16% of a
     mission's LLM time** on these delivery missions (6–33% of the post-wait steps).
   - **K2 at high effort has the most private state,** because its long planning reasoning
     stays in the history.
5. **The agent is not mission-ready on P1's world yet.**
   - It completed every delivery in 72% of missions (78/108), but only 27% (29/108) pass the
     strict check.
   - **Collisions are the main failure:** 56% of missions (61/108) collide. The model flies
     diagonal shortcuts through the 20 m buildings, and aerogen's kinematic sim has no
     buildings, so nothing stops it.
   - **This does not change the token counts,** but a building-aware sim is a prerequisite
     before B's success rates mean anything.

**Implication for the options.**
- **B is viable.** Step-wise agents on P1's delivery missions keep the post-wait steps short,
  with both a hybrid thinking model and a dense reasoning model, with or without thinking.
- **On short deliveries the per-session state is modest.** P5's case is strongest where that
  state grows:
  - longer missions (lawnmower, concentric circles: 20–150 steps);
  - models that keep their reasoning in the history;
  - several drones per box.
- **The planning call is decode-heavy.** A thinking budget for it is option A's lever, and it
  complements retention rather than competing with it.

![Output tokens per step](figures/output_per_step_cdf.png)

## Setup

- **Agent:** `aerogen_mcp`'s loop, unchanged: one tool call per step, one growing `messages`
  list. It runs from the private WS copy, with the driver patching only the client and the
  logging, as in the 2026-10-01 runs.
- **Prompts:**
  - aerogen's guidelines, tool protocol and examples;
  - AeroEval's `robot.txt`;
  - the **same delivery world and navigation runtime files that P1's AeroEval agent uses**
    (`common_world_delivery.txt`, `modularized_new/navigation/runtime_information.txt`).
  - aerogen's world envelope already matches that world: 1–45 m altitude, 2 m/s, the boundary,
    and depot I40.
- **Tasks:** P1's D1 (ordered three-stop delivery), D2 (checkpoint) and D3 (two out-and-back
  trips), verbatim, with P1's node remaps for instances 2 and 3 (`instances.py`). They are kept
  on the WS (`~/work/tasks/`), not in this repo.
- **Simulator:** aerogen's kinematic sim at 50× real time. Pacing does not affect token counts.
  Flight times come from the sim clock: 283–612 s per mission, median per arm.
- **Serving:** SGLang 0.5.20, one A5000 per model, context 65,536.

| Model | State | Pool | Settings | Max tokens |
|---|---|---|---|---|
| Qwen3.5-9B | Hybrid: 8 full-attention + 24 linear-attention layers. The unified radix cache reuses KV and recurrent state | 35.5K tokens | Thinking on or off. **Greedy** is P1's protocol (temperature 0, top-k 1, seed 42); **sampled** follows the model card | 32,768 (as P1) |
| K2-Horizon-7B (revision `f846b1e`, as in all earlier runs) | Dense | 25.4K tokens | Effort low or high, temperature 1.0 (model card). The template keeps past reasoning in the history | 16,384 (as 2026-10-01) |

- **Runs:**
  - D1: 2 runs × 3 instances (greedy), 3 × 3 (sampled and K2).
  - D2 + D3: 1 × 6 (greedy), 2 × 6 (sampled and K2).
  - Greedy runs at N = 1, the others at N = 2 concurrent sessions.
  - Greedy repeats were identical, so each greedy arm has 3 distinct trajectories per task set.
- **Strict check** (`jsw/workloads/delivery_check.py`), using P1's Gazebo geometry and
  tolerances (3 m in xy, 2 m in z):
  - stops visited in order, each with a descent to ≤ 3 m and a hold of ≥ 10 s;
  - for D2, the checkpoint visited first; for D3, a return to the depot between the two trips;
  - a return to the depot at the end;
  - no flight through a building below its 20 m roof.
- **Ceiling:** P / (P + r·O) per call, pooled token-weighted.
  - "Private" counts only the prompt beyond the mission's first prompt.
  - r = 67 is Gemma-4-26B-A4B on the Thor (P1's traces). On the WS r = 120–127, from cold
    prefill against decode measured in these runs.

## Results

**D1 (the agreed test).** "Steps" are LLM calls that follow a tool result.

| Arm | Missions: all delivered / strict pass | LLM calls per mission | 1st call output: median (max) | Output per step: median / p90 / max | Steps > 1K | Prompt: first → peak (median) | Ceiling at Thor r, mission (private) | Ceiling at Thor r, steps (private) | Measured saving on WS |
|---|---|---|---|---|---|---|---|---|---|
| Qwen thinking, greedy (P1 protocol) | 2 / 0 of 6 | 13.7 | 696 (**24,236**, runaway) | 86 / 289 / 1,165 | 2.6% | 11.3K → 18.0K | 20% (3%) | 57% (9%) | 11% |
| Qwen thinking, sampled | 6 / 2 of 9 | 21.6 | 628 (1,998) | 90 / 288 / 1,578 | 2.2% | 11.3K → 17.6K | 53% (11%) | 57% (12%) | 34% |
| Qwen no thinking, greedy | 4 / 0 of 6 | 20.0 | 28 (28) | 82 / 100 / 406 | 0% | 11.3K → 15.7K | 71% (8%) | 71% (8%) | 53% |
| Qwen no thinking, sampled | 7 / 5 of 9 | 21.7 | 28 (97) | 79 / 108 / 2,042 | 1.1% | 11.3K → 15.7K | 68% (10%) | 67% (11%) | 48% |
| K2 high effort | 5 / 5 of 9 | 17.8 | 5,147 (12,159) | 64 / 204 / 694 | 0% | 9.4K → 18.3K | 36% (16%) | 72% (33%) | 14% |
| K2 low effort | 6 / 4 of 9 | 15.1 | 796 (2,178) | 63 / 204 / 1,210 | 1.6% | 9.4K → 12.9K | 49% (10%) | 62% (13%) | 33% |

**D2 + D3.** Same arms, 6–12 missions each.

| Arm | All delivered / strict pass | 1st call output: median (max) | Output per step: median / p90 / max | Ceiling at Thor r, mission (private) | Ceiling at Thor r, steps (private) |
|---|---|---|---|---|---|
| Qwen thinking, greedy | 6 / 0 of 6 | 649 (759) | 99 / 394 / 857 | 51% (6%) | 57% (7%) |
| Qwen thinking, sampled | 10 / 4 of 12 | 724 (3,816) | 91 / 367 / 1,814 | 49% (9%) | 56% (11%) |
| Qwen no thinking, greedy | 6 / 0 of 6 | 28 (97) | 75 / 115 / 357 | 72% (5%) | 72% (6%) |
| Qwen no thinking, sampled | 11 / 1 of 12 | 28 (99) | 80 / 122 / 3,457 | 65% (6%) | 64% (6%) |
| K2 high effort | 9 / 6 of 12 | 2,709 (8,572) | 61 / 187 / 1,458 | 42% (14%) | 68% (24%) |
| K2 low effort | 6 / 2 of 12 | 546 (3,431) | 55 / 134 / 1,084 | 53% (10%) | 68% (14%) |

- **The measurements cross-check.**
  - On the WS the measured saving is below the WS ceiling in every arm, by 1–9 points.
  - K2 low on D1 saves 33%, the same as on aerogen's own tasks on 2026-10-01.
  - Prompt reuse is 82–98%.
- **Flights dominate mission time once the steps are short.** At the Thor's speed with nothing
  kept, the drone would be flying for 49–85% of a mission (projection from the sim clock and
  the token counts).
- **Long post-wait outputs are rare:** 17 of 1,649 steps exceed 1K tokens.
  - 6 of them are final mission summaries.
  - The rest are mid-mission re-planning. For example, the 3,457-token no-thinking outlier is
    the model writing out its whole route as plain text after takeoff.

## What this does not show

1. **P1's model.** Qwen3.5-9B and K2-Horizon-7B stand in for Gemma-4-26B-A4B, which does not
   fit on one A5000 in bf16. The pattern (long planning, short steps) holds across two quite
   different models, but Gemma's own numbers should be measured on the Thor or an Orin when one
   is free.
2. **P1's prompts.**
   - aerogen's prompts are written for step-wise control: the examples show one tool per step.
   - P1's prompts ask for whole programs, so a step-wise P1 agent would need prompts like
     these anyway.
3. **Physical realism.**
   - The kinematic sim has no buildings and no physics. In Gazebo, or with a building-aware
     guard, rejected moves would add steps and corrections.
   - Only delivery missions were run. The large farm tasks were not.
4. **Memory pressure.** Pools were ample (N ≤ 2) except for the greedy runaway. This test
   measures what the state is worth, not how a policy behaves when state must be evicted.
5. **Statistics.** The test used 6–12 missions per arm per task set, greedy arms have 3 distinct
   trajectories, and there are no confidence intervals. The step-length result is consistent
   across all 12 arm × task-set cells; the success rates are not reliable.

## Next, if B is chosen

1. **Make the sim respect P1's world.** Reject moves through buildings in aerogen's sim guard,
   using the geometry already used by `delivery_check.py`. This gives fair success rates.
2. **Run the large tasks** (lawnmower, concentric circles), where private state grows.
3. **Run under memory pressure:** N drones per box, an edge-sized pool, and the admission
   policies in the simulator, then live.
4. **Measure Gemma-4-26B-A4B per step** on a device.

## Reproduce

```bash
# WS: servers (GPU0 Qwen, GPU1 K2), then the two queues
bash env/launch_qwen35_tp1.sh 0 30010     # in tmux
bash env/launch_k2_tp1.sh 1 30011         # in tmux; pinned to revision f846b1e
bash env/queue_stepwise_d.sh qwen         # in tmux; needs ~/work/tasks/p1_d1.txt, p1_d23.txt
bash env/queue_stepwise_d.sh k2
# local: copy runs back and analyze
rsync -a saisandeshk@10.24.32.174:~/work/runs/ data/ws_runs/
python3 -m analysis.stepwise_ceiling
```

# Energy waterfall: where P1's board energy went (WF-1, WF-2, first WF-3)

**14 Oct 2026 · ENERGY_PLAN §4–§5.** Code: `analysis/waterfall.py`, `analysis/stop_bounds.py`, `analysis/fail_predictor.py`, `analysis/waterfall_figure.py`
(each committed before its results were read). Data: P1's final data at `0cc2311a`, P1's selection rule and grades, all
25 edge configurations (17 traffic, 8 drone). Outputs: `waterfall.json`, `stop_bounds.json`, `waterfall.png`.

**The answer:**
- **Runs that fail take most of the energy.** That is over half of the board energy in 22 of 25 configurations (median 69%).
  P1's submitted paper reports the same headline, so it is P1's finding, not ours.
- **Inside passing runs**, the largest avoidable part is decoding one request at a time: 2–36% of all energy in traffic (median 17%;
  drone 1–34%, median 5%), priced at 4 requests decoding together.
- **Reading prompts and tool waits are small:** prefill 0–4%, tool waits 0–7% (traffic Reflexion's unmetered critic
  calls sit in the grey "other").
- **No single fixed stop rule closes the gap.** The best fixed stop rule that keeps the pass rate differs by
  configuration. It leaves at least 15% of energy per success between itself and the oracle in 24 of 25
  configurations.

![Where P1's board energy went](waterfall.png)

## What each configuration shows

Energy per success is P1's board energy over all runs divided by passing runs. The stop rules are applied to the recorded
runs: a stopped run counts as a failure, and a rule may cut at most 5% of the passes. "Best fixed stop rule" is the best
such rule for that configuration; the passes it cuts are in brackets. "Task oracle" skips every task the configuration
never passes. "Oracle" stops every failing run at its start.

**Traffic**

| Configuration | Passed | kJ per success | Energy in failed runs | Top causes of failed-run energy | One-at-a-time decode cost (k = 4) | Best fixed stop rule (passes cut) | Task oracle | Oracle |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Orin 64 · Devstral-24B · Reflexion | 31/126 (25%) | 127.2 | 95% | wrong answer 79%, timeout or step limit 13% | 2% | -79% (0) | -91% | -95% |
| Orin 64 · Qwen2.5-VL-7B | 60/252 (24%) | 8.7 | 82% | wrong answer 87%, timeout or step limit 13% | 10% | -19% (1) | -73% | -82% |
| Orin 32 · Qwen2.5-VL-7B · Reflexion | 70/252 (28%) | 14.7 | 82% | wrong answer 100% | 9% | -26% (3) | -53% | -82% |
| Orin 32 · Qwen2.5-VL-7B | 66/252 (26%) | 8.2 | 78% | wrong answer 80%, timeout or step limit 20% | 13% | -12% (3) | -53% | -78% |
| Orin 32 · Ministral-8B | 154/252 (61%) | 19.2 | 73% | timeout or step limit 48%, window overflow 25% | 14% | -47% (5) | -2% | -73% |
| Orin 64 · gemma-26B · Reflexion | 64/196 (33%) | 58.3 | 73% | wrong answer 58%, window overflow 23% | 6% | -12% (2) | -53% | -73% |
| Thor · Devstral-24B | 126/189 (67%) | 55.1 | 69% | capped calls 58%, wrong answer 26% | 22% | -38% (3) | -26% | -69% |
| Thor · gemma-26B | 187/252 (74%) | 58.1 | 68% | capped calls 87%, wrong answer 13% | 13% | -43% (7) | -32% | -68% |
| Thor · gemma-26B · Reflexion | 167/196 (85%) | 155.4 | 63% | timeout or step limit 50%, capped calls 39% | 8% | -47% (6) | -30% | -63% |
| Orin 64 · Devstral-24B | 111/189 (59%) | 32.1 | 62% | timeout or step limit 44%, wrong answer 34% | 25% | -14% (5) | -35% | -62% |
| Orin 32 · granite-8B | 97/189 (51%) | 70.5 | 59% | timeout or step limit 35%, window overflow 32% | 29% | -5% (4) | -20% | -59% |
| Orin 64 · gemma-26B | 113/252 (45%) | 26.0 | 57% | timeout or step limit 40%, window overflow 31% | 17% | -4% (3) | -24% | -57% |
| Thor · granite-8B | 124/189 (66%) | 101.8 | 54% | capped calls 66%, wrong answer 32% | 32% | -8% (2) | +0% | -54% |
| Orin 32 · gemma-E4B | 184/252 (73%) | 37.3 | 50% | capped calls 74%, timeout or step limit 15% | 30% | -29% (9) | -28% | -50% |
| Orin 64 · granite-8B | 111/189 (59%) | 51.6 | 49% | capped calls 33%, wrong answer 27% | 36% | -4% (3) | -13% | -49% |
| Orin 32 · granite-8B · Reflexion | 73/126 (58%) | 116.0 | 43% | timeout or step limit 43%, wrong answer 23% | 22% | -4% (0) | -16% | -43% |
| Thor · Qwen3.6-35B-A3B | 226/252 (90%) | 29.7 | 13% | capped calls 55%, wrong answer 35% | 35% | -1% (6) | +0% | -13% |

**Drone**

| Configuration | Passed | kJ per success | Energy in failed runs | Top causes of failed-run energy | One-at-a-time decode cost (k = 4) | Best fixed stop rule (passes cut) | Task oracle | Oracle |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Orin 32 · Ministral-8B | 43/144 (30%) | 209.6 | 98% | capped calls 71%, wrong answer 26% | 1% | -95% (1) | -90% | -98% |
| Orin 32 · gemma-E4B | 50/144 (35%) | 193.8 | 97% | capped calls 92%, wrong answer 8% | 2% | -91% (2) | -96% | -97% |
| Orin 64 · Devstral-24B | 45/144 (31%) | 96.0 | 96% | wrong answer 91%, capped calls 9% | 1% | -85% (0) | -93% | -96% |
| Orin 64 · granite-8B | 45/144 (31%) | 453.6 | 93% | wrong answer 85%, capped calls 15% | 5% | -70% (1) | -79% | -93% |
| Orin 32 · granite-8B | 49/144 (34%) | 461.4 | 90% | wrong answer 88%, capped calls 12% | 7% | -59% (0) | -75% | -90% |
| Thor · gemma-26B | 74/144 (51%) | 397.0 | 84% | capped calls 99%, wrong answer 1% | 5% | -49% (3) | -42% | -84% |
| Thor · gemma-26B · Reflexion | 102/144 (71%) | 154.3 | 63% | capped calls 95%, wrong answer 5% | 8% | -26% (4) | -32% | -63% |
| Orin 64 · Qwen3.8-27B | 109/144 (76%) | 198.3 | 51% | wrong answer 83%, capped calls 9% | 34% | -2% (1) | -9% | -51% |

## What it means for P5

1. **The failed-run headline belongs to P1.**
   - **What P1's paper already reports:**
     - failed runs consume most of the energy;
     - a failed run costs several times a passing one;
     - offline policies: an attempt budget chosen per task class, and step cutoffs for traffic (gemma only).
   - **P1's own conclusion:** "reductions require task-specific decisions".
   - **What we add:**
     - the split by cause for all 25 configurations;
     - the overflow mechanism (point 3);
     - the fixed-against-oracle gap (point 2).
2. **Q1 and Q2 for stopping doomed work.**
   - **No one fixed rule fits all configurations:**
     - the best rule that keeps the pass rate is a sign (first capped call, or context near the window) for some
       configurations, an energy budget for others;
     - its multiple of a passing run's median energy ranges from 1.5× to 12×;
     - the one rule that keeps the pass rate everywhere (stop at 5× the median passing energy of the same task) gives
       −0% to −88%, often well below the per-configuration best.
   - **The gap between the best fixed rule and the oracle** is at least 15% of energy per success in 24 of 25
     configurations (13% for Qwen3.6 on Thor). That is room for a policy that predicts failure from what happens inside
     the run.
   - It is an upper bound: the oracle knows the outcome.
3. **Window overflows on the Orins happen in one jump, not by growth.**
   - Across all 278 overflowed runs, the request that overflowed was a median 10.5K tokens larger than the run's
     largest earlier prompt (10th–90th percentile 2.5K–23.8K).
   - It typically comes at about the second step, after a tool output: `get_traffic_series` in 177 of the 278
     (`run_python` in 46).
   - The overflowed request then exceeds the window: 26,624 tokens for granite, 12,288 for gemma-26B on Orin 64.
   - Overflows end 19–28% of the selected runs of granite and gemma-26B on the Orins. Thor, with a 110K window, has
     at most 3 per configuration.
   - A capacity limit turns directly into failed tasks. The failure is visible to the serving layer the moment the tool
     returns, before the next request is sent.
4. **Most failure energy in small models is spent on tasks they never pass.**
   - The task oracle saves −53% to −97% for the small drone models and for Qwen2.5-VL in traffic.
   - Not attempting, or handing the task to a stronger model, would save it.
   - Stopping late saves less.
5. **Inside passing runs, one-at-a-time decoding is the largest avoidable part** (2–36% of traffic energy, median 17%).
   - Packing agents captures it as a fixed setting (B*).
   - What a run-time policy can add there depends on load, which these logs do not have.

## Can an online predictor capture the gap? (WF-3b)

**Mostly no, without task history.** Code: `analysis/fail_predictor.py` (committed before its results were read).
Output: `fail_predictor.json`.

**Setup:**
- **Decision points:** at the end of every LLM call, a logistic model decides whether to stop the run.
- **Features:** only what the serving layer has seen by then:
  - energy so far against a reference;
  - calls, capped calls and consecutive caps;
  - prompt against the window;
  - output against its cap;
  - tool calls so far;
  - with history, the task's past pass rate.
- **Threshold:** chosen on the training runs to cut at most 5% of their passes.
- **Comparison:** against the in-sample best fixed rule above, which favours the fixed rule.

| Evaluation | Beats the best fixed rule | Keeps cuts ≤ 5% of passes on held-out runs | Both, and ≥ 15% of the gap to the oracle |
| --- | --- | --- | --- |
| New tasks (folds by task, no history) | 3 of 25 | 13 of 25 (cuts 2.7–24.5%) | 1 of 25 |
| Repeats (one repeat held out, the task's history known) | 18 of 25 (3–76% of the gap) | 12 of 25 (cuts 0–14%, median 5.4%) | 5 of 25 (Orin 64 gemma-26B, Devstral and Qwen2.5-VL traffic; Orin 32 Qwen2.5-VL traffic; Orin 64 Qwen3.8 drone) |

**What it means:**
- The signals the serving layer sees inside a run predict failure poorly on tasks it has not seen.
- With per-task history, a predictor captures a real part of the gap, but its threshold does not hold the pass rate
  reliably on held-out runs.
- Most of what it captures comes from knowing which tasks fail. That is closer to deciding before a run (admit, route
  or skip) than to stopping during it.
- Richer in-run signals are untested: tool errors, repeated arguments, the text itself. P1's traffic traces now carry
  them.

## Method notes and caveats

- **Energy.** Board energy from P1's power fields: per run `workflow_energy_J`; per LLM call and tool phase
  `iter_energy_j`.
  - Drone boards also power P1's simulator.
  - Traffic Reflexion's critic calls carry no phase energy, so they land in "other" (up to 25%, Orin 32 granite
    Reflexion).
- **Drone data.** Drone cells read the run folders as they are now. That is P1's E2 re-run for the sweeps P1 re-ran;
  P1's paper reports the measured record.
- **One-at-a-time cost.** It is priced at 4 requests decoding together with board cost curves.
  - Measured for gemma-26B on Thor-1 (0.45 per token against one request) and for dense models on the Orin 32
    (0.26).
  - Elsewhere the measured curve of the same class is a proxy.
  - The cost curve on Orin-64-1 at P1's flags gains nothing from batching at an 8K context, so the server's flags
    matter.
  - It assumes the pool allows 4 contexts at once.
- **Retrospective rules.** Stop rules are applied after the fact to recorded runs. A stopped run is a failure; nothing is
  rescued. The oracles know the outcome.
- **Warning signs.** They were fixed before the numbers were read. The 80%-of-window sign never fires on the one-jump
  overflows (point 3).

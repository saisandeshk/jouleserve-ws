# Runaway calls in P1's drone runs, and what P1's 3 October results change

**2026-10-04 · Sai Sandesh (P5)**, prepared with Claude Code.

P1 presented new results at the paper meeting with the professor on 2026-10-03 (the
EdgeAgentBench deck, slides 387–406). This report covers the **drone** part only. It does three
things:
1. it checks P1's drone numbers against our copy of the same Thor traces;
2. it adds what our traces show on top: the calls that hit the output-token cap are repetition
   loops, and an online loop stop beats a fixed cut;
3. it lists what changes in our earlier reports.

P1's traffic results are not covered. We get access to P1's repository on 2026-10-06.

Data: [`loops.json`](loops.json); figure: [`figures/loops.png`](figures/loops.png). P1's
figures below are crops of the deck's figures to their drone rows. They are unpublished, so they
sit in `p1_figures/`, which git ignores.

## Answer

1. **P1's drone numbers reproduce from our copy** (Gemma-4-26B-A4B on the Thor, Reflexion,
   143 runs; P1 counts 144):

   | | P1's deck | Our recomputation |
   | --- | --- | --- |
   | Runs passed | 71% | 71% (102 of 143) |
   | LLM time in calls that hit the output-token limit | 71% | 71% |
   | Pass rate of runs with / without such a call | 39% / 92% (57 runs with one) | 39% / 92% (56 runs) |
   | Failed runs: share of runs / of board energy | 29% / 63% | 29% / 63% |
   | Prompt tokens served from the prefix cache | 26% | 26% |
   | Prefill's share of LLM time | 1.8% | 1.8% |
   | Energy of a generated token ÷ a prefilled token | 75× (average price), 90× (marginal) | 74× (our regression) |
   | Share of LLM energy from generated tokens | 97% | 97% |
   | Runs with a KV-cache eviction | 33% | 33% (47 runs) |

   Nothing in P1's drone results contradicts our earlier analysis.
2. **The runaway calls are repetition loops.**
   - 120 of the 121 Reflexion calls that hit their output-token limit end in a loop that repeats
     the same text. So do all 127 of the tool-calling calls capped at 32,768 tokens.
   - **None of the 1,337 calls that finished on their own** (909 Reflexion, 428 tool calling)
     trips the detector.
   - An online detector fires at a median of 35% of the way into a Reflexion call (about 11,200
     tokens) and 44% into a tool-calling call (about 14,500 tokens).
3. **Stopping the loops would save more than a fixed cut, and stop nothing that would have
   finished.** The savings are upper bounds on board energy (method below):

   | Stop rule | Reflexion, all 16 tasks | Reflexion, 12 CLGSCE tasks | Tool calling, 12 CLGSCE tasks |
   | --- | --- | --- | --- |
   | Online loop stop | **44%**, stops 0 finished calls | **31%**, 0 | **36%**, 0 |
   | Fixed cut at 16K tokens | 34%, stops 14 finished calls | 27%, 14 | 34%, 32 |
   | Either | 45%, 14 | 34%, 14 | 40%, 32 |

4. **The likely cause is greedy decoding.**
   - Every P1 configuration decodes at temperature 0 with thinking on (P1's deck).
   - On the WS, Qwen3.5-9B with thinking ran away only under greedy decoding: none of 21 sampled
     missions did (2026-10-02).
   - Qwen's model cards warn that greedy decoding in thinking mode causes endless repetition.
   - Whether Gemma-4 still loops under sampling is not measured.
5. **The KV-cache evictions P1 reports are a side effect of the runaways.**
   - 45 of the 47 Reflexion runs with an eviction contain a capped call, and 40 of the 44
     tool-calling runs do.
   - Those runs fill P1's 80,000-token pool cap (`--max-total-tokens 80000`), which is a server
     setting on a 128 GB Thor, not a memory limit.
   - This explains the same-role cache misses we flagged on 2026-10-01 better than our guess that
     Gemma's sliding-window state was lost. Those misses cost 0.3–1.1% of LLM time.
6. **Our retention ceilings fall a little at P1's price ratio.** We used r ≈ 67, a time ratio.
   At P1's marginal 90×:
   - P1 Reflexion goes from 2.1% to 1.6% of LLM time, and P1 tool calling from 0.6% to 0.5%.
   - The step-wise agent on D1–D3 goes from 20–72% to 16–66% of mission LLM time.
   - Its private state goes from 3–16% to 2–13%.

   The conclusions do not change. They get slightly stronger.
7. **There is no thermal throttling at room temperature.**
   - P1 saw no GPU clock below 98% of its pinned value in 392 h of runs (MAXN).
   - The hottest drone reading was 77 °C on the Thor over 63 h.
   - So thermal state does not change any serving decision on these runs. P1 plans
     hot-enclosure runs.
8. **Repeats at temperature 0 are not identical on Jetson.** 23–25% of drone prompts took more
   than one path in 3 repeats (P1).
9. **The agent-design comparison depends on the success check.**
   - The step-wise agent's "5–13× less energy per success" than P1's Reflexion counts a mission
     as successful if it delivered every package and returned.
   - With the strict check, which also fails flights through buildings, the ratio is 0.9–9.6×.
   - A building-aware sim is needed to settle it (table below).

**What this means for P5's options.**
- **Option A** (decode-side energy) gains a concrete, safe mechanism: stop the loop, not the
  call length.
- **Two cautions for A:**
  - If greedy decoding causes the loops, the fix may be configuration (sampling, or a
    repetition guard), not research. That is the same verdict the FP8 KV cache got.
  - P1's own plan includes an early-abort policy as its systems contribution, so A needs
    coordinating with P1. One option is to offer this result to P1's paper.
- **B** keeps its finding, with a wider range (above).
- **C and D** are unchanged by the drone results.

## Results

### Runaway calls are loops

![Capped calls are loops; where an online loop stop would cut](figures/loops.png)

- **(a)** The most repetitive 16,000 characters of each call, compressed with zlib:
  - calls that hit their limit compress to 1–9% of their size (one call to 11%), the signature of
    text repeating itself;
  - calls that finished on their own compress to 14–29%, like ordinary reasoning and code.

  Only calls with at least 16,000 characters are shown.
- **(b)** Where the online detector fires, in output tokens, against a fixed 16K cut.
  - It fires before 16K on 86% of the Reflexion loops and 61% of the tool-calling loops.
  - Loops that start late are still cut early enough to save their tail.

| | Reflexion (143 runs, 16 tasks) | Tool calling (104 runs, 12 tasks) |
| --- | --- | --- |
| LLM calls | 1,030 | 571 |
| Calls that hit their output-token limit | 121 (115 at 32,768; 3 validator calls at 8,192; 3 at 4,096) | 143 (127 at 32,768; 16 evaluator calls at 1,024) |
| Of these, flagged as loops | 120 | 127 (all at 32,768; the 1,024-token calls are too short to test) |
| Calls that finished on their own and were flagged | 0 of 909 | 0 of 428 |
| Detector fires at (median) | 35% of the call, ~11,200 tokens | 44%, ~14,500 tokens |

### The KV-cache evictions are runaways

| | Reflexion | Tool calling |
| --- | --- | --- |
| Runs with a KV-cache eviction | 47 of 143 (33%) | 44 of 104 |
| Of these, runs with a capped call | 45 | 40 |

In the Reflexion runs with an eviction, the full-attention cache peaked at a median of 54K
tokens (28–55K): a prompt of up to ~22K plus a 32K-token loop. With the earlier prompts still cached, that
overflows P1's 80K-token pool.

### P1's drone figures

These are P1's figures from the EdgeAgentBench deck of 3 Oct 2026, cropped to the drone rows. The
second row in each is Orin 64 with Devstral-24B, a tool-calling configuration we have no traces
for.

![P1, slide 396: time in calls that hit the token limit](p1_figures/p1_capped_calls_s396.png)

![P1, slide 394: energy of a generated vs a prefilled token](p1_figures/p1_token_price_s394.png)

![P1, slide 400: largest prompt per run, and runs with a KV-cache eviction](p1_figures/p1_context_evictions_s400.png)

![P1, slide 405: GPU temperature over each sweep](p1_figures/p1_thermal_s405.png)

### The agent-design comparison under both success checks

P1's Reflexion is measured on the Thor; the step-wise agent is projected onto the Thor at one
drone (`analysis/admission_figures.py`). For D2 + D3 the comparison is with P1's D2, because P1's
D3 had no passes.

| Step-wise configuration, task set | Delivered and returned | Strict check | P1 Reflexion ÷ step-wise, energy per success |
| --- | --- | --- | --- |
| Qwen3.5 thinking, D1 | 6 of 9 | 2 of 9 | 10.7× lenient, 3.6× strict |
| Qwen3.5 thinking, D2 + D3 | 10 of 12 | 4 of 12 | 7.2×, 2.9× |
| Qwen3.5 no thinking, D1 | 7 of 9 | 5 of 9 | 13.5×, 9.6× |
| Qwen3.5 no thinking, D2 + D3 | 11 of 12 | 1 of 12 | 10.0×, 0.9× |
| K2 high effort, D1 | 5 of 8 | 5 of 8 | 7.3×, 7.3× |
| K2 high effort, D2 + D3 | 9 of 12 | 6 of 12 | 5.7×, 3.8× |
| K2 low effort, D1 | 6 of 9 | 4 of 9 | 11.7×, 7.8× |
| K2 low effort, D2 + D3 | 6 of 12 | 2 of 12 | 4.6×, 1.5× |

- **The truth is probably in between.** The step-wise agent never got feedback about buildings,
  because aerogen's kinematic sim has none. With a building-aware guard it would correct its
  moves at the cost of a few more steps.

### Retention ceilings at P1's price ratio

| Workload | Ceiling at r = 67 (time ratio, used so far) | At r = 90 (P1's marginal energy price) |
| --- | --- | --- |
| P1 Reflexion, all calls | 2.1% | 1.6% |
| P1 tool calling, all calls | 0.6% | 0.5% |
| Step-wise on D1–D3, mission LLM time | 20–72% | 16–66% |
| Step-wise on D1–D3, private state only | 3–16% | 2–13% |
| Step-wise on D1–D3, steps after a tool wait | 56–72% | 48–66% |

## P1's schedule (as of 2026-10-03 15:00)

![P1's run schedule](p1_figures/p1_schedule_s389.png)

- **P1's last runs end on Thu 8 Oct at 16:40.** The paper is due on Sat 10 Oct at 17:30.
- **The Thor we read from (thor-1) is booked back to back:**
  - Gemma tool calling: 99 of 144 runs done. This sweep also covers the 4 AeroEval tasks, so it
    will not end at 108.
  - Then granite and Devstral tool calling.
- **What this means for us:** copies from the Thor would land mid-run in P1's last week. We wait
  for the repository.

## Method

- **The detector** (`analysis/p1_loops.py`) reads each call's text as it would stream: the
  reasoning, then the output.
  - Every 1,000 characters it compresses the last W characters with zlib.
  - It flags the call when the compressed size stays below 10% of the window for 3 checks in a
    row, at W = 4,000 or 16,000 characters, whichever fires first.
  - A token position is taken as proportional to the character position.
  - **Sensitivity.** At a 10% threshold, windows of 8,000–16,000 characters flag no call that
    finished on its own. At 15%, one or two such calls are flagged; at 20% and above, 2–51 are.
- **Savings** use the method of `analysis/p1_runaway.py`. For each stopped call:
  1. take the decode time it would not have spent, at its measured decode rate;
  2. charge it at the board's 71.9 W while a call runs;
  3. divide by the sweep's measured board energy.

  The rest of each run is assumed to go as recorded. Every capped call ended at the token limit
  with no usable answer, so stopping it earlier hands the agent the same failure sooner. A stop
  on a call that finished on its own is counted as a false stop.
- **The price ratio** comes from a least-squares fit of each call's measured energy on its
  prefilled, cached and generated tokens, with no intercept.
  - The generated-to-prefilled ratio and the generated share match P1's.
  - The cached-token price is not well determined.
  - On the tool-calling calls the fit is not identifiable (negative coefficients), as P1 found
    for some of its configurations.
- **Not covered:**
  - P1's path counts (23–25% of drone prompts took more than one path) and temperatures are
    quoted from the deck, not recomputed.
  - We do not have P1's device telemetry beyond the copied traces.

## Reproduce

```bash
python3 -m analysis.p1_loops            # loops.json, figures/loops.png
python3 -m analysis.stepwise_ceiling    # adds the r = 90 ceilings to ../2026-10-02-stepwise-d1/stepwise.json
python3 -m analysis.admission_figures   # adds strict-check counts to ../2026-10-03-admission-sim/summary.json
```

Inputs: `data/p1_thor_drone/` (Reflexion, 143 runs) and `data/p1_thor_toolcalling/` (tool calling,
104 runs as of 2026-10-03 16:16).

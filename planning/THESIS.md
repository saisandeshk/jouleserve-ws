# P5 thesis: draft for discussion (TH-1)

**15 Oct 2026, draft 2.** Draft 1 (14 Oct) is in git. It led with stopping doomed runs; the predictor test (WF-3b)
weakened that, and the candidates analysis moved the core. It is built on:
- the energy waterfall ([`../reports/2026-10-14-waterfall/`](../reports/2026-10-14-waterfall/README.md));
- the candidates analysis ([`../reports/2026-10-15-candidates/`](../reports/2026-10-15-candidates/README.md)).

Sandesh and the mentor decide whether to adopt it; nothing is agreed yet. The traffic experiments (CAND-T1/T2) are
running, and their results will confirm or change §4.

## 1. The claim

An edge board serving LLM agents has spare decode width and a small KV pool, and P1 left both idle (one request at a
time). There are two ways to spend them:
- **across agents:** pack more agents on the board;
- **within an agent:** run several sampled candidates for a risky step and keep the first good one.

Which is better, and how wide to go, changes with:
- the model's cost curve (dense or mixture-of-experts);
- how often the model still degenerates under sampling;
- the board's load;
- its memory.

So a fixed setting loses, and a serving layer that makes the choice at run time cuts energy per successful task.

## 2. Why it is not a setting (the professor's "isn't that common sense?")

From the mentor's drone sample banks and the boards' measured cost curves (computed by us):

| Board, model | One more candidate costs | First-of-4 against one answer, energy per success | Best k at 1, 2, 4 agents | Best use of spare capacity |
| --- | --- | --- | --- | --- |
| Thor, gemma-26B (mixture of experts) | +81% per step at 4 | +12% (hard prompts), +25% (controls) | 1, 1, 1 | more agents |
| Orin 32, gemma-E4B (dense) | +5% per step at 4 | **−70%** | 8, 4, 1 (memory) | **candidates**: 2 agents × 4 candidates beat 4 agents × 1 (0.16 against 0.26 of one answer at one agent) |
| Thor-2, granite-8B (dense) | +10% per step at 4 (4K context), +23% (16K) | *live on traffic: CAND-T2 running* | to be computed | to be measured |

- **The answer flips with the model.** On the MoE, extra streams activate other experts. Sampling already removed its
  runaway answers (0 of 168 samples capped), so candidates only buy pass rate (56% → 70% on hard prompts), at more
  energy per success.
- **On the dense model, candidates are nearly free, and they double as an escape** from answers that still run to the
  cap under sampling (21 of 168 samples).
- **The best k falls with load, because of memory.** k = 8 at one agent, 4 at two, 1 at four.
- **A fixed k loses:** k = 1 costs 2.7× the adaptive choice on average over 1–4 agents.
- No fixed "use FP8", "pack N agents" or "use k candidates" reproduces this, because the right answer depends on run-time
  load and on the model.

## 3. Where the energy is (the professor's "is there an opportunity?")

P1's logs, all 25 edge configurations (waterfall):
- **Failed runs take most of the board energy** (13–98%, median 69%). That is P1's own headline.
- **Inside passing runs, one-at-a-time decoding is the largest avoidable part** (traffic 2–36%).
- **Reading prompts and tool waits are small**, which is why retention is out.
- **Stopping doomed runs is a weak core.**
  - The best fixed stop rule leaves at least 15% to the oracle in 24 of 25 configurations.
  - But an online predictor rarely beats it on unseen tasks (3 of 25), and does not hold the pass rate reliably even
    with task history.
  - A wrong "stop" costs a success, while a wrong "widen" costs a few percent of decode. So the success estimate is used
    where being wrong is cheap: to choose which steps get candidates.

## 4. The mechanism (sketch)

- **Inputs:** the model's measured cost curve (energy per step against width), the KV pool, the current load (agents
  and their contexts), and a rough risk estimate per step:
  - a retry after a failed attempt;
  - loop or cap signs;
  - the task's history.
- **Decision, at every agent call:** how many candidates to run (k ≥ 1) within the board's spare width and memory, and,
  when agents are admitted, whether to admit another agent or keep width for candidates.
- **Selection:** the first candidate to finish on its own, or a cheap check (the program parses; a tool call is
  well-formed).
- **Baseline it must beat (B\*):** P1's agents with model-card sampling, the best fixed number of agents per box, FP8 KV
  where the pool binds, and the best fixed k.

## 5. What we have, and what is missing

| Question | Status |
| --- | --- |
| Where does the energy go? | Done: waterfall, 25 configurations |
| Do candidates pay on drones? | Done on banks: yes on the Orin's dense E4B, no on Thor's MoE 26B. The E4B base is weak (15 of 168 sampled programs pass) |
| Do candidates pay on traffic? | **Running** (CAND-T1 gemma-26B, CAND-T2 granite dense; rules fixed before data) |
| Is the live traffic platform faithful to P1? | **Running** (TRF-3); P1's grader reproduces 336 of 336 of P1's grades |
| Does the choice matter live with several agents? | Not yet: needs fleets with candidates (the mentor's W1 harness, Thor-2 traffic fleets) |
| Do other dense models behave like E4B? | Partly testable now: granite's cost curve on Thor-2 is queued |

## 6. Overlaps and risks

- **Prior work:**
  - Parallel sampling with first-to-finish exists for math reasoning (short-m@k, SART): fixed k, no energy, no agents,
    no edge.
  - EdgeReasoning measures thinking budgets and parallel sampling energy on a Jetson: measurement only, no controller.
  - Continuum and Autellix schedule agent programs for latency.

  The novelty is the run-time choice between agents and candidates, driven by cost curve, load and memory, judged by
  energy per success on edge boards.
- **The dense case rests on E4B, a weak model.** The granite and traffic runs test whether it generalises.
- **On the MoE, candidates lose energy.** If every model worth deploying on a Thor is an MoE, the story narrows to the
  Orin-class boards.
- **Overlap with P1.** P1 owns the failed-energy observation and its offline policies (attempt budgets, step cutoffs).
  P5's part is the online, multi-agent decision.

## 7. Decisions this draft needs

1. **Sandesh and the mentor:** adopt "spend the board's width and memory: agents or candidates, chosen at run time" as
   the core?
2. **The professor:** is this the proposal he asked for?
3. **P1:** agree the split.

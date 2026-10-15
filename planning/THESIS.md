# P5 thesis: draft for discussion (TH-1)

**15 Oct 2026, draft 2 (13:00: goodput framing and the full menu of consumers added as suggestions).** Draft 1 (14 Oct) is in git. It led with stopping doomed runs; the predictor test (WF-3b)
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

**Suggested framing: useful utilization, or goodput (for the professor to decide).**
- Energy per successful task = average board power ÷ goodput, where goodput is successful tasks per hour. Successes per
  kJ is goodput per joule, the inverse of our metric.
- Raw utilization rewards waste: a runaway decode keeps the GPU fully busy. Useful utilization counts only work that ends
  in a correct answer.
- On P1's logs, a median **7%** of board energy went into the decode and prefill that passing runs needed (traffic 8%,
  drones 2%; priced at 4 requests decoding together; `waterfall.json`). That is a lower bound, because passing runs' tool
  waits and flight time count as overhead.
- Serving papers count goodput within a latency target. A deadline per task would make packing's latency cost (the
  mentor's fleets: p95 mission time 69 min → 3.5 h) part of the trade, which a run-time controller has to manage.
- **Suggested metrics:**
  - headline: energy per success (goodput per joule);
  - secondary: goodput within a deadline, and p95 task time;
  - explanatory: the useful-energy share.

  The deadlines are not set yet.

## 2. Why it is not a setting (the professor's "isn't that common sense?")

From the mentor's drone sample banks and the boards' measured cost curves (computed by us):

| Board, model | One more candidate costs | First-of-4 against one answer, energy per success | Best k at 1, 2, 4 agents | Best use of spare capacity |
| --- | --- | --- | --- | --- |
| Thor, gemma-26B (mixture of experts) | +81% per step at 4 | +12% (hard prompts), +25% (controls) | 1, 1, 1 | more agents |
| Orin 32, gemma-E4B (dense) | +5% per step at 4 | **−70%** | 8, 4, 1 (memory) | **candidates**: 2 agents × 4 candidates beat 4 agents × 1 (0.16 against 0.26 of one answer at one agent) |
| Thor-2, granite-8B (dense) | +10% per step at 4 (4K context), +23% (16K) | **−24% live on P1's traffic agent** ("weaker" by the rule; 8 against 6 of 10 passed; same total energy) | to be computed | to be measured |

- **The answer flips with the model.** On the MoE, extra streams activate other experts. Sampling already removed its
  runaway answers (0 of 168 samples capped), so candidates only buy pass rate (56% → 70% on hard prompts), at more
  energy per success.
- **On the dense model, candidates are nearly free, and they double as an escape** from answers that still run to the
  cap under sampling (21 of 168 samples).
- **The best k falls with load, because of memory.** k = 8 at one agent, 4 at two, 1 at four.
- **Against fixed settings, the gap is smaller than it first looks.** Always k = 1 costs 2.7× the adaptive choice over
  1–4 agents. But the best fixed k (4) is within 8% at the loads where it fits, and on Thor's MoE the adaptive choice
  is always k = 1, which a setting captures.
  - So the thesis rests on conditions that change during operation: agents arriving and leaving, contexts growing
    (the cost of 4 streams rises from 1.10× to 1.23× between 4K and 16K on granite), memory filling, and risky calls.
  - This is the missing Q2 bound (§6).
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

## 5. Every way to spend the spare capacity, and what each can attack

The board's slack has three parts: decode width (several streams cost little more than one), KV memory, and idle time
during tool waits. Its power can also be cut instead of used. Each consumer attacks a different part of the energy.
Sizes are median shares of all board energy across P1's configurations (`waterfall.json`).

| # | Way to spend it | Resource | What it attacks | Size: traffic / drones | Status |
| --- | --- | --- | --- | --- | --- |
| O1 | More agents per board (packing) | width, memory | one-at-a-time decoding | 17% / 5% | **Measured** on drones (the mentor's fleets: 2.3× less energy per success on Thor; the Orin is best at 4 agents). Traffic fleets **not tested** |
| O2 | Parallel candidates, first to finish wins | width | runaway (capped) calls | 7% / 37% | **Testing now.** Drone banks done (Orin dense −70%, Thor MoE +12–25%); traffic CAND-T2 (granite) and CAND-T1 (gemma) running on Thor-2, results today |
| O3 | Parallel candidates checked or voted on (run each candidate's program, keep the majority answer) | width, tool time | wrong answers | 16% / 34% | **Not tested** |
| O4 | Speculative decoding (draft or n-gram tokens verified in one pass; the same answers) | width | one-at-a-time decoding, per token | 17% / 5% | **Not tested**; SGLang supports it |
| O5 | Memory for longer contexts (FP8 KV, fewer agents) | memory | context overflow | 6% / 0% | **Measured** as a setting: FP8 doubles the pool and cuts energy per token 44% (CAP-J1, Orin 32) |
| O6 | A second, smaller model on the board (cascade, router or draft) | memory | wrong and runaway answers, at a lower cost per try | — | **Not tested** |
| O7 | Run the likely next tool call during a wait (prefetch) | idle time | tool waits | 0–7% | **Not tested** (small bucket) |
| O8 | Lower power mode or clocks when the width cannot be used | power | base power in every bucket | not measured | **Not tested**; P1 ran at locked maximum clocks |

Status: **Measured** = a result exists on P1's boards; **Testing now** = runs in progress; **Not tested** = an idea, no data yet.

The same table, for the presentation, is in `reports/2026-10-15-meeting/README.md` §2.

**What this means for the thesis:**
- **Packing (O1) and speculative decoding (O4) compete for the same width and the same bucket** (one-at-a-time decoding).
  Speculation is the obvious reviewer question ("why not just speculate?"). It must be measured, either in B\* as a
  fixed setting or as a third consumer the controller can choose.
- **Candidates (O2, O3) are the only consumers that attack failed runs, the largest bucket.** The selection rule decides which
  failures they reach:
  - first to finish catches runaways, which dominate drones and Thor's traffic;
  - a check or vote catches wrong answers, which dominate traffic on most boards.
- **A lower power mode (O8) is the "don't spend it" baseline.** It belongs in B\*, because P1 ran at locked maximum clocks.
- **Suggested scope:** the core is the run-time split of width and memory among agents, candidates and speculation.
  FP8 and the power mode join B\* as settings. The check or vote is a selection variant of candidates. Prefetch and a
  second model are named as future work.

## 6. What we have, and what is missing

| Question | Status |
| --- | --- |
| Where does the energy go? | Done: waterfall, 25 configurations |
| Do candidates pay on drones? | Done on banks: yes on the Orin's dense E4B, no on Thor's MoE 26B. The E4B base is weak (15 of 168 sampled programs pass) |
| Do candidates pay on traffic? | Granite (dense): **−24% energy per success, "weaker"** by the rule (needs 30% for "pays"), same total energy, 8 against 6 of 10 passed, one repeat. Gemma-26B (MoE): running |
| Is the live traffic platform faithful to P1? | **Running** (TRF-3); P1's grader reproduces 336 of 336 of P1's grades |
| Does the choice matter live with several agents? | Not yet: needs fleets with candidates (the mentor's W1 harness, Thor-2 traffic fleets) |
| Do other dense models behave like E4B? | Partly testable now: granite's cost curve on Thor-2 is queued |

## 7. Overlaps and risks

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

## 8. Decisions this draft needs

1. **Sandesh and the mentor:** adopt "spend the board's width and memory: agents or candidates, chosen at run time" as
   the core?
2. **The professor:** is this the proposal he asked for?
3. **P1:** agree the split.

# Parallel candidates: when do they pay? (WF-4, CAND-T1/T2)

**15 Oct 2026.** Two parts:
- **The bank analysis (done).** It uses the mentor's drone sample banks and cost curves (13–14 Oct, read-only copies in
  `~/work/mentor/` on the WS).
- **The live traffic experiment CAND-T1 (running on Thor-2).** Its plan and rules were fixed before data in
  [`PLAN.md`](PLAN.md).

Code: `analysis/candidates_bank.py` (committed before its results were read). Output: `candidates_bank.json`.

## Bank analysis: first-of-k computed from every subset of 8 sampled answers

**Method:**
- **Banks:** each bank holds 8 sampled answers per prompt (Gemma's model-card sampling), every program flown and
  graded by P1's check.
- **First-of-k:** for k = 1, 2, 4, 8, every k-subset is enumerated. The winner is the shortest answer that finished on
  its own. The pass rate is the winner's.
- **Cost:** the winner's length × the board's measured energy per decode step at A × k streams (A agents, each with
  k candidates) / A.
- **Memory:** A × (prompt + k × winner length) must fit the server's pool.
- **Range:** only measured widths (≤ 16 streams).

| Board, model, prompts | k = 1: winner tokens, pass | k = 4: winner tokens, pass | Energy per decode step, 4 streams against 1 | First-of-4 against one sampled answer, energy per success, one agent | Best k at 1, 2, 4 agents |
| --- | --- | --- | --- | --- | --- |
| Thor-1, gemma-26B (mixture-of-experts), 12 hard prompts | 9,850, 56% | 7,553, 70% | 1.81× | **+12%** (costs more) | 1, 1, 1 |
| Thor-1, gemma-26B, 9 control prompts | 5,904, 88% | 4,135, 88% | 1.81× | **+25%** | 1, 1, 1 |
| Orin-32-1, gemma-E4B (dense), 21 prompts | 7,192, 8.9% | 2,880, 12.6% | 1.05× | **−70%** | 8, 4, 1 (memory) |

![Energy per success against candidates per call, by load](candidates.png)

**What it shows:**
- **Mixture-of-experts on Thor: candidates buy success, not energy.**
  - First-of-4 raises the pass rate on hard prompts from 56% to 70%, and first-of-8 to 75%.
  - But each extra stream activates other experts, so 4 streams cost 1.81× per step.
  - Sampling had already removed the long degenerate answers: 0 of 168 samples hit the cap. So the winner is only
    23% shorter.
  - Energy per success rises 12–25%. The best k is 1 at every load.
- **Dense on the Orin: candidates are a large energy lever, and the best k must fall with load.**
  - Extra streams cost almost nothing (1.05× at 4).
  - E4B still runs into the cap under sampling (21 of 168 samples), so first-of-k doubles as an escape: the winner is
    60% shorter.
  - At one agent, first-of-4 cuts energy per success by 70%.
  - As agents are added, the 46K-token pool cannot hold all the candidates, so the best k goes from 8 to 4 to 1.
  - Against fixed settings: always k = 1 costs 2.7× the adaptive choice over 1–4 agents. But the best fixed k, 4, is
    within 8% of it at the loads where 4 candidates fit (1 and 2 agents), and it does not fit at 4. So at a steady load
    a well-chosen setting captures most of the gain. The run-time gain has to come from changing conditions: load,
    growing contexts, memory, and which calls are risky. That is not measured yet (the Q2 bound).
  - This rests on few successes: E4B passed 15 of 168 sampled programs.
- **Agents or candidates: on the Orin the board's capacity is better spent on candidates.**
  - Under the Orin's memory limit, the most efficient feasible point is 2 agents with 4 candidates each: 0.16 of one
    answer at one agent.
  - That beats 4 agents with one answer each (0.26). With more than 2 agents, the candidates no longer fit the pool.
  - On Thor's mixture-of-experts model it is the reverse: more agents always help, and candidates never do.
  - Whether to pack more agents or to widen each agent's risky calls depends on the model and the memory.
- **The decision depends on the model's cost curve, on how often it still degenerates under sampling, on load and on
  memory.** That is a run-time decision, not a setting. It is the shape of an answer to "isn't that just a
  recommendation?". But it holds on one of the two boards measured, with a weak model.

**A third board and model: granite-8B (dense) on Thor-2.** CAND-T2's calibration was measured on 15 Oct, 10:42–11:50,
with the mentor's design (forced 2,048-token outputs, 2 repeats) and our sampler (`costcurve_granite_thor2.txt`). Energy
per decode step, against one stream:

| Context | 2 streams | 4 streams | 8 streams | 16 streams |
| --- | --- | --- | --- | --- |
| 4K tokens | 1.02× | 1.10× | 1.24× | 1.55× |
| 16K tokens | 1.09× | 1.23× | 1.49× | 2.13× |

A dense model on Thor sits close to the Orin's E4B (1.05× at 4) and far from Thor's mixture-of-experts (1.81× at 4).
So the extra width is cheap because the model is dense, not because the board is an Orin. Longer contexts make each
extra stream dearer (1.10× → 1.23× at 4), so the right k also depends on the context, which grows during a traffic run.

**Caveats:**
- The call-level model treats a failed call's retry as an independent repeat at the same cost. It leaves out the
  reflection call and the flight time between attempts, which would favour k > 1 a little.
- The candidates are assumed to decode in lockstep until the winner finishes.
- The cost curves were measured at fixed widths with forced lengths.

## Live traffic experiment (CAND-T1)

Running on Thor-2 after the TRF-3 validation. See [`PLAN.md`](PLAN.md) for the arms (P1's greedy runs; one sampled
answer; first-of-4), the 12 tasks and the rules. Given the bank result on Thor's mixture-of-experts model, first-of-4 is
expected to cost energy on gemma-26B traffic too. The experiment checks whether traffic's chains of capped calls change
that, and what sampling alone does against P1's greedy protocol.

**CAND-T2, granite-8B (dense) on Thor-2: done (15 Oct, 11:50–17:26). Verdict by the rule fixed before the data:
"weaker".** First-of-4 cut energy per success by 24.1% against one sampled answer. "Pays" needed 30% or more.

| Arm | Runs | Passed | kJ per success | Total kJ | Winning tokens | Capped calls (gateway) |
| --- | --- | --- | --- | --- | --- | --- |
| G: P1 greedy, recorded (3 per task) | 30 | 15 | 151.5 | 2,273 | — | 8 (traces) |
| S1: one sampled answer | 10 | 6 | 126.1 | 757 | 105,213 | 2 |
| F4: first-of-4 | 10 | 8 | 95.7 | 766 | 79,206 | 0 |

- **First-of-4 cost no extra energy in total** (+1%, 766 against 757 kJ). The winners were 25% shorter (79K against 105K
  tokens). The losers decoded 170K tokens in parallel, at 1.10–1.23× per step on this dense model.
- **F4 passed every task S1 passed, and two more** (class-mix, compare-periods). Under the rule, a 2-pass difference is
  not read as an effect.
- **48 of 68 winners were not the first candidate,** so the race was real.
- **One repeat, 10 tasks.** The energy per success result rests on 6 against 8 passes.
- **G is P1's recorded greedy runs** from P1's box and time. Sampled answers (S1) are not worse than them here (6 of 10
  against 15 of 30).

- **A trace gap:** peak-start-end hit the agent's 1-hour workload timeout. P1's trace then keeps only the run's first
  call; the gateway logged 12, including the 2 capped ones. P1's recorded runs have the same gap, so trace-based counts
  undercount runs cut by the timeout in every arm. For S1 and F4 the gateway log is the full record.

**CAND-T1, gemma-26B (mixture of experts) on Thor-2: done (15 Oct, 17:28–22:47). Verdict by the rule fixed before
the data: "absent".** First-of-4 raised energy per success by 39.7% against one sampled answer, and it passed 3 fewer
tasks. The loss is more than 2 passes, so it is read as an effect.

| Arm | Runs | Passed | kJ per success | Total kJ | Winning tokens | Capped calls (gateway) |
| --- | --- | --- | --- | --- | --- | --- |
| G: P1 greedy, recorded (4 per task) | 48 | 28 | 83.4 | 2,335 | — | 31 (traces) |
| S1: one sampled answer | 12 | 10 | 64.6 | 646 | 178,118 | 5 |
| F4: first-of-4 | 12 | 7 | 90.2 | 631 | 95,319 | 1 |

- **Energy was not the problem.** Even at 1.81× per step for 4 streams, first-of-4 used slightly less energy in total
  (631 against 646 kJ). Its winners were 46% shorter, and the losers decoded 176K tokens in parallel.
- **Passes were the problem.** F4 lost day-summary, first-last-sighting, heavy-vehicle and unusual-vs-median, and
  gained viz-stacked-area.
  - In heavy-vehicle, the winning candidate answered from general knowledge after 3 steps ("heavy goods vehicles are
    generally restricted…") without reading the camera data. The first candidate to finish can be the one that gives up
    early.
  - unusual-vs-median hit the 1-hour workload timeout in F4.
- **What it means for the mechanism:** first-to-finish selects for speed. On granite that cut off runaways (winners 25%
  shorter, 2 more passes). On gemma it also selected premature final answers. The selection rule has to know what a good
  answer looks like:
  - a check, for example "do not accept a final answer before the agent has read the data";
  - or a vote over the candidates' answers (option O3).

  That is a design result, and it is one repeat on 12 tasks.
- **G is P1's recorded greedy runs,** from P1's box and time. One sampled answer (S1, 10 of 12) did better than them here
  (28 of 48), with fewer capped calls, as the drone banks suggested sampling would.

**Both traffic arms together (15 Oct).** Candidates cost little or no extra energy on P1's traffic agent on either
model, because the winners are shorter. Whether they pay depends on the selection rule:
- on the dense granite, first-to-finish gave −24% energy per success ("weaker");
- on the mixture-of-experts gemma, +40% ("absent"), because it picked premature answers.

The bank prediction (candidates cost energy on the mixture of experts, at an unchanged pass rate) was wrong in its
reason. Energy held; quality fell.

**Gateway check (15 Oct, 00:55, before the arms):** the first-of-k gateway was run against P1's client stack.
- **Client:** langchain 1.4.0, langchain-core 1.6.1, langchain-openai 1.6.0, langgraph 1.2.11, openai 3.8.0, with P1's
  agent module imported so that its sglang reasoning patch applies.
- **Setup:** `ChatOpenAI` built as P1 builds it (streaming with usage, temperature 0, seed 42), a two-tool `create_agent`
  loop, and granite-4.2-8b on the WS (SGLang 0.5.20, P1's parsers).
- **Results:**
  - Direct, k = 1 and k = 4 all completed the task, with tool calls, reasoning and usage intact.
  - At k = 4 every call ran 4 candidates. Each had one winner, the rest were aborted, and different candidates won.
  - SGLang 0.5.16 on Thor-2 accepts the `rid`, `top_k` and `seed` fields the gateway sends.

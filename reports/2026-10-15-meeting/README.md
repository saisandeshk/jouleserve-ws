# P5 for the professor: where the energy goes, and what we propose

**Draft, 15 Oct 2026.** This brief prepares the next meeting, on 16 Oct; the presentation is built from it. It answers the questions of
14 Oct (D23). Sources:
- the energy waterfall ([`../2026-10-14-waterfall/`](../2026-10-14-waterfall/README.md));
- the candidates analysis ([`../2026-10-15-candidates/`](../2026-10-15-candidates/README.md));
- the thesis draft ([`../../planning/THESIS.md`](../../planning/THESIS.md));
- the mentor's drone fleets (her doc, 14 Oct);
- the live traffic runs on Thor-2 (§3; both candidate verdicts are in; TRF-3's last 2 tasks were rerun at the end).

## The short answer

1. **Is there an opportunity?** Yes, and it is in decoding.
   - Runs that fail take a median 69% of board energy. That is P1's own headline.
   - Inside passing runs, decoding one request at a time is the largest avoidable part: 2–36% of traffic energy,
     median 17%.
   - Reading prompts and tool waits are small, which is why retention is out.
2. **What do we propose?** A serving layer that spends the board's spare decode width and KV memory in two main ways (§2's options table lists the others, O1–O8):
   - on **more agents** (packing);
   - on **parallel candidates** for an agent's risky calls (first of k sampled answers wins).

   It chooses between them at run time, from the model's cost curve, the load and the free memory, to cut energy per
   successful task.
3. **Why is it not a setting?** The right choice flips:
   - **with the model:** on P1's live traffic agent, first-of-4 cut energy per success by 24% on the dense granite (two more
     passes of 10 at the same total energy, inside the rule's 2-pass noise), and raised it by 40% on the
     mixture-of-experts gemma (three fewer passes of 12). One repeat each. The drone banks show the same split: −70% on the
     dense E4B, +12–25% on the 26B;
   - **with the load:** the best number of candidates falls from 8 to 4 to 1 as agents are added (the Orin's bank model,
     which rests on 15 passing programs of 168; not measured live);
   - **with the selection rule:** on gemma, the first candidate to finish was once a premature answer, given without reading
     the data (heavy-vehicle). Which candidate to keep is part of the design.

   At a steady load, though, the best fixed k comes close: on the Orin, fixed k = 4 is within 8% of the adaptive choice
   where it fits. The case for a run-time choice therefore rests on changing conditions (load, context length, memory,
   risky calls), which is the next analysis (§5).
4. **What did the workstation work bring?**
   - It closed retention with numbers: at most 3.2% on the board.
   - It built the platform: a gateway with first-of-k, replayers, cost models, and P1's grader reproduced exactly.
   - Every result in this brief is from P1's boards or P1's logs.

## 1. The opportunity: where P1's board energy went

![Where P1's board energy went](../2026-10-14-waterfall/waterfall.png)

The data is all 25 of P1's edge configurations (17 traffic, 8 drone), from P1's final data with P1's selection rule and
grades.

| Bucket | Share of board energy | Whose finding |
| --- | --- | --- |
| Runs that fail | 13–98%, median 69%; over half in 22 of 25 | P1's paper reports it |
| Decoding one request at a time, in passing runs (priced at 4 together) | traffic 2–36% (median 17%); drone 1–34% (median 5%) | ours |
| Degenerate decoding (calls run to the cap) in passing runs | large on Thor gemma; small elsewhere | P1 (loops) and ours |
| Reading prompts (prefill) | 0–4% | ours, and P1's |
| Tool waits | 0–7% | ours |

**Useful utilization is about 7%.** Only a median 7% of P1's board energy went into the decoding and prompt reading that
passing runs needed, priced at 4 requests decoding together. That is traffic 8% and drones 2%, and it is a lower bound,
because passing runs' tool waits and flight time count as overhead. Seen this way, our metric is goodput per joule:
energy per success = average board power ÷ successful tasks per hour (a suggested framing; THESIS.md §1).

- **Stopping doomed runs is not our core.**
  - The best fixed stop rule leaves at least 15% to the oracle in 24 of 25 configurations.
  - But an online predictor beats that rule in only 3 of 25 on unseen tasks.
  - It also cuts too many passes even when it knows the task's history: both bars are met in 5 of 25.
  - A wrong "stop" loses a success, while a wrong "widen" costs a few percent of decode. So we use the risk estimate
    only to choose which calls get candidates.
- **The two halves of "spare capacity" are visible in P1's logs.** P1 ran one request at a time, so:
  - the decode width the board could add almost for free went unused;
  - so did most of the KV pool on Thor. In our simulation on P1's traces (5 Oct), 8 traffic agents fit Thor's pool and
    cut energy per completed task by 2.2× (gemma) to 3.8× (granite). On the Orins, the pool binds after 2–4 agents.

## 2. The proposal: agents or candidates, chosen at run time

![Energy per success against candidates per call, by load](../2026-10-15-candidates/candidates.png)

The figure and the drone numbers come from the mentor's drone sample banks: 8 sampled programs per prompt, each flown
and graded, combined with each board's measured energy per decode step. The live traffic numbers are from Thor-2 (§3).

| Board, model | Cost of 4 streams against 1, per step | First-of-4 against one answer, energy per success | Best k at 1, 2, 4 agents | Best use of spare capacity |
| --- | --- | --- | --- | --- |
| Thor, gemma-26B (mixture of experts) | 1.81× | Drone banks: +12% (hard prompts), +25% (controls); passes 56% → 70%. **Live traffic: +40%**, 10 → 7 of 12 passed, same total energy | 1, 1, 1 | more agents |
| Orin 32, gemma-E4B (dense) | 1.05× | **−70%**; passes 8.9% → 12.6% | 8, 4, 1 (memory) | candidates: 2 agents × 4 beat 4 agents × 1 (0.16 against 0.26 of one answer at one agent) |
| Thor-2, granite-8B (dense) | 1.10× (4K context), 1.23× (16K) | **Live traffic: −24%**, 6 → 8 of 10 passed, same total energy (within the 2-pass noise) | to be computed | candidates, by its cost curve |

- **Why the answer flips with the model.**
  - On a mixture-of-experts, each extra stream wakes other experts, so width is expensive. Sampling already removed its
    runaway answers.
  - On a dense model, width is nearly free. Candidates double as an escape from answers that still run to the cap.
- **Why it flips with the load.** k candidates per agent must fit the KV pool. As agents are added, the best k falls
  (bank model; not measured live).
- **The mechanism**, at every agent call:
  - **Inputs:** the model's cost curve, the free KV memory, the agents on the board, and a cheap risk estimate (a
    retry after a failure, signs of a loop or cap, the task's history).
  - **Decision:** how many candidates to run (k ≥ 1). At admission, it also decides whether to take another agent or to
    keep width for candidates.
  - **Selection:** the first candidate that finishes on its own wins, or one that passes a cheap check (it parses, the
    tool call is well-formed).
- **The baseline it must beat (B\*)** is P1's agents with every fixed setting that helps:
  - model-card sampling;
  - the best fixed number of agents per box;
  - FP8 KV where the pool binds;
  - the best fixed k.

  The bar is 15% better in energy per success at the same pass rate (ENERGY_PLAN §5).

### Options for the professor: every way to spend the spare capacity

**For the presentation: one slide with this table.** The professor chooses among the options. O1, O2 and O5 have
measurements, and the rest are ideas.

The board's slack has three parts:
- decode width (several streams cost little more than one);
- KV memory;
- idle time during tool waits.

Its power can also be cut instead of used. Each option attacks a different part of the energy. Sizes are median shares
of all of P1's board energy (`../2026-10-14-waterfall/waterfall.json`).

| # | Way to spend it | Resource | What it attacks | Size: traffic / drones | Status |
| --- | --- | --- | --- | --- | --- |
| O1 | More agents per board (packing) | width, memory | one-at-a-time decoding | 17% / 5% | **Measured** on drones (the mentor's fleets: 2.3× less energy per success on Thor; the Orin is best at 4 agents). Traffic fleets **not tested** |
| O2 | Parallel candidates, first to finish wins | width | runaway (capped) calls | 7% / 37% | **Measured** on traffic, one repeat each: granite (dense) −24% energy per success; gemma (MoE) +40%, with 3 fewer passes at the same total energy (in one lost task, heavy-vehicle, the fastest candidate was a premature answer). Drone banks: Orin dense −70%, Thor MoE +12–25% |
| O3 | Parallel candidates checked or voted on (run each candidate's program, keep the majority answer) | width, tool time | wrong answers | 16% / 34% | **Not tested**; the gemma result points here |
| O4 | Speculative decoding (draft or n-gram tokens verified in one pass; the same answers) | width | one-at-a-time decoding, per token | 17% / 5% | **Not tested**; SGLang supports it |
| O5 | Memory for longer contexts (FP8 KV, fewer agents) | memory | context overflow | 6% / 0% | **Measured** as a setting: FP8 doubles the pool and cuts energy per token 44% (CAP-J1, Orin 32) |
| O6 | A second, smaller model on the board (cascade, router or draft) | memory | wrong and runaway answers, at a lower cost per try | — | **Not tested** |
| O7 | Run the likely next tool call during a wait (prefetch) | idle time | tool waits | 0–7% | **Not tested** (small bucket) |
| O8 | Lower power mode or clocks when the width cannot be used | power | base power in every bucket | not measured | **Not tested**; P1 ran at locked maximum clocks |

Status: **Measured** = a result exists on P1's boards; **Testing now** = runs in progress; **Not tested** = an idea, no data yet.

**What the table says:**
- **O4 is the first gap a reviewer will find.** Speculative decoding uses the same width as packing (O1) and attacks
  the same bucket. "Why not just speculate?" needs a measured answer: in B\* as a setting, or as a third choice for the
  controller.
- **Only candidates (O2, O3) attack failed runs, the largest bucket.** The selection rule decides which failures they
  reach:
  - first to finish catches runaways, which dominate drones and Thor's traffic;
  - a check or vote catches wrong answers, which dominate traffic on most boards.
- **O8 is the "don't spend it" baseline.** P1 ran at locked maximum clocks, so a lower power mode belongs in B\*.
- **Suggested scope:**
  - the core is the run-time split of width and memory among O1, O2 and O4;
  - O5 and O8 join B\* as settings;
  - O3 is a selection variant of O2;
  - O6 and O7 are future work.

## 3. Evidence on P1's boards

**Drones: the mentor's fleets.** These are N copies of P1's Reflexion drone agent, unchanged, on one board with
SGLang's default scheduler. The numbers come from her run summaries, read on the units on 15 Oct at 01:00, and from
her doc for P1's single-drone column.

| Board, model, missions | Drones per board | Passed | kJ per success | Missions per hour | p95 mission time |
| --- | --- | --- | --- | --- | --- |
| Thor-1, gemma-26B (MoE), 21 hard missions | 1 (P1, recorded) | about 17.3 expected | about 131 | about 2.3 | about 69 min |
| | 4 | 16 | 80.3 | 4.5 | 2.3 h |
| | 8 | 17 | **58.2** | 6.0 | 3.5 h |
| Orin-32-1, gemma-E4B (dense), 36 missions | 2 | 17 | 35.7 | 7.5 | 29 min |
| | 4 | 17 | **25.7** | 11.1 | 1.8 h |
| | 8 | 17 | 29.0 | 9.8 | 2.2 h |

- **Packing pays on both boards at the same pass count.** On Thor, 8 drones cost 2.3× less per success than P1's
  single drone.
- **The best number of agents differs by board.** Thor is still improving at 8. The Orin is best at 4 and 13% worse at 8,
  probably because E4B's 46,645-token pool binds (one run per point; P1's traffic logs showed the same on Orin pools,
  §1).
- **Packing's price is each mission's latency.** p95 mission time grows nearly 4× from 2 to 4 agents on the Orin, and
  rises to 3.5 h at 8 on Thor.
- **The open question for the controller:** on the Orin, the bank analysis says the capacity past 2 agents is better
  spent on candidates (2 agents × 4 candidates). A live test, not yet scheduled, would be a 2-drone fleet with first-of-4
  against the 4-drone fleet above.
- **Since then:** step-wise fleets (a different agent and task set, so not comparable with the table) finished on
  Thor-1 (gemma-26B, 14 missions: 10 passed at 93 kJ per success with 4 drones, 64 kJ with 8) and on Orin-32-1 (E4B,
  12 missions: 5 passed at 37 kJ with 4, 6 at 31 kJ with 8). Steady-state fleets are running on Thor-1 and the Orins
  (logs read 15 Oct, 23:00). Details are in her doc.

**Traffic: P1's agent, unchanged, on Thor-2 (ours, 15 Oct).**
- **Is the platform faithful to P1? Yes, on the 7 tasks run before the crash.** TRF-3 ran gemma-26B with P1's greedy protocol, graded by P1's grader (which
  reproduces 336 of 336 of P1's grades), on 7 of 9 tasks; Thor-2's crash cut the other 2, which were rerun at the end of the chain.
  - We passed 7 of 7, where P1 passed 22 of 28 on the same tasks.
  - Our energy lies within P1's own min–max on 5 of 7 tasks.
  - Per generated token, our energy is within 3–7% of P1's on 5 of 7 tasks.
  - Where we differ, the agent took a different path (more calls), as P1's own repeats do.

  Details: [`../2026-10-14-traffic-agent/`](../2026-10-14-traffic-agent/README.md).
- **Do candidates pay on a dense model?** CAND-T2 runs granite-8B on 10 tasks, one sampled answer (S1) against
  first-of-4 (F4). The rules were fixed before the data.
  - **Verdict: "weaker"** (the rule needed 30% for "pays"). First-of-4 cut energy per success by 24% (126 → 96 kJ),
    with the same total energy (757 → 766 kJ). It passed 8 of 10 tasks against 6 of 10, including every task the single
    answer passed; a 2-pass difference is not read as an effect, and
    the whole gain is those 2 passes, so the verdict is fragile. The winners were 25% shorter. This is one repeat on 10
    tasks. P1's greedy runs of the same tasks (another setup) passed 15 of 30 at 152 kJ.
  - Granite's cost curve on Thor is in: 4 streams cost 1.10× per step at a 4K context and 1.23× at 16K. Extra width is
    cheap on a dense model on Thor too.
- **And on the mixture-of-experts?** CAND-T1 runs gemma-26B on 12 tasks, S1 against F4.
  - **S1 done (17:28–20:13):** one sampled answer passed 10 of 12 at 65 kJ per success, with 5 capped calls. P1's greedy
    runs of the same tasks (another setup) passed 28 of 48 at 83 kJ, with 31 capped calls.
  - **Verdict: "absent".** First-of-4 raised energy per success by 40% (65 → 90 kJ) and passed 7 of 12 against 10.
    Energy was not the problem: its total was slightly lower (631 against 646 kJ), because the winners were 46%
    shorter. Passes were the problem: it lost day-summary, first-last-sighting, heavy-vehicle and unusual-vs-median, and
    gained viz-stacked-area. In heavy-vehicle the fastest candidate answered from general knowledge after 3 steps,
    without reading the camera data; unusual-vs-median hit the 1-hour timeout. First-to-finish rewards speed, and a
    premature answer is fast.
- **What the two traffic results say together:** candidates cost little or no extra energy on P1's agent with either
  model, because the winners are shorter. Whether they pay depends on the model and on the selection rule. A check
  ("no final answer before the data is read") or a vote (O3) is the next design step.
- **An edge lesson from the platform:** P1's server flags reserve 80% of Thor's unified memory for the model server.
  Our live agent run exhausted the rest and crashed the board (15 Oct, 01:24). Memory left beside the server is part of
  the capacity problem the controller must manage, not a fixed setting.

## 4. The critiques of 14 Oct, answered

| Critique | Answer |
| --- | --- |
| "What did the WS experiments bring?" | They closed retention with numbers, built the platform, and found the decode-width lever. All new results are on P1's boards |
| "FP8 to enlarge the pool is common sense, just a recommendation" | Agreed. FP8, packing and sampling are settings. They join B\*, the baseline we must beat by 15% |
| "Multiple agents help, so what?" | Packing alone is a setting. What is not a setting is how to split spare width between agents and candidates: the split flips with the model and the load, and packing costs latency (p95 69 min → 3.5 h) |
| "How does it look as a paper?" | See the outline below |

**Paper outline (working):**
- **Claim:** edge boards serving LLM agents waste their spare decode width and memory. A serving layer that spends them
  on agents or on candidates, chosen at run time, cuts energy per successful task against the best fixed configuration.
- **Measurement:** the energy waterfall over P1's 25 configurations. Where the joules go, and what is avoidable.
- **Design:** the controller (inputs, decision, selection), inside SGLang's serving path, through our gateway.
- **Evaluation:**
  - 2 agent families (traffic, drones), each with P1's agents unchanged except for sampling;
  - Thor and Orin boards, MoE and dense models, 1 to N agents;
  - against P1 as run and against B\*;
  - energy per success, pass rate, p95 latency.
- **Related work:**
  - parallel sampling with first-to-finish for reasoning (short-m@k, SART): fixed k, no energy, no agents;
  - EdgeReasoning (energy of reasoning on a Jetson): measurement only;
  - agent schedulers (Continuum, Autellix): latency, not energy.

## 5. Path to OSDI (abstract 1 Dec, paper 8 Dec)

| By | What | Who |
| --- | --- | --- |
| 18 Oct | **The decisive bound (Q2-1):** run-time choice against the best fixed configuration under changing load, growing contexts and risky calls, offline. If it is under 15%, switch to the fallback below | Sandesh with Claude |
| 19 Oct | Candidates with a check (no final answer before the data is read) against first-to-finish, gemma traffic on Thor-2 | Sandesh with Claude |
| 20 Oct | Speculative decoding (O4) measured on Thor-2, and the power mode (O8) if Sandesh allows changing P1's clock settings; both for B\* | Sandesh with Claude |
| 25 Oct | The controller, first version, in the gateway. B\* measured on traffic (Thor-2) and drones (the mentor's fleets) | Sandesh with Claude; the mentor |
| 8 Nov | Live fleets with the controller: traffic on Thor-2 and an Orin, drones on Thor and the Orins | both |
| 22 Nov | Full evaluation, ablations, sensitivity (pool size, model) | both |
| 1 Dec | Abstract | both |
| 8 Dec | Paper | both |

**Fallback:** if no run-time policy beats B\* by 15%, the paper becomes a measured design space. That is the waterfall,
plus the agents-against-candidates map per board and model. We tell the professor as soon as that is clear.

## 6. Decisions for the professor

1. Is "spend spare width and memory on agents or candidates, chosen at run time" the proposal he asked for?
2. Candidates need sampling, while P1 ran greedy. Is switching to the model card's sampling an acceptable, justified
   change to P1's agents?
3. If candidates pay only on dense models (the Orin class), is a story centred on Orin-class boards acceptable? Or must
   it hold on Thor's mixture-of-experts too, where packing alone wins?
4. **The metric's framing:** energy per success presented as goodput per joule, with a deadline per task so that
   latency counts? The deadlines would have to be chosen per workload.
5. **Scope:** do speculative decoding and the board's power mode go into B\* as settings, or into the controller as
   run-time choices?
6. **The split with P1:** failed-run energy and offline stop policies stay P1's. P5 claims the online, multi-agent
   decision. Is that right?

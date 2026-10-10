# P5 options: the even-handed case and the WS versions — plan

Status: **v1.2** (2026-10-11). v1.0 was approved by Sandesh on 2026-10-05 (decisions D13–D17 as proposed; capacity
is in; our lean is stated once, separately, at the end of the comparison). Work started the same evening.
- **G1 is done (2026-10-06):** the comparison, [`../reports/2026-10-06-options/README.md`](../reports/2026-10-06-options/README.md)
  (CMP-2), is with Sandesh for review. Each evidence task's outcome against its decision rule is in §2.5.
- **v1.1 changes:** §2.5 (outcomes), §3.1/§3.3 as built, D13's outcome, D18 (RET-E1's comparison method), outcomes
  in §7. G2 continues after Sandesh's review.
- **v1.2 (2026-10-11), after P1's submission (10 Oct):** no change to the plan's structure. P1's submitted paper and final
  data are in CMP-2 §12. Two consequences here: (1) CAP-E1's "Gemma-4 FP8 KV cannot start on Ampere" is narrowed to our
  A5000s with SGLang 0.5.20, since P1 ran it on an Orin 64 with 0.5.16 (§2.5); (2) the Orin replays (RET-E1, CAP-E1)
  are redone on P1's re-run sessions, tracked as P1F-1 to P1F-6 in [`TRACKER.md`](TRACKER.md). P1's post-submission
  MB4 and MB5 overlap A-E1/A-E2 and CAP-E1; the split is a question for the professor meeting on Mon 12 Oct (D12).
- **Tracker:** [`TRACKER.md`](TRACKER.md). This plan changes rarely; the tracker changes every working session.
- **Relation to the master plan:** [`JOULESERVE_WS_PLAN.md`](JOULESERVE_WS_PLAN.md) milestones M3–M5 assume a
  retention/admission gateway and are on hold. Until the professor's direction decision (D12), this plan
  replaces them. M0–M2 pieces that exist are reused (`HANDOFF.md` §3).
- **Facts behind it:** `HANDOFF.md` §2 and §4, the evidence summary
  [`../reports/2026-10-02-p5-evidence/README.md`](../reports/2026-10-02-p5-evidence/README.md), and the
  feasibility checks of 2026-10-05 (§9 below).

---

## 0. Why this plan

The professor chooses P5's direction (D12). The meeting will not happen before Sat 10 Oct, so we use the time
on two goals at once.

- **G1. The even-handed case.** Build a case for every option with the same criteria, so the professor can
  choose with the pros, cons and open gaps side by side. Where an option has a gap that a cheap experiment
  can fill, run it.
- **G2. The WS versions.** Build working WS versions of the options ahead of time, so that whichever option
  the professor picks, we are already days into it.

**Principles.**
1. **Shared parts first, option-specific policies second.** A serving gateway, a trace replayer, P1's models
   on the WS and one run format serve every option. Little is wasted whichever way the decision goes.
2. **Evidence and prototypes stay apart.** A working prototype makes an option look more mature without
   making it more worth studying. The comparison reports prototypes in a separate box.
3. **One template, one set of criteria per option** (§2.2). Every option gets its strongest case and its
   strongest objection.
4. **Decision rules are written before the experiment runs** (§2.4). Results are reported against them,
   null results included.
5. **Lean.** The smallest experiment that answers the question. Negative results count.

## 1. The options as of 2026-10-05

| Option | What P5 would study | Strongest current evidence | Biggest gap | Where the edge enters |
| --- | --- | --- | --- | --- |
| **A. Decode-side energy** | Stopping runaway decodes online, retrying, thinking budgets, batching long decodes | Capped calls take 67–69% of board energy (drone, Thor gemma), 38% (traffic, Thor gemma), 33% (Orin 32 E4B traffic) [P1-meas]. An online loop stop saves 43.5% / 35.7% and stops no finished call [P1-meas, replayed] | Do the loops vanish under sampling (a configuration fix)? What happens after a stop? Novelty against reasoning-length work (unread) and P1's paper | Board power, weak batching on MoE models, one agent saturating a device |
| **B. Agent design** | A step-wise agent with flight-level tools on P1's tasks | 5–13× less energy per success than P1's Reflexion (0.9–9.6× under the strict check) [proj from WS-meas]; 4–16 drones per Thor instead of 2 [sim] | Measured with Qwen3.5/K2, not P1's Gemma; sim has no buildings; it is P1's territory | Drones per device; the agent's step size against the price of a generated token |
| **C. Standard benchmarks with injected waits** | The original retained-state question on τ²-bench/BFCL | Easy comparison with prior work (Continuum and Adaptive KV Retention use these) [lit] | **No measurement at all.** Is there an opportunity, or does it collapse like traffic? | Only through injected waits and the device's prices; otherwise not edge-specific |
| **D. Memory that changes over time** | Admission/retention when model-backed tools or co-located models take and release memory | The vision burst evicts the paused context on Orin 64 (62 of 62 calls) [P1-meas]; gap to unlimited memory 33–64% at 8 agents [sim] | Worth only 0.6% of LLM time at one agent; unmeasured with several agents; P1 may say `ask_vlm` is a separate server | Unified memory, small pools, tools that run models on the same board |
| **CAP. Capacity** (candidate, see §8) | KV precision, fixed-prompt size and tool-output caps as levers, at run time or as configuration | Doubling the pool cuts energy per completed task 31–46% at 8 agents [sim]; window overflows end 11–21% of Orin runs [P1-meas] (up to 28% in P1's final data of 10 Oct) | Does FP8 KV cost quality on these agents? Is it more than configuration? | Small pools on 32–64 GB boards shared by weights, KV and tools |

**Not an option, but behind all of them: RET**, the retention/admission controller on P1's workloads. Its
negative result (SGLang's default within 2.4% of every policy for traffic, 9.9% for drones) [sim] is the reason
the options exist. It rests on simulation, so G1 also anchors it with one live check (RET-E1).

Source tags used throughout: **[P1-meas]** measured on P1's Jetsons; **[WS-meas]** measured on the WS;
**[sim]** our simulator; **[proj]** projected with a cost model; **[lit]** a paper (re-check against the PDF
before citing).

## 2. Goal G1: the even-handed case

### 2.1 Output

A separate comparison doc, `reports/2026-10-06-options/README.md`, started from existing evidence and filled
as results arrive. It is merged into the evidence doc and the deck later (Sandesh's choice, 2026-10-05).

Outline:
1. **The decision in one paragraph:** what the professor chooses between, and what is already ruled out (RET).
2. **Side by side:** options × criteria (§2.2), one line per cell with its source tag.
3. **One section per option, same template:**
   - what P5 would study, and the claim a paper could make;
   - evidence for, evidence against (numbers with source tags);
   - open gaps, and what this week's experiments filled;
   - novelty against prior work and against P1's paper;
   - edge specificity: what needs a Jetson, what the WS can show;
   - feasibility and cost to a paper; dependence on P1;
   - risks, and what would change our mind;
   - **separate box:** what the WS version shows (G2).
4. **Cross-cutting:** RET and its live anchor; the overlap map with P1's paper; combinations (for example A + D
   in one serving layer).
5. **Questions for the professor.**
6. **Method, data and caveats.**

### 2.2 Criteria (the same for every option)

| # | Criterion | What counts |
| --- | --- | --- |
| K1 | **Prize** | Share of P1's measured energy (or energy per success) at stake, and on which configurations |
| K2 | **Evidence strength** | Measured on P1's devices > measured on the WS > simulated > projected > literature; sample sizes |
| K3 | **Novelty** | Against Track B prior work (plus this week's reviews) and against P1's paper |
| K4 | **Edge specificity** | Why it matters on a Jetson; whether the WS can show it or it needs a device |
| K5 | **Generality** | Whether it holds beyond P1's two workloads, its agents and its models |
| K6 | **Feasibility** | What is built, what is left, the risk of not finishing within the ISP |
| K7 | **Dependence on P1** | Devices, data, code, agreement, overlap with P1's paper |
| K8 | **Risk** | What would kill it |

### 2.3 Rules for even-handedness

1. Each option section makes the strongest case first, then the strongest objection.
2. WS stand-ins are labeled as such (for example a 4-bit Gemma is not P1's bf16 Gemma).
3. Prototype results go in the separate box and are never counted as evidence for the research value.
4. Every experiment has a decision rule fixed before it runs (§2.4).
5. Our lean is stated once, separately, at the end (open question for Sandesh, §8).
6. Numbers are re-checked against their source before the doc goes to anyone (AGENTS.md §7).

### 2.4 Evidence tasks

Each task names its decision rule. The thresholds are proposals for Sandesh to confirm (D15).

| ID | Option | Question | Method (short) | Decision rule (proposed) | Needs | Effort |
| --- | --- | --- | --- | --- | --- | --- |
| **A-E1** | A | Do Gemma-4's loops survive sampling? | Replay P1's recorded capped prompts and finished controls; greedy (P1's) vs Gemma's default sampling | See spec | S1, S4 | 3 h + 3–10 GPU-h |
| **A-E2** | A | After an online stop, does a retry finish usefully, and at what cost? | Same prompts: stop where the detector fires, retry three ways, check the output | See spec | A-E1, S4 | 4 h + 2–4 GPU-h |
| **A-E3** | A | What does reasoning-length and early-exit work already cover? | Literature review, review docs in `review/systems/` | Novelty paragraph for A with the closest 3–5 works | — | 4–6 h (background) |
| A-E4 | A | What are traffic's capped tool calls? | Analysis of P1's traffic traces only (arguments, tools, sizes); no replay possible | Report only | — | 2 h |
| A-E5 | A, sim | How well do long decodes batch on Gemma-4 (MoE) vs dense models? | `jsw/costs/calibrate.py`: J/token against batch 1–16 at 4K/16K/32K context | Report; feeds the simulator's batching model | S1 | 2 h + 2 GPU-h |
| **B-E1** | B | Does P1's own model keep its steps short in a step-wise agent? | aerogen driver with gemma-4-E4B (P1's weights) and the 4-bit 26B on D1–D3 | See spec | S1 | 3 h + 4 GPU-h |
| B-E2 | B | What do the step-wise projections become with Gemma's step sizes? | Rerun `stepwise_ceiling` and the Thor projection with B-E1's runs | Report | B-E1 | 2 h |
| B-E3 | B | What does agent-design literature say (code-as-action, ReAct, plan-and-execute, drone agents)? | Short literature review | Novelty paragraph for B | — | 2–3 h (background) |
| **C-E1** | C | Does τ²-bench have a retained-state opportunity? | τ²-bench on the WS, single sessions, then injected waits through S3 | See spec | S1, (S3) | 6–8 h + 4 GPU-h |
| **RET-E1** | RET, D, CAP | Do the simulator's results hold on a live engine? | Replay P1's granite traffic runs live on granite at P1's pool sizes, N = 1–8, three policies; compare with the simulator | See spec | S1, S2, S3, S5 | 4 h + 6–8 GPU-h |
| **D-E2** | D | Is the vision burst worth more than 0.6% with several agents? | Replay P1's Orin 32 E4B traffic runs on E4B with real image bursts at small pools; default, pin, burst admission | See spec | S1–S3, D-P1 | 5 h + 4–6 GPU-h |
| D-E3 | D | What does unified-memory and co-located-model work cover? | Short literature review (mzCache and newer) | Novelty paragraph for D | — | 2 h (background) |
| **CAP-E1** | CAP | Does an FP8 KV cache cost quality on these agents? | Pool size and loop/finish rates with FP8 vs bf16 KV on A-E1 controls and a B-E1 subset | See spec | S1, A-E1, B-E1 | 2 h + 3 GPU-h |
| CAP-E2 | CAP | What does KV quantization and prompt/tool-loading work cover? | Short literature review | Novelty paragraph for CAP | — | 2 h (background) |
| **CMP-1** | all | Comparison doc skeleton from existing evidence | Write §2.1's outline with today's numbers | Sandesh reviews the template | — | 4 h |
| CMP-2 | all | Full comparison | Fill from all tasks above | Sandesh's review | all | 6–8 h |

Outcomes: §2.5.

#### A-E1 — do the loops survive sampling?

- **Prompts:** P1's recorded capped Thor prompts. All have full `messages`:
  - 122 Reflexion calls (repository), 121 of which our detector flags as loops;
  - 143 tool-calling calls (`data/p1_thor_toolcalling/`): 127 at 32,768 tokens, all loops, plus 16
    evaluator calls at 1,024 that are not runaways and are left out;
  - controls: the 173 long Reflexion calls that finished on their own.
- **Model:** the 4-bit gemma-4-26B-A4B on one GPU (D13). gemma-4-E4B (P1's exact weights) is a check on its own
  5 capped drone generator prompts from Orin 32.
- **Arms:**
  - greedy as P1 ran it (temperature 0, top_k 1, seed 42, thinking on, `max_tokens` 32,768);
  - Gemma's default sampling (temperature 1.0, top_k 64, top_p 0.95, from its `generation_config.json`),
    3 seeds.
- **Measures:** loop flag (online detector, S4), finish reason, output tokens, time, NVML energy, whether the
  final output parses as Python and calls only P1's drone API.
- **Cost control:** the greedy arm stops when the detector fires, since only "does it loop" is asked. Pilot
  first: 60 loop prompts + 40 controls × 1 seed, then the full set.
- **Decision rule (proposed):**
  - **Reproduction check first:** greedy on the WS must loop on ≥ 50% of the prompts that looped on the Thor.
    If it does not, the quantized stand-in does not reproduce P1's behaviour: the result is inconclusive and
    we say so (fallback in §7).
  - **"Sampling removes the loops"** if sampled runs loop on ≤ 10% of those prompts (Wilson 95% interval
    reported) and the controls do not get worse (finish rate, valid programs).
  - Between the two: sampling reduces but does not remove loops; an online stop is still needed as a guard.

#### A-E2 — stop and retry

- **Prompts:** A-E1's looping prompts under greedy.
- **Stop:** where the online detector fires (median 35% of the call on the Thor).
- **Retry variants:** R1 the same prompt resampled with Gemma's defaults; R2 greedy with a short nudge
  appended ("your previous attempt repeated itself; write the final program now"); R3 a lower `max_tokens`.
- **Measures:** does the retry finish; tokens and energy to finish, against P1's recorded path; valid program
  (parses, P1's API only).
- **Stretch:** execute the program in our x86 headless AirSim (legacy build) and grade it with P1's
  deterministic checker (`data/p1_aeroeval_src/final_sweep/_harness/verdicts.py`) for a real pass or fail.
  Feasibility not yet checked.
- **Decision rule (proposed):** "stop and retry preserves runs" if ≥ 70% of retries end with a valid program at
  ≤ 50% of the recorded call's energy. This is the part of A that P1's paper does not have: P1 gives only
  an upper bound for stopping at the first cap.

#### B-E1 — P1's own model in a step-wise agent

- **Setup:** the existing aerogen driver (`--task-file`, `--world-prompt`, `--runtime-prompt`) on P1's D1–D3
  task texts, 3 instances each, 50× pacing, strict checker. SGLang's `gemma4` tool-call and reasoning parsers.
- **Configurations:** E4B and 26B-4bit; thinking on (P1's setting); greedy and sampled. 9 missions each.
- **Measures:** output tokens per step after a tool result, planning-call length, runaways, delivered-all and
  strict pass, prompt growth and reuse.
- **Decision rule (proposed):** if the median output after a tool result is ≤ 300 tokens (the Thor break-even
  for re-prefilling a 20K context), B's projection holds for P1's model family. Above it, the projection is
  redone with Gemma's sizes (B-E2).

#### C-E1 — τ²-bench

- **Setup:** `sierra-research/tau2-bench` (MIT, active) in its own venv. The agent model on one GPU (gemma-4-E4B
  or Qwen3.5-9B, thinking on and off); the user simulator on the same server or the other GPU.
  Domains: airline, retail, telecom; 20–50 tasks, single session.
- **Measures:** calls per task, prompt growth per step, output per step, cache reuse, task reward, and the
  ceiling P/(P + r·O) at the WS's r and at the Jetsons' r (52–312).
- **Then:** replay the runs through S3 as N sessions with waits injected from P1's distributions (flights:
  median 17–113 s; traffic tools 0.5–3 s; vision tool 53–158 s).
- **Decision rule (proposed):** C has a retained-state opportunity worth a full comparison if the per-step
  ceiling at a Jetson r is ≥ 20% of LLM time. If it is below 10%, C collapses for the same reason traffic does.

#### RET-E1 — live anchor for the simulator (also D's and CAP's baseline)

- **Workload:** P1's granite-4.2-8B traffic runs (Orin 64 and Orin 32 granite: the configurations where
  capacity binds), replayed by S3 on granite-4.2-8B on one A5000. The model and the token counts are P1's;
  only the GPU differs.
- **Pools:** P1's real pools (32,768 and 26–27K tokens) and half of them, as far as the WS pool allows
  (measured in S1).
- **Policies run live:** SGLang's default; keep (soft pin with `--enable-session-radix-cache` and
  open/close session); no reuse (a unique cache salt per call, the "drop at every wait" bound).
- **N:** 1, 2, 4, 8 agents; 2 h per point to start.
- **Simulator side:** `traffic_sim` with a WS granite device model fitted with `calibrate.py`.
- **Decision rule (proposed):** the anchor holds if live and simulated energy per completed task agree within
  ±15% at every point, and the three policies rank the same. If not, the negative result is restated with the
  live numbers.

#### D-E2 — the vision burst with several agents

- **Workload:** P1's Orin 32 gemma-E4B traffic runs, which include 50 `ask_vlm` calls, replayed on gemma-4-E4B
  (P1's weights, multimodal).
  - During each recorded `ask_vlm` window S3 sends the recorded number of concurrent image requests (running
    requests: median 23).
  - Their size is set so that peak KV matches the vitals stream.
- **Pools:** 12.4K tokens (Orin 64 gemma's) and 71K (Orin 32 E4B's).
- **Policies:** default; pin the paused context during the tool (session soft pin or priority); admit the
  burst at most k requests at a time; both (D-P1).
- **N:** 1, 2, 4 agents.
- **Measures:** recomputed tokens after the tool, energy per completed run, the tool's own time (admission
  slows it), run time.
- **Decision rule (proposed):** D's prize at N agents is the best policy against the default in energy per
  completed run. It is reported next to the 0.6% single-agent number. If it stays < 5% at 4 agents, D's live
  case is small.
- **Depends on P1's answer** about which server `ask_vlm` calls. If it is a separate server, the emulation
  becomes a second SGLang server sharing the GPU (still option D, a different mechanism).

#### CAP-E1 — FP8 KV quality

- **Setup:** check which `--kv-cache-dtype` values SGLang 0.5.20 accepts on Ampere (to check in S1). Pool size
  with FP8 vs bf16 KV for granite and E4B.
- **Quality:** A-E1's finished controls and a B-E1 subset with FP8 KV: loop rate, finish rate, valid programs,
  delivered/strict pass.
- **Decision rule (proposed):** no measurable degradation means capacity is a free configuration choice: a
  finding to report to P1, and CAP weakens as a research option. Degradation means a run-time trade-off
  exists (a CAP or D angle).

### 2.5 Outcomes against the decision rules (2026-10-06)

Details, numbers and caveats: the comparison doc, §3–§8. [WS-meas] unless marked.

| Task | Rule | Outcome | Verdict |
| --- | --- | --- | --- |
| A-E1 | Reproduction: greedy on the WS loops on ≥ 50% of the Thor loop prompts; then "sampling removes the loops" if sampled runs loop on ≤ 10% of them and the controls do not get worse | E4B (SGLang) never loops, even on its own Orin 32 loop prompts. A 4-bit GGUF of P1's 26B through llama.cpp (D13's outcome): greedy loops on 23/30 loop prompts (77%, CI 59–88%) and 6/20 controls; Gemma's default sampling on 0/30 and 0/20, 28/28 valid programs (one seed) | 26B: **sampling removes the loops**; E4B: inconclusive (no reproduction) |
| A-E2 | Stop and retry preserves runs if ≥ 70% of retries end valid at ≤ 50% of the recorded call's energy (tokens as the proxy) | Resample: 17/17 re-looping calls recovered, 28/29 valid overall, but only 10/29 at ≤ 50% cost (median 19.7K vs 32.8K tokens). Nudge: 7 of 10 retries loop again. Budget: dropped | **Not met**: a safety net, costlier than sampling from the start |
| A-E4 | Report only | Repeated capped `run_python` calls hold 33% (Thor gemma) and 31% (Orin 32 E4B) of traffic LLM-call energy [P1-meas] | — |
| A-E5 | Report only | Batch 1 → 16 cuts energy per token 13× (granite) and 13.5× (E4B) | — |
| B-E1 | Short steps if the median output after a tool result is ≤ 300 tokens | E4B: median 63 (greedy) / 68 (sampled); strict pass 9/11 and 7/13; 9 of 33 missions lost to a tool-format bug (fixed, not re-run) | **Met** |
| B-E2 | Report only | 26–27 kJ per strict success greedy, 35–40 sampled, vs P1's Reflexion 284–499 kJ (Thor prices) [proj] | — |
| C-E1 | Opportunity if the ceiling is ≥ 20% of LLM time at a Jetson r; collapses if < 10% at every r | Thinking on: 7.5% / 9.9% at E4B's r, 16–24% at Thor's drone r (retail ≥ 20%). Thinking off (airline): 25% at E4B's r | Thinking on: **borderline** (the rule fires for retail only at Thor's drone prices); thinking off: **opportunity** |
| D-E2 | D is worth more than the burst's 0.6% if the best policy beats the default by > 5% at 4 agents | Mechanism reproduced (88–100% of the paused prefix recomputed at 12.4K). Best at 4 agents: pin, −3.8%; pin + cap 2 cuts recompute to 37% at one agent but costs +11% | **Not met**: within 5% |
| RET-E1 | Anchor holds if live and simulated energy per completed task agree within ±15% at every point and the policies rank the same | Run narrower than specified (GPU time): Orin 32 granite only, P1's pool only (no half pools, no Orin 64), N = 1, 4, 8, two policies (default, no reuse; keep not run), 45 min per point. Within 14.2% at every point (2% except N = 4); FP8 run out of sample within 6.4%. Ranking: a tie in both, because at N = 8 the default keeps nothing (0/102 calls hit) | **Met** on the points run (ranking degenerate) |
| CAP-E1 | No measurable FP8 degradation means capacity is free configuration; degradation means a trade-off | FP8 KV doubles granite's pool (53,296 vs 26,648) and cuts energy per session 62% at 8 agents. Gemma-4 FP8 KV cannot start on our A5000s in SGLang 0.5.20, so the quality pairs did not run (P1 ran it on an Orin 64 with SGLang 0.5.16: not an Ampere-wide limit, corrected 11 Oct) | **Undecided** (quality side not measured) |

## 3. Goal G2: the WS versions

### 3.1 Shared base (every option needs these)

| ID | Piece | Where | What it does | Done when | Effort |
| --- | --- | --- | --- | --- | --- |
| **S1** | P1's models on the WS | `env/launch_*.sh`, `AGENTS.md` §6b | Download and pin: gemma-4-26B-A4B 4-bit (17.2 GB), gemma-4-E4B (16.0 GB), granite-4.2-8b (17.6 GB); offline mode. Smoke tests: chat, thinking on/off, the `gemma4` tool parser, images (E4B), `/metrics` fields (SWA pool), pool size at the chosen mem fraction, FP8 KV dtype options | Each model serves a tool call and reports its pool; recipe and gotchas in AGENTS.md | 4–6 h |
| **S2** | Gateway v0 | `jsw/gateway/` | Async OpenAI-compatible proxy in front of SGLang. Per-session routes `/s/<sid>/v1/...` and a native `/s/<sid>/generate` passthrough. Streams upstream even when the client does not, so policies can watch tokens. Per-call log (P1-compatible superset). Policy hooks `on_request` (forward, delay, modify, reject), `on_chunk` (continue or abort), `on_complete`, `on_tick` (`/metrics`). Abort through `/abort_request` and disconnect | Unit tests with a fake upstream; K2 and Gemma smoke; added latency measured (target < 5 ms per call) | 8–10 h |
| **S3** | Trace replayer | `jsw/workloads/replay.py` | Plays recorded runs (P1 traffic and drone via `analysis/p1_repo.py`, WS aerogen runs) as N closed-loop agents against the gateway. SGLang's native `/generate` with synthetic token IDs gives exact prompt lengths. Each call's prompt is the previous prompt + the previous **generated** IDs + a synthetic tool result, so prefix reuse is real. Outputs held to the recorded length (`ignore_eos`, `max_new_tokens`). Tool gaps replayed as waits. Optional vision-burst injection. Seeds and task mix as in the simulator | Replays one P1 run with prompt and output lengths within 1% and cache hits as expected; runs N = 8 | 8–10 h |
| **S4** | Streaming loop detector | `jsw/policies/loop_detector.py` | The online detector of `analysis/p1_loops.py` (4,000- and 16,000-character windows, every 1,000 characters, fires after 3 checks below 10%) as an incremental class shared by the analyses and the gateway | Reproduces the offline flags exactly on P1's 265 capped and 173 finished calls | 2 h |
| **S5** | Runner and manifest | `jsw/runner/` | One run directory format, manifest (git SHA, versions, server flags, model revision, GPU state, seeds), sampler start/stop, teardown check; factored out of `aerogen_driver.py` | aerogen driver, replayer and A-E1 all write the same format | 3 h |
| S6 | Analysis helpers | as built: `jsw/workloads/loop_replay.py` (A-E1/A-E2 replays), `analysis/{a_e1,a_e2,a_e4,b_e1,b_e2,c_e1,d_e2,ret_e1,cap_e1,options_figures}.py` | A-E1/A-E2 tables and figures; live-vs-simulator comparison for RET-E1 and D-E2 | Figures for the comparison doc | 4 h |

Open technical checks for S2/S3, made at the start of S2: whether `/generate` returns the output IDs for an
`input_ids` request; whether a client disconnect aborts the request in 0.5.20; how `ignore_eos` interacts with
Gemma's three EOS IDs.

### 3.2 Option versions

First wave (Sandesh's choice: the shared base plus A and D; others if time allows):

| ID | Option | Version | Built on | Evaluated with | Done when |
| --- | --- | --- | --- | --- | --- |
| **A-P1** | A | **Decode guard**, a gateway policy. Streams every call through S4. When a loop is detected, one of three actions: return what was generated with `finish_reason=length`, so the agent's own retry applies (an earlier P1 cap); stop and retry inside the gateway (the agent sees one call); stop and retry with a nudge. A per-session rule stops after k consecutive capped calls (traffic). A thinking-budget hook is reserved for after A-E3 | S2, S4 | A-E2's prompts (offline), and live with aerogen on Gemma (step-wise; greedy thinking to provoke loops) | Energy per success and runs lost against no guard, on both |
| **D-P1** | D | **Burst-aware memory**, a gateway policy. Tool-originated requests are tagged (route `/s/<sid>/tool/v1` or a header). Policies: pin the paused context while a known long tool runs (session soft pin or priority); admit tagged requests at most k at a time when pool use passes a threshold; both | S2, S3 | D-E2 | Energy per completed run against the default at N = 1, 2, 4 |

Upgrades, if time is left (in this order):

| ID | Option | Version | Blocker |
| --- | --- | --- | --- |
| A-P2 | A | P1's CLGSCE agent live on the WS (x86 AirSim, P1's harness, real pass/fail) behind A-P1 | The two CLGSCE files changed on the Thor on 23 Sep must come from P1; Sandesh's OK to run P1's code |
| C-P1 | C | τ²-bench through the gateway with the published baselines (default, keep, discard, INFERCEPT-style min-waste, Continuum-style TTL) | C-E1 says there is an opportunity |
| D-P2 | D | The simulator with a memory budget that changes over time (bursts, co-located models) | D-E2 |
| B-P1 | B | Step-wise agent with a building-aware sim (collision check in aerogen's kinematic sim) | mayankarya's OK to extend aerogen |
| CAP-P1 | CAP | Capacity-aware admission (window and pool guard) | CAP-E1 says there is a trade-off |

### 3.3 Code layout (new pieces)

As built (2026-10-06):

```
jsw/gateway/      server.py (routes, streaming, call log, policy hooks, abort), pythonic.py (text tool-call fallback)
jsw/policies/     base.py (hook interface), loop_detector.py, decode_guard.py (A-P1), burst_memory.py (D-P1)
jsw/workloads/    replay.py (S3), loop_replay.py (A-E1/A-E2); aerogen_driver.py (existing)
jsw/runner/       run.py (S5: manifest, samplers, energy over a window)
jsw/costs/        calibrate2.py (prefill, decode against batch and context, NVML energy)
env/              launch_model.sh (gemma-e4b, granite8b, 26B attempts), launch_llamacpp.sh (26B GGUF),
                  fetch_models.py, smoke_model.py, sync_ws.sh, queue_*.sh (WS-side tmux queues)
analysis/         a_e1, a_e2, a_e4, b_e1, b_e2, c_e1, d_e2, ret_e1, cap_e1, options_figures, loop_prompts, replay_sets
tests/            test_gateway (fake upstream), test_pythonic_gateway, test_loop_detector (offline parity)
```

## 4. Order of work

Sandesh said to work without stopping and not to worry about dates, so the plan is a sequence of waves, not a
calendar. GPU0 and GPU1 run independent streams. Literature reviews run in the background (subagents) and need
no GPU.

| Wave | GPU0 (cores 0–9, 20–29) | GPU1 (cores 10–19, 30–39) | No GPU |
| --- | --- | --- | --- |
| 0 Setup | S1: 26B-4bit smoke | S1: E4B and granite smoke | CMP-1 skeleton; A-E3, B-E3, D-E3, CAP-E2 start; τ²-bench venv; S4; S5 |
| 1 | A-E1 pilot, then full | B-E1 | S2 gateway v0; S3 replayer |
| 2 | A-E2 + A-P1 v0 | granite calibration, RET-E1 | C-E1 when a GPU is free; S6; A-E4 |
| 3 | A-E5, CAP-E1 | D-E2 + D-P1 v0 | B-E2 |
| 4 | Upgrades (§3.2) | Upgrades | CMP-2; Sandesh's review; HANDOFF, then merge into the evidence doc and the deck |

Each wave ends with the tracker updated, runs copied to `data/ws_runs/`, and GPUs back to idle.

**As run (5–6 Oct):** waves 0–3 and CMP-2 finished on 2026-10-06 08:40; the order changed with D13's outcome (the
26B moved to llama.cpp, A-E1 ran first on E4B) and P1's data reaching the WS. The merge into the evidence doc, the
teaching guide and the deck (v2.1) was done the same day; wave 4's upgrades wait for Sandesh's review.

## 5. Experiment protocol (WS)

- The rules in `AGENTS.md` §4 and §6b hold: check `nvidia-smi` and `tmux ls` before launching, run long jobs
  in tmux, pin to the GPU's NUMA node, stop every server and confirm idle GPU memory afterwards.
- One tmux session per stream (`g0-<task>`, `g1-<task>`). Run directories `~/work/runs/<task>-<tag>/`; copy
  them back with `rsync` after each run.
- Every model is pinned to a revision and served with `HF_HUB_OFFLINE=1` after download (the K2 re-upload of
  2026-10-02).
- Every run has a manifest (S5). Energy is NVML GPU energy on the WS and is labeled as such; P1's numbers are
  board energy.
- **The Thor is off-limits** until Sandesh says otherwise (2026-10-05). P1's repository and our local copies
  are the only P1 sources.
- Code is developed in `~/jsw-dev` (rsync) and committed to `main` at milestones; the WS clone pulls.

## 6. Decisions

D12 stays the professor's direction decision (open). New decisions in this plan:

| ID | Decision | Status |
| --- | --- | --- |
| D13 | Stand-in for gemma-4-26B-A4B on the WS: the 4-bit compressed-tensors checkpoint (`cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`, 17.2 GB) on one GPU; FP8-dynamic over two GPUs as fallback | **outcome 2026-10-06:** neither runs on Ampere in SGLang 0.5.20 (4-bit MoE SiLU-only; FP8 MoE needs fp8e4nv). The 26B runs through llama.cpp as a 4-bit GGUF (unsloth UD-Q4_K_XL) for A-E1/A-E2; gemma-4-E4B elsewhere |
| D14 | The replayer drives SGLang's native `/generate` with synthetic token IDs and recorded lengths. Text effects (loops, tool parsing) are outside its scope; A-E1/A-E2 replay real text instead | **approved** 2026-10-05 |
| D15 | The decision rules in §2.4 | **approved** 2026-10-05 |
| D16 | The comparison criteria K1–K8 and template (§2.1–2.3) | **approved** 2026-10-05 |
| D17 | Capacity (CAP) as its own option in the comparison | **approved** 2026-10-05 |
| D18 | RET-E1's comparison method, fixed before its data arrived: the simulator stops at the live run's span (the live run cuts its last sessions), takes its powers from NVML's energy counter like the live energy (the power reading runs 24% above it), and a difference under 2% counts as a tie in the ranking | **taken** 2026-10-06 during G1 (Claude); for Sandesh to confirm |

## 7. Risks and fallbacks

| Risk | Fallback |
| --- | --- |
| The 4-bit Gemma does not run on Ampere in SGLang 0.5.20, or runs badly | FP8-dynamic over two GPUs; else E4B only, with the caveat that its drone loops are few (5). **Happened:** neither ran; llama.cpp served a 4-bit GGUF instead (D13) |
| The quantized Gemma does not loop under greedy decoding (A-E1's reproduction check fails) | Report it as inconclusive; run E4B on its own capped prompts; defer the Gemma-26B test to a Thor after 10 Oct. **Happened for E4B** (no loops at all); the 26B GGUF did loop |
| The `gemma4` tool parser fails with aerogen's tool calls | Patch at run time in the driver (as for K2's `reasoning_content`); else run B-E1 with thinking off first |
| `/generate` cannot give exact lengths or output IDs | Use the chat API with a tokenizer-checked synthetic text; accept ±2% length error |
| granite's pool on one A5000 is below P1's Orin pools | Run the half-pool cells and the largest pool that fits; label it |
| τ²-bench's user simulator is too weak on small local models | Use the stronger local model as the user; or switch to BFCL multi-turn, which needs no user model |
| Building the prototypes biases the comparison | Rule 3 of §2.3: prototypes in a separate box |
| P1 says `ask_vlm` is a separate server | D-E2 emulates a co-located second server instead (§2.4) |
| P1 pushes new data mid-way | Rerun the affected analyses (`HANDOFF.md` §6 item 3) after Sandesh agrees to the pull |
| The WS goes offline again | Short runs, copied back after each; analyses run locally. **Changed:** the laptop proved the weak link (power cuts, RAM bit flips), so runs became WS-side tmux queues and analyses run on the WS |

## 8. Sandesh's answers (2026-10-05)

1. The plan is approved, with the decision rules (D15) and the criteria (D16) as proposed.
2. Capacity (CAP) is its own option (D17).
3. The comparison states our lean once, separately, at the end.
4. Workflow: keep working without stopping; run long jobs in the background and continue when they finish;
   update the tracker at fixed points; **stop and report to Sandesh when G1 is reached**.

## 9. Feasibility facts checked on 2026-10-05

- **SGLang 0.5.20** (legacy venv): Gemma-4 model code (`gemma4_causal.py`, `gemma4_mm.py`), `gemma4`
  tool-call and reasoning parsers, granite, Qwen2.5-VL; `compressed_tensors_wNa16_moe` (the 4-bit MoE path);
  `/abort_request`, `/pause_generation`; sessions, `priority` eviction and preemption (`review/systems/sglang-kv.md`).
- **Models on Hugging Face** (ungated):
  - gemma-4-26B-A4B-it: 25.8B parameters, 30 layers (5 full, 25 sliding window of 1,024).
  - 4-bit version: 17.2 GB; FP8-dynamic: 28.7 GB.
  - gemma-4-E4B-it: 8.0B parameters, 16.0 GB, 42 layers (7 full, 35 sliding window of 512), 2 KV heads,
    multimodal.
  - granite-4.2-8b: dense `GraniteForCausalLM`, 40 layers, 8 KV heads, 17.6 GB.
  - Gemma-4's default sampling: temperature 1.0, top_k 64, top_p 0.95.
- **P1's traces:**
  - Every drone LLM call holds the full prompt messages and outputs: all 265 capped Thor calls replay
    exactly.
  - Traffic traces hold the token counts and the assistant turns. Tool results are empty and the tool
    definitions are absent, so traffic replays only by token counts.
- **τ²-bench:** `sierra-research/tau2-bench`, MIT, last pushed 2026-09-28.
- **WS:** 258 GB disk free, 251 GB RAM, both GPUs idle; legacy venvs, aerogen copy and x86 AirSim build intact.

## 10. Earlier labels

The options first offered to Sandesh on 2026-10-05 map to this plan as follows:

| Earlier label | This plan |
| --- | --- |
| W1 | A-E1 |
| W2 | A-E2, A-P1 |
| W3 | S3, RET-E1 |
| W4 | D-E2, D-P1 |
| W5 | A-E5 |
| W6 | CAP-E1 |
| W7 | A-P2 |
| W8 | A-P1's thinking-budget hook, after A-E3 |
| W9 | C-E1/C-P1, B-E1/B-P1 |

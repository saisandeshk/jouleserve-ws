# P5's options side by side: the evidence for and against each

**Draft (CMP-1), 2026-10-06 · Sai Sandesh (P5)**, prepared with Claude Code. Plan:
[`../../planning/OPTIONS_PLAN.md`](../../planning/OPTIONS_PLAN.md) (G1); task status:
[`../../planning/TRACKER.md`](../../planning/TRACKER.md).

This doc lays out every option P5 could take, with the same criteria and the same template, so the professor
can choose with the pros, cons and open gaps side by side. It is a separate doc for now, to be merged into the
evidence doc and the deck later. Sections marked **[pending: task]** are filled as this week's experiments
finish. Our own lean is stated once, at the end (§9), and nowhere else.

Source tags: **[P1-meas]** measured on P1's Jetsons (board energy); **[WS-meas]** measured on our workstation
(NVML GPU energy); **[sim]** our simulator; **[proj]** projected with a cost model; **[lit]** a paper (depth as
stated in the literature notes `lit_*.md`; re-check against the PDF before citing).

## 1. The decision

P5 asked how an edge serving system should manage the state an agent holds while it waits for a tool, to
minimise energy per successful task on Jetson Orin and Thor. On P1's agents, that question is answered mostly
"no": kept state is worth 1–4% of LLM time, and no memory policy beats SGLang's default by more than 2.4%
(traffic) or 9.9% (drones) in simulation (RET, §7). So the professor chooses what P5 studies instead, or whether
it stays with retained state in another form:

| Option | In one line |
| --- | --- |
| **A. Decode-side energy** | Stop runaway decodes online in the serving layer, retry well, budget thinking, batch long decodes |
| **B. Agent design** | A step-wise agent with flight-level tools uses far less energy per success than P1's whole-program agents |
| **C. Standard benchmarks with injected waits** | The original retained-state question, on τ²-bench/BFCL with P1-like waits |
| **D. Memory that changes over time** | Admission and retention when model-backed tools or co-located models take and release unified memory |
| **CAP. Capacity** | KV precision, fixed-prompt size and tool-output caps as levers, as configuration or chosen at run time |

Combinations are possible (§8).

## 2. Side by side

The criteria (plan §2.2, D16): **K1** prize, **K2** evidence strength, **K3** novelty, **K4** edge specificity,
**K5** generality, **K6** feasibility, **K7** dependence on P1, **K8** risk.

| | A. Decode-side | B. Agent design | C. Benchmarks + waits | D. Memory over time | CAP. Capacity |
| --- | --- | --- | --- | --- | --- |
| **K1 Prize** | Capped decodes: 67–69% of board energy (drone, Thor gemma), 38% (traffic, Thor gemma), 33% (Orin 32 E4B traffic), 0–19% elsewhere [P1-meas] | With P1's own E4B: 26–27 kJ per strict success on D1–D3 against P1's Reflexion 284–499 kJ (11–19×) [proj from WS-meas] | Unknown: no measurement yet **[pending: C-E1]** | Vision burst: 0.6% of LLM time at one agent [P1-meas]; several agents **[pending: D-E2]** | Doubling the pool: −31–46% energy per task at 8 agents [sim]; overflows end 11–21% of Orin runs [P1-meas] |
| **K2 Evidence** | Energy measured; P1's 26B (4-bit) on the WS loops on 23/30 of P1's loop prompts under greedy and on 0/30 with Gemma's default sampling [WS-meas] | Step sizes measured with P1's E4B (24 missions) and projected; still no Jetson run | None | Mechanism read from server counters; multi-agent unmeasured | Simulated; FP8 quality on these agents unmeasured **[pending: CAP-E1]** |
| **K3 Novelty** | Partly covered: loop stop + recovery (Word Salad Chopper), energy-motivated agent stop (AgentStop), stop + restart (Fail-Fast), early exit in SGLang (Dynasor); P1's paper reports the loops [lit] | Direction known (Cost of Dynamic Reasoning, Sustainable Agents, CodeAct, AeroGen); this exact comparison not found [lit] | Generic version published (INFERCEPT, Continuum, TokenCake, Adaptive KV Retention, CacheScout) | Elastic KV (Prism/kvcached, MorphServe) and tool-aware pinning (Continuum, MORI) exist; tool foreknowledge on unified memory not found [lit] | Each lever studied (TriAxialKV, Less-is-More, CarbonCall, Complexity Trap, FP8 KV); a run-time controller across levers not found [lit] |
| **K4 Edge** | Decode is 96–99% of LLM time on Jetsons; board power; weak MoE batching | Drones per device; the price of a generated token | Weak: edge only through injected waits and prices | Strong: unified memory, model-backed tools on one board | Strong: small pools on 32–64 GB boards |
| **K5 Generality** | Any thinking agent; greedy loops are model-general [lit] | Task-dependent; delivery tasks only | High | Agents with model-backed tools | High |
| **K6 Feasibility** | Detector, gateway and decode guard built (§3) | aerogen driver exists; needs a building-aware sim | τ²-bench (MIT) and the gateway; needs a user-simulator model | Gateway and replayer built; burst policy to build | Configuration; small study |
| **K7 Dependence on P1** | High: P1's paper claims the loop finding; split to agree | High: agent design is P1's territory | Low | Medium: P1's answer on `ask_vlm`; devices for real unified memory | Medium: P1 proposed these remedies (MB5, not run) and deferred its KV-pool sweep (E4) |
| **K8 Risk** | Realised for drones: sampling removes the loops (a configuration fix for P1); what is left is smaller | Attributable to agent engineering; strict range includes parity | Waits are synthetic; may collapse like traffic | Effect small; a 2026 elastic-KV paper found ~1% | A good static setting may capture it all |

## 3. A. Decode-side energy

**What P5 would study.** The serving layer watches each call as it streams, stops a call that has started to
repeat itself, and decides what happens next (return it capped, retry it resampled, nudge it, give it less
budget), judged by energy per successful task and runs lost. Plus thinking budgets, and how long decodes from
several agents share a device.

**The claim a paper could make.** "On edge devices running thinking agents, most energy is spent in decodes
that run to their cap. An online, text-only stop in the serving layer with a retry policy recovers X% of energy
per successful task, losing Y runs, where sampling alone recovers Z%."

**Evidence for.**
- Capped calls take 67–69% of board energy for both drone agents on Thor gemma, 38% for traffic on Thor
  gemma and 33% for Orin 32 gemma-E4B traffic; 0–19% elsewhere [P1-meas].
- In drone runs they are repetition loops: 121 of 122 capped Reflexion calls and 127 of 127 tool-calling
  calls capped at 32,768 [P1-meas, our detector on recorded text].
- An online stop at the detector's firing point would save 43.5% (Reflexion) and 35.7% (tool calling) of
  board energy and stop none of the 173/194 long calls that finished on their own (upper bound; P1's
  first-cap rule saves 50.2% / 63.1% but loses 22 / 16 passing runs) [P1-meas, replayed].
- In traffic, the waste is a capped tool call that is dropped and retried: 121 of 158 capped calls on Thor
  gemma follow a capped call; stopping at the second consecutive cap saves 27% (1 completed run lost), 25% on
  Orin 32 E4B (7 lost) [P1-meas].

**Evidence against.**
- The cause is greedy decoding: on the WS, P1's 26B loops on 77% of P1's loop prompts under greedy and on none
  under Gemma-4's own default sampling (A-E1, below); Qwen3.5 ran away only under greedy too (0 of 21 sampled
  missions) [WS-meas]. So the drone fix is configuration.
- P1's paper now reports the loop finding itself (offline detector, stop-at-first-cap bound).
- The traffic workload is ungraded, so "runs lost" there counts completions, not correct answers.

**Novelty** (`lit_A.md`; 25 works). Partly covered. Published: stopping reasoning that repeats itself and
recovering with a forced conclusion (Word Salad Chopper, EMNLP 2025; Circular Reasoning, 2026), energy-motivated
early termination of local agents (AgentStop, CAIS 2026), stop-and-restart for agents (Fail-Fast
Restart-Smart, 2026), early exit inside SGLang (Dynasor), thinking budgets evaluated on Jetson Orin
(EdgeReasoning). Not found: the combination of an engine-side, training-free text detector for thinking-on agent
calls, a retry policy for capped tool-call bodies, and energy per successful task on Jetson boards, including the
cost of wrong stops. Moderate novelty, mostly empirical.

**Edge specificity.** On P1's Jetsons decode is 96–99% of LLM time and prefill 0.7–3.4% of board energy; board
power stays high through a runaway decode. Weak batching on mixture-of-experts models (a 16-request decode step
takes ~5.3× one on Thor gemma [sim fit]) makes one runaway hold the device. Board energy needs a Jetson; the WS
can replay P1's exact prompts on a stand-in model.

**Dependence on P1.** P1 owns the observation; P5 could own the online mechanism and its evaluation (Sandesh:
build now, agree the split after 10 Oct). P1's prompts are needed on the WS GPUs for A-E1/A-E2 **[waiting:
Sandesh's permission]**.

**What would change our mind.** This happened for the drone agents: sampling removes the loops on P1's 26B
without hurting finished calls (A-E1). A now rests on the traffic agent's repeated caps, a safety net, and
budgets; A-E2 tests the safety net.

**This week.**
- **A-E4, traffic's capped calls** (`a_e4.json`; P1's traces) [P1-meas]:
  - On gemma the waste is a few runs looping through capped `run_python` calls: on Thor gemma 121 of 158 capped
    calls follow a capped call, chains run up to 21 calls, and the repeats after a run's first cap hold 33% of its
    LLM-call energy. Orin 32 E4B: 64 of 76, chains up to 20, 31%.
  - Where the text survives, the cap hits inside a dropped `run_python` body (30 on Thor gemma, 62 of 76 on E4B)
    or inside the reasoning (21 on Thor gemma). Granite caps mostly inside its reasoning and rarely repeats
    (repeats ≤ 3% of energy); Orin 64 gemma's caps are all the context guard (capacity).
  - Runs with a cap complete 4 of 33 times on Thor gemma but 10 of 11 on E4B: on E4B the retries eventually work,
    at great cost, so a blunt stop would lose completions where a better retry might keep them.
- **A-E1, do the loops survive sampling?** (`a_e1.json`; P1's recorded prompts replayed exactly) [WS-meas]:
  - **gemma-4-E4B does not loop on the WS, even greedy:** 0 of 60 of the 26B's Thor loop prompts (95% upper bound
    11%), 0 of 40 controls, and 0 of its own 5 Orin 32 loop prompts under greedy or two sampled seeds. Every call
    finished, in a median 1.9-4.4K tokens. Under the pre-registered rule this is inconclusive (no reproduction),
    and it says loops depend on more than greedy decoding: on the model, and apparently on the serving stack or
    device (E4B looped on all 5 on P1's Orin 32; P1 reports inference varying between repeats there).
  - **P1's gemma-4-26B-A4B through llama.cpp (4-bit GGUF; SGLang cannot run any 26B on our GPUs) reproduces the
    loops under greedy, and Gemma's default sampling removes them** (P1's Thor Reflexion prompts, 30 that looped
    and 20 that finished on P1's device; one sampling seed):

    | | Greedy (P1's protocol) | Gemma's default sampling |
    | --- | --- | --- |
    | Looped on P1's Thor (30) | **23 loop (77%; 95% CI 59-88%)**; 7 finish | **0 loop (0-11%)**; 29 finish, 28/28 programs valid |
    | Finished on P1's Thor (20) | 6 loop (30%) | 0 loop; 20 finish |
    | Output tokens, median (loop prompts) | 11,574 (stopped by the detector) | 8,136 |
    | GPU energy for the 50 prompts | 685 kJ (loops stopped early) | 483 kJ |

    The greedy loops trip the detector at a median 11.6K tokens, as P1's did on the Thor (35% of 32,768). The
    4-bit model loops somewhat more readily than P1's bf16 one (6 of 20 controls). Verdict under the
    pre-registered rule: **sampling removes the loops**.

    ![A-E1](figures/a_e1_loops.png)

  - **What this means for A.** The largest energy item in P1's drone runs (capped decodes, 67-69% of board energy
    on Thor gemma) looks like a decoding configuration problem: P1 runs temperature 0, the model's own
    generation config samples (temperature 1.0, top_k 64, top_p 0.95). The fix for P1 is one line, and it belongs
    in P1's paper. What remains for P5 under A is the safety net (an online stop for residual loops, A-E2's
    retries), the traffic agent's repeated capped tool calls (A-E4), budgets and batching of long decodes.
- A-E2 (stop and retry) **[pending: queued on the 26B]**; A-E5 (batching) **[partial: granite done]**.

> **WS version (G2).** Built: the streaming loop detector (`jsw/policies/loop_detector.py`; fires at exactly the
> offline position on all 1,620 recorded Thor calls, reproducing the 121 + 127 counts), the gateway
> (`jsw/gateway/`; ~0.3 ms per call) and the decode guard (`jsw/policies/decode_guard.py`: truncate, resample,
> nudge or budget after a stop; a session stop after k consecutive caps), tested end to end against a fake
> engine. **[pending: A-P1 evaluated on A-E2's prompts and a live agent]**

## 4. B. Agent design

**What P5 would study.** The agent paradigm as the energy lever: a step-wise agent (one tool call per flight
action, one growing conversation) against P1's whole-program agents (Reflexion; one program per tool call), on
P1's tasks, measured by energy per successful mission and agents per device.

**The claim a paper could make.** "For drone missions on edge devices, a step-wise agent uses N× less energy
per successful mission than whole-program generation, because steps after a tool result stay short and the
growing conversation is reused, and it fits M× more drones per device."

**Evidence for.**
- On P1's delivery tasks D1–D3, a step-wise agent writes a median 55–99 output tokens after a tool result
  (p90 ≤ 394) in every configuration tested [WS-meas, 108 missions, Qwen3.5-9B and K2-Horizon-7B].
- Projected to Thor costs: 22–68 kJ per success against P1's Reflexion 219–499 kJ (5–13×); 4–16 drones per
  Thor within 1.5× p95 mission time against 2 [proj, sim].
- P1's two agents on the same 12 tasks: tool calling 231 kJ per success, Reflexion 79 kJ (2.9×), because of
  runaway thinking [P1-meas].

**Evidence against.**
- Under the strict check (order, descent and hold, no flight through a building) the ratio falls to 0.9–9.6×;
  only 27% of step-wise missions pass it, because the kinematic sim has no buildings [WS-meas].
- Gemma-4's own step sizes were unmeasured until this week; now measured with gemma-4-E4B (B-E1, below).
- The win belongs to the agent, which is P1's territory; a memory controller adds at most ~10% on top [sim].

**Novelty** (`lit_B.md`; 25 works). The direction is known with energy numbers: iterative designs (Reflexion,
LATS, multi-agent) cost far more than lighter loops (Cost of Dynamic Reasoning, KAIST; Engineering Sustainable
Agents; energy per successful goal, A-LEMS); code actions need fewer turns than JSON tool calls (CodeAct);
single-shot drone programs beat closed-loop generation on tokens (AeroGen, the supervisor's group). Not found:
step-wise vs whole-program vs Reflexion on the same embodied tasks with energy per success on edge hardware,
and the serving effects (prefix reuse, drones per device). As a paradigm comparison it fits P1 and the AeroGen
line better than a serving project.

**Edge specificity.** Through drones per device and through r, the price of a generated token in prefilled ones
(52–312 on P1's Jetsons): short steps matter most where decode is expensive.

**Dependence on P1.** High. Running P1's AeroEval tasks with a step-wise agent is an open question for P1's
mentor (task overview §9); extending aerogen needs its author's OK.

**What would change our mind.** Gemma-4 writes long steps after tool results (median > 300 tokens, B-E1's rule),
or a fair whole-program arm with guardrail prompts closes the gap.

**This week: B-E1 and B-E2** (`b_e1.json`, `b_e2.json`; WS, gemma-4-E4B with P1's weights, aerogen's loop, P1's
D1–D3 texts and delivery world, thinking on, 33 missions).
- **E4B keeps its steps short.** After a tool result it writes a median 63 tokens under P1's greedy protocol (p90
  121, max 284) and 68 when sampled (p90 169, max 539); the planning call writes a median 1,204–1,574; no call hit
  its cap. B-E1's rule (median ≤ 300) holds for P1's model family [WS-meas].
- **It passes the strict check more often than the 2 Oct stand-ins:** 9 of 11 greedy missions and 7 of 13 sampled
  (Qwen3.5 and K2: 27%) [WS-meas].
- **Projected at Thor gemma-26B prices** (the 2 Oct method): 26.6 kJ per strict success on D1 and 26.2 on D2+D3,
  against P1's Reflexion measured at 499 kJ (D1) and 284 kJ (D2; D3 had no passes): **11–19×** [proj]. At Orin 32
  E4B prices (P1's fit on its own E4B calls): 14–19 kJ [proj].
- **But E4B does not always use its tool-call format.** With aerogen's prompt (whose examples show calls as
  Python text) it sometimes writes the call as text, or writes the whole mission in one reply with imagined tool
  results. The gateway converts such calls (`jsw/gateway/pythonic.py`), but 9 of 33 missions (1 greedy, 8
  sampled) still ended at the first call because of a conversion bug, since fixed and not yet re-run. These
  missions are left out of the numbers above.
- Caveats: the projection applies the 26B's per-token costs to E4B's token counts (as the 2 Oct projection
  applied them to Qwen's); the kinematic sim has no buildings; one run per configuration.

> **WS version (G2).** The aerogen driver (`jsw/workloads/aerogen_driver.py`) runs a step-wise agent on P1's
> task texts; a building-aware sim (B-P1) waits for the author's OK.

## 5. C. Standard benchmarks with injected waits

**What P5 would study.** The original question (keep, drop, offload or recompute paused state) on standard
agent benchmarks with accumulating contexts, with tool waits injected from P1's measured distributions, so the
results compare directly with prior work.

**The claim a paper could make.** "With edge prices and waits of seconds to minutes, the best retention policy
differs from published ones by X%."

**Evidence for.**
- Easy comparison with INFERCEPT, Continuum, Adaptive KV Retention (which use BFCL, SWE-bench, τ²-bench) [lit].
- Accumulating native tool-calling contexts reuse 96–99% of prompts in published measurements (MLPerf Edge
  Agentic, AgentSysBench) [lit].
- Adaptive KV Retention's break-even hold time (t* ≈ 109 s on an H100) falls inside P1's flight waits
  (median 17–113 s) [lit].

**Evidence against.**
- P1's own accumulating-context agent (traffic) has 56–82% cache reuse yet kept state is worth only 1–4% of
  LLM time, because its steps write 424–999 tokens and the state idles 1–3 s [P1-meas]. A benchmark agent with
  thinking on may behave the same.
- P1's real tools return in 0.5–3 s; long waits would be synthetic.
- It loses the drone and traffic story and P1's devices.

**Novelty.** The generic version is published (INFERCEPT, Continuum, TokenCake, Adaptive KV Retention,
CacheScout; Track B F1–F10). What the edge adds would come only through the injected waits and Jetson prices.

**Edge specificity.** Weak.

**Dependence on P1.** Low; only P1's wait distributions.

**What would change our mind.** τ²-bench steps are short enough that the ceiling P/(P + r·O) at a Jetson r is ≥ 20%
of LLM time (C-E1's rule).

**This week: C-E1** (`c_e1.json`; tau2-bench on the WS, gemma-4-E4B as the agent with thinking on and as the
user simulator, one conversation at a time) [WS-meas]:
- **Airline (20 tasks, mean reward 0.50, 10 passed):** about 10 agent calls per conversation; the context starts
  at 3.9K tokens and grows a median 182 tokens per step (peak 5.8K); 93.5% of prompt tokens come from the cache.
- **But each step writes a median 333 tokens (p90 831), 83% of it reasoning**, so the most kept state could save
  is 7.5% of LLM time at E4B's own Jetson price (r = 147), 3.7-9.2% at the traffic prices and 16-19% only at the
  drone prices (r = 52-63). C-E1's rule: in between (below 20% at every Jetson r, above 10% at some).
- Retail **[running]**; airline with the agent's thinking off (C's best case: short steps) **[queued]**.

> **WS version (G2).** C-P1 (τ²-bench through the gateway with published baselines) is built only if C-E1 finds
> an opportunity.

## 6. D. Memory that changes over time

**What P5 would study.** Admission and retention when model-backed tools, co-located models or simulators take
and release unified memory during an agent's run: pin a paused context through a known burst, admit a burst at
lower concurrency, or resize the pool, judged by energy per successful task.

**The claim a paper could make.** "On unified-memory edge devices, an agent's own tools change the memory
available to it; a serving layer that uses its foreknowledge of tool calls recovers X% of energy per task at N
agents per device, where policies tuned for a fixed budget recover nothing."

**Evidence for.**
- P1's vision tool (`ask_vlm`) sends 8–45 concurrent requests (median 8–23) to the agent's own server; on Orin
  64 gemma (12.4K-token pool) the burst fills 99.5% of the pool and evicts the paused agent's context before
  every one of the 62 calls that follow it (90% of the prefix recomputed); 12 of 50 on Orin 32 E4B; none on Thor
  [P1-meas, server counters].
- Small pools cap consolidation: with 8 agents the gap to unlimited memory is 33–64% on the Orins [sim].

**Evidence against.**
- The recompute the burst causes is 0.6% of LLM time at one agent per device, because prefill is cheap
  [P1-meas].
- Most of the 33–64% gap is capacity, which configuration recovers (CAP), not policy.
- A 2026 paper on elastic KV inside one engine found reclaiming memory worth about 1% TTFT [lit, abstract].
- P1 describes `ask_vlm` as a second model, and its microbenchmark targets a separate endpoint; our reading is
  from the agent server's request counters only (correction 1 sent to P1, reply pending).

**Novelty** (`lit_D.md`). Run-time resizable KV pools exist (Prism/kvcached, open source on SGLang 0.5.20;
MorphServe), as does tool-aware pinning (Continuum, MORI); on-device KV under a budget (LLMS on Jetson Orin NX;
mzCache on phones). Not found: a serving policy that knows a tool will take memory on the same device and uses
it to pin, throttle or resize, judged by energy per task on unified memory.

**Edge specificity.** Strong: unified memory has no host tier, and tools that run models share the board.

**Dependence on P1.** Medium: P1's answer on `ask_vlm` decides whether the contention is inside one engine; real
unified-memory behaviour needs a device.

**What would change our mind.** D-E2: the best policy stays within 5% of the default at 4 agents.

**This week: D-E2** (`d_e2.json`; P1's Orin 32 E4B traffic sessions with `ask_vlm` bursts, replayed on gemma-4-E4B
with the bursts sent as real concurrent requests; one run per cell) [WS-meas]:
- **The mechanism reproduces live:** at a 12,415-token pool the call after a burst recomputes 88-100% of its
  paused prefix (P1's Orin 64 data: 90%); at the full 63.5K pool, 43%.
- **The first policies changed nothing measurable** (energy per completed session within -4% to +8% of the default,
  one run each): admission never held a request (the burst arrived before the pool-usage metric rose) and pinning
  cannot protect a context when the burst alone exceeds the free pool. A fair re-test (burst capped at 2 requests,
  with and without pinning) is **[queued]**.
- **Capacity dominates:** with 4 agents, the 63.5K pool needs 3.25 kJ per completed session against 7.92 kJ at
  12.4K (2.4x less) and completes 46 sessions against 19 in the same time; 4-5 sessions per run at 12.4K could not
  run at all (prompts larger than the pool, as P1's Orin 64 overflows). That is CAP's lever, measured live.

> **WS version (G2).** Built: the gateway with tool-tagged routes and tool events, and the trace replayer
> (`jsw/workloads/replay.py`) with burst injection. **[pending: D-P1 burst-aware memory policy]**

## 7. CAP. Capacity

**What P5 would study.** KV precision (FP8/INT4), fixed-prompt and tool-definition size, and tool-output caps as
the levers that decide how many agents fit a device, either as configuration or chosen at run time from pool
pressure, judged by energy per successful task and task success.

**The claim a paper could make.** "On 32–64 GB edge boards, capacity sets energy per task for multi-agent
serving; a measured design space of KV precision, prompt size and output caps shows which lever buys how much
capacity per quality point, and a run-time controller recovers X% beyond the best static setting."

**Evidence for.**
- Traffic, 8 agents per device: doubling the pool cuts energy per completed task by 31–46% on the Orins; no
  retention policy comes close (≤ 2.4%) [sim].
- Drones: an FP8 KV cache recovers 10–34% at 1–4 GiB of state [sim].
- Window overflows end 11–21% of Orin traffic runs; the fixed prompt (system text and 7 tool definitions,
  3.9–5.1K tokens) is 38% of Orin 64 gemma's window [P1-meas].

**Evidence against.**
- These are configuration choices; P1 already proposes them (MB5, not run).
- FP8 KV quality on these agents is unmeasured **[pending: CAP-E1]**, and FP8 KV speed on Orin (sm_87, no
  native FP8 attention) is unverified [lit].
- With 7 tools, tool retrieval has little room (published gains appear at 19–46 tools) [lit].

**Novelty** (`lit_CAP.md`; 24 works). Each lever is studied: role-aware INT2/INT4 KV within ~1 point on
tool-calling benchmarks (TriAxialKV), FP8 KV near-lossless on reasoning, tool selection on Jetson Orin with power
numbers (Less-is-More, CarbonCall), observation masking at half the cost (Complexity Trap). Not found: energy
per successful task for any of these levers on an agent workload, and a run-time controller that moves among
them from live pool pressure across concurrent agents.

**Edge specificity.** Strong: weights, KV and tools share 32–64 GB.

**Dependence on P1.** Medium: overlaps P1's proposed remedies and its deferred KV-pool sweep (E4).

**What would change our mind.** CAP-E1: FP8 KV shows no quality loss, so the best static setting is free and the
run-time part has nothing to recover.

**This week.** CAP-E1 (FP8 vs bf16 KV) **[pending]**.

> **WS version (G2).** CAP-P1 (capacity-aware admission) only if CAP-E1 finds a trade-off.

## 8. Cross-cutting

**RET: the retention controller on P1's workloads (the negative result behind every option).**
- Kept state saved 0.2–0.5% of LLM time on Thor drone runs and 1.1–4.2% on traffic; the most any retention policy
  could save is 0.9–7.2% (Devstral 23%, Qwen2.5-VL 26%) [P1-meas].
- With several agents per device, the best of 12 policies beats SGLang's default by at most 2.4% (traffic, 48
  cells) and 9.9% (drones, 455 cells) [sim].
- This rests on simulation; **[pending: RET-E1]** replays P1's granite traffic runs live at P1's pool sizes and
  compares with the simulator.

**Overlap with P1's paper.** Loops (A: P1 owns the observation), capacity remedies (CAP: proposed, not run),
the KV-pool sweep and warm-cache arm (deferred; RET/D/CAP territory), agent paradigm (B).

**Combinations.** A + CAP (decode guard plus a capacity study) and A + D (one serving layer that handles both
runaway decodes and tool bursts) share the same gateway. **[filled in CMP-2]**

## 9. Our lean

**[filled in CMP-2, after the experiments.]** As of 2026-10-05 the lean was A, coordinated with P1; this section
will state whether this week's evidence changes it.

## 10. Questions for the professor

1. Which option, or combination (A, B, C, D, CAP)?
2. Scope: leave retained state (A, B, CAP) or stay with it (C, D)?
3. The deployment assumption: how many agents one edge box serves (it sets the memory pressure in C, D and CAP).
4. The go/no-go thresholds (D4) for the chosen option.
5. How to split with P1: what P5 may claim on loops (A) and capacity (CAP).

## 11. Method, data and caveats

- P1's data: the repository at `3c47ebc` (drone 3 cells, traffic 8 cells) and our copy of P1's Thor drone
  tool-calling sweep (104 runs).
- **Local data integrity (2026-10-05).** The laptop's RAM corrupts files held in its page cache: three files of
  P1's clone read back with single-bit flips, while the disk copies match P1's commits. All data processing
  moved to the WS (ECC memory): P1's repository cloned there from GitHub at `3c47ebc`, our tool-calling copy moved
  with matching SHA-256. **Re-verified:** the 5 Oct analyses rerun on the WS give byte-identical `opportunity.json`
  and `caps.json`.
- **No stand-in for P1's gemma-4-26B-A4B runs on our A5000s** (D13's outcome, 2026-10-06): in SGLang 0.5.20 the
  4-bit MoE kernel supports only SiLU (Gemma uses GELU), the FP8 MoE kernel needs an FP8 type only newer GPUs have
  (fp8e4nv), and bf16 (52 GB) exceeds both GPUs. Experiments use gemma-4-E4B and granite-4.2-8B, P1's exact weights;
  the 26B tests wait for a Jetson. SGLang 0.5.20 (P1: 0.5.16); NVML GPU energy, not board energy.
- Literature depth varies per work (`lit_*.md`); most 2026 preprints were read through summaries or abstracts.

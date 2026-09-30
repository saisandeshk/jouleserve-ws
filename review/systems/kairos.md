# KAIROS — context-aware GPU frequency, concurrency and routing control for power-efficient agentic serving

- **Source:** KAIROS: Stateful, Context-Aware Power-Efficient Agentic Inference Serving; Yichao Yuan, Mosharaf Chowdhury, Nishil Talati; arXiv preprint, submitted 2026-04-17; arXiv 2604.16682 (CC BY 4.0)
- **Review depth:** full text — arXiv HTML plus PDF text (extracted locally): §3 characterization, §6 design, §7 methodology, §8 results, Appendix A.4/A.5/B. Figures were read only through their captions and surrounding text.
- **Category:** energy-aware serving (with agentic context as the control signal)
- **Code/artifacts:** none stated in the paper or on the arXiv page **[paper]**. Pseudocode is in Appendix A.1 (per-instance controller) and A.2 (router). Engine: vLLM v0.14.0, Zeus for power and clock control. Replayed agent traces: no public release stated.

## 1. Summary
- KAIROS controls GPU SM frequency, per-instance concurrency (admission) and multi-instance placement for agent workloads, using aggregate resident context as the signal. Reported: 27% average and up to 39.8% power reduction at a per-agent throughput SLO (Abstract, Fig. 7). Multi-instance: 46.3% (Fig. 12, 784.8 W to 686.5 W with context-aware routing, per the fetched text; the two figures are not obviously the same comparison, so check Fig. 12 before quoting).
- Cross-model (Table 1, SWE-Bench Verified): 34.5% on Qwen3-Coder-30B, 28.9% on Ministral-3-14B.
- It is the closest published system to "energy of agentic serving", but it never decides what to do with a paused agent's KV. It assumes the prefix cache retains context and only prevents the aggregate from exceeding capacity.

## 2. Problem and key insight
- Agents carry long-lived context across tool-interleaved turns (1 to 2518 turns, mean 37, heavy-tailed; §3.2). Context footprint is uneven: an agent finishing frees all its cache at once, and growth rates differ.
- Insight (§3.3, Fig. 4): lowering frequency from 1680 to about 900 MHz cuts energy and power about 30% with little throughput loss. Below 900 MHz it reverses. With a fixed arrival rate, slower service builds a pending queue, aggregate context exceeds GPU memory, cached context is evicted and recomputed ("thrashing"), and energy rises.
- So frequency must be coupled to memory state. Appendix A.4 quantifies thrashing with recompute vs LMCache CPU offload: offload starves GPU compute through transfers, recompute wastes cycles; useful decode throughput falls 22.3% in one of the cases.

## 3. Workloads
- Benchmarks: SWE-Bench Verified, DABStep (data analysis), Terminal-Bench 2.0 (§7). Agents: mini-swe-agent and Terminus-2 (Harbor). ReAct-style loops only.
- Arrival: Poisson job arrivals; 0.08 jobs/s for characterization, 0.03 to 0.16 jobs/s in evaluation. Each run is a 3-hour window. Requests and timings are recorded from real agent executions and replayed identically across policies.
- Models: Qwen3-Coder-30B (FP8), Ministral-3-14B; dense/MoE-style full-attention serving under vLLM. Hardware: H100 NVL 80 GB (400 W TDP, max clock 1680 MHz), Xeon 8592+, 2 TB DRAM; up to 4 GPUs.
- Tool-wait durations are not characterized in the text I extracted; tools ran on CPU (containerized, per the benchmark harness **[inferred]**). Conversation lengths: heavy tail up to thousands of turns (Fig. 13, A.3). No prefix-sharing analysis beyond "context retained in prefix cache".

## 4. Assumptions
- Single model per instance; ReAct paradigm; prefix/PagedAttention cache keeps a session's context resident between turns. A tool wait is implicitly a "cache hit next turn" event.
- Near-constant or slowly varying arrival rate; thresholds (alpha 0.75, beta 0.95, gamma 0.9, reassignment after 8 turns, 50% consolidation threshold) were tuned empirically, with limited sensitivity analysis (§8/B).
- Per-agent throughput (P5 output tokens/s, target 20, also 35 and 45) is the SLO, chosen over TTFT/TBT (B.2). Not a task-completion or success-rate SLO.
- No PD disaggregation (B.1). Frequency control via Zeus: needs privileged clock APIs (NVML application clocks) **[inferred]**; not discussed.

## 5. Controller / mechanism
- **State:** U_k = sum of context tokens of running agents; U_max = KV token capacity; per-agent throughput; set of pending agents.
- **Frequency (Eq. 8-9):** discrete levels; frequency increases monotonically with U_k/U_max; above alpha*U_max jumps to a protective high regime. **SLO boost:** if min per-agent throughput drops below tau, go to max frequency.
- **Concurrency (§6.2.4):** enforce U_k <= beta*U_max; admit pending agents only when U_k < gamma*U_max (hysteresis). Agents are held in a pending set, not preempted.
- **Router (§6.3, Alg. 2-3):** consolidate (fill low-index instances) while active instances are below 50% context; otherwise spread to lowest-usage instance. Reassign after 8 turns if current instance context >= 2x the lowest. Rationale: an idle H100 draws about 50 W but light load adds about 100 W even at lowest clock (§6.3), so consolidation lets other GPUs idle.
- **Predictors:** none; purely reactive. Control epoch length is not stated in the extracted text.
- Implementation hooks at the orchestrator/vLLM boundary plus Zeus; no engine kernel changes described.

## 6. Evaluation and reported results
- Metrics: power (average of summed instance power), per-agent P5 throughput and SLO attainment, job throughput, **energy per finished agent (kJ)** (Fig. 7 panels).
- Baselines: max clock (1680 MHz), fixed 810 MHz, round-robin routing. No comparison to DynamoLLM, GreenLLM, or a KV-retention policy.
- Numbers: 27% avg / 39.8% max power (Fig. 7); tightening SLO from 20 to 45 tokens/s drops savings from 32.9% to 6.3% (Fig. 8 text); without thrashing avoidance, per-agent throughput collapses to 2.3 tokens/s and jobs pile up (Fig. 10); multi-instance 46.3% (Fig. 12).
- Energy measurement: Zeus, GPU only, integrates power; sampling interval not specified. Metrics are mostly power at fixed throughput; energy per finished agent appears but the headline is power.

## 7. What JouleServe-WS can take
- **Must-have baseline:** reimplement "context-aware concurrency cap" as an SGLang-side admission gate: cap resident tokens at beta*pool (SGLang exposes `max_total_num_tokens`; gate in the LangGraph/router client, no engine patch). Frequency part cannot be reproduced without root (see §9); use it as an analytic or as a concurrency-only ablation.
- Reuse the thrashing definition and detector: resident context vs KV pool, and recompute-token counter (SGLang cached-token vs prompt-token stats) as thrashing indicator.
- Measurement: Zeus-style GPU energy integration; on our A5000 use NVML `nvmlDeviceGetTotalEnergyConsumption` (cumulative mJ), which is equivalent and avoids sampling error. Report **energy per finished task** and kJ per agent, plus idle-subtracted energy separately. Their fixed-arrival-rate replay (record then replay timing) is the right experimental pattern.
- Their per-agent throughput SLO is a reasonable secondary metric; JouleServe should use task-level SLO.

## 8. What JouleServe must add beyond it
- Decide what happens to paused state: KAIROS assumes retention and treats overflow as failure. JouleServe must choose keep / demote / offload / evict-recompute per paused session, using tool-wait knowledge and reuse probability.
- Task-level objective (energy per successful task, including retries and failed tasks) rather than power at a throughput SLO.
- Hybrid models (SWA, recurrent state): U_k is not linear in tokens; sliding-window layers cap state, recurrent state is constant per session.
- Distinguish active from paused footprint: KAIROS's U_k lumps them. Our P1 data suggests active long decodes dominate pressure.
- Non-DVFS energy levers where clocks are locked: admission, offload, batch composition.
- Rebuilt-per-role prompts: retention value is low (10 to 31% reuse), which KAIROS's design does not test.

## 9. Workstation -> edge
- Frequency knob: A5000 without root has none (no NVML clock setting, no power limit). Only relative levers: concurrency, admission, routing across 2 GPUs (consolidation is testable on our 2 GPUs: park one GPU near idle).
- Jetson: nvpmodel/jetson_clocks/devfreq need root and mode switches are slow, so per-epoch DVFS as in KAIROS is not an option in the deployed setting; a small set of static modes is more realistic. Idle vs active gap logic (50 W idle on H100) differs: Orin idle is few watts and board rails (INA3221 via tegrastats) include CPU/DRAM, which are unified with KV.
- Unified memory: "offload to CPU" costs no PCIe transfer but competes for the same DRAM; thrashing means system memory pressure. Thermal throttling replaces "frequency lowers power" as an involuntary DVFS.
- Small batch: KAIROS's savings rely on batch-level slack at H100 scale; at batch 1 to 4 on Orin the power/frequency curve differs.
- Port effort: controller logic portable (about 100 lines of policy); measurement and actuation must be rewritten.

## 10. Relevance to our current findings
- Supports our suspicion that concurrency pressure comes from active state; KAIROS's thrashing is driven by slow service, not paused state.
- Their agents (SWE-bench, ReAct) accumulate context across turns (reuse high); ours rebuild prompts per role (reuse 10 to 31%), so their "context as control signal" is weaker for our drone/Reflexion loop; reasoning-heavy decode is similar.
- Tool waits: our real-time simulator waits (median 13 s to 115 s) are much longer than typical containerized shell commands, so retention cost vs recompute trade-off is not covered.

## 11. Open questions / uncertainty
- Control epoch length, Zeus sampling interval, tool-latency distributions, and whether retained-context eviction in vLLM is LRU on all paused sessions are not stated in extracted text. Fig. 12's 46.3% vs 27% headline scope needs verification in the figure itself.
- Whether idle H100 power (50 W) claims hold with the vLLM server resident. Code not released as of review.
- Novelty risk: overlap with JouleServe is on "context-aware energy control for agents"; the gap is retained-state policy, hybrid/edge, task-level objective.

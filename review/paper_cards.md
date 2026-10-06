# Paper cards for the JouleServe proposal review

The assigned papers, EnerInfer and Camel, are reviewed in depth. The remaining cards focus on works that materially change the novelty decision. All quantitative results below are the respective authors' reported results, not independently reproduced results.

## 1. EnerInfer: Energy-Aware On-Device LLM Inference

**Source and status.** Zou et al., arXiv:2606.23001v2, June 2026. The local assigned copy is `papers/EnerInfer.pdf` in the legacy repo (`~/Study/ISP/JouleServe`; PDFs are not kept here). Treat it as a preprint unless publication status is separately verified.

### Research problem

EnerInfer argues that maximum NPU and memory frequency is often unnecessary for acceptable on-device token generation. The efficient frequency pair depends on the model, engine, platform, interference, and thermal history, while commercial mobile devices may not expose component-level power sensors.

### Actual action surface

- NPU frequency.
- DDR/memory frequency.
- A mode switch between energy-efficient operation and thermally constrained operation.

This is already joint hardware control, not a single-frequency controller. It does not control queue admission, batching, suspended agent state, or KV tiers.

### Model and controller

EnerInfer builds offline, model-structure-aware predictors for throughput and power across NPU/DDR configurations. It uses disaggregated predictors and relies on predicted ranking plus online feedback rather than assuming the absolute predictions are exact.

For thermal control, it uses:

- a 20-second shell-temperature history;
- predicted NPU power at the selected frequency;
- a linear regressor predicting 1–21 seconds ahead;
- an event-triggered controller inspired by model predictive control; and
- a thermal cost that penalizes tokens expected after crossing a temperature threshold.

The paper reports 0.16 C mean absolute error for the temperature predictor in its tested range and environment.

### Evaluation and reported result

The evaluation spans phones, a laptop, and a development board. It trains its generalization machinery using 300 synthetic model configurations and validates on production-grade models. The paper reports:

- energy-efficiency improvements up to 65% on phones, 12% on a laptop, and 24% on a board for the targeted components/configurations; and
- up to 11% reduction in overall device energy, with no QoE violation in the evaluated scenarios.

The primary QoE constraint is generation throughput rather than a multi-request tail-latency or completed-agent-task SLO.

### Strengths

- It treats on-device thermal behavior as a first-class control signal.
- It explicitly co-manages accelerator and memory frequency.
- It distinguishes component efficiency from end-to-end device energy.
- It makes predictor generalization and runtime correction part of the design.
- Its event-triggered thermal loop is much more concrete than the initial JouleServe proposal's generic “receding horizon” phrase.

### Limitations relevant to JouleServe

- The workload is essentially single-device inference sessions, not concurrent suspended/resumed agent loops.
- There is no admission queue, batch-size decision, KV retention/tiering, or memory-fragmentation constraint.
- Thermal training is described around room-temperature traces and device-specific shell temperature; enclosure and cross-device transfer need new calibration.
- The offline training cost and availability of NPU/DDR controls do not translate directly to Jetson GPU/EMC controls.
- The reported component-efficiency gains are not interchangeable with total-system energy savings.

### Effect on the initial proposal

EnerInfer directly contradicts novelty N2 if N2 is phrased as “predict future temperature and act before throttling.” That idea already exists. A defensible JouleServe delta must specify what the prediction changes that EnerInfer cannot change—most plausibly retention/offload/recompute decisions for suspended agent KV state plus admission under unified-memory pressure.

### Baseline mapping

Implement an **EnerInfer-style baseline** on the available Jetson action surface: a predictive thermal loop choosing the allowed frequency/power setting subject to a throughput or TPOT target, with admission and KV policy fixed. Do not claim a faithful reproduction until its measurement scope, action cadence, and prediction training protocol match.

---

## 2. Camel: Energy-Aware LLM Inference on Resource-Constrained Devices

**Source and status.** Xu et al., arXiv:2508.09173v1, August 2025. The local assigned copy is `papers/Camel.pdf` in the legacy repo (`~/Study/ISP/JouleServe`; PDFs are not kept here). Treat it as a preprint unless publication status is separately verified.

### Research problem

Camel searches for an energy/latency operating point for batched LLM inference on a resource-constrained device. Its central observation is that neither maximum GPU frequency nor an extreme batch size is necessarily optimal.

### Actual action surface

- Seven GPU-frequency levels from 306 to 930.75 MHz.
- Seven batch sizes from 4 to 28.
- Forty-nine frequency/batch arms.

This is the most direct contradiction of the initial proposal's “single-knob literature” premise. It jointly controls the system-level frequency and application-level batching knob on Jetson AGX Orin.

### Model and controller

Each frequency/batch pair is a multi-armed-bandit arm. Thompson sampling balances exploration and exploitation. The objective is a scalarized, normalized weighted sum of per-request GPU energy and request latency:

`cost = alpha * normalized_energy + (1 - alpha) * normalized_latency`

The paper uses alpha = 0.5 for its main balanced case and explores sensitivity to alpha. This is not a constrained SLO formulation: energy and latency can trade against one another inside the scalar reward.

### Evaluation and reported result

- Hardware: Jetson AGX Orin 32GB.
- Engine: llama.cpp.
- Models: Llama-3.2-1B and Qwen2.5-3B, Q5_K_M quantization.
- Requests arrive at a fixed one-second interval in the main setup.
- The main result reports 12.4–29.9% EDP reduction against the maximum-frequency/maximum-batch configuration.

### Strengths

- The platform directly matches the Jetson-class edge setting.
- The two-knob interaction is measured rather than asserted.
- The bandit handles an unknown response surface without requiring a perfect analytical model.
- The alpha sensitivity exposes that the chosen objective weight materially changes the selected action.

### Limitations relevant to JouleServe

- No agentic tool-call pauses, growing context, KV retention, or external cache tier.
- No thermal state, temperature constraint, or time-varying heat history.
- No P95/P99 SLO-attainment constraint; average latency and a weighted cost dominate.
- Only two small quantized models and a narrow, largely stationary arrival/output setup.
- The default comparison is weak; an oracle best fixed arm and stronger adaptive baselines are needed for a modern serving paper.
- GPU energy is not clearly equivalent to complete board energy, and idle-energy attribution is not sufficiently explicit for a JouleServe baseline.
- A stationary Gaussian arm model may adapt slowly to thermal drift, changing request distributions, or context growth.

### Effect on the initial proposal

Delete G1 and N1 as originally written. “Joint admission/batch plus frequency control on an edge accelerator” is not novel. JouleServe must both:

1. compare against Camel on the same device and energy boundary; and
2. demonstrate that thermal history and agent KV state create decisions that a frequency/batch bandit cannot represent.

### Baseline mapping

Implement a **Camel-style matched bandit** over the exact safe JouleServe frequency/admission action grid, while holding KV policy fixed. Report both its original scalarized objective and JouleServe's constrained task-SLO view so improvements are not caused merely by choosing a different metric.

---

## 3. KAIROS: Stateful, Context-Aware Power-Efficient Agentic Inference Serving

**Source and status.** arXiv:2604.16682, 2026 preprint.

### Why it is the largest novelty threat

KAIROS is explicitly an agentic serving system. It tracks context growth and memory pressure, controls GPU frequency and per-instance concurrency, and performs multi-instance placement/routing. It minimizes power while maintaining per-agent throughput SLOs. The paper evaluates Qwen3-Coder-30B FP8 on H100 NVL using agent benchmarks and reports 27% average and up to 39.8% power reduction.

The edge setting alone is not enough to turn the same controller into a new contribution. JouleServe needs a mechanism that KAIROS lacks: temperature-horizon-aware selection among retain/offload/evict/recompute for suspended agent KV state on a shared/unified memory hierarchy.

### Required baseline

A matched KAIROS-style controller using context length, queue state, memory pressure, admission/concurrency, and frequency—without temperature prediction or external KV tiers.

---

## 4. Continuum: Efficient and Robust Multi-Turn LLM Agent Scheduling with KV Cache Time-to-Live

**Source and status.** arXiv:2511.02230, 2025 preprint.

Continuum treats tool-interleaved agent state as a scheduler problem. It selectively pins KV on GPU using a TTL derived from reload/recompute cost and queue delay, and supports GPU/CPU/SSD state through integration with LMCache. Its experiments use vLLM and LMCache on A100/H100/B200 and report 1.12–3.66x improvements in trace experiments and up to 8.18x in selected real cases.

This work means JouleServe cannot claim novelty for making agentic KV residency a scheduling decision. The defensible delta is an energy- and thermal-risk-aware retention value under unified-memory pressure, measured at board scope and evaluated against Continuum's latency-oriented TTL.

### Required baseline

A Continuum-style reload-vs-recompute TTL or cost policy with no temperature or energy term, using the same cache actions and workload trace.

---

## 5. Festina in Energy-Aware Scheduling for Serverless LLM Serving on Shared GPUs

**Source and status.** arXiv:2606.30391, 2026 preprint.

Festina jointly manages placement, SM partitioning, GPU operating point, phase-aware batching/resources, and scale-in on an eight-H100 serverless testbed. It reports energy reductions up to 56% while staying within 2% of SLO. It is not an edge or agentic KV system, but it invalidates any broad claim that energy-aware serving has only isolated single-knob controllers.

Use it to define the datacenter boundary; do not promise a full reimplementation on Jetson because several actions have no equivalent there.

---

## 6. AgentServe

**Source and status.** arXiv:2603.10342, 2026 preprint.

AgentServe targets local/consumer GPUs and recognizes cold prefill, resume prefill, and short decode as distinct phases. It isolates prefill and decode, dynamically budgets resources, and uses CUDA Green Contexts. The reported evaluation uses A5000 and RTX 5090 with ToolBench/ReAct/plan-and-execute workloads and reports up to 2.8x TTFT and 2.7x TPOT improvement.

It is a performance/SLO baseline for agent-specific phase behavior, not an energy/thermal baseline. JouleServe workloads and metrics should preserve these phases rather than collapsing an agent session into a generic request.

---

## 7. GreenLLM

**Source and status.** arXiv:2508.16449, 2025 preprint.

GreenLLM separates prefill and decode control, routes prompts into length queues, fits frequency/latency/power models for prefill, and uses a fast feedback loop for decode frequency. Its A100 trace replays report up to 34% total energy reduction with no throughput loss and less than 3.5% additional SLO violations.

It is stronger than the initial proposal's description of “frequency alone”: its frequency policy is queue- and phase-aware. Use it as a phase-aware DVFS baseline, with KV policy fixed.

---

## 8. LMCache

**Source and status.** arXiv:2510.09665, 2025 preprint.

LMCache exposes first-class KV controls—pin, lookup, cleanup, movement, and compression—across GPU, CPU, storage, and network, and integrates with vLLM and SGLang. It is a candidate substrate, not a JouleServe contribution. The local Orin software lock currently has no LMCache installation, so all tier-control claims remain conditional.

---

## 9. TAWS and SeKV: scope corrections

TAWS studies thermal-aware LLM batch scheduling with voltage/frequency awareness in cooling-regulated datacenters. Therefore, “thermal scheduling does not exist” is untenable; the edge/unified-memory distinction must carry the argument.

SeKV stores semantic summaries on GPU and low-rank bases on CPU, reconstructing relevant spans on demand. It is a model/KV representation method rather than the agent-session serving policy described by JouleServe. Cite it accurately as adjacent memory work, not as proof that all KV systems expose the same residency action.

## Synthesis

The literature leaves a plausible but unproven intersection:

> On a single unified-memory edge accelerator, use predicted temperature and memory pressure to price the future energy/SLO value of retaining each suspended agent's KV state, and co-decide admission plus retain/offload/evict/recompute actions.

This is a hypothesis, not yet a novelty fact. A six-week novelty/feasibility sprint should determine whether the intersection is implementable, produces a repeatable control conflict, and beats matched KAIROS-style and Continuum-style baselines.

---

## 10. TokenCake

**Source and review status.** arXiv:2510.18586. The current refresh verified
the primary abstract and retained the earlier targeted review; a new full-paper
extraction remains mandatory before baseline freeze.

TokenCake directly targets KV behavior in multi-agent applications with
function-call stalls. Its space scheduler dynamically partitions memory, while
its time scheduler proactively offloads and predictively uploads KV state. P5
therefore cannot claim novelty for identifying idle KV during tool calls,
partitioning agent memory, or predicting a return before upload.

**Required comparison.** A behaviorally aligned partition plus proactive
movement baseline on exactly the validated P5 action surface. P5 must show that
local-tool resource demand and shared-memory/thermal risk change decisions
beyond TokenCake-style pause/reuse prediction.

## 11. INFERCEPT

**Source and review status.** arXiv:2402.01869, targeted primary-PDF review.

INFERCEPT supports API-paused requests using a scheduler, CPU swap manager,
resource monitor, waste estimator, and profiler. It can swap some paused KV,
preserve or discard remaining state, and later restore or recompute it while
scheduling waiting work. This removes swap/preserve/discard/recompute during API
pauses as a standalone P5 contribution.

**Required comparison.** A waste/cost-aligned paused-request baseline using the
same actions and queue. Jetson host-offload semantics must be measured rather
than copied from a discrete-memory GPU/CPU assumption.

## 12. CacheScout

**Source and review status.** arXiv:2608.14624, primary abstract reviewed on
2026-09-02. Treat all detailed claims as provisional until full extraction.

CacheScout learns agent execution transitions online and uses those semantics
to guide KV eviction and proactive prefetch without predefined workflow graphs
or offline training. The paper reports improvements in cache hit rate, TTFT,
per-turn latency, and peak throughput on multi-agent workloads.

**Effect on P5.** “Use agent/workflow semantics to predict reuse and manage KV”
is no longer a clean delta. P5 must compare against a transition-aware policy
and show incremental causal value from local-tool placement/resource demand,
physical shared-memory state, thermal state, or a different verified objective.

## 13. Adaptive KV Retention for human-approval waits

**Source and review status.** arXiv:2608.30830, primary abstract reviewed on
2026-09-02. Full-paper extraction is mandatory before final novelty or baseline
claims.

This work studies minute/hour agent suspensions and frames retained KV through
GPU opportunity cost. Its tiered controller chooses retention/expiration under
uncertain approval waits and compares against vLLM, MORI, and Continuum. It
reports active-serving goodput and resume-latency benefits.

**Effect on P5.** Generic “dynamic value of retained agent state” or “balance
future resume cost against active-serving opportunity cost” is no longer a
sufficient novelty statement. The N1 candidate must test the resource-active
tool phase and edge physical-memory/thermal coupling. A matched opportunity-
cost baseline is mandatory.

## Updated synthesis — 2026-09-02

The remaining candidate intersection is narrower and more falsifiable:

> On a shared-memory edge accelerator, does the predicted local resource
> envelope of the current tool phase, combined with resume uncertainty and
> measured physical-memory/bandwidth/thermal risk, change the best
> retain/de-prioritize/offload/evict-recompute/admit decision and reduce board
> energy per successful task beyond matched paused-KV, transition-aware, and
> generic opportunity-cost policies?

If tool-resource and edge-state factors add no held-out action value, P5 must
follow the N2–N5 ladder in the refresher/master plan rather than revert to the
older generic retained-state claim.

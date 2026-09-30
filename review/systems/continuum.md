# Continuum — tool-call-aware KV time-to-live pinning with program-level FCFS

- **Source:** Continuum: Efficient and Robust Multi-Turn LLM Agent Scheduling with KV Cache Time-to-Live; Hanchen Li, Runyuan He, Qiuyang Mang, et al.; arXiv preprint, 2025; https://arxiv.org/abs/2511.02230 ; code https://github.com/Hanchenli/vllm-continuum (paper says "not yet public at writing"; check)
- **Review depth:** full text (arXiv HTML via fetch-and-summarize extraction; formulas/numbers quoted from that, not re-verified against PDF). Code not read.
- **Category:** agentic KV retention (with agent-aware scheduling)
- **Code/artifacts:** vLLM fork (~1,000 lines Python, vLLM 0.10.2 base). Authors promise open-sourced traces and testbed. Paper CC BY 4.0; repo license TBD.

## 1. Summary
- Agent turns alternate LLM call and tool call. Continuum pins the KV of a request for a TTL tau after it emits a tool call, so the next turn hits cache. TTL is chosen from the empirical CDF of that tool's past durations, trading reload+queueing savings against occupation cost. Scheduler is program-level FCFS with pinned requests prioritized.
- Headline: 8.18x job-completion-time improvement on real SWE-agents (Fig. 12), 1.10-3.22x throughput, up to 2x avg response time on Llama-8B traces (Fig. 8) [paper]. Abstract says ">8x".

## 2. Problem and key insight
- Chat-style end-of-turn eviction is fine for human pauses but bad for agents with short, variable tool pauses. Even with CPU offload (InferCept style), evicted programs re-enter the waiting queue behind others each turn, accumulating "queueing bubbles"; so reload cost alone is the wrong metric. Eviction cost = reload + out-of-order queueing delay [paper, Sec. 4 / Fig. 4].

## 3. Workloads
- SWE-Bench via mini-swe-agent, 100 traces: 10.9 ± 2.1 turns; tool time 925 ± 3,550 ms (heavy tail); 70,126 ± 19,732 tokens per program; bash tools; traces scaled to fit 128K [paper].
- BFCL v4 web-search: 6.3 ± 2.3 turns; tool 1,923 ± 2,133 ms; 93,256 ± 68,687 tokens/program; slowest 10% of calls = 52.5% of delay. Downsampled 0.4x to fit.
- OpenHands (Multi-SWE-Bench Go), plus real SWE-agent runs (500 tasks, Fig. 12, GPT-5 used for collecting).
- Context **accumulates** across turns (tool outputs appended; native-style ReAct) [paper]. Arrival Poisson, 0.13-0.4 jobs/s.
- Models: Llama-3.1-8B/70B, Gemma-3-12B, GLM-4.5-355B (RL). HW: A100, H100, B200. All datacenter; no hybrid.
- Pauses are ~1-2 s means: an order of magnitude+ below our 13-115 s.

## 4. Assumptions
- Tool durations are predictable in distribution per tool name; needs >100 samples per tool, else global CDF (>100 total), else fixed threshold with Exp(1) and eta=1 [paper].
- GPU is the bottleneck under heavy concurrency (queueing delay T>0); ReAct-style sequential tool calls only; no parallel tools/speculation [paper, limitations].
- Hierarchy: GPU HBM, optional LMCache CPU DRAM (100-200 GB/GPU) and SSD (400-800 GB). Prefill-Reload = quadratic prefill fit, or `tokens/bandwidth` with offload [paper].

## 5. Controller / mechanism
- TTL (Eq. 2) [paper]: `tau* = argmax_tau  P(tau,f) * (T*eta + PrefillReload(r)) - tau`
  - P(tau,f): empirical CDF that tool f returns within tau.
  - T: sliding-window average queueing delay per unit memory. eta in [-1,1] = -Corr(k, N-k), "memoryfulness" (how much later turns of a program depend on earlier ones).
  - Expanded: benefit = MemUsage*PrefillReload/M + (T/M)*MemUsage*eta; cost = MemUsage/M * tau (M = mean active footprint).
- Pause duration prediction: inter-request gap `t_arrive(i+1)-t_finish(i)` recorded per tool; unknown tool -> global pool.
- Scheduling: preempted first; within-TTL pinned next; then by program-level arrival.
- Deadlock guard: unpin latest programs if memory full. Functions `set_up_ttl`, `pin_request`, `unpin_requests`. Offline profiling <10 min per model/HW (prefill curve chunks 1000..max, CPU bandwidth).
- Cadence: per tool call; overhead negligible.

## 6. Evaluation and reported results
- Baselines: vLLM 0.10.2, Autellix (PLAS), InferCept, SGLang 0.5.5 (real runs), Dynamo 0.7.0 [paper].
- Fig. 8: up to 2x lower avg response; Fig. 12: 8.18x JCT; throughput 1.10-3.22x; P95 better (Fig. 11); delay stable as turns grow 1-5x (Fig. 14). Fig. 10: beats InferCept with CPU offload.

## 7. What JouleServe-WS can take
- **Baseline (must).** Reimplement TTL on SGLang 0.5.20 as an external controller: keep per-tool duration samples; at tool-call start compute tau* with the formula (queueing term T measurable from SGLang scheduler waiting-queue time); pin by holding radix-node locks (e.g. a keep-alive handle/session mechanism or `--enable-priority-scheduling` with priority for returning sessions) and unpin at tau or on memory pressure [inferred; check 0.5.20 hooks]. Effort: ~1 week for controller + pin/unpin patch in radix cache; simplest variant (fixed TTL sweep) ~2 days.
- Trace format and SWE/BFCL/OpenHands traces if released.
- Methodology: JCT per program, program-level FCFS as a scheduling baseline.

## 8. What JouleServe must add beyond it
- Energy per successful task; TTL for 13-115 s waits where P(tau,f) is nearly flat until tens of seconds; no tier/hybrid states; explicit accounting that pinned memory blocks active decodes; mixed roles with rebuilt prompts (eta ~ 0 by their definition).

## 9. Workstation -> edge
- CPU offload/LMCache branch is void on Jetson: reload cost reduces to prefill only (no bandwidth term), and offload frees no memory, so only pin-or-discard remains — exactly the paper's no-offload branch, which still works.
- Profiling of prefill curve must be redone per power mode. Small batch means queueing term T is small; TTL then simply reflects prefill savings vs occupancy. Cold-start (>100 samples per tool) is hard when tools are 15-min simulators.

## 10. Relevance to our current findings
- Benefit term `P(tau)*(T*eta + PrefillReload)`: our prefill is 1-8% of LLM time and per-role prompts share only 10-31% prefix, so PrefillReload (of the reusable part) is small and eta near 0; cost term `MemUsage*tau` with tau of tens of seconds is large. Expected tau* ~ 0 (discard) for most calls. Under concurrency, pinning hurts active decodes. The paper's own contrast (end-of-turn eviction works for long human pauses) actually classifies our workload with chat, not with SWE-agents.
- Caveat: could help the AeroEval case (66% overlap), only if pauses are short (they are 115 s).

## 11. Open questions / uncertainty
- Repo release state and license unknown.
- Whether SWE traces (accumulating, prefill-heavy, sub-second tools) transfer at all.
- Extraction is via summarizer; verify Eq. 2 details (definition of eta) in the PDF.

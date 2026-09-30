# CacheScout — online-learned agent-transition model driving KV eviction and anchor prefetch in multi-agent serving

- **Source:** Learning Agent Execution for KV-Cache Management in Agentic Serving; Rui Zhang, Chaeeun Kim, Shaoting Feng, Kuntai Du, Yuhan Liu, Yi Zhong, Cheng-Wei Ching, Junchen Jiang, Liting Hu; arXiv preprint, 2026; https://arxiv.org/abs/2608.14624 (ID verified, matches title)
- **Review depth:** full text — arXiv HTML read via extraction (mechanism, workloads, evaluation, limitations). Appendices only as surfaced by the extraction; exact table numbers not verified line by line.
- **Category:** agentic KV retention
- **Code/artifacts:** Paper says it "will be open-sourced along with the benchmark suite"; no URL found. Implemented as an ~800-line patch (~2,300 lines runtime logic) to vLLM v0.11 (V1 engine), reusing LMCache / CPU offload unchanged. Traces not public as far as seen.

## 1. Summary
- Learns a first-order Markov chain over agent dispatches online, scores KV blocks by predicted "survival" (how many hops until their agent runs again), recency and size, and evicts the lowest scores [paper].
- Optionally prefetches the predicted next agent's "anchor" (system prompt + tools + minimal user prompt) with a max_tokens=1 warmup request [paper].
- Headline (Llama-3.1-8B, 4 workloads): hit rate +10–18 pp (to 81–85%), TTFT -18–45%, per-turn latency -29–38%, peak throughput +19–57% [paper].

## 2. Problem and key insight
- Multi-agent supervisor apps repeatedly reuse fixed per-agent context (prompts, tools, examples); recency-based LRU evicts it before the next agent call.
- Insight: reuse is governed by agent execution semantics, not recency. Fixed context is 53–62% of prompt tokens; agent-anchor blocks are reused 49–173 times on average vs 12–15 for session-history blocks [paper].
- No predefined workflow or offline training: agent identity is inferred from prompt-prefix fingerprints (block-hash change signals a dispatch) [paper].

## 3. Workloads
- GSM8K, MT-Bench, GAIA, SWE-bench, all run through one six-agent supervisor with tools using AutoGen SelectorGroupChat (LLM-selected dynamic routing). Multi-agent, not single.
- SWE-bench described as long and prefill-heavy; GAIA tool-heavy. Turn counts and tool-pause durations: not extracted (tool time is not a modeled quantity; Continuum baseline uses 0.3 s TTL).
- Context accumulates in session history, but the anchor is 43–60% of every prompt even a dozen turns in.
- Models: Llama-3.1-8B-Instruct (main); Qwen3-235B-A22B-FP8 (MoE, scale study, SWE-bench). Both attention-based, no hybrid.
- Hardware: 8× RTX PRO 6000 Blackwell 96 GB; 4× H200 141 GB with TP over NVLink.
- Arrival model: load sweeps; "Random topology" stress case exists.

## 4. Assumptions
- Datacenter-class GPUs with abundant memory; vLLM prefix caching with LMCache/CPU offload available.
- Agents have stable anchors (fixed prompts) and local transition structure that a first-order Markov model can learn within tens of dispatches.
- Prefill reuse is the dominant cost being saved; outputs are short (agent turns), so decode is not the bottleneck.
- Objective: hit rate, TTFT, per-turn latency, throughput. No energy, no task success.

## 5. Controller / mechanism
- State: transition counters C_ij, smoothed matrix P_ij=(C_ij+eps)/sum_k(C_ik+eps), block-to-agent map, last-access timestamps; <25 KB even for 24 agents [paper].
- Survival scorer: BFS over sparse graph thresholded at confidence tau gives hop distance E[a]; p_surv(a)=1-min(E[a],Emax)/Emax.
- Eviction score: Score(b)=(p_surv(a_b)+delta)*(exp(-lambda*age(b))+delta)*|b|; lowest evicted first; evicts reactively when the GPU pool saturates.
- Prefetch: issue warmup for predicted next agent when entropy reduction R>=Rmin; async between requests; adaptive gating disables it under low predictability.
- Overheads: ObserveTouch ~1 us per block, PredictSurvival <=6 us at 24 agents [paper].
- Hooks: block pool, engine core, scheduler in vLLM; env-var toggle.
- **Preemption/admission:** not addressed; relies on vLLM's scheduler [paper, per extraction]. No priority, no admission control.

## 6. Evaluation and reported results
- Baselines: vanilla vLLM (prefix cache + LRU); Continuum (TTL pinning, 0.3 s).
- Sustains 1.7–12× the load of vLLM and 4.2–16× that of Continuum at the same latency budget.
- Qwen3-235B SWE-bench: hit rate +7–13 pp, TTFT -33–54%, peak throughput +37%.
- Ablation: predictive eviction alone gives ~18–22 pp hit-rate gain; prefetch alone <=1 pp; combined adds 28% latency reduction on GAIA (251 vs 347 ms per turn).
- Gains shrink toward random routing (R=0.12 in Random topology). Cold start/convergence not evaluated.

## 7. What JouleServe-WS can take
- The scoring function is a cheap, self-contained eviction policy; reimplement as a baseline on SGLang 0.5.20: subclass the radix-cache eviction policy (evict-by-priority hook in `mem_cache/evict_policy.py`/RadixCache `evict`), tag radix nodes with an agent id (derive from hash of the first K tokens or a client-supplied header), keep the Markov counters in the scheduler process, and compute the score per candidate leaf. Effort: ~3–5 days for eviction only; prefetch is a trivial client-side warmup request (1 day). Caveat: SGLang radix node granularity differs from vLLM blocks [inferred].
- Reusable as a *negative-control* baseline: with role-rebuilt prompts and 1-in-3 role rotation, the Markov predictor is easy, so it tests whether paused-state reuse matters at all.

## 8. What JouleServe must add beyond it
- Any handling of active long decodes (preemption, retraction, admission), energy/thermal terms, task-level SLOs, knowledge of tool-wait duration, hybrid-state (SWA/recurrent) retention.

## 9. Workstation → edge
- Eviction score is compute-trivial and ports directly. Prefetch warmup consumes GPU compute that competes with small-batch decode and adds joules; on unified memory there is no offload tier, so "evict to CPU" is not a real tier (LMCache CPU offload becomes same DRAM).
- The 25 KB state and microsecond overhead are fine on Orin/Thor CPUs. Port effort: low for scoring, but engine port (vLLM -> SGLang) needed.

## 10. Relevance to our current findings
- Its wins come from a 43–60% anchor fraction and short outputs. Our P1 drone traces have 10–31% cross-call prefix repetition, prefill 1–8% of LLM time, and 32K thinking decodes, so the ceiling (0.3–1.7% single session) is far below its reported gains. The anchor idea (system prompt + tools + role header) may still hold within a role, worth measuring across roles.
- Deliberately ignores active decode pressure, the regime we expect under concurrency.

## 11. Open questions / uncertainty
- Exact turn counts, tool times and trace release unknown; code not yet released. Whether SGLang radix eviction can be swapped without invasive changes needs checking in 0.5.20. Extraction was through a summarizer; verify constants (delta, lambda, tau) in the PDF before reimplementing.

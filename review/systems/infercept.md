# INFERCEPT — per-interception min-waste choice among preserve / discard / swap for augmented LLMs

- **Source:** InferCept: Efficient Intercept Support for Augmented LLM Inference; Abhyankar, He, Srivatsa, Zhang, Zhang; ICML 2024 (arXiv 2402.01869v2, May 2024); https://arxiv.org/abs/2402.01869 ; code https://github.com/WukLab/InferCept
- **Review depth:** full text (arXiv HTML v2, extracted via fetch-and-summarize tool; equations and table quoted from that extraction, not re-verified against the PDF). Code repo not cloned/read.
- **Category:** agentic KV retention
- **Code/artifacts:** WukLab/InferCept, built on vLLM (old version, PagedAttention era). Datasets are public (GSM8K-XL, multihop Wikipedia QA, ALFWorld, ShareGPT); Image/TTS workloads generated with Stable Diffusion / Bark. No trace release noted.

## 1. Summary
- vLLM treats an API call as end of request: discards the KV and recomputes the whole context on return. Paper says this recompute is 37-40% of model forwarding time [paper, abstract/intro].
- InferCept picks, per intercepted request, preserve / discard / swap by estimating GPU memory *waste* (token-memory x time), with chunked recompute and a per-iteration "free" swap budget.
- Claims 1.6x-2x throughput and ~2x requests/s over vLLM [paper, abstract; Fig. 2].

## 2. Problem and key insight
- Preserve wastes memory for the whole pause; discard wastes GPU compute (and stalls other requests in the recompute batch); swap wastes time if it is not hidden behind forward passes. No single choice is best, so choose per request by comparing wastes in a common unit (GPU memory x time).
- Key insight: swap is free up to the amount that fits behind a forward pass, so the swap budget is derived from the iteration's own compute time.

## 3. Workloads
- Six augment types (Table in Sec. 3/5) [paper]: duration mean/sigma; calls/request; context length:
  - Math (calculator): 9e-5 s / 6e-5; 3.75 / 1.3; 1422 / 738 (GSM8K-XL)
  - QA (Wikipedia): 0.69 s / 0.17; 2.52 / 1.73; 1846 / 428
  - VE (ALFWorld): 0.09 s / 0.014; 28.18 / 15.2; 2185 / 115
  - Chatbot (human, ShareGPT): 28.6 s / 15.6 (estimated); 4.45 / 1.96; 753 / 703
  - Image (Stable Diffusion): 20.03 s / 7.8 (partly estimated); 6.91 / 3.93; 1247 / 792
  - TTS (Bark): 17.24 s / 7.6 (partly estimated); 6.91 / 3.93; 1251 / 792
- Context accumulates across interceptions (KV extended, not rebuilt) [paper]. Chatbot/image/TTS are the "long pause" classes (17-29 s), the only ones near our 13-115 s regime, and their durations are estimated/synthetic.
- Mixed workload samples uniformly across the six; arrival is a request-rate sweep (Poisson assumed [inferred]).
- Models: GPT-J-6B (1xA100), Vicuna-13B (1-2 A100, TP), Llama3-70B (4xA100, GQA). No hybrid/MoE.

## 4. Assumptions
- Discrete GPU + CPU DRAM over PCIe; swap bandwidth is the constraint, DRAM assumed plentiful.
- Interception duration unknown in advance: uses elapsed time `t_now - t_call` as estimator; reports 93% of oracle performance [paper]. Short-call types (math/QA/VE, ms-1s) dominate the benefit of preserve.
- Datacenter A100 throughput objective (requests/s, normalized latency). Prefill-heavy recompute (long contexts, short decodes) — waste model assumes recompute matters.

## 5. Controller / mechanism
- Waste formulas [paper, Eq. 1-4]; M = KV bytes per token, C_i context, C_other = other running contexts:
  - Preserve: `T_INT * C_i * M`
  - Discard: `T_fwd(C_i)*C_i*M + T_fwd(C_i)*C_other*M` (own recompute footprint + stall imposed on others)
  - Swap: `2*T_swap(C_i)*C_batch*M` (in+out, stalls whole batch if not hidden)
  - Chunked discard: `T_fwd(C_i)*C_i*M/2 + n*T_fwd(C_i/n)*C_other*M`, n chunks; chunk size = GPU saturation point S minus running-group size.
- Swap budget: per iteration i with batch B_i, set `T_swap(N_i) = T_fwd(B_i)`; N_i tokens are swappable for free. Constraints: swap-in+out <= N_i; swapped-out <= free CPU + swapped-in; swapped-in + new <= swapped-out + free GPU.
- Min-waste algorithm (Sec 4.3): for each intercepted request compute min(preserve, chunked-discard); sort by waste descending; give swap budget in that order; remaining contexts preserved or discarded by comparison.
- Resumed requests: three FCFS queues (running/swap/waiting) by arrival time.
- Layer-pipelined swap (each layer a pipeline stage). Offline profiler builds T_fwd and T_swap tables.
- Implementation: vLLM modification (scheduler, waste estimator, swap manager, API executor).

## 6. Evaluation and reported results
- Baselines: vLLM (discard), ImprovedDiscard (keeps original arrival time), Preserve, Swap [paper].
- 6B: up to 1.6x higher arrival rate at same normalized latency; 1.9x-5.7x lower normalized latency (Fig. 2). 13B 1 GPU: 1.25x rate; 2 GPU: 1.8x rate, 1.6x-10x latency. 70B: 2x rate, 1.3x-12x latency [paper, Fig. 2].
- Single augment: QA up to 2.3x, chatbot 1.9x normalized latency.
- Waste: Discard 27%, Swap 26%, InferCept 0.69% [paper].

## 7. What JouleServe-WS can take
- Waste-estimator as a **baseline decision rule**: implement on SGLang 0.5.20 as a policy layer outside the engine. Sketch: on tool-call start, session controller computes preserve cost (`elapsed_est * ctx_tokens * bytes/tok`) vs recompute cost (`T_prefill(ctx)` from an offline profile, x concurrency penalty). If preserve is cheaper, keep radix nodes locked (SGLang lock_ref via a keep-alive/dummy request or session/priority API [inferred; verify exact 0.5.20 API]); otherwise let radix LRU evict. Swap variant maps to HiCache host tier (`--enable-hierarchical-cache`) with write-through then evict [inferred]. Effort: preserve/discard baseline ~2-4 days; faithful swap-budget and chunked recompute not portable without engine changes (~2+ weeks; low value on our workload).
- Elapsed-time estimator (`t_now - t_call`) as a zero-knowledge pause predictor.
- Waste in memory-x-time units as a common currency; could be extended to joules.

## 8. What JouleServe must add beyond it
- Energy objective; task-level SLOs; decode-dominated agents; long (13-115 s) real waits; hybrid-state; unified memory; active-decode pressure. INFERCEPT never models decode cost or power.

## 9. Workstation -> edge
- Swap is meaningless on Jetson: host DRAM is the same pool, so swap frees nothing; the policy collapses to preserve vs discard, i.e. the first two waste terms. Swap budget N_i (hidden behind forward) has no analogue. On A5000 (PCIe) swap works but 25K-token pool makes budgets tiny.
- T_fwd tables must be re-profiled per DVFS/nvpmodel state; recompute cost on Orin is large in wall-time but small in energy share if prefill is 1-8%.

## 10. Relevance to our current findings
- With pauses 13-115 s, preserve waste `T_INT*C*M` is huge compared with any recompute cost; the rule says **discard** for nearly every call, which matches our finding that retention buys 0.3-1.7% of LLM time. Rebuilt per-role prompts mean recompute is mostly unavoidable anyway (only 10-31% overlap). The rule is a cheap, correct-directional baseline, not a win.
- Its target regime (short calls, prefill-heavy, accumulating context) is opposite ours.

## 11. Open questions / uncertainty
- Numbers via summarizer extraction; verify Eq. 1-4 against PDF before citing.
- Chatbot/Image/TTS durations are partly estimated by authors.
- Repo state / vLLM version not checked.

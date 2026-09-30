# AgentServe — phase-isolated single-GPU serving for local agents (cold prefill / resume prefill / short decode) with Green Contexts

- **Source:** AgentServe: Algorithm-System Co-Design for Efficient Agentic AI Serving on a Consumer-Grade GPU; Yuning Zhang, Yan Yan, Nan Yang, Dong Yuan; arXiv preprint, 11 Mar 2026; https://arxiv.org/abs/2603.10342 (HTML https://arxiv.org/html/2603.10342v1). License CC BY-NC-ND 4.0.
- **Review depth:** full text via arXiv HTML through a fetch-and-summarize tool (two passes were not possible; details as extracted). Algorithm constants (theta_high/low, budgets), appendix proofs and exact figure numbers not verified. No code link found in the page.
- **Category:** agent-aware scheduling; edge/on-device (consumer GPU)
- **Code/artifacts:** not found. Base engine llama.cpp with CUDA Green Contexts **[paper]**. Traces: not stated public; workload is ToolBench-derived.

## 1. Summary
Single-GPU serving for local SLM agents. Classifies work into cold prefill, resume prefill, short decode; isolates decode with SM reservations via 10 pre-created Green Context slots; TPOT-feedback controller adjusts resume-prefill token budget and decode SM floor. Up to 2.8x TTFT and 2.7x TPOT improvement vs baselines **[paper, abstract]**.

## 2. Problem and key insight
Agents interleave long cold prefills (~2.5-3.5k-token system prompt + tool specs), small resume prefills (tool output appended to cached context), and very short decodes. Mixing them causes head-of-line blocking and TPOT jitter on a shared consumer GPU. Insight: resume prefills are small enough to be budgeted/throttled instead of chunked blindly; decode gets protected SMs **[paper]**.

## 3. Workloads
- Two ToolBench-derived paradigms: ReAct (decode avg 37-45 tokens; resume prefill 30-127 tokens) and Plan-and-Execute (decode avg 55-64; resume 125-421; heavier initial planning). Overall cold ~3k, decode 21-141 tokens **[paper]**.
- Frameworks: LangChain, AutoGen, ToolBench integration. Models: Qwen2.5-3B/7B, LLaMA-3-8B. GPUs: RTX A5000 (64 SMs, 24 GB) and RTX 5090 (128 SMs, 32 GB) **[paper]**.
- Concurrency: N agents (up to 6 on A5000) issuing closed-loop requests. Tool durations: **not extracted; likely short/synthetic, not characterized** (unverified). No thinking-mode reasoning, no minutes-long waits.

## 4. Assumptions
- Everything fits in GPU memory; all KV for active agents resident; "cached context" for resume assumed still present (no eviction, no offload, no tiering).
- Short outputs (tens of tokens), small models, structured tool use; SLO is per-request TPOT/TTFT, not task-level. Explicitly not for compute-heavy general agents or cloud **[paper]**.
- Monotone throughput vs SM share; discrete 10% granularity.

## 5. Controller / mechanism
- Three layers: application, CPU orchestration (TPOT-driven scheduler), GPU execution (Green Contexts).
- Controls: B_prefill(t) (resume-prefill token budget) and R_min(t) (minimum SMs for decode). If measured TPOT > theta_high: shrink B_prefill, raise R_min; if < theta_low: relax both **[paper]**.
- 10 Green Context slots (10%..100% SMs); switching <50 us, <0.1% of decode step. Two CPU threads (prefill/decode); shared KV pool with mutexes and cudaEvent sync (no inter-process KV transfer) **[paper]**.
- Competitive-ratio analysis vs offline optimum under decode SLO: loss from granularity, controller lag, context overhead.

## 6. Evaluation and reported results
- Baselines: SGLang (PD disaggregation), vLLM (chunked prefill), llama.cpp. Metrics TTFT, TPOT (p95), throughput, SLO attainment.
- TTFT up to 2.8x, TPOT up to 2.7x; throughput 1.2-2.2x; A5000 stable up to 6 agents where baselines degrade at 4; 5090 near-perfect SLO. Ablation N=4: no TPOT scheduling -> +15-25% TTFT, 1.4x TPOT; no Green Contexts -> +20-30% latency variance **[paper]**.
- Energy: not evaluated (as far as extracted).

## 7. What JouleServe-WS can take
- Direct: the phase taxonomy. In SGLang 0.5.20 log per-request `cold` (no radix hit), `resume` (radix hit + small extension), `decode` sizes; report their split for K2-Horizon traces. Reimplement as baseline: cap `--chunked-prefill-size` small and a TPOT-feedback loop changing it (proxy for B_prefill); SM partition is not natively in SGLang.
- Green Contexts: CUDA 12.4+ driver API on A5000 (Ampere sm_86) should work without root **[inferred; verify]**, but integrating into SGLang means custom kernel-launch contexts: high effort. Cheaper approximation: MPS with `CUDA_MPS_ACTIVE_THREAD_PERCENTAGE`, or two SGLang instances on two GPUs (we have 2 A5000) as PD-split baseline.
- Measurement: reuse the TTFT/TPOT/SLO-attainment plots; add joules/task.

## 8. What JouleServe must add beyond it
Retained-state policy across long tool waits (AgentServe assumes cache stays), energy objective, task-level SLOs, large reasoning decodes, admission control when KV pool (~25K tokens on our WS) is full, hybrid models.

## 9. Workstation → edge
- Green Contexts: supported on Jetson (Orin GA10B, CUDA 12.x, JetPack 6.x) **[inferred; verify]** but Orin has 16 SMs (AGX Orin 64GB: 2048 cores) so 10% slots become 1-2 SMs: coarse. Thor Blackwell has more SMs.
- Unified memory: "shared KV pool without transfer" is trivially true; but memory bandwidth (not SMs) is the decode bottleneck on Orin (~204 GB/s), and SM partitioning does not isolate DRAM bandwidth from co-located sims. Isolation effect would be smaller than on A5000 **[inferred]**.
- DVFS/thermal changes TPOT thresholds; controller must be retuned; power rails give energy for free.

## 10. Relevance to our current findings
P1: prefill 1-8% of LLM time, decode dominates with long thinking — the opposite of AgentServe's short-decode regime. Phase isolation matters mainly under concurrency with cold prefills of rebuilt role prompts (10-31% reuse means most prompt tokens are effectively cold). Resume-prefill optimization is low value for Reflexion; useful for tool-calling/ReAct in P1 with shorter outputs.

## 11. Open questions / uncertainty
No code or trace; tool-duration distribution unverified; controller constants unknown; compared to SGLang PD-disagg on a single GPU (fairness of baseline config).

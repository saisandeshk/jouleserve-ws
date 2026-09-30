# KVFlow — Agent-Step-Graph-driven radix eviction plus overlapped CPU-to-GPU prefetch on SGLang

- **Source:** KVFlow: Efficient Prefix Caching for Accelerating LLM-Based Multi-Agent Workflows; Zaifeng Pan et al.; arXiv preprint, July 2025; https://arxiv.org/abs/2507.07400 (ID verified)
- **Review depth:** full text — arXiv HTML (Sections 3.1–3.3, 4.1–4.2, limitations). Appendix not checked.
- **Category:** agentic KV retention
- **Code/artifacts:** No repo or availability statement found in the paper. Built on SGLang v0.4.4. No public traces.

## 1. Summary
- Models a multi-agent workflow as an Agent Step Graph; computes a steps-to-execution value per agent; assigns it as eviction priority on radix nodes (fixed prompts) and prefetches soon-needed prefixes from CPU to GPU in background threads [paper].
- Reported: up to 1.83× vs SGLang+HiCache for a single workflow with large prompts; up to 2.19× vs HiCache under concurrent workflows (Sec 4.1–4.2) [paper].

## 2. Problem and key insight
- LRU evicts fixed agent prompts right before reuse in cyclical/sequential agent pipelines; HiCache reloads on demand, stalling.
- Insight: the workflow graph tells you how soon each agent runs, a better eviction signal than recency, and it enables prefetch.

## 3. Workloads
- Synthetic sequential 10-agent workflow: fixed prompts 4096–8192 tokens, dynamic suffix 32–256, output 32–256 (Sec 4.1).
- Realistic: 4-agent PEER-template workflows, Financial QA, prompts tens to hundreds of tokens (Sec 4.2, Fig 7/8).
- High concurrency: 4–64 concurrent workflows, fixed 512–1024, dynamic/output 256.
- Multi-agent only; no tool pauses modeled (agents are LLM calls). Context does not accumulate beyond fixed+suffix.
- Models: Llama-3.1-8B, Qwen2.5-32B (GQA, dense). GPUs: A10G 24 GB (PCIe 2 GB/s as stated), H100 80 GB (64 GB/s). Temperature 0. Batch size 1 in single-workflow tests.

## 4. Assumptions
- Workflow structure known at runtime (sgl.function per agent); no runtime branch prediction; fixed/dynamic prompt boundary marked by user or inferred from hit consistency.
- Discrete GPU + CPU host tier with full-duplex PCIe; short outputs (paper notes speedup diminishes with longer output because decode dominates).
- Memory must fit the retained prefixes; "if concurrency is too high, all available memory is consumed" (Sec 4.2).

## 5. Controller / mechanism
- Step graph: nodes = agent invocations, edges = dependencies; aggregation max(E1,E2)+1 for joins, min(E1,E2)+1 for conditional any-path (Sec 3.1).
- Priority to radix nodes: steps-to-execution set on the last node of the fixed prompt, propagated upward; shared nodes take the minimum among children; dynamic suffixes get highest eviction priority.
- Node states: in-GPU, backup-in-CPU, loading, offloading. Prefetch of next agents' prefixes within a concurrent-prefetch limit; status-aware scheduling skips requests whose prefix is still loading (Sec 3.2).
- Metadata carried by JIT-substituted HTTP requests: current agent id + steps-to-execution of all agents; client ID per application (Sec 3.3).
- **Preemption/admission:** none for active decodes; only the skip-if-loading rule [paper].

## 6. Evaluation and reported results
- Baselines: SGLang (GPU-only radix, LRU), SGLang+HiCache.
- Single workflow (8192/32/32, A10G): 1.83× vs HiCache, 2.91× vs GPU-only. Speedup shrinks with longer outputs.
- Concurrency: up to 1.25× (synthetic multi-workflow), up to 2.19× vs HiCache; HiCache falls to 0.57× of SGLang baseline at 1024 fixed tokens with 64 workflows.
- PEER realistic: 1.12× vs SGLang, 1.08× vs HiCache (Fig 8): gains nearly vanish with short prompts.

## 7. What JouleServe-WS can take
- Baseline on SGLang 0.5.20: (a) client sends a per-request `steps_to_execution` (extra field in request, or via session/`custom_labels`); (b) add a priority eviction policy in the radix cache (0.5.x has pluggable eviction policies) using this value on the node's last fixed-prompt token; (c) for prefetch on WS, use HiCache host tier plus an explicit prefetch/warmup call; (d) status-aware skip already exists partially in HiCache load-back. Effort: ~1 week (eviction 2–3 days, prefetch integration 3–4 days). Since P1 graphs (generator/evaluator/reflector) are fixed and known, the step graph is trivial to supply.
- Method to copy: steps-to-execution as the priority label.

## 8. What JouleServe must add beyond it
- Active-decode preemption, tool-wait duration awareness (its graph has no time dimension), hybrid-state handling, energy/thermal terms, task-level SLOs, unknown/dynamic graphs.

## 9. Workstation → edge
- Prefetch relies on a separate host tier and PCIe full-duplex; on Orin/Thor there is no PCIe copy, host tier is the same DRAM, so "CPU backup" only frees pool space, and the overlap gain reduces to allocator bookkeeping. The reload cost being hidden becomes near zero, but so does the reason to offload. Small batches remove HiCache contention effects it exploits. Port effort: eviction part trivial; prefetch part largely moot.

## 10. Relevance to our current findings
- Its speedup is a prefill-dominated effect (fixed prompts 4–8K, outputs 32–256). Our runs are decode-dominated (prefill 1–8%), so its benefit falls in the regime the paper itself flags as diminishing. Per-role rebuilt prompts mean fixed-prompt reuse is limited to a role's system header. Long real-time waits are outside its model.

## 11. Open questions / uncertainty
- No code; SGLang 0.4.4 vs 0.5.20 radix internals differ. Tool/wait handling is absent, so extending it to time-aware retention is our contribution. Full-text extraction via summarizer; verify Fig 3 aggregation and prefetch limit values.

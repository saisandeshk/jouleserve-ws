# Prism / kvcached — memory ballooning for multi-LLM GPU sharing, with an open elastic-KV library that already supports SGLang 0.5.20

- **Source:** Prism: Cost-Efficient Multi-LLM Serving via GPU Memory Ballooning; Shan Yu, Yifan Qiao, ... Ying Sheng et al. (21 authors); arXiv preprint 2505.04021 (v3, 10 Jun 2026; v1 titled "Prism: Unleashing GPU Sharing for Cost-Efficient Multi-LLM Serving"); https://arxiv.org/abs/2505.04021 ; code https://github.com/ovg-project/kvcached (balloon driver) and https://github.com/Multi-LLM/prism-research (research prototype). No peer-reviewed venue found in the PDF.
- **Review depth:** partial-to-full text. Read the PDF text (abstract, intro, §2 trace analysis, §5 ballooning, §6 policies headings, §7 evaluation, production section, ~14.5K words) via pdftotext; did not read appendices in detail; README of kvcached read through a fetch-and-summarize tool (lower fidelity). Code not run.
- **Category:** KV substrate/tiering (datacenter multi-model co-serving)
- **Code/artifacts:** kvcached: Apache-2.0 **[code, README]**; SGLang >= 0.5.11 (tested to 0.5.20), vLLM >= 0.17.0; MHA/GQA/MLA/sliding-window/hybrid attention incl. Gemma-4 and Qwen3.5/3.8-type linear-attention hybrids; prefix cache (vLLM APC, SGLang RadixCache) with a configurable memory bound; AMD ROCm builds; env vars (`ENABLE_KVCACHED`, `KVCACHED_AUTOPATCH`, `KVCACHED_PAGE_SIZE_MB`, ...) and a "memory control CLI" to enforce limits. README lists A100-80G as tested; no Jetson / unified-memory mention. Traces: production traces (Hyperbolic, Novita AI) are summarized, not necessarily released (not verified).

## 1. Summary
Prism observes that datacenter multi-LLM serving needs both space sharing (co-locate models) and time sharing (swap models in and out), and that GPU memory is the common bottleneck. It introduces a "balloon driver" (kvcached) that lets each serving engine reserve a large virtual address range and back it with physical GPU pages (2 MB) only on demand, so a model's KV pool can grow and shrink at run time and memory moves between models. Two-level scheduling (placement + slack-aware request arbitration) sits on top. **[paper, abstract, §1, §5]**

## 2. Problem and key insight
- Engines like SGLang and vLLM pre-allocate a static KV pool per model; PagedAttention manages memory inside one model but cannot harvest across models. **[paper §1]**
- Insight: treat GPU memory like a hypervisor treats guest VM memory. Reclaim from idle models (swap in weights, time sharing) or shrink the KV reservation of low-rate models (space sharing). **[paper §1]**
- Mechanism: decouple virtual from physical memory (CUDA VMM). "fine-grained memory redistribution at a 2 MB granularity with millisecond-level overhead" **[paper §1]**.

## 3. Workloads
- Two production traces for evaluation (Hyperbolic, Arena-Chat); trace analysis over 4 traces, 24-129 deployed models, 11 days to 16 months, 58 models in total **[paper §1, §2]**. Models 3B-70B.
- Observation of a "bursty-group" pattern driven partly by "compound AI systems and agentic pipelines" **[paper §1]**; but requests are plain chat/completions, **not agent sessions with tool pauses** **[inferred]**.
- Hardware: up to 4 nodes x 8 H100-80G (32 GPUs) **[paper §7]**; overhead microbenchmark on A100-40G.

## 4. Assumptions
- Datacenter GPUs with a separate host tier; model weights can be evicted to host or reloaded; many models, SLO on TTFT/TPOT; memory demand changes come from the other **models** in the same system, which the scheduler controls and can see. **[inferred from design]**
- Single serving stack (SGLang) modified by 22 lines to integrate kvcached **[paper §7]**.
- No notion of an external, uncontrolled memory consumer (a vision tool, a simulator) and no notion of paused session state.

## 5. Controller / mechanism
- **Balloon driver (kvcached)**: engine sees a contiguous "elastic tensor" (eTensor, PyTorch extension) over reserved virtual space; physical 2 MB pages mapped lazily; layout reorganized so all layers' K/V of a token are contiguous in virtual space (one batch allocation instead of 2L); a pre-allocation thread keeps a small buffer of pages; "kvcached dynamically adjusts physical memory limits: when an evicted model is reactivated, it shrinks the limits of other models on the same GPU" **[paper §5.2 D1-D4]**.
- **Policies (§6)**: placement that preserves ballooning headroom; model eviction/activation when idle; slack-aware arbitration of requests using a GPU-level queue.
- Overhead: worst case with two Llama-3.2-3B models on A100-40G, 3 ms (4%) TTFT and 4 ms (13%) TPOT at 32 req/s vs static partitioning **[paper §7.5]**.

## 6. Evaluation and reported results
- "up to 3.3x higher TTFT SLO attainment and 2x higher TPOT SLO attainment given the same number of GPUs"; "up to over 2x cost reduction or 3.5x more requests" at equal SLO attainment **[paper §1]**.
- Baselines: MuxServe (ported to SGLang as MuxServe++), QLM-style time sharing, static partitioning, Aegaeon (named in reviewer-visible text of the tool summary; check §7 before quoting).
- Production shadow replay: Company A 3.89x average per-GPU token throughput, no SLO violations **[paper §7.6]**. kvcached README: "2-28x TTFT reduction" for three Llama-3.1-8B on A100-80G under intermittent peaks **[code, README]**.
- No energy metric.

## 7. What JouleServe-WS can take
- **Directly usable.** kvcached on SGLang 0.5.20 (the WS version) gives a run-time-resizable KV pool on the 2x A5000 box with no engine fork. The memory-control CLI lets an experiment script emulate "a tool takes N GB, later releases it" and measure what the agent loses. This is the cheapest way to build the Option D baseline "resize the pool at run time".
- Emulation sketch: launch SGLang with kvcached; a background process allocates/frees GPU memory (stand-in for a VLM tool); set the kvcached limit accordingly; replay P1 agent traces; count prefix misses on resume.
- Question to test early: does kvcached + RadixCache keep paused agents' prefixes when the limit shrinks, or does it evict via LRU like the default? (README says prefix cache is bounded by a configurable limit; behavior under shrink not verified.) **[inferred, untested]**

## 8. What JouleServe must add beyond it
- A policy that decides **what to keep** when memory shrinks: agent-aware (paused sessions with known resume time and known burst) rather than idle-model/slack based.
- Handling memory taken by **non-LLM consumers** (tools, co-located models) that the serving engine does not schedule.
- Task-level energy objective; edge platform; hybrid-model state (sliding window / recurrent state): kvcached claims support, but policy for it is absent.

## 9. Workstation -> edge
- kvcached relies on CUDA VMM APIs (cuMemCreate/Map). On Jetson Orin/Thor these exist in recent JetPack/CUDA but README lists no Jetson support **[code]**; porting effort unknown, must be tested.
- On unified memory, "reclaiming" a page frees it for the CPU-side tool as well; there is no host tier to swap weights to (Prism's time sharing assumes one). Only the space-sharing half of Prism transfers. **[inferred]**
- 2 MB page granularity, ms overhead measured on A100; Jetson page-mapping cost unmeasured.

## 10. Relevance to our current findings
- P1 traffic-agent burst (8-45 image requests filling 99.5% of a 12.4K-token pool on Orin 64) is the exact situation ballooning targets, but in P1 the burst goes to the same SGLang server, so the contention is inside one engine, not across engines. kvcached would not remove the cap; it would let a **different** consumer (e.g., a separate VLM process) borrow pages, which changes where the 12.4K comes from. **[inferred]**
- Prism's slack-aware arbitration is a request-level idea; drone traces are decode-dominated with long tool waits, so little overlap.

## 11. Open questions / uncertainty
- Whether prefix cache entries are first to be reclaimed on shrink and how paused sessions are treated; appendix not read.
- Venue: arXiv v3 only; v1 title differed. A companion paper on kvcached/GPU multitasking is cited in the README but not identified.
- Trace availability not verified.
- Related negative result: "Elastic KV Cache for LLM Serving: A Working Reclamation Mechanism, and Why Chunked Prefill Already Closes the Gap" (arXiv 2608.23658, S. Sivashanmugam, Aug 2026; abstract read, PDF text skimmed only through a summarizer) reports ~1% median-TTFT difference between chunk sizes 8192 and 32768 and a prefill-reserve of 16% at 1 GPU falling to 2.7% at 4 GPUs **[paper, abstract]**; it argues that reclaiming the engine's own prefill reserve is not worth it, and releases an elastic virtual-memory allocator. It concerns the reserve inside one engine, not external pressure.

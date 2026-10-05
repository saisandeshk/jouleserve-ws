# MorphServe — pressure-aware KV cache resizing plus runtime quantized layer swapping

- **Source:** MorphServe: Efficient and Workload-Aware LLM Serving via Runtime Quantized Layer Swapping and KV Cache Resizing; Zhaoyuan Su, Zeyu Zhang, Tingfeng Lan, Zirui Wang, Haiying Shen, Juncheng Yang, Yue Cheng; arXiv preprint 2506.02006 (v2, 7 Jan 2026; MLSys-style template, "Preprint"); https://arxiv.org/abs/2506.02006
- **Review depth:** full text via PDF text extraction (abstract, §1, §3-§5 including KVResizer §4.4, evaluation setup and headline results); appendices only skimmed.
- **Category:** KV substrate/tiering (elastic KV under memory pressure, datacenter GPU)
- **Code/artifacts:** none found; reference list only has a trace link. Built on SwiftLLM (not vLLM/SGLang) with ~2,200 lines of Python and 500 lines of C++/CUDA **[paper §5]**.

## 1. Summary
A controller watches KV-cache utilization and queueing delay. When load surges it (a) swaps selected FP16 layers for INT4 versions, freeing memory, and (b) grows the KV cache with those freed blocks (KVResizer). When pressure subsides, layers and blocks are restored. **[paper abstract, §4]**

## 2. Problem and key insight
Static KV pre-allocation and static quantization both fail under bursty load: either SLO violations (memory exhaustion, preemption, swap) or permanent accuracy loss. Memory should be traded between weights and KV at run time, in a state-preserving way. **[paper §1]**

## 3. Workloads
- Azure LLM Inference trace and BurstGPT, 72 s snippets, arrival rates downscaled by 1.75x and 4.75x **[paper §5]**.
- Vicuna 7B v1.5, Llama 2 7B, Llama 3 8B on an NVIDIA L4 (24 GB HBM, 256 GB DRAM); CodeLlama 34B on A100-80G. Prompts 512-1024 tokens, outputs 256-512 **[paper §5]**.
- Plain chat/summarization, single-turn. Not agentic.

## 4. Assumptions
- The memory pressure is **self-generated** by the engine's own request burst, visible through KV usage and queue length. Thresholds are user-defined (example: KV usage over 85%, queueing delay over 100 ms) **[paper §4.1]**.
- A quantized variant of every layer exists and layer sensitivity is profiled offline.
- Host DRAM tier exists (layer swapping CPU<->GPU).
- Objective: TTFT SLO (2 s) and accuracy, not energy.

## 5. Controller / mechanism
- **Morphing Controller** = global GPU memory manager; triggers LayerSwapper and KVResizer from monitored metrics.
- **KVResizer** extends PagedAttention with on-demand block allocation/deallocation "through memory mapping without requiring kernel recompilation", asynchronous on separate CUDA streams **[paper §4.4]**. It does not compress existing KV.
- Trigger: insufficient memory for prefill or decode block allocation, or queue length/wait above threshold.
- Reverse transitions when pressure subsides.

## 6. Evaluation and reported results
- "reduces average SLO violations by 92.45% and improves the P95 TTFT latency by 2.2-3.9x compared to full-precision serving" **[paper abstract]**; 3.4-19.5x in performance mode vs full precision **[paper §5.1]**.
- Quality loss 0.51-3.82% (F1/Rouge-L) vs 2.34-9.47% for static INT4 **[paper §5.1]**.
- Baselines: FP16 and static INT4 (AWQ), same engine; no comparison with other elastic-KV systems.

## 7. What JouleServe-WS can take
- The **trigger design** (KV utilization + queue delay thresholds, hysteresis, reverse transition) as a reactive baseline for "pool shrinks when a tool takes memory".
- The idea of **trading weight precision for KV capacity** as an Option D knob: when a vision burst is coming, swap some layers to INT4 to keep paused contexts resident. Needs a quantized weight copy; not available in SGLang as a hot swap, so would be emulated by launching two engines **[inferred]**.
- No code to reuse.

## 8. What JouleServe must add beyond it
- Anticipation: MorphServe reacts after pressure appears. A tool-aware controller knows a vision burst is coming.
- Session-aware choice of **which** KV to protect (paused agent contexts vs active decodes).
- External consumers; energy; edge.

## 9. Workstation -> edge
- Layer swap assumes a slower host tier; on Jetson unified memory, "swap to CPU" frees nothing. Quantized-layer swap (INT4 replaces FP16 in place) still frees capacity, which is the only part that transfers. **[inferred]**
- Orin memory bandwidth is lower than L4/A100; swap latency unknown.

## 10. Relevance to our current findings
- P1's problem is pool size (12.4K tokens on Orin 64) and an in-engine burst. KVResizer could enlarge the pool when weights shrink, but Orin 64 holding a 12.4K pool suggests the rest is weights/other processes; whether INT4 swap yields enough extra pool is **[inferred, unquantified]**.
- Does not address paused-session retention.

## 11. Open questions / uncertainty
- No public code; numbers not reproducible.
- Venue unknown (preprint, v2 Jan 2026).
- KVResizer overhead numbers not extracted (§5 detail only skimmed).

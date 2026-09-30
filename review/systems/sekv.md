# SeKV — semantic-span KV cache with GPU summaries and CPU low-rank reconstruction for long context

- **Source:** SeKV: Resolution-Adaptive KV Cache with Hierarchical Semantic Memory for Long-Context LLM Inference; Amirhossein Abaskohi, Giuseppe Carenini, Peter West, Yuhang He; arXiv preprint (cs.CL), submitted 30 Jun 2026; https://arxiv.org/abs/2606.31145 (ID resolves and matches). Code: https://github.com/AmirAbaskohi/SeKV
- **Review depth:** full text via HTML (arxiv.org/html/2606.31145v1) as summarized by the fetch tool, plus repo overview. I did not read the PDF line by line; numbers below are from that extraction and should be re-checked against the tables before citing.
- **Category:** KV substrate/tiering (KV compression; adjacent, not session-serving)
- **Code/artifacts:** GitHub repo released, MIT license (per repo page), standalone PyTorch + HuggingFace; adapters for Llama 3.x, Mistral-7B, Qwen2.5. No vLLM/SGLang integration mentioned. Training data RedPajama; benchmarks public.

## 1. Summary
- Compresses **within one long context** (single request) rather than retaining state across turns. Context is cut into entropy-guided spans; each span keeps a GPU-resident summary plus anchors, and a CPU-resident low-rank (SVD) basis. A trained "zoom-in" gate expands query-relevant spans during decoding.
- Reported: +5.9% average over the strongest semantic-compression baseline (SentenceKV) at 10% GPU KV budget and 53.3% GPU-memory reduction at 128K context (abstract; Table 1, Fig 4). [paper]

## 2. Problem and key insight
- Long-context KV memory; token-eviction methods lose information irreversibly; semantic compression loses detail.
- Insight: keep coarse representation on GPU and reconstructable detail on CPU, and expand only spans that the current query routes to (resolution-adaptive).

## 3. Workloads
- Static long-context benchmarks: LongBench (4,750 ex., 1K-18K tokens), RULER (4,000, 4K-128K), InfiniteBench (3,946, ~100K avg), NIAH (~800/setting, up to 128K), GSM8K 50-shot (13K-15K context) (Table 1/2). Not multi-turn, no agents, no tool waits, no arrivals/concurrency. Single request at a time.
- Models: Llama-3.2-3B, Llama-3-8B, Llama-3.1-8B, Mistral-7B, Qwen2.5-14B (all full-attention/GQA). Hardware: A100-80GB (up to 8 for InfiniteBench/FullKV reference).
- The prior card mentions "agent planning motivation": the extracted text says multi-turn/agent use is **not** evaluated. [paper as extracted]

## 4. Assumptions
- CPU-GPU transfer over PCIe with asynchronous prefetch of SVD bases during decoding; a discrete host tier.
- Frozen base LLM; trained routing projections (4.19M params), per-head/layer thresholds (1,024), rank-gate (<0.1M) = <0.05% of params, trained on RedPajama with 22-66 h per backbone on 8xA100 (~0.5B tokens, 8K->32K curriculum).
- Quality depends on entropy-based span boundaries; fragmented content (code, tables) may degrade (paper's stated limitation).
- Bandwidth bottleneck under adversarial high-activation queries (paper's limitation).
- Objective: accuracy at fixed GPU KV budget (10%), memory, latency; no energy.

## 5. Controller / mechanism
- Span segmentation: token surprisal from prefill; above mu + alpha*sigma => span anchor kept at full resolution on GPU.
- GPU: 32-dim key-projection summary per span + anchor tokens + surprisal-weighted mean KV. CPU: SVD low-rank bases with learned per-component soft gates (adaptive rank).
- Decoding: per head per layer, sigmoid gating of summary-query dot products decides whether to expand a span (fetch basis, reconstruct KV).
- Implementation: model-side, HuggingFace Transformers; not a scheduler or cache manager. Nothing about retention across requests.

## 6. Evaluation and reported results
- Baselines: StreamingLLM, H2O, SnapKV, PyramidKV, ChunkKV, SemantiCache, SentenceKV, FullKV; matched 10% GPU KV budget.
- Table 1: wins all 20 benchmark-model comparisons; NIAH 91.17 vs 84.83 (Qwen, vs SentenceKV), RULER 87.34 vs 82.04, InfiniteBench 24.83 vs 23.14, LongBench 54.71 vs 52.31.
- Table 2 (50-shot GSM8K, Qwen2.5-14B): 84.5% vs 82.1% SentenceKV, 86.7% FullKV.
- Table 3 (Qwen2.5-14B): 4K in/1K out: 38.05 s vs 43.60 s FullKV (120.11 vs 105.92 tok/s); 8K/4K: 166.95 s vs 183.42 s (64.21 vs 55.93 tok/s). It is faster than FullKV because decode reads less KV.
- Fig 4: GPU memory 31.2->34.9 GB (8K->128K) vs FullKV 36.0->74.8 GB (53.3% reduction at 128K).

## 7. What JouleServe-WS can take
- Little for the serving policy. It's the only one of the four not about session reuse.
- Useful **as a memory-pressure lever comparison** ("compress instead of evict"): a lossy option when the 25K-token pool is full. Anything from it would be an offline accuracy-vs-budget experiment, not a baseline.
- Repo is standalone PyTorch (needs trained gates per model; K2-Horizon-7B would need training: 22-66 GPU-hours on 8xA100 per backbone, an unrealistic cost for us).

## 8. What JouleServe must add beyond it
- Anything about serving: concurrency, pause/resume, eviction policy, energy, SLOs. SeKV states nothing about multi-request state or shared caches (span state is per request; whether it can integrate with paged/radix caches is unaddressed).

## 9. Workstation -> edge
- Its CPU tier is discrete host memory over PCIe; on Jetson the "CPU basis" is the same DRAM, so its GPU-memory saving is a **compression** saving only if the SVD bases are stored lower-rank; it does not move bytes out of the shared pool. [inferred]
- Expanding spans costs SVD reconstruction compute on the GPU under a power cap. Not evaluated on edge devices or with energy meters.
- Hybrid models (Gemma-4, Qwen3.8 with Gated DeltaNet) have less full-attention KV to compress; method is defined for full-attention layers.

## 10. Relevance to our current findings
- Our sessions are decode-dominated with bounded context (~tens of K tokens); SeKV targets 100K+ contexts and holds up at 10% budget. Its decode speedup at 8K/4K (about 9% shorter latency) is a *modest* effect for a 14B model.
- Cite it as adjacent memory work, in line with the earlier card correction, rather than as a comparator for session retention.

## 11. Open questions / uncertainty
- Numbers come from an HTML extraction; verify tables before quoting. Code was not run.
- Behaviour with multi-turn/agent inputs and with paged serving engines unknown.
- Preprint from June 2026, not peer-reviewed as of review date.

# CacheBlend — reuse precomputed KV at non-prefix positions, selectively recomputing ~15% of tokens per layer

- **Source:** CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion; Jiayi Yao, Hanchen Li, Yuhan Liu, ..., Junchen Jiang (U Chicago, Microsoft Research, Stanford); EuroSys '25 (DOI 10.1145/3689031.3696098); arXiv 2405.16444 (v3, Apr 2025). ID and venue verified. Code: https://github.com/LMCache/LMCache
- **Review depth:** full text — arXiv v3 PDF read (§1-§7, appendix A on RoPE). Code repo not read; LMCache docs and one open issue read.
- **Category:** KV substrate/tiering (non-prefix reuse)
- **Code/artifacts:** LMCache (Apache-2.0 [inferred]); integrated with vLLM (and listed for SGLang for general caching; blending itself is documented for vLLM only). Paper implementation: ~3K lines Python on vLLM, PyTorch 2.0. Datasets 2WikiMQA, Musique, SAMSum, MultiNews are public.

## 1. Summary
- Prefix caching reuses KV only for the leading chunk; in RAG the other chunks sit after different predecessors, so their KV is invalid (cross-attention with previous chunks missing).
- CacheBlend loads the precomputed per-chunk KV (positions corrected) and **recomputes only the High-KV-Deviation (HKVD) tokens** per layer, gradually filtered, to restore cross-attention. Loading of layer i+1 is pipelined with selective recompute of layer i.
- Reported: TTFT 2.2-3.3x lower and throughput 2.8-5x higher than full KV recompute with quality loss within 0.02 F1/Rouge-L (Fig 12, §7.2). Versus full KV reuse (no recompute): about the same TTFT, +0.15 to +0.35 quality (§7.1/7.2). [paper]

## 2. Problem and key insight
- Full KV reuse (PromptCache-like) = wrong answers because cross-attention between chunks is ignored (Fig 1c, Fig 2 example).
- Insight: attention is sparse; the tokens whose KV deviates most from a full prefill ("HKVD") are a small set (10-20%), and their identity is **correlated across layers**, so pick them after layer 1 and refine. Recomputing ~15% recovers near-full-prefill quality (Fig 16; r* = 15%). [paper §4.3, §5.1]

## 3. Workloads
- RAG/QA and summarization: 2WikiMQA (200 cases), Musique (150), SAMSum (200; few-shot), MultiNews (60). Chunks 512 tokens (SAMSum 200-400) via LangChain; 6 top chunks per request in the main comparison (Fig 12). Also a synthetic chunk-reuse dataset, and Poisson request rate 0.25-0.75/s for the throughput plot (Fig 14).
- Not a multi-turn or agentic evaluation: single-shot inputs made of retrieved chunks; no tool waits, no decode-heavy outputs (short answers).
- Models: Mistral-7B, Yi-34B, Llama-70B (quantised for 34B/70B). Hardware: Runpod, 2xA40, 128 GB RAM, 1 TB NVMe at 4.8 GB/s (also RAM and slower "4Gbps" disk in Fig 17).

## 4. Assumptions
- **Chunks are reusable text units** with known boundaries (the docs use a separator string, `LMCACHE_BLEND_SPECIAL_STR`, e.g. " # # "; chunks are tokenized separately then concatenated).
- RoPE models (positional recovery relies on RoPE's relative-position invariance, Appendix A).
- Layerwise KV loading must be enabled; prefill is the metric (TTFT), and the *answer is short*: generation time is not part of the claims.
- Storage: KV cache for chunks resident in RAM/SSD (KV of every chunk kept, storage cost grows with corpus).
- Quality measured by F1/Rouge-L on QA/summarization; **no code-generation or reasoning-chain tasks**, nothing about thinking-mode models.

## 5. Controller / mechanism
- **Selective recompute** (§4.2-4.3): at layer 1, compute the KV of all tokens and per-token deviation vs stored KV; pick the top r1% as HKVD; on each later layer recompute those tokens' KV (queries only for them, attention over the whole context including reused KV), then filter to r2% < r1%, ... "gradual filtering". Extra memory: reused KV of layer i is discarded once updated.
- **Pipelining** (§5): recompute of layer i overlaps loading layer i+1's KV; loading controller picks r = max(r_match, r*), where r_match makes recompute time equal load time for the device, and r* = 15% (min quality-safe). It also chooses the cheapest storage device that adds no delay (Fig 10b).
- **Interfaces** (§6): `fetch_kv(text, layer_id)`, `prefill_layer(input, KVCache)`, `synchronize`; ~3K LoC on vLLM.
- **Positional handling:** reused chunk KV is stored at fixed positions; RoPE is re-applied so its relative distance is right; only cross-chunk attention is missing and repaired by selective recompute.
- Overheads: HKVD selection on layer 1 needs a full first layer pass; memory holds both old and new KV for one layer.

## 6. Evaluation and reported results
- Fig 12: TTFT reduction 2.2-3.3x vs full recompute, quality within 0.02. Fig 14: 2.8-5x throughput vs full recompute at similar quality. Fig 13: better quality than MapReduce/MapRerank RAG at similar latency.
- Baselines: full KV recompute; prefix caching (SGLang-style; given **idealised zero load delay**); full KV reuse (PromptCache-style).
- Sensitivity (Fig 15-16): compute-time reduction stays similar across 3-12 chunks and 300-900 token chunks; quality vs recompute ratio flattens above ~10-15%.
- Storage (Fig 17): with RAM or slow disk, CacheBlend still improves TTFT because recompute is at most 15%; the delay lower bound is the recompute itself.

## 7. What JouleServe-WS can take
- **Code:** LMCache blending (`LMCACHE_ENABLE_BLENDING`, layerwise on). Caveats found: docs mark in-process mode **deprecated** (use MP mode); open issue #3238 (May 2026, vLLM 0.17-0.18) says non-prefix reuse does not work with the vLLM V1 connector because scheduler-side lookup is prefix-hash only. So in practice a research-grade re-implementation is needed; **no SGLang 0.5.20 support for blending** was found. [docs, issue]
- Baseline for JouleServe: "CacheBlend-style partial recompute" as an *analytical* baseline first (no engine change): estimate recovered prefill time = f_nonprefix * (1 - r) * T_prefill, r = 0.15, then decide if an engine implementation is worth it.
- Sketch on SGLang: a per-layer prefill hook computing deviation on layer 1 and running attention for selected query rows only; SGLang radix cache would need a "chunk store keyed by content hash, not path hash". Substantial engineering (attention backend + cache manager).
- Methodology: quality-vs-recompute-ratio curves (F1/Rouge); loading vs recompute delay estimators.

## 8. What JouleServe must add beyond it
- Evidence on **agent** prompts: code outputs and observations embedded in other roles' prompts; quality metric = task success, not F1.
- Energy accounting: extra layer-1 full pass + gradual selection vs saved prefill; storage/IO energy.
- Interaction with generated-token KV (KV of decode-produced tokens re-tokenized in a later prompt is not bitwise the same as chunk KV; see §10).
- Hybrid models: Gated DeltaNet / sliding-window layers have **no per-token KV to splice**; a recurrent state cannot be blended per token. CacheBlend is defined for full-attention KV only. [inferred]

## 9. Workstation -> edge
- Pipeline works because loading is slower than recompute for SSD and the two overlap. On unified-memory Jetson, "loading" from a DRAM-resident store is memory traffic on the same bus as compute; with a RAM-resident store the recompute (15%) becomes the floor and load overlap gives little. [inferred]
- NVMe on Orin gives capacity but with lower bandwidth than the 4.8 GB/s tested; recompute ratio would have to be tuned by the paper's own controller.
- Prefill is relatively costlier on Orin (compute-poorer than Thor/A5000 relative to bandwidth): e.g. 8K prefill of a 7B dense model is ~115 TFLOP of work vs ~14 GB of weights read per decoded token [inferred arithmetic: 2*7e9 FLOP/token]. So prefill share can be well above the 1-8% measured on Thor; cost of blending errors is also higher.
- Porting effort: high (custom attention path); LMCache/vLLM only on Jetson/aarch64 with a working build.

## 10. Relevance to our current findings
- **Where P1's reusable content sits:** agent prompts embed earlier outputs (generated code, observations) after role-specific headers, i.e. at non-prefix positions. Prefix caching gets only the shared head (10-31% repeat; 66% AeroEval).
- **Qualitative estimate of recovery** [inferred, not measured]. Recoverable time <= f * (1 - r) * P, with P = prefill share of LLM time (1-8%), f = fraction of prompt tokens that repeat *at non-prefix positions* and whose KV was cached, r ~ 0.15. Even at the optimistic f = 1 with P = 8%, ceiling ~6.8% of LLM time; with the measured repeat rates (10-31%, 66% in total, part of it already prefix) and P = 1-8%, plausible gains are **well under ~2-3% of LLM time** on Thor. That is the same order as perfect prefix retention (0.3-1.7%). It adds engine complexity, storage, and quality risk in long-chain reasoning. Not a first-order win for our current workload.
- Caveat 1: the chunks are **model output**. Thinking traces are usually not fed back (or are stripped), and the retained observations are re-tokenized/reformatted, so byte-identical chunk match may be low.
- Caveat 2: CacheBlend improves TTFT; our SLO is task-level and decode-dominated, so TTFT is a minor part of task latency.
- **When it matters more:** (a) Orin-class compute (prefill share rises), (b) long accumulating tool-calling agents with large repeated observations (tens of thousands of tokens of tool results re-sent each turn: prefill share climbs and repeated content grows), (c) prompts with big static documents/tool schemas placed after variable text, (d) RAG-style agents with many retrieved chunks.
- On the WS (A5000, 25K-token pool, 144 KiB/token): a 1K-token chunk = ~144 MB; PCIe Gen4 x16 at ~26 GB/s reloads it in ~6 ms, so the reload is not the problem; the pool size is.

## 11. Open questions / uncertainty
- No published quality numbers for code generation or multi-step agent success under blending.
- Compatibility with SGLang 0.5.20 and with hybrid attention is unknown; V1 connector issue suggests the open-source path is fragile.
- Whether P1 traces actually contain repeated chunks at non-prefix positions can be measured offline by a token-chunk hash pass over the existing traces. This costs no GPU time and would settle the estimate above.

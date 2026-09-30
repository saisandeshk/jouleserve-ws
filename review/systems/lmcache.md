# LMCache — an engine-agnostic KV cache layer (GPU/CPU/disk/remote tiers) with batched, pipelined data movement and a cluster controller

- **Source:** "LMCache: An Efficient KV Cache Layer for Enterprise-Scale LLM Inference"; Yuhan Liu et al. (Junchen Jiang group, UChicago/TensorMesh); arXiv preprint, submitted 2025-10-08, revised 2025-12-05 (arXiv 2510.09665, id verified; cs.LG); code: github.com/LMCache/LMCache; docs: docs.lmcache.ai
- **Review depth:** full text (arXiv HTML via fetch: §4-§9 incl. Tables 2-3, Figs 8-16) + docs index/`mp/kv_cache_management` page + the SGLang-side connector source (`sglang/srt/mem_cache/storage/lmcache/lmc_radix_cache.py`, installed 0.5.20). Not read: LMCache repo source, the legacy Controller docs page, CacheBlend/CacheGen papers.
- **Category:** KV substrate/tiering
- **Code/artifacts:** open source (Apache-2.0 per repo; [inferred] license not re-checked here); engines vLLM (mature) and SGLang (connector in-tree); no public enterprise traces.

## 1. Summary
- LMCache is a library that sits between an inference engine and heterogeneous storage (GPU, CPU DRAM, local disk, remote disk, Redis; §4 [paper]). It offloads/reuses KV across queries and engines. Headline: "up to 15x" throughput with vLLM on multi-round QA and document analysis [paper, abstract].
- Contributions are systems-engineering ones: chunked (default 256-token) batched transfers, layer-wise compute/IO pipelining, zero-copy ref-counted writes, a thin connector API, and a controller with `lookup/move/pin/unpin/compress`.
- It does not decide *what a session is worth retaining*; it provides the mechanism (tiers + pin) and leaves policy to routers/operators. That gap is where JouleServe sits.

## 2. Problem and key insight
- Problem: prefix reuse is bounded by GPU HBM; production traffic (multi-round chat, RAG, document analysis) has large reusable context that does not fit. [paper §1-2]
- Insight: paged 16-64 KB blocks are too small for PCIe/network; regroup into large chunks via a staging buffer, and overlap I/O with compute per layer. Table 5 (§8.6): 400 Gbps CPU-to-GPU load vs 88 Gbps for vLLM's native offload [paper].
- Enterprise lessons (§9): context truncation cut prefix hit rate from about 85% to 45% at Company F; Company G saw about 50% hit rate; remote storage mainly helps hit rate, with 22-32% lower TTFT vs full prefill at Company C [paper].

## 3. Workloads
- Multi-round QA (40 users, arrivals at a set rate), LongBench long-context, and two real company traces (F, G) [paper §8.1]. Traces are not public [inferred; no release mentioned].
- Models: Llama-3.1-8B/70B, L3-8B, Qwen2.5-Coder-32B, Qwen3-Coder-480B-A35B-FP8, Qwen2.5-72B. All dense/GQA or MoE with full attention; **no hybrid/SSM/SWA models** [paper §8.1].
- Hardware: 8xH100 servers. Baselines: vLLM 0.10.2, vLLM 0.11.0 CPU offload, two commercial offerings.
- No tool-calling or agent workload: no pauses, no tool-wait model. Reuse is conversation/document based.

## 4. Assumptions
- Datacenter: high PCIe/NIC bandwidth, large host DRAM (a separate, cheap tier), many concurrent queries, throughput and TTFT as the objective. Energy is not considered.
- Reuse is content-addressed (token-prefix hash of 256-token chunks); no knowledge of session pause duration.
- Remote loading only wins when bandwidth justifies it: Fig 15 (§8.7) says loading beats prefill for contexts over 256K tokens at 32 Gbps and at all lengths at 64+ Gbps [paper].

## 5. Controller / mechanism
- **Components** (§4): KV Connector, Token Processor, Storage Manager, Event Manager, Cache Controller [paper].
- **Data movement (§5):** chunk = 256 tokens default; parallel multi-tier store/retrieve; layer-wise pipelining on separate CUDA streams with only a one-layer GPU buffer; prefetch for queued queries; zero-copy ref-counting; "dynamic offloading" with a three-pointer (start/current/end) state machine to trade duplication against allocation stalls.
- **Connector API (Table 2, §6):** `get_num_new_matched_tokens`, `update_state_after_alloc`, `build_connector_meta`, `start/wait_load_kv`, `start/wait_store_kv`. Modeled on vLLM's scheduler/worker split.
- **Controller API (Table 3, §7):** external `lookup(tokens)`, `move(src,dst,tokens)`, `pin/unpin(tokens, instance, device)`, `compress/decompress`; internal `batched_admit/batched_evict`, `batched_p2p_lookup`. Pin is used for operator-driven retention (a financial firm pinning frequently used documents, §3.1.3) [paper].
- No default eviction algorithm is specified in the paper; docs point to L1/L2 eviction pages (`mp/l2_storage`). Current MP-mode docs say the management surface (`move`, `pin`, `compress`) is "coming soon"; the older in-process controller is documented under Legacy [docs, fetched summary].
- **SGLang connector (installed 0.5.20)** [code]: `--enable-lmcache [--lmcache-config-file]` makes `default_radix_cache_factory` (`mem_cache/registry.py`) return `LMCRadixCache` (subclass of the plain `RadixCache`) unless the model is pure-SWA or the external-linker is on. Two modes, `LMCacheMode.MP` (`LMCacheMPConnector`, separate daemon) and `IP` (`LMCacheLayerwiseConnector`, in-process). Flow: `match_prefix` does a lookup only; `init_load_back` retrieves into freshly allocated slots and inserts into the radix tree; `cache_finished_req` inserts on GPU and `store_kv` to LMCache on request finish; `evict()` first syncs the store stream. The connector takes `k_pool`/`v_pool` from the KV pool, so it is a **dense MHA/GQA path only**; no Mamba state, no SWA pool [inferred from the code path; not run].
- Paper §8.8/Fig 16: on SGLang LMCache gives "comparable performance" to SGLang's native CPU offload (one model) [paper].

## 6. Evaluation and reported results
- Fig 8 (§8.2): CPU offload, 1.9-8.1x lower TTFT at low QPS, 2.3-14x higher throughput, 7-92% lower ITL.
- Figs 9-10 (§8.3): real traces, at least 3.7-6.8x lower TTFT; 19-58% lower ITL at high QPS.
- Fig 11 (§8.4): centralized storage, 1.3-3x throughput. Fig 12 (§8.5): PD-disagg, 1.5-1.8x lower mean TTFT, 1.1-1.7x lower ITL. Fig 13: compute/IO overlap gives 1.46x lower end-to-end delay.
- All numbers are on H100 clusters vs vLLM; they say nothing about energy or edge memory.

## 7. What JouleServe-WS can take
- **Baseline "LMCache CPU offload" (should):** on SGLang 0.5.20 launch with `--enable-lmcache` plus a YAML (`chunk_size`, `local_cpu: true`, `max_local_cpu_size`). Works only for the dense K2-Horizon-7B WS model, not for Gemma-4/Qwen3.8. Useful for a "retain-in-host-tier" arm and for its store/retrieve latency measurements.
- **Mechanisms to copy:** chunked host transfers (256-token chunks) and `pin/unpin` semantics as the vocabulary for JouleServe's retention actions; `lookup()` as the cheap "is this session's prefix still cached anywhere" query.
- **Methodology:** report TTFT/ITL and hit-rate (`sglang:cached_tokens_total`) alongside energy per task.
- Not reusable: no traces; no agent workload.

## 8. What JouleServe must add beyond it
- A policy: when to pin, offload, or drop a session's state given expected tool-wait time, prompt-rebuild reuse fraction, and energy of recompute vs holding/copying.
- Hybrid-state support (SWA windows, recurrent checkpoints): the SGLang connector has none.
- Energy/thermal accounting; task-level SLO; active-decode preemption awareness. LMCache's pin API also has no TTL or session semantics.

## 9. Workstation to edge
- Its whole win rests on a fast, separate, large CPU tier. On Jetson the "CPU tier" is the same LPDDR; see `sglang-kv.md` section on unified memory. Offload to local_cpu buys no capacity there, only moves bytes within one DRAM and costs bandwidth and energy. Disk (NVMe/SD) and remote tiers are the only genuine capacity extension, and their bandwidth is far below the 400 Gbps of Table 5.
- Python chunk-management overhead on an Orin CPU: unmeasured [open].

## 10. Relevance to our current findings
- Our drone traces show only 10-31% (66% AeroEval) of a prompt repeating and prefill at 1-8% of LLM time; LMCache's multi-round-QA benefit (large reuse, prefill-bound) is the opposite regime. Expect a near-zero gain from LMCache on the single-session case (bound of 0.3-1.7% LLM time), and possible loss from store overhead. The paper's own truncation finding (§9) is a warning that rebuilt/truncated prompts kill prefix reuse, which matches our per-role rebuilt prompts.
- Hybrid target models are not supported by the connector.

## 11. Open questions / uncertainty
- Whether `LMCRadixCache` stores on every request finish (write cost per agent turn) or has a threshold; not verified beyond `cache_finished_req` reading.
- Legacy controller pin/unpin exact endpoints not read; whether SGLang integration can call them is unknown.
- Fetched full text was summarized by a helper model; specific numbers above should be re-checked against the PDF before publication.

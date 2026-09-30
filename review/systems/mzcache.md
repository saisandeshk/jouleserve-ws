# mzCache — restoration-oriented eviction of weights and KV cache under unified memory on phones

- **Source:** mzCache: On-Device LLM Memory Management under Multitasking; arXiv 2609.01338 (Sep 2026); https://arxiv.org/abs/2609.01338 (authors not captured in my extraction; check page).
- **Review depth:** full text via arXiv HTML through a fetch-and-summarize tool; partial fidelity.
- **Category:** edge/on-device; KV substrate/tiering
- **Code/artifacts:** none found. Built on llama.cpp (~6K LoC C/C++, 0.6K OpenCL), no kernel changes.

## 1. Summary
Under memory pressure from other apps, OS paging kills or stalls LLM processes. mzCache elastically evicts weights and KV in fine-grained units and restores them quickly.

## 2. Problem and key insight
OS swap/LMK behave badly for LLM state; generic compressors (lz4) barely compress KV. Restoration-oriented eviction: keep state cheaply restorable **[paper]**.

## 3. Workloads
Qwen3-0.6B (8k-32k ctx, 0.9-3.5 GB KV) and EXAONE-4.0-1.2B on Galaxy S25+ and OnePlus 12 (12 GB LPDDR5X unified, UFS 4.0). TriviaQA 428 QA, 8.8-28k contexts; realistic multitasking with Instagram, YouTube, PUBG. Not agentic.

## 4. Assumptions
Storage tier (UFS) exists; memory pressure comes from co-running apps; single LLM.

## 5. Controller / mechanism
Layer-granular weights, KV in 256-token chunks in OpenCL SVM buffers; hybrid swap over in-memory decompression and storage reads (offline profiled); four eviction stages (KVonly, KVandW, Wonly, CompKV); backward-out/forward-in ordering to overlap restore with prefill; 8-bit quant or CacheGen compression **[paper]**.

## 6. Evaluation and reported results
TTFT 2.1-5.5x vs storage-backed partial offload; 2.5-3.0x (S25+) and 9.2-25.9x (OnePlus 12) vs OS paging on full eviction. OS paging triggers low-memory killer every round; mzCache survives 10 rounds. Higher peak power (19.2 W vs 14.6 W) but lower total energy **[paper]**.

## 7. What JouleServe-WS can take
Idea: eviction stages + restore-vs-recompute choice per chunk; on WS emulate with SGLang HiCache host tier as an upper bound on a "host tier" (but discrete-memory PCIe, not the same).

## 8. What JouleServe must add beyond it
Multi-session agents, tool-wait-aware retention, task-level energy, GPU-serving engine (SGLang) rather than llama.cpp.

## 9. Workstation → edge
Closest in memory model to Jetson: unified DRAM, co-tenant pressure, OS reclaim/OOM as failure mode. On Jetson no UFS but NVMe; "offload to host" gains no capacity, only compression/SSD adds capacity.

## 10. Relevance to our current findings
Paused sessions' KV matters only if memory pressure exists; on Thor 128 GB with a 26B MoE, capacity pressure is mild, consistent with P1 finding that active decode, not paused state, dominates.

## 11. Open questions / uncertainty
Phone-class (0.6-1.2B) scale; authors and code unverified.

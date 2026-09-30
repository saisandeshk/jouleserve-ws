# CachedAttention / AttentionStore — session KV kept in DRAM+SSD, prefetched layer-wise, evicted using scheduler queue hints

- **Source:** Cost-Efficient Large Language Model Serving for Multi-turn Conversations with CachedAttention; Bin Gao, Zhuomin He et al. (NUS, SJTU, Huawei Cloud); USENIX ATC 2024 (arXiv v3, 30 Jun 2024); arXiv 2403.19708 (ID verified; v1/v2 were titled "AttentionStore: Cost-effective Attention Reuse across Multi-turn Conversations")
- **Review depth:** full text — full PDF text (arXiv v3) read: intro, §2 motivation, §3 design, §4 evaluation. No appendix or code (none exists).
- **Category:** KV substrate/tiering (multi-turn session KV retention)
- **Code/artifacts:** No public repo found (web search, and the paper gives none). Implemented in PyTorch/Python on a Transformers-based engine (LLaMA, Falcon, Mistral). Workload = ShareGPT (public), but arrival times are synthetic Poisson.

## 1. Summary
- Keeps the KV cache of *every* conversation session after a turn ends, in a three-level store: HBM, host DRAM, SSD ("AttentionStore"). The next turn loads it instead of re-prefilling history. [paper §1, §3]
- Four mechanisms: layer-wise KV pre-loading; asynchronous saving; scheduler-aware fetch/evict; decoupled positional encoding so truncated contexts stay valid. [paper abstract]
- Reported: TTFT down up to 87%, prefill throughput up to 7.8x, end-to-end cost down up to 70% vs recompute (RE). [paper abstract, §4.2]

## 2. Problem and key insight
- Engines discard KV on session end, so every turn re-prefills all history; repeated work grows linearly with turns. ShareGPT analysis: up to 99% of prefill cost is repeated computation. [paper §1, §2.3]
- 73% of ShareGPT conversations are multi-turn; 30% exceed 4K tokens (Fig 2). [paper §2.3]
- HBM cannot hold it: LLaMA-65B on 4xA100 generates KV at ~13.9 GB/s of prefill and fills 190 GB free HBM in 14 s; a 512 GB host tier fills in <1 min (§2.3). So a disk tier is needed.
- Key insight: the **job queue is a look-ahead oracle** for which session is needed next, so placement between DRAM and SSD can be decided by the scheduler, not by LRU.

## 3. Workloads
- ShareGPT, ~9K conversations, mean 5.75 turns, ~52K turns total; first 10K turns warm up the store, next 42K are measured. [paper §4.2]
- Arrivals: no timestamps exist in ShareGPT, so **session** arrivals are Poisson (lambda=1.0/s). Turn inter-arrival ("think time") is **not** modelled or reported explicitly [paper §4.1]. This is the main workload gap vs. agent tool waits.
- Context growth: history grows each turn; truncation at the context window (4K for LLaMA-2; Mistral-7B with 32K also run) with truncation ratio 0.5 in the baseline (§4.1).
- Models: LLaMA-13B/65B/70B, Falcon-40B, Mistral-7B; FP16; MHA and GQA mix (per-token KV: 2.5 MB for 65B, 0.78 MB for 13B). Hardware: 4xA100-80GB, 128 GB DRAM, 10 TB SSD, PCIe Gen4 (~26 GB/s effective). [paper §2.3, §4.1]

## 4. Assumptions
- Large DRAM (128 GB) and huge SSD (10 TB) **separate** from HBM; PCIe is the transfer path; SSD <5 GB/s. [paper §2.3]
- Session is either fully used or not (eviction granularity = whole session's KV). No partial-session eviction. [paper §3.3]
- KV of a session is a *prefix* of the next prompt: history + new question. Exact-prefix reuse only.
- Objective: GPU cost (GPU-hours + DRAM/SSD storage cost); prices used: $5/h per A100, $0.0088/h/GB DRAM, $0.000082/h/GB SSD [§4.2]. Not energy.
- Relative positional encoding (RoPE-like) models only for the truncation trick [paper §3.4].
- Throughput-oriented datacenter serving; no SLO on task level.

## 5. Controller / mechanism
- **Layer-wise pre-loading** (§3.2.1): start loading layer l+1's KV while layer l computes on new tokens. Imperfect overlap when T_load*L_hist > T_pref*L_new; a read buffer sized S_buf = B*(T_load*L_hist - T_pref*L_new) lets loads start earlier. Example numbers: prefill of 2K tokens = 360 ms vs 192 ms to load 5 GB over PCIe (LLaMA-65B, 4xA100). Ablation: 35% prefill reduction without buffer, 61% with a 15-layer buffer (LLaMA-13B, hist 1K, new 100; Fig 19).
- **Async saving** (§3.2.2): KV written out on a separate stream during decode; 13-15% execution time reduction vs sync saving (Fig 20).
- **Scheduler-aware fetching** (§3.3): scan the waiting-job queue, pre-fetch SSD->DRAM for jobs about to run, bounded by the DRAM buffer.
- **Scheduler-aware eviction** (§3.3): a look-ahead window of length (C_mem + C_disk)/S_kv over the job queue; anything inside the window is exempt from eviction; evict from the window tail first. Beats LRU and FIFO: with 128 GB/10 TB hit rate 86% vs LRU 58% vs FIFO 48%; with 128 GB/2 TB it beats them by 27 and 31 points (§4.4).
- **Decoupled positional encoding** (§3.4): store K *without* RoPE, re-embed positions at load; then truncating the oldest half of tokens is a slice of the saved KV. PPL within 0.02 of recompute-after-truncation (Table 1). Without it, hit rate drops 17.6-41.5% under overflow (Fig 22).
- Overheads: not reported separately apart from the ablations above.

## 6. Evaluation and reported results
- Baseline: RE (recompute all history, no cache). Only one baseline; no vLLM prefix cache, no CPU-offload comparisons. [paper §4.1]
- Hit rate 86% / 71% / 89% / 90% for LLaMA-13B/65B/70B/Falcon-40B (Fig 13); 65B is lower because 2.5 MB/token exhausts space.
- TTFT reduction 85/61/87/86% (Fig 14); prefill throughput 6.8x/2.6x/7.8x/7.2x (Fig 15); end-to-end GPU time speedup 4.0x/1.9x/3.3x/3.4x (Fig 16); cost saving 70/43/66/68% (Fig 17).
- Storage cost is small: about 9% of total cost at most (§4.2).
- Capacity sensitivity: hit rate 51% at RCC/CCpUT = 0.1, 98% at 0.25 (§4.5).

## 7. What JouleServe-WS can take
- No code to reuse. Reimplementable **baselines**:
  - "Keep in HBM, radix cache" = SGLang default (exact prefix, LRU). Already there.
  - "Offload to DRAM, reload" = SGLang HiCache (host tier) enabled on 0.5.x; approximates AttentionStore's DRAM tier without SSD. [inferred; verify flag names in 0.5.20]
  - Scheduler-aware eviction: in an agent runner the analogue of the job queue is known exactly: the runner knows the tool-call return time. Sketch: pass a `retain_until` hint per session to the radix-tree eviction priority.
- Methodology: cost model with DRAM/SSD $/GB-h and GPU $/h; hit-rate vs capacity ratio sweep; the T_load*L_hist vs T_pref*L_new overlap criterion is a useful analytic check for our host-tier reload.
- Workload: ShareGPT is a sanity check only; it has no tool waits.

## 8. What JouleServe must add beyond it
- Objective: energy per successful task; CachedAttention is cost/TTFT-only.
- Tool-wait-aware retention where wait time is *known or predicted* (13-115 s), not a random queue position.
- Partial retention and hybrid-state (sliding-window, recurrent) handling; CachedAttention assumes uniform full-attention KV.
- Load-aware admission under active-decode pressure; CachedAttention never studies long decodes.
- Because P1 prompts are rebuilt per role, exact-prefix session reuse rarely applies (see §10).

## 9. Workstation -> edge
- Unified memory: no separate DRAM tier. "Offload to host" is a copy inside the same DRAM (no capacity gain, consumes the same bandwidth that decode needs). Only the SSD/NVMe tier adds capacity, at a much lower bandwidth (<5 GB/s class).
- Layer-wise prefetch overlap loses its point when both load and compute contend for the same DRAM bandwidth; on Jetson it can slow decode of other requests. [inferred]
- Benefit is the *avoided prefill*; on Jetson with small batches that is a small share of energy if decode dominates. SSD wear and I/O power add energy cost; storage $ model is irrelevant to Jetson.
- Porting effort: mechanism trivial to express (retain vs drop), but the evidence needs new measurements. Tiering code (GDS, pinned memory) differs on Tegra.

## 10. Relevance to our current findings
- Best case for it is human think-time chat with **persistent prefix growth**. Our agents rebuild prompts per role, so only 10-31% (AeroEval 66%) of a prompt repeats, and only ~0.3-1.7% of LLM time is recoverable even with perfect retention. CachedAttention's gains (prefill is repeated history) do not transfer when decode dominates.
- Its useful idea for us: **queue/hint-driven eviction**. With tool waits of 13-115 s the runner has a timer instead of a guess.
- Decoupled RoPE truncation is relevant only for context-window overflow (32K max tokens in P1); not for hybrid sliding-window models, which already discard old tokens.

## 11. Open questions / uncertainty
- Think-time distribution used is unstated; effect of long idle periods on hit rate is not shown.
- Code not public; details (buffer sizing, SSD I/O path) are only what the paper says.
- Whether the 86-90% hit rates survive a 25K-token KV pool (paper uses 128 GB DRAM + 10 TB SSD, i.e. capacity ratios far beyond ours).

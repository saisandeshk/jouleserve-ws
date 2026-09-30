# Pensieve — stateful multi-turn serving with a chunk-level GPU/CPU cache, leading-token eviction and a multi-token paged attention kernel

- **Source:** Stateful Large Language Model Serving with Pensieve; Lingfan Yu, Jinkun Lin, Jinyang Li (NYU); EuroSys '25 (Rotterdam, Mar 30-Apr 3 2025; DOI 10.1145/3689031.3696086); arXiv 2312.05516 (v3, Oct 2024; v1 Dec 2023) — ID and venue verified.
- **Review depth:** full text — full PDF of arXiv v3 read (§1-§7, tables); no appendix beyond that; no code (none found).
- **Category:** KV substrate/tiering (multi-turn session KV retention)
- **Code/artifacts:** No public repo found (searched GitHub / author profile). Own kernel built with CUTLASS on PyTorch 2.0 C++ front-end; compared against vLLM 0.2.0 and TensorRT-LLM 0.12.0. Datasets ShareGPT, UltraChat are public.

## 1. Summary
- Stateless engines re-process a growing conversation log every turn. Pensieve stores the processed context (KV) in a **two-tier GPU + CPU cache**, evicts per **chunk of tokens** (not per conversation), and recomputes only what was dropped.
- Adds a **multi-token attention kernel** for query tokens attending to non-contiguous cached KV; enables unified prefill+decode batches. [paper abstract, §4.4]
- Reported 1.14-3.0x throughput of vLLM and TensorRT-LLM; 1.14-1.70x for single-GPU 13B models, 1.64-3.0x for 4-GPU 66B/70B. [paper §1, §6.2]

## 2. Problem and key insight
- History is recomputed per request; caching in GPU alone is too small, disk is too slow => CPU as second tier. [§1-§2]
- Insight 1: recompute cost of a token chunk grows with its position (attention cost linear in context, Fig 4), so **leading tokens are cheapest to recompute** and should be dropped first. Prior systems (CachedAttention, SGLang) evict whole sessions or trailing tokens (Table 3).
- Insight 2: with layered models, swap-in can be **pipelined layer by layer** with compute.

## 3. Workloads
- ShareGPT: 48,159 conversations, mean 5.56 turns, mean request input 37.77 tokens, output 204.58 tokens. UltraChat (synthetic): 1,468,352 conversations, mean 3.86 turns, input 51.78, output 257.81 (Table 2). Max context capped at 16,384; 0.57% of ShareGPT dropped.
- Closed-loop per conversation: next turn is sent only after previous response returns; **user think time ~ exponential, default mean 60 s**, varied (30/60/120 s and vLLM at 600 s in Fig 15). [paper §6.1, §6.6] This is the closest published analogue to our tool waits.
- Arrival of conversations: varying rate (req/s); systems compared at throughput vs normalized latency (s/token).
- Models: OPT-13B, OPT-66B, Llama 2-13B (GQA variant, KV heads changed 40->10), Llama 2-70B; FP16; 66B/70B on 4 GPUs with tensor parallelism. Hardware: Azure NC A100 v4, up to 4xA100-80GB, 24-core EPYC, 220 GB CPU RAM per GPU; 40 GB of each GPU set to KV cache.

## 4. Assumptions
- Large host memory (220 GB per GPU) vs 40 GB GPU KV: CPU tier is ~5x GPU tier. PCIe swap "never" fails to keep up (they only use a conservative one-way at a time schedule, not duplex).
- Persistent store of raw token text exists (for recompute of dropped tokens).
- Full-attention transformers (MHA/GQA); FP16; throughput objective, not SLO or energy.
- Requests within a conversation are strictly sequential; user pauses are *unknown* to the scheduler but assumed long enough (60 s default) that GPU eviction is needed.
- Short user prompts (~40-50 tokens) and moderate replies (~200-260 tokens): history dominates the prompt. Opposite of long decode-dominated reasoning.

## 5. Controller / mechanism
- Architecture (§4.1): one scheduler + one worker per GPU. Scheduler does iteration-level batching (FCFS) and plans cache moves; workers run kernels and copy data.
- **Eviction policy** (§4.3.1): chunk-level; retention value combines (a) inactivity time (LRU-like) and (b) recomputation cost Cost(s,l) = Cost_attention(s,l) + Cost_other(s) for chunk size s and context l; evict ascending retention value, from leading end of each conversation.
- **Ahead-of-time swap-out** (§4.3.2): when GPU free slots fall below a threshold (e.g. 25%), copy chosen KV to CPU in advance; GPU memory is reclaimed lazily so swap-out latency is hidden. Scheduler also reserves 10% of GPU slots for running generation requests (§4.3.2/4.3).
- **Pipelined KV recovery** (§4.3.3): layer-by-layer swap-in overlapped with model compute, as in CachedAttention's layer-wise pre-loading.
- **Dropped-token handling** (§4.3.4): cached layout = [dropped leading tokens][CPU middle][GPU trailing]; dropped tokens' raw text is prepended to the new prompt and recomputed; the multi-token kernel handles the resulting split query.
- **Kernel** (§4.4): fused multi-token attention using CUTLASS over paged non-contiguous KV (vLLM's kernel is mat-vec, theirs is mat-mat). Batches prefill+decode ("unified") which helps over separate phases (Fig 13).
- **Positional encoding:** not decoupled; they cap context at 16K and drop the few longer conversations rather than truncating (no truncation mechanism as in CachedAttention). [paper §6.1; inferred that truncation is not supported]

## 6. Evaluation and reported results
- Throughput (§6.2, Figs 10-11): 1.14-1.70x on OPT-13B/Llama 2-13B, 1.64-3.0x on OPT-66B/Llama 2-70B vs vLLM/TensorRT-LLM at matched latency; larger models amplify the gain because compute grows faster than KV size.
- Eviction policy (Fig 14, §6.6): vs Pensieve-with-LRU, up to 4.4 points higher CPU cache hit rate and up to 14.6% fewer recomputed KV tokens; hit rate under 80% in both.
- Think time (Fig 15): benefit shrinks as think time grows (state lives longer, more evicted), but still above vLLM at 120 s (text says gap narrows).
- Unified scheduling (Fig 13) and kernel microbenchmarks (Fig 12) show the kernel is competitive with vLLM's for the multi-token case.
- Baselines are stateless (vLLM 0.2.0, TensorRT-LLM 0.12.0). vLLM has no prefix cache in this version, so it is not compared to *modern* prefix caching (RadixAttention).

## 7. What JouleServe-WS can take
- No code. Reimplementable in SGLang 0.5.20 terms:
  - **Chunk-level, leading-first eviction with recompute-cost-weighted retention value** — a policy plug-in for the radix tree eviction: `score = idle_time_weight * f(time_since_last_use) + recompute_cost(len, pos)`. Note SGLang's radix tree already evicts leaves (trailing), the opposite preference; leading-first breaks prefix sharing, so it only makes sense for non-shared session KV. [inferred]
  - **Exponential think-time, closed-loop client** as the replacement for open-loop Poisson benchmarking; here think-time = tool wait, and replacing the exponential by the measured 13/37/115 s distributions is direct.
  - **Ahead-of-time swap with free-slot threshold (25%) and 10% decode reserve**: a simple, cheap policy to copy as a baseline ("Pensieve-style").
- Methodology: normalized latency (s/token) vs throughput curves; hit-rate accounting per tier.

## 8. What JouleServe must add beyond it
- Energy per successful task as objective and task-level SLOs; Pensieve optimizes throughput/latency only.
- Knowledge of pause duration (tool return time) instead of an LRU guess; retention value using expected wait.
- Handling of **long active decodes**: Pensieve's requests have ~200-token outputs; ours are thousands of thinking tokens, so active KV, not paused KV, drives the pool pressure.
- Hybrid-model state (sliding window, recurrent): chunk-level positional recomputation is defined for full attention only.
- Non-prefix reuse: cached layout requires the history to be an exact prefix.

## 9. Workstation -> edge
- Unified memory: "GPU tier" and "CPU tier" are the same physical DRAM. Swapping copies from one DRAM region to another, freeing nothing; the tier only helps if the pool is a carve-out. Real capacity relief requires storage (NVMe), or dropping and recomputing.
- Pipelined swap-in overlaps PCIe copies with compute; on Jetson the same overlap would contend for the shared LPDDR bandwidth with the decoder. [inferred]
- The recompute-cost model (attention linear in context) is portable; the cost constants must be re-measured on Orin/Thor and under DVFS.
- Porting effort moderate: policy is engine-level; the multi-token kernel is already provided by chunked-prefill/prefix-cache paths in SGLang/FlashInfer (no need to rebuild). [inferred]

## 10. Relevance to our current findings
- Think time 60 s (mean) is of the same order as our waits (13-115 s), so Pensieve's retention question is well-posed for us. But its value depends on prompts sharing an exact prefix with history; ours are rebuilt per role (10-31% repeated; 66% AeroEval).
- Its gains came from short outputs and long histories; our agents are inverse. Predicted upper bound remains ~0.3-1.7% LLM time from retention (own measurement).
- Where it can matter: 25K-token pool per GPU. With 144 KiB/token, a session at 8K tokens holds ~1.1 GB; a few concurrent paused sessions would evict active decodes. Pensieve's ahead-of-time swap and reserve policy is directly relevant to that concurrency case, even if single-session savings are tiny.

## 11. Open questions / uncertainty
- No open code; kernel/eviction details only from the paper.
- The full numeric results per figure were not extracted (figures are plots); the ranges above are from text.
- No comparison against RadixAttention/SGLang-style prefix caching.

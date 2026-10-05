# LLMS (LLM as a System Service) — chunk-wise KV compression and swapping for stateful on-device LLM contexts, evaluated on Jetson

- **Source:** LLM as a System Service on Mobile Devices; Wangsong Yin, Mengwei Xu, Yuanchun Li, Xuanzhe Liu; arXiv 2403.11805 (v1, 18 Mar 2024); https://arxiv.org/abs/2403.11805 . A later ACM version, "An Efficient Context Management System for On-Device LLMaaS" (https://dl.acm.org/doi/10.1145/3774906.3800479), looks like the published form; the page returned HTTP 403, so its venue and any changes are **unverified**.
- **Review depth:** partial-to-full text of arXiv v1 (abstract, §1-§3 design, §4-§5 setup and evaluation headlines) via pdftotext. Published version not read.
- **Category:** edge/on-device; KV substrate/tiering
- **Code/artifacts:** none found. The authors say they "will make the traces used in our experiments publicly available" **[paper §4]**; not verified.

## 1. Summary
LLMS treats the LLM as a stateful system service shared by apps. Each app context's KV cache is split into chunks that are independently compressed (tolerance-aware, mixed bit-widths), swapped to disk, recomputed or loaded in a pipeline, and evicted by an LCTRU queue (Least Compression-Tolerable and Recently-Used) with ahead-of-time swap-out. Goal: minimise context-switching latency under a tight memory budget. **[paper abstract, §3]**

## 2. Problem and key insight
- Unlike stateless DNNs, LLM invocations need persistent KV across calls; a 4K-token Llama2-7B context uses over 2 GB, over 50% of the model's weights **[paper §2]**. The Android low-memory killer (LMK) kills the context and forces recomputation: 22.92 s and 94.57 J on the phone **[paper §2, Fig 2b]**.
- Insight: decouple context memory from app memory and manage at chunk granularity with global optimisation.

## 3. Workloads
- Synthesised 72-hour context-switching traces (no public trace existed), calling rate one request in five (unit per paper §5), from several datasets (Table 3) **[paper §4]**. Not agentic tool-call traces; contexts belong to different apps.
- Llama2-7B and OPT-7B on Jetson Orin NX (8 GB, NVMe), Jetson TX2 (8 GB, SATA HDD), Xiaomi MI14 (8 GB, UFS 4.0) **[paper Table 2]**.

## 4. Assumptions
- A **fixed** memory budget per experiment (1/2/3 GB sweeps); the budget does not change during a run **[paper §5, Fig 10]**. Closest to "memory pressure" is the app-vs-LLM split decided once.
- Disk (NVMe/UFS) is available as the swap tier. On Orin NX the disk is separate storage while RAM is unified.
- Requests come from apps with time locality; no knowledge of future resume time.

## 5. Controller / mechanism
- Chunks (fixed token counts) with per-chunk compression rate chosen by measured accuracy tolerance.
- IO-recompute pipelined loading: swap in some chunks while recomputing others.
- Chunk lifecycle: swap out ahead of time; LCTRU eviction picks heavy-to-restore, least recently used chunks.
- API: LLMS exposes context create/call/delete calls (Table 1) and limits active contexts per app **[paper §3.1]**.

## 6. Evaluation and reported results
- Up to two orders of magnitude lower switching latency than LMK, plain swapping and others; versus vLLM-style chunk management with static 8-bit quantisation: "up to 20x and on average 9.7x" **[paper §1]**.
- Under a 10 ms switching constraint LLMS supports 4.32/10.72/16.32 contexts at 1/2/3 GB budgets, 1.99x/2.48x/2.85x more than baselines; 25 ms: 9.28/19.34/27.38 contexts, 4.16x/3.62x/3.57x **[paper §5, Fig 10]**.
- Energy is discussed as motivation (recompute costs 94.57 J) but not an optimisation target.

## 7. What JouleServe-WS can take
- The **restore-vs-recompute pipelining** and the "recompute is energy, too" accounting, as a baseline policy for what to do with an evicted paused context when a burst has passed.
- The 1/2/3 GB budget sweep methodology: it can be reused as a **step-function budget** (static sweep -> time-varying) for Option D.
- No code. Reimplement on SGLang HiCache with a host tier only as an upper bound (the WS has a discrete-memory host tier).

## 8. What JouleServe must add beyond it
- Budgets that change during the run; agents with tool pauses and known resume times; task-level energy; a GPU-serving engine (not llama.cpp-style) with batching.

## 9. Workstation -> edge
- It is already on Jetson (Orin NX, TX2), so assumptions hold on unified memory; but the swap tier is storage, which is where its capacity gain comes from. Our Orin 32/64 and Thor have NVMe, so porting is feasible.
- Models are 7B, 2-4K contexts; our agents have 12K-106K-token contexts **[P1 numbers from HANDOFF.md]**, which changes swap sizes by an order of magnitude **[inferred]**.

## 10. Relevance to our current findings
- When P1's vision burst evicts the paused context (Orin 64, 62 of 62), the recovery is a recompute (0.6% of LLM time). LLMS's pipeline would shave this, but the headroom is that 0.6%.

## 11. Open questions / uncertainty
- Published version unread; numbers above are from arXiv v1 and may differ.
- Authors' trace not confirmed public.

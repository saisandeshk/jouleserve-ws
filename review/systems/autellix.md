# Autellix — program-level least-attained-service scheduling (PLAS/ATLAS) for LLM agent programs

- **Source:** Autellix: An Efficient Serving Engine for LLM Agents as General Programs; Michael Luo, Xiaoxiang Shi, Colin Cai, Tianjun Zhang, Justin Wong, Yichuan Wang, Chi Wang, Yanping Huang, Zhifeng Chen, Joseph E. Gonzalez, Ion Stoica; arXiv Feb 2025 (2502.13965, verified); a USENIX NSDI'26 listing appears under the name "Agentix" [from search result, not read]
- **Review depth:** full text — arXiv HTML (algorithms, implementation, evaluation, limitations). Appendix not checked.
- **Category:** agent-aware scheduling
- **Code/artifacts:** Paper describes a research prototype; no official URL in the paper. A GitHub repo `Crystalclear9/Autellix` came up in search (supports vLLM and SGLang backends plus a CPU simulator); provenance/official status **unverified**, appears third-party. Original base: vLLM v0.6.1, ~5k lines.

## 1. Summary
- Treats an agent *program* as the scheduling unit. Non-clairvoyant: no prior DAG. Prioritizes each LLM call by the program's attained service so far (PLAS for single-threaded, ATLAS for multi-threaded DAG), with preemptive multi-level queues [paper].
- Headline: 4–15× program throughput at the same latency vs vLLM (abstract; Sec 6).

## 2. Problem and key insight
- Head-of-line blocking at call level and at program level: FCFS and per-call SJF-like policies ignore that later calls of a program inherit its earlier delay.
- Insight: a program's completed service predicts its remaining service (least-attained-service, LAS); give short programs priority without knowing lengths.

## 3. Workloads
- ShareGPT chatbot: 6.66 mean calls/program, 277 decode vs 256 prefill tokens.
- BFCL (ReAct tool-calling): 10.75 calls, 735 prefill vs 34 decode.
- LATS (MCTS): 159.7 calls, 467 prefill vs 73 decode, high parallelism.
- Mixed: equal sampling of the three.
- Single and multi-thread programs; tool time is simulated/short (not a modeled long pause). Context accumulates across calls (prefill much greater than decode in BFCL).
- Models: Llama-3.1 8B/70B, Falcon-180B; 1–8 A100-80GB, NVLink. Metric: program-level token latency (critical path for multithreaded).

## 4. Assumptions
- Datacenter multi-GPU with CPU swap over PCIe; many concurrent programs; decodes are short (tens to hundreds of tokens) so quanta and swaps are cheap.
- Program identity available via a stateful frontend API (extends OpenAI chat/vLLM API); service time of completed calls observable.
- Objective: program latency/throughput; no tail-in-tokens for 32K decodes; no energy.

## 5. Controller / mechanism
- PLAS: priority p(c_j)=sum of execution times of prior calls of the same program (Eq. 1). ATLAS: p(c_j)=max over parents of p(c_k)+t_k, i.e. longest critical path so far (Eq. 2). Process table per program.
- K discretized priority queues Q1..QK with per-queue quanta; exhausting a quantum demotes the call; lower number = higher priority.
- **Anti-starvation:** programs promoted to Q1 when Wait_total/Service_total >= beta (Alg. 1, line 26).
- **Preemption:** running calls that exhaust their quantum are preempted; KV swapped GPU<->CPU. Optimizations: multi-step scheduling (decide every N decode steps), and consolidated swap through one contiguous buffer rather than per-block async copies.
- Load balancer (Alg. 2): calls under ~2048 tokens go to least-loaded engine (cache hit >=75% anywhere); longer calls pin to the program's engine for locality.
- Hooks: scheduler and swapping kernel only; multi-engine layer via IPC (AsyncMultiLLMEngine).

## 6. Evaluation and reported results
- Baselines: vLLM FCFS, vLLM-opt (chunked prefill + prefix caching + multi-step), MLFQ (program-agnostic preemptive).
- Single engine: ShareGPT/BFCL 8× over vLLM and 1.5× over MLFQ under heavy load; LATS 5× over vLLM, 2.5× over MLFQ (MLFQ breaks parallel threads). Multi-engine (4×8B): 1.4× over round-robin/least-used. Offline: 10–40% makespan reduction; MLFQ OOMs at 4000 programs. P95/99 lower in 7 of 8 scenarios.

## 7. What JouleServe-WS can take
- Reimplement PLAS/ATLAS as a baseline on SGLang 0.5.20: SGLang has priority scheduling (`--enable-priority-scheduling`, per-request `priority`, with preemption threshold options) so a thin gateway can compute program attained service from returned token/time counts and set `priority` per request, with a periodic re-bucket into K levels and a beta promotion rule. Session/program ID from a header. Effort: ~2–4 days for gateway-side PLAS; true quantum-based preemption inside the scheduler (retraction with recompute instead of swap) another ~1 week [inferred].
- Measurement methodology: program-level token latency, and starvation ratio.

## 8. What JouleServe must add beyond it
- Cost model for preempting 32K-token decodes: LAS demotes long calls but each swap/recompute of a 30K-token context is expensive (~144 KiB/token here, so ~4 GB per swap); needs retract-vs-swap-vs-continue decisions, energy per task, task success SLOs, tool-wait retention.

## 9. Workstation → edge
- CPU swap has no separate tier on unified memory (swap is a memcpy within DRAM, pointless for capacity); preemption must be recompute or pause-in-place, so the costs change. Small batches (1–4) make queue prioritization matter less than capacity. Scheduler logic itself ports easily; effort low for gateway-level priority.

## 10. Relevance to our current findings
- Most relevant of the four for the concurrency pain (active decodes). But its design assumes short decodes; program-level attained service under Reflexion (generator/evaluator/reflector, each with long thinking) would demote programs that have simply thought a lot, not ones that are long overall. Starvation and HOL under 32K decodes is the open question we can test.

## 11. Open questions / uncertainty
- Third-party repo status unknown; the NSDI'26 "Agentix" version may differ from the arXiv v1 read here. Swap-vs-recompute details of preemption not fully extracted.

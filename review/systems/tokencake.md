# TokenCake — KV-cache-centric multi-agent serving with spatial partitioning and time-based offload/upload

- **Source:** TokenCake: A KV-Cache-centric Serving Framework for LLM-based Multi-Agent Applications; Zhuohang Bian, Feiyang Wu, Zhuoran Li, Teng Ma, Youwei Zhuo; arXiv 2510.18586 (listed as accepted at EuroSys '27 on the abs page); https://arxiv.org/abs/2510.18586 ; code https://github.com/pku-lemonade/TokenCake
- **Review depth:** full text (arXiv HTML via fetch-and-summarize extraction; formulas/params from that, not re-verified against PDF). Code not read.
- **Category:** agentic KV retention (with agent-aware scheduling)
- **Code/artifacts:** ~9,000 lines Python reusing vLLM components (baseline vLLM v0.8.6); public repo; synthetic workloads (ShareGPT/AgentCode with Poisson arrivals), no real traces.

## 1. Summary
- For multi-agent DAG applications (Code-Writer, Deep-Research), TokenCake (a) reserves part of the GPU KV pool for critical-path agents (space scheduler) and (b) offloads an agent's KV to CPU when it starts a function call and predictively uploads it before the call returns (time scheduler).
- Headline: up to 47.06% lower end-to-end latency vs vLLM under memory pressure (gpu_mem_util 0.5), GPU utilization +16.9 points (85.7-87.0% vs 69.9-74.1%) [paper, Fig. 9-10].

## 2. Problem and key insight
- Multi-agent apps have (1) spatial contention: many agents' caches compete, non-critical ones evict critical ones; (2) temporal stalls: KV of agents waiting on tools sits idle. Since PCIe round-trip is ~28x cheaper than recompute (4,096 tokens: 63.7 ms round-trip vs 1,815 ms recompute, Fig. 17) offload is worth it *if* another request can use the freed blocks.

## 3. Workloads
- Code-Writer: 11 agent types; file I/O, web search, external tests. Deep-Research: fewer agents, deeper chains.
- Function-call duration (Table 1) [paper]: file system 100 ± 50 ms; Git 100 ms ± 100-1000 ms; SQLite 100-1000 ms ± 500 ms; web search 1-5 s ± 1-10 s; AI generation (GPU) 5-30 s ± 10-60 s. Only the last class approaches our regime and is synthetic/simulated.
- Context: 1,024-5,120 tokens (64-320 blocks) — tiny. Whether context accumulates within an agent call chain is unclear; agents are distinct role nodes in a DAG (closer to our per-role structure than the others). Prefix caching baseline used for shared prompts.
- Arrival: Poisson, 0.05-1.0 apps/s. Models Qwen2.5-14B (A100-80GB), 32B (H20-96GB), 72B (2xH20 TP2); 100 GB CPU offload memory.

## 4. Assumptions
- Discrete GPU + CPU DRAM over PCIe; transfer time linear in blocks (Eq. 2). DRAM plentiful.
- The application DAG is declared via a stateful graph-registration API (frontend), so agent roles and structure are known; user hints for call duration (`t_user`).
- Memory pressure exists: offload only if GPU usage >= 0.60 and a waiting request could use the freed blocks.

## 5. Controller / mechanism
- **Prediction (Eq. 1):** `t_est = beta*t_user + (1-beta)*t_history`, history via EWMA (alpha=0.5), beta=0.5. Observed times reported via `call_finish` HTTP endpoint.
- **Offload trigger (Algorithm 1, on `call_start`):** reject if CPU capacity insufficient; predicted stall <= transfer time; no waiting request fits freed blocks; GPU pressure < 0.60. Cost-benefit window `T_window = T_FC - T_transfer` vs threshold 1.0. Selection: first_fit.
- **Upload (Eq. 3-4):** proactive, before predicted return; `B_upload = max(0, B_free - max(0, D_critical - B_shared_free))`, reserve at most half remaining deficit per cycle; rank by importance+urgency.
- **Space scheduler:** shared + reserved pool. Reserved ratio starts 0.05, +0.05 if GPU usage >0.75, -0.05 if <0.40, clamp [0.05, 0.30]; 75% of active agent types are "critical". Request priority (Eq. 5) = structural + sync + aging; agent-type score (Eq. 6) weights 2:1:0.5:1 (static priority, urgency, recompute cost, graph context).
- Lightweight CPU block pool (allocation from ~1 s to sub-ms). MCPManager tracks states running/pending-offload/offloaded/pending-upload/uploaded.

## 6. Evaluation and reported results
- Baselines: vLLM 0.8.6, vLLM-Prefix, Mooncake 0.3.0-beta, Parrot [paper].
- 47.06% latency reduction (Fig. 9, memory-constrained); 20.7% on 72B Code-Writer 1.0 QPS default. Component study (Fig. 11): agent-only 15.4% reduction; offload-only issues 11,339 offloads, 51% more than full TokenCake (naive offloading is wasteful); full 344.6 s vs 502.2 s baseline. vs Mooncake at 0.5 QPS: 384 s vs 533 s, throughput 0.0124 vs 0.0090 req/s. vs Parrot 6.5-9x lower latency (Fig. 13).

## 7. What JouleServe-WS can take
- The **offload gate** (skip offload unless a waiting request can use the space, predicted stall > transfer time, pressure threshold) as a baseline for "offload during pause" on the A5000 pair; SGLang HiCache (`--enable-hierarchical-cache`) provides the host tier, so a controller decides *when to demote* a session's radix path [inferred; verify 0.5.20 explicit-demote API]. Effort: ~1-2 weeks incl. predictive upload (prefetch API needed); gate-only ~3 days.
- The EWMA+hint duration predictor and `call_start/call_finish` event API (cheap to add to our MCP/LangGraph harness).
- Reserved-pool idea for protecting active long decodes (relevant to preemption pressure), independent of offload.

## 8. What JouleServe must add beyond it
- Energy objective; hybrid-state; unified memory; real long waits; decode-dominated per-role calls; task-level SLO. Contexts in TokenCake are 1-5K tokens, so its transfer/recompute trade is off by a factor of ~10 from our contexts.

## 9. Workstation -> edge
- The whole temporal scheduler assumes GPU HBM is scarce and host DRAM separate. On Jetson host==device memory: "offload" frees no blocks, the gate's "no waiting request fits freed blocks" always holds false, so it never fires; only the spatial scheduler and discard survive. On Orin/Thor a "tier" would have to be SSD (NVMe) with different cost. Reserved-pool partitioning is portable.

## 10. Relevance to our current findings
- Temporal scheduler needs *another request to consume freed memory*; our single-session/small-batch regime has none, and the pressure we expect is active decoding (32K-token thinking), not paused state. Offloading a 13-115 s pause would be justified by transfer-vs-stall inequality, but recomputation is only 1-8% of LLM time, so the upside is bounded by the same 0.3-1.7%. The spatial scheduler (protecting critical-path agents' decode) and the per-role DAG view fit us better than the offload half.

## 11. Open questions / uncertainty
- Workloads are synthetic; latency numbers are per-application end-to-end; whether prefix reuse counts across agents unclear.
- EuroSys '27 acceptance comes from the abs page extraction; verify.
- Priority weights (Table 4) are hand-tuned constants.

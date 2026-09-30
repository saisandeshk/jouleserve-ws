# AgentSysBench — characterization + measurement toolkit for agentic workloads in cloud serving

- **Source:** From LLM Inference to Agentic Workloads: Characterization and Implications for Serving Systems; Chaokun Chang, Yukun Zhou et al. (13 authors); arXiv preprint, 2026; https://arxiv.org/abs/2608.15127 (ID resolves and matches).
- **Review depth:** partial — abstract page plus a tool-mediated extraction of the arXiv HTML (tables/sections/figure numbers as surfaced by the fetcher). No appendix or code read. Figure-level numbers should be re-checked in the PDF before citing.
- **Category:** workload/benchmark
- **Code/artifacts:** Paper says AgentSysBench "to be released as open source" (§1) [paper]; no repo URL found. Production trace (178,799 sessions) is from the authors' own deployment; public release not confirmed.

## 1. Summary
Characterizes 10 agentic applications (RAG, HuggingGPT, DeepResearch, Mini-SWE, Codex, WebAgent, GUIAgent, Claude Code, Openclaw, Pi-AutoR) with per-operation traces, 4,641 benchmark requests, 64,924 LLM calls, 118,274 tool calls [paper]. Six findings: non-LLM components dominate latency in 5/10 apps; heterogeneous resources; shifting bottlenecks; long idle-but-live sessions; control-plane overhead; cross-request redundancy. Four design explorations show gains (29-40% latency, 4.5x, 4.6x memory, 35% search savings).

## 2. Problem and key insight
Serving systems optimize for the LLM call; agentic sessions are dominated by heavyweight sandboxes, retrieval, and idle-live state. The insight relevant to us: session state (KV, sandbox memory, vector DBs) persists through idle intervals of seconds to hours, so serving should be session-aware.

## 3. Workloads
- Apps/datasets/models/paradigm [paper, table in §3-4]: RAG (WQA, MS-MARCO; Qwen2.5-7B; pipeline); HuggingGPT (TaskBench; DS-V4-Pro; plan-execute); DeepResearch (YDC, GAIA, HLE; Qwen3.7-Max, DS-V4-Pro/Flash); Mini-SWE (SWE-bench Verified; ReAct); Codex (Terminal-Bench); WebAgent (WebArena Verified; Kimi-K2.6); GUIAgent (OSWorld); Claude Code (MCP-Atlas); Openclaw (WildClawBench); Pi-AutoR (MLE-Bench). Nearly all use frontier/API-scale models (DeepSeek-V4, Kimi-K2.6), except RAG.
- Session duration: seconds to several hours; coding >10 min, research hours (§4.1).
- Context: multi-turn ReAct accumulates context (paper says quadratic growth of processed tokens, §4.2); prefix-cache hit up to 99% for Claude Code, ~1% or lower for DeepResearch.
- KV: one Claude Code session with large model up to 11 GB KV (Fig 6a). Sandbox working set median 0.8 GB, peak 28 GB (Fig 6b).
- Tool-time: sandbox commands vary 171x (pip install vs sed) within Mini-SWE; same LLM task varies up to 30x within one run (Fig 11-12). Claude Code: LLM up to 90% of time for some task types, tool up to 84% for others (Fig 14).
- Production trace: 178,799 sessions/24 h (35,037 coding, 141,376 search QA, 2,386 office automation). Median session executes only 20% of its lifetime; idle intervals mostly 1-10 min (Fig 20, §7.1). Context compaction in 3,170 events, >70% reduction in 99% of cases. Cache eviction hits 59.4% of sessions, 31.5% of aggregate monetary cost.
- Hardware: single-GPU server per workflow (RAG on 8x4090D), Docker, Milvus, Exa search.

## 4. Assumptions
Datacenter GPU, Docker sandboxes, hosted/large models, cloud search. Concurrency modest in controlled experiments (e.g., concurrency=10 for distributed RAG). Objective is latency/cost, no energy.

## 5. Controller / mechanism
Not a controller paper. Design explorations (§8): task-aware/disaggregated serving (§8.1, 29-40% lower latency); communication-aware placement (§8.2, up to 4.5x); state offloading via quiescent-point checkpointing (§8.3, 4.6x less memory); tool-result caching (§8.4, 35.2% fewer redundant searches, 19.3% less search latency). Instrumentation: per-op traces, cAdvisor/DCGM/Prometheus.

## 6. Evaluation and reported results
Headline numbers as above. Interference: embed-query latency 35.7x under heavy doc embedding (Fig 13a); short-context request TPOT +79.7% co-batched with two long-context requests; sandbox 1.22x slower under shared CPU.

## 7. What JouleServe-WS can take
- Motivation and citation: production evidence that sessions are idle-live 80% of lifetime with idle mostly 1-10 min, and that eviction affects 59.4% of sessions. Supports the retained-state premise (though from cloud coding/search).
- Methodology: per-operation traces separating LLM vs tool time; bottleneck-shift analysis; co-batching interference (79.7% TPOT) is relevant to active-decode pressure.
- Workloads: not directly runnable (frontier models, Docker sandboxes, Exa). Mini-SWE/SWE-bench is available elsewhere; see workloads-catalog.md.

## 8. What JouleServe must add beyond it
Energy, thermal, unified-memory, small-model edge setting; a controller. AgentSysBench characterizes only.

## 9. Workstation -> edge
Sandbox working sets (0.8-28 GB) would collide with model memory on 32-128 GB unified memory; this actually strengthens the "co-located tools" story on the edge. Docker/Milvus assumptions do not carry over.

## 10. Relevance to our current findings
- Confirms idle-live is common in cloud coding/search, but our drone tools wait 13-115 s (up to 15 min), i.e. in the same 1-10 min regime.
- Its high-hit-rate case (Claude Code 99%) is prefix-stable ReAct; DeepResearch at ~1% resembles our rebuilt-per-role prompts. Consistent with our 10-31% prompt reuse.
- Non-LLM-dominated latency in 5/10 apps contrasts with our decode-dominated finding.

## 11. Open questions / uncertainty
- Repo/trace release status unknown. Numbers were extracted through an HTML summarizer; verify. Which of the 10 apps used which hardware in each figure is unclear.

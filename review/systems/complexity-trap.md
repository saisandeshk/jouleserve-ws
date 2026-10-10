# The Complexity Trap — observation masking vs LLM summarization for agent context management (SWE-agent)

- **Source:** The Complexity Trap: Simple Observation Masking Is as Efficient as LLM Summarization for Agent Context Management; Tobias Lindenbauer, Igor Slinko, Ludwig Felder, Egor Bogomolov, Yaroslav Zharov (JetBrains Research); DL4Code workshop at NeurIPS 2025; arXiv:2508.21433; code https://github.com/JetBrains-Research/the-complexity-trap
- **Review depth:** partial. arXiv HTML read through the fetch tool's extraction plus the search abstract; tables not read directly. Re-check numbers.
- **Category:** workload-side context management (observation pruning); not a serving system
- **Code/artifacts:** repo and data released (per paper/repo page).

## 1. Summary
- Compares raw agent, observation masking (replace tool outputs older than M=10 turns with a placeholder) and LLM summarization (N=21, M=10) in SWE-agent on SWE-bench Verified (500 instances, 250-turn limit). Masking roughly halves cost versus raw with equal or better solve rate. A hybrid (masking N=43 then summarization) cuts cost another 7% and 11% vs masking or summarization alone. [paper]

## 2. Problem and key insight
- Tool observations dominate the context in coding agents; they are rarely needed after a few turns. Summaries cost extra calls (2.86-7.2% of instance cost) and lengthen trajectories by 4-15% because they hide failure signals. [paper]

## 3. Workloads
- Qwen3-32B, Qwen3-Coder-480B, Gemini 2.5 Flash (with/without reasoning). Local models served with vLLM on 8 H200. Example: Qwen3-Coder-480B masking 54.8% solve vs summary 53.8%, $0.03 per instance cheaper. Cost is API-style token cost, not energy. [paper]

## 4. Assumptions
- Verbose tool outputs (code, logs); cost proportional to tokens and not dominated by caching (relevant: masking invalidates the prefix cache from the changed position on; see the next note). Fixed heuristic triggers.

## 5. Controller / mechanism
- Sliding-window rule, no learning. Fixed M, N. Authors note optimal window differs across scaffolds (OpenHands). [paper]

## 6. Evaluation and reported results
- Masking cost reduction about 51-57%, summary about 41-55% relative to raw; solve rates comparable. [paper, as extracted]

## 7. What JouleServe-WS can take
- Observation masking is a trivial baseline for the P1 agents (placeholder for old tool results) and runs in the agent framework (LangGraph), not the engine. Related caution: "Token Reduction Is Not Cost Reduction" (arXiv:2607.12161, API-based Claude coding agents) reports tool-output compression of -38.4% tokens raised billed cost by +6.8% because trajectories lengthen and cache effects, so measure end-to-end energy per success, not tokens. [paper, per fetched extraction; not read in full]

## 8. What JouleServe must add beyond it
- Edge KV-pool capacity as the target, energy as the metric, small models and thinking-heavy agents, interaction with prefix caching and with overflow events. Link masking threshold to live pool pressure (adaptive M), which this work leaves as future (fixed triggers).

## 9. Workstation -> edge
- Pure software; small models may lose more when observations are masked (unknown). Real-time drone/traffic tool outputs are structured, not code dumps; the masking gain may be smaller.

## 10. Relevance to our current findings
- P1 window overflows (11-21% of Orin runs before P1's re-runs; up to 28% in P1's final data of 10 Oct) are the failure this lever addresses; whether P1's tool outputs are large enough to matter must be measured.

## 11. Open questions / uncertainty
- Coding-agent specific; fixed windows; no energy; no small-model results.

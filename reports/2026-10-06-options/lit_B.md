# Option B literature review (task B-E3): agent design as the energy lever

Depth key: F = full text read; P = partial (fetched HTML/PDF through a summarising tool); A = abstract/search-snippet level only. Numbers are quoted from those sources only. Several 2026 arXiv items could only be checked at P/A depth.

## Works found

| Name | Venue/year | Link | What it compares | Cost/energy? | Edge/embedded? | Closeness to B | Depth |
|---|---|---|---|---|---|---|---|
| ReAct (Yao et al.) | ICLR 2023 | arXiv 2210.03629 | Baseline paradigm, interleaved thought/action | no | no | low (baseline) | not read (known) |
| Reflexion (Shinn et al.) | NeurIPS 2023 | arXiv 2303.11366 | Baseline paradigm, trial+reflection | no | no | low (baseline) | not read (known) |
| ReWOO | arXiv 2023 | 2305.18323 | Plan-without-observation vs interleaved ReAct | tokens: claims 5x token efficiency, +4% acc on HotpotQA | no | medium | A |
| LLMCompiler | ICML 2024 | 2312.04511 | Parallel function-calling DAG vs ReAct | latency up to 3.7x, cost up to 6.7x, accuracy up to ~9% vs ReAct (abstract) | no | medium | A |
| CodeAct | ICML 2024 | 2402.01030 | Code vs JSON vs text actions | success and turns only: M3ToolEval GPT-4-1106 74.4% vs 52.4% JSON, 5.5 vs 7.6 turns (Table 3); no tokens/latency/energy | no | high on the paradigm, none on cost | P |
| AI Agents That Matter | arXiv 2024 | 2407.01502 | Cost-accuracy Pareto; simple baselines beat Reflexion/LDB/LATS on HumanEval at ~50x lower cost (abstract-level) | dollars | no | medium | A |
| Cost of Dynamic Reasoning (KAIST) | arXiv 2025, v2 Jan 2026 | 2506.04301 | CoT, ReAct, Reflexion, LATS, LLMCompiler on vLLM/A100 | yes: GPU Wh per query (Reflexion 8B 41.53 Wh vs ShareGPT 0.32 Wh) | no | high | P (doc written) |
| Beyond Accuracy (Mehta) | arXiv 2025 | 2511.14136 | ReAct, Reflexion, Plan-Execute, etc., enterprise tasks; Reflexion 74.1% at $5.12 vs ReAct-o3 68.7% at $0.31 (Table 1) | dollars, no energy | no | medium; single author, tasks unreleased | P |
| Energy per Successful Goal (A-LEMS) | arXiv May 2026 | 2605.22883 | Agentic vs linear: 4.33x EpG; tool tasks OOI<1 | yes, CPU RAPL, TinyLlama-1B/Groq | laptop CPU only | high (metric), toy scale | F (doc written) |
| Engineering Sustainable Agents | arXiv Oct 2026 | 2610.03010 | NA vs single/dual/multi-agent; 6.36x energy for MA | yes (CodeCarbon) | RTX A2000 workstation | medium-high | P (doc written) |
| Where Does the Energy Go? (HKUST-GZ) | arXiv Sep 2026 | 2609.29707 | Agentic coding vs reasoning vs serving; 2,989 kJ per SWE-bench task, 63x energy per output token vs saturated serving, GPU-only telemetry misses 41-45% | yes, system energy | no (Blackwell server) | medium-high | P |
| Where Should Agents Live? (agentic-eCAL) | arXiv Sep 2026 | 2609.18283 | 8 multi-agent topologies; Qwen3.5-9B single agent 61.7% at 17.4 kJ/solved vs 29-79.2 kJ multi-agent | yes, A100/H100; Jetson modelled, not measured | modelled only | medium | P |
| Promoting Sustainable Web Agents | arXiv 2025 | 2511.04481 | Six web agents' design: 0.33 to 3.31 kWh on Mind2Web | yes (carbontracker) | no | low-medium | P |
| Kairos (agentic power-efficient serving) | arXiv Apr 2026 | 2604.16682 | serving system (already in review/systems/kairos.md) | yes | no | related, not paradigm study | existing doc |
| Tool-Making and Self-Evolving Agents (Amazon) | arXiv Jul 2026 | 2607.08010 | CodeAct-style code loop vs pre-built tool calls: p50 latency -42%, tokens -58% (14,998 to 6,225) | latency, tokens | no (fulfilment-centre ops) | medium (code-vs-tool, different sense) | P |
| The Bitter Lesson of Tool Calling | arXiv Aug 2026 | 2608.06370 | Programmatic vs JSON tool calling, 14 models, BFCL v4 | accuracy | no | low-medium | A |
| Fewer Tokens, Better Action (PyRUA-Lean) | arXiv Oct 2026 | 2610.01939 | Python-cell robot agents vs per-step tool calls: success 63.1 to 71.7%, 65% fewer input tokens (abstract) | tokens | sim only | medium: code vs step in robotics | A |
| TypeFly / ChatFly | arXiv 2023 (v2 2024) | 2312.14950 | Whole-plan generation in MiniSpec vs Python; streaming interpretation; up to 62% faster, ~34% fewer output tokens | latency, tokens | RTX 4090 edge server + GPT-4; no Jetson | medium-high (drone, latency) | P |
| Code as Policies | arXiv 2022 (ICRA 2023) | 2209.07753 | LLM-written policy programs for robots | no | no | low (origin of paradigm) | A |
| ChatGPT for Robotics | arXiv 2023 | 2306.17582 | Prompt+function library incl. aerial navigation | no | no | low | A |
| CLG / CLGSCE (Wang et al.) | arXiv 2025 | 2507.01930 | Closed-loop code generation w/ semantic observation vs GSCE, Self-Refine: advanced SR 85.0% vs 66.7% (Table I) | no | no | medium (P1's Reflexion lineage) | P |
| AeroGen (Astu, Simmhan) | arXiv Mar 2026 | 2603.14236 | Single-shot whole-program vs closed-loop CLG: 118k vs 209k tokens, $0.19 vs $0.59, 877 s vs 6,480 s | tokens/$/time, no energy | Jetson Thor local models, Orin Nano on drone | high (drone, same lab) | F (doc written) |
| DroneServer (MAVLink MCP) | arXiv Jan 2026 | 2601.15486 | Step-wise MCP tool-calling drone agent, 11 models; median tool call 211/377 ms | interface latency only | no energy | medium (step-wise drone agent) | P |
| AeroVerse, UAVBench, alpha3-Bench | arXiv 2024-26 | 2408.15511, 2511.11252, 2601.03281 | UAV/LLM benchmarks (alpha3-Bench lists "efficiency") | not checked | not checked | low | A (search snippets only) |

## What is covered
- Paradigm vs cost, general: ReWOO and LLMCompiler (token/latency vs ReAct), AI Agents That Matter (Pareto), Beyond Accuracy, and above all Cost of Dynamic Reasoning (ReAct/Reflexion/LATS/LLMCompiler with GPU energy). Direction is consistent across all: iterative self-correction (Reflexion/LATS) costs 1-2 orders of magnitude more than lighter loops, for small accuracy gains.
- Energy of agent designs: A-LEMS (EpG, tool tasks cheaper than linear), Sustainable Agents (6.36x for multi-agent), agentic-eCAL, Blackwell profiling (63x per token vs serving), web-agent energy.
- Code vs tool action: CodeAct (fewer turns, higher success), Bitter Lesson, PyRUA-Lean, Amazon tool-making (all report tokens/turns/latency, none energy).
- Drone code-gen: TypeFly (latency of plan generation), CLG/GSCE, AeroGen (whole-program vs closed-loop in tokens/time).

## What is still open for P5 (as far as I could find)
1. No paper compares whole-program code-as-action vs step-wise tool calling vs Reflexion on the same embodied tasks with energy per success on edge hardware. AeroGen compares closed-loop vs single-shot (tokens, no energy); DroneServer is step-wise but reports no cost.
2. No work reports serving-level effects of the paradigm: growing single conversation (prefix reuse, short post-tool outputs) vs rebuilt role prompts, and concurrent agents per device (P5: 4-16 vs 2 per Thor).
3. No Jetson-measured agent energy per task; agentic-eCAL models Jetson only.
4. Thinking-concentrated-in-first-call behaviour is not characterised elsewhere that I found.
Search was limited to web search and fetch; I may have missed workshop papers, and many 2026 items were read via summaries.

## Novelty paragraph (option B)
The direction of the effect is not new: it is already shown, with energy numbers, that iterative or multi-agent designs such as Reflexion, LATS and multi-agent topologies cost far more energy than lighter loops for modest accuracy gain (Cost of Dynamic Reasoning, Sustainable Agents, EpG), that code actions need fewer turns than JSON tool calls (CodeAct), and that single-shot whole-program drone generation uses fewer tokens than closed-loop generation (AeroGen). What I could not find is the specific measurement P5 holds: step-wise vs whole-program vs Reflexion on the same drone missions, energy per successful mission, extrapolated to Jetson, with the number of drones per device. That is a modest, empirical contribution and the result is partly a workstation projection with a strict-success range (0.9-9.6x) that includes parity. As a claim "agent design is the energy lever" it is a benchmark/agent-design finding that fits P1 (EdgeAgentBench) and the AeroGen line better than a serving project. It becomes a serving contribution only if tied to mechanisms: context reuse in a growing conversation, short-decode steps, and admission by drones per device.

## Biggest risk
The advantage may be attributable to agent engineering (a better prompt, fewer retries, a lenient success check) rather than a general paradigm effect; the strict-success range reaching 0.9x shows this.

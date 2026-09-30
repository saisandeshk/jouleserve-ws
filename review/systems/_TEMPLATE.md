# Track B — shared context and per-system template

## Context: what JouleServe is and where we are (read first)

**Research question (P5 "JouleServe", IISc ISP, Prof. Yogesh).** How should an **edge** LLM
serving system manage the **retained state** of agent sessions while those agents wait for
tools? "Retained state" means the KV cache, and for hybrid models the sliding-window or
recurrent state. The options are to keep it, de-prioritize it, offload it, evict it and
recompute later, or change admission. The target objective is **energy per successful task**
under task-level SLOs, on Jetson-class devices:
- Jetson AGX Orin 32/64 GB and AGX Thor 128 GB
- **unified CPU/GPU memory**, so a "host tier" is the same DRAM
- power and thermal limits (nvpmodel, DVFS, throttling)
- small batches
- tools and simulators co-located on the same SoC

**Right now.** The edge devices are with a sister project, P1 "EdgeAgentBench": a closed-loop
agent benchmark with drone and traffic workloads, SGLang + LangGraph + MCP, and the tool-calling,
ReAct and Reflexion paradigms. P5 is building a **workstation version ("JouleServe-WS")** first:
- 2× RTX A5000 24 GB (discrete memory, PCIe host link, no NVLink)
- SGLang 0.5.20
- model: IFM/K2-Horizon-7B, bf16, dense full attention (~144 KiB of KV per token). On one GPU this leaves a KV pool of ~25K tokens.

The WS version should make the later edge port easy.

**What we already measured on P1's drone traces** (Gemma-4-26B-A4B on Thor, Reflexion, thinking on, 32K max tokens, single session):
- Runs are dominated by decode (long "thinking" outputs). Prefill is only 1–8% of LLM time.
- Every LLM call gets a freshly rebuilt, role-specific prompt (generator / evaluator / reflector), so the session's state is mostly never reused. Only 10–31% of a prompt repeats an earlier call in the same CLGSCE session, and 66% for AeroEval.
- Tool waits are real simulator time: median 13 s (basic), 37 s (advanced), 115 s (AeroEval), up to 15 min.
- Best-case saving from perfect KV retention in a single session: **≈0.3–1.7% of LLM time**.
- Under concurrency, the likely pressure is **active** long decodes (preemption, batch capacity), not paused state.
- Both P1 models are hybrid: Gemma 4 uses sliding-window attention + global layers; Qwen3.8-27B uses Gated DeltaNet + full attention.

The **prior assessment** of these papers is in `review/paper_cards.md`,
`review/decision_matrix.csv` and `review/claim_ledger.csv`. You may read these for context,
but **verify against the primary source**. Several earlier cards were abstract-only.

## Rules for every system doc
- Use **primary sources**: the arXiv abstract page + full text (HTML at `arxiv.org/html/<id>` or the PDF), the official code repo, and the docs. If the full text is not accessible, say so and mark the doc `abstract-only`.
- **Never invent numbers.** Quote reported results with where they appear (section, table or figure). Mark each important claim **[paper]**, **[code]** or **[inferred]**.
- If an arXiv ID given to you does not resolve or doesn't match the title, search for the right one and note the correction.
- Be concrete and dense; aim for ~800–1500 words per system. Prefer bullets.
- Write ONE file per system: `/home/saisandeshk/Study/ISP/jouleserve-ws/review/systems/<slug>.md`. Slugs are lowercase-hyphenated, e.g. `continuum.md`. Do not modify any other file in the repo.

## Per-system template (use these exact headings)

```markdown
# <System> — <one-line description>

- **Source:** <title>; <first author> et al.; <venue or "arXiv preprint">, <year>; <links: arXiv/DOI/code>
- **Review depth:** full text | partial | abstract-only — <what was read: sections, appendix, code>
- **Category:** <agentic KV retention | agent-aware scheduling | energy-aware serving | edge/on-device | KV substrate/tiering | hybrid-model caching | workload/benchmark>
- **Code/artifacts:** <repo URL, license, engine + version, traces/datasets public?>

## 1. Summary
## 2. Problem and key insight
## 3. Workloads
<applications/benchmarks; agent type and paradigm; turns per session; tool/pause types and
duration distributions; context length and its growth; prefix sharing; concurrency and arrival
model; trace source (public?); models (size and architecture: full attention / GQA / MoE /
hybrid); hardware>
## 4. Assumptions
<explicit and implicit: memory hierarchy (GPU/CPU/SSD tiers, PCIe bandwidth), knowledge of
pause durations, scale (datacenter concurrency), objective, what is held fixed>
## 5. Controller / mechanism
<state/inputs → decision → actions; prediction models; cadence; overheads; implementation
(engine, version, where it hooks in); anything reusable>
## 6. Evaluation and reported results
<metrics, baselines, headline numbers with locations>
## 7. What JouleServe-WS can take
<code to reuse, mechanisms to reimplement as baselines (with a sketch of how on SGLang 0.5.20),
workloads/traces, measurement methodology>
## 8. What JouleServe must add beyond it
## 9. Workstation → edge
<which assumptions break on Jetson Orin/Thor (unified memory, no separate host tier, thermal/DVFS,
board power rails, co-located tools/sims, small batch, hybrid models), and the porting effort>
## 10. Relevance to our current findings
<how it relates to the P1 drone findings above: decode-dominated reasoning agents, rebuilt
per-role prompts, long real-time tool waits, hybrid models>
## 11. Open questions / uncertainty
```

## What each agent returns (final message, not a file)
1. The list of files written.
2. One **matrix row per system**, in exactly this pipe format:
   `system | category | workload (short) | platform | actions/knobs | objective | agent-aware? | KV tiering? | energy? | thermal? | edge? | code public? | baseline priority for JouleServe (must/should/optional) | one-line takeaway`
3. Up to 5 bullets of cross-cutting insights for the JouleServe-WS design.
4. Candidate **workloads** with public code or traces that could replace or supplement P1's drone workload. For each: name, source, availability, tool-wait characteristics, context growth, and edge plausibility.

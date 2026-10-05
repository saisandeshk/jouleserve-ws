# AeroGen — single-shot, whole-program LLM code generation for drones (the P1 lineage), compared with closed-loop CLG

- **Source:** AeroGen: Agentic Drone Autonomy through Single-Shot Structured Prompting & Drone SDK; Kautuk Astu, Yogesh Simmhan (IISc); arXiv preprint 2603.14236 (cs.RO), 15 Mar 2026; https://arxiv.org/abs/2603.14236
- **Review depth:** full text (PDF converted locally with pdftotext; read Sections 1-3, 5.1-5.5, 6 and grep of the rest; Appendix A skimmed only for prompts/code listings). No code read.
- **Category:** workload/benchmark (agent paradigm: whole-program generation). Not a serving paper.
- **Code/artifacts:** Paper says "The AeroGen code and prompts will be released after the peer review process" (§3.2) **[paper]**. Builds on AeroDaaS SDK (ref [1]) and CLG/CLGSCE (github.com/ai-uavsec/CLGSCE, ref [17], by Wang et al., arXiv 2507.01930). Not confirmed public at time of review.

## 1. Summary
- Treats drone autonomy as constrained code generation P = f(M, A, C) (mission, AeroDaaS API, constraints), §3. A long structured system prompt (static guardrails: guidelines/constraints/APIs/examples; dynamic guardrails: robot, runtime, world info) makes the LLM produce a complete ~40-line Python mission program in one pass **[paper]** (abstract, §3.2).
- Claims 100% first-pass success with GPT o3-mini and Gemini 2.5 Pro on 20 navigation tasks + 5 missions (Gazebo; real DJI Tello with Jetson Orin Nano for real tests), §1, §5.2, §5.5 **[paper]**.
- Directly relevant to P5/P1: it is the whole-program paradigm that P1's generator uses, and it argues the paradigm is cheaper in tokens than closed-loop (CLG) generation. It does not compare against step-wise tool calling and does not measure energy.

## 2. Problem and key insight
- Problem: LLM-generated drone code is unreliable; closed-loop (generate-simulate-evaluate-regenerate) fixes this but costs tokens, time and needs simulation (§1).
- Insight: move correction "from the execution phase to the prompt construction phase" (§3): invest in a larger, constraint-rich prompt so the first attempt is right. The argument is explicitly about cumulative tokens/time over attempts **[paper]**.

## 3. Workloads
- 20 "advanced" navigation tasks inherited from GSCE/CLG; 5 new missions (multi-destination delivery, farm survey, cable inspection, radio-tower inspection, search and track) with imperative and declarative prompts (Table 1, §4) **[paper]**. Delivery in Gazebo: 6 min mission, 600 m, 2 m/s; radio tower: 24 min (Table 1).
- Models: o3-mini (default, cloud), Gemini 2.5 Pro (cloud), DeepSeek-R1-Distill-Llama-70B-Q8 and DeepSeek-Qwen-32B-Q16 local on Jetson Thor (128 GB), §5.1.1, §5.5.
- Real world: DJI Tello + Jetson Orin Nano as the on-board "edge node" for analytics (§5.1.1); the LLM itself ran in cloud or on Thor.
- Paradigm: open-loop single-shot, with one regeneration if trajectory tolerance (0.2 m) is violated, with only a "high-level prompt indicating mission failure" (§3.1).

## 4. Assumptions
- A high-level SDK (AeroDaaS) hides low-level control, so generated programs are short (29-63 LOC, §5.3). Whole-program success depends on this abstraction.
- Large context window (they say 200k and 1M for o3-mini and Gemini; local models have 16k and fail, §5.5).
- Tool/execution time is not part of the LLM cost; cost is tokens and "token generation time".

## 5. Controller / mechanism
- Agent assembles prompt (static + dynamic guardrails), calls LLM once, runs the program in Gazebo, checks the trajectory vs ground truth, optionally regenerates, then deploys to the real drone (§3.1). Nothing relevant for serving: prompts are rebuilt per task; the ~85% input-token share (§5.2) is a large shared static prefix, which is a prefix-caching opportunity the paper does not exploit.

## 6. Evaluation and reported results
- CLG vs AeroGen, navigation (Fig. 5, §5.2): CLG has 0/20 single-shot successes (16 tasks need 2 attempts, 4 need 3, 4 never succeed); AeroGen 100% single-shot. CLG uses about 4,700 tokens per attempt but 209k tokens total and 6,480 s generation time for the 20 tasks; AeroGen 118k tokens (43% lower) and 877 s; cost $0.59 vs $0.19; 85% of AeroGen tokens are input tokens **[paper]**. (Note: CLG here is the o3-mini closed-loop baseline; the 6,480 s vs 877 s ratio is about 7x in generation time.)
- Complex missions (Fig. 7, §5.3): declarative missions need 5,056-5,376 reasoning tokens vs 2,432-4,288 for imperative; LOC 38 (delivery), 42 (search & track), 63 (radio tower) **[paper]**.
- Models (Fig. 9, §5.5): o3-mini and Gemini reach 100% on all missions; local Llama and Qwen on Thor succeed only on cable inspection (16k context limit, invalid APIs) **[paper]**.
- Energy: none reported **[paper]** (grep for energy: no results).

## 7. What JouleServe-WS can take
- Realistic drone prompt corpus and mission taxonomy (basic / imperative / declarative) with different reasoning-token profiles.
- A whole-program baseline with a measured token cost per success; the large static prefix is an ideal test for prefix caching across missions (not studied there).
- The 5 missions give much longer simulated flight times (4-24 min) than P1 basic tasks, i.e. long tool waits if used in a step-wise agent.

## 8. What JouleServe must add beyond it
- Energy and power measurement; concurrency (several drones per Thor); a step-wise comparator on the same missions and the same model; per-success accounting including failures.

## 9. Workstation -> edge
- Already partly edge: local models run on Thor, but 70B/32B at 16k context failed the task, so the "edge" story there is quality-limited rather than energy-limited. P5's use of Gemma-4-26B-A4B (MoE) on Thor is a different regime.

## 10. Relevance to our current findings
- It is the closest published statement of the whole-program paradigm P1 uses, and it argues whole-program is cheaper than closed-loop in tokens (43% fewer, ~7x less generation time vs CLG). P5's finding (step-wise 5-13x less energy per success than P1's Reflexion) is a different axis: AeroGen compares open-loop-with-retry to closed-loop-with-evaluator, not to step-wise tool calling. A Reflexion-style loop with rebuilt role prompts (supervisor/generator/evaluator/reflector) is the CLG-like closed-loop family, so the P5 result is consistent in direction with AeroGen's own message that retries/closed loops dominate cost **[inferred]**. Note, however, that AeroGen reaches that conclusion by making the single call better; P5 does it by making calls shorter and sharing context.
- Same lab as P5's supervisor (Simmhan): the novelty claim in B must be positioned against this group's prior framing, and probably belongs in the same project line.

## 11. Open questions / uncertainty
- Does AeroGen's 100% hold with thinking-on small MoE models? Their local models failed at 16k context.
- Code not released; tokens-only cost model; "cost" uses API pricing, not energy.

# Circular Reasoning (LoopBench + CUSUM loop predictor) — why reasoning models enter self-reinforcing loops, and a hidden-state early-warning detector

- **Source:** Circular Reasoning: Understanding Self-Reinforcing Loops in Large Reasoning Models; Zenghao Duan, Liang Pang, ..., Xueqi Cheng; arXiv preprint 2601.05693v1 (Jan 2026), ICT CAS; https://arxiv.org/abs/2601.05693
- **Review depth:** partial. Abstract, Section 2-4 text and Table 3 read via PDF text extraction; Table 1/6/7 numbers taken from a fetch-and-summarize pass over the HTML and marked as such; appendix not read. No code released as far as the paper states.
- **Category:** workload/benchmark + inference-time detection (not a serving system)
- **Code/artifacts:** none stated. LoopBench (700 samples, 7 sub-tasks) described, release not confirmed.

## 1. Summary
- Characterises two loop types: numerical loops (periodic arithmetic, k x l > 500 tokens) and statement loops (>3 sentence-level repetitions), and shows loops are common in reasoning models. [paper, Sec. 2.2]
- Proposes a hidden-state linear probe plus CUSUM change-point detector that warns of a statement loop before text repeats; average warning ~40 sentences / ~1,500 tokens ahead. [paper, Sec. 4, Table 3]

## 2. Problem and key insight
- Loops waste compute and cause failures. "Semantic circularity precedes statement repetition" (Sec. 3.1, Fig. 5c): repetition is preceded by a surge of reflection sentences (high-entropy tokens such as "But", "Wait") and a distinct hidden-state shift. [paper]

## 3. Workloads
- LoopBench: high-precision arithmetic and recursive reasoning puzzles; compared against AIME2025 and SuperGPQA. Models: DeepSeek-R1-Distill, Qwen3, QwQ-32B, Phi-4-reasoning, base/instruct models, closed APIs. [paper]
- No agents, no tools, no hardware or energy measurement.

## 4. Assumptions
- White-box access to hidden states; a linear classifier trained per model from labelled loops; loops produced by adversarially hard prompts (LoopBench), so loop rates are higher than on AIME (0-13.33% combined on AIME, per summary).

## 5. Controller / mechanism
- Score x_i = w^T h_i + b per chunk; CUSUM statistic S_i; alarm if S_i > h for p consecutive steps (persistence). [paper, Sec. 4]
- Table 3: e.g. DeepSeek-R1-Distill-Qwen-7B EDR 0.74, FPR 0.24, ASLT 44.1 sentences, ATLT 1663.5 tokens; without persistence (p=1) EDR 0.82 but FPR 0.44. Qwen3-8B EDR 0.64, FPR 0.30. [paper, Table 3]
- Intervention is only "early stopping"; no recovery policy evaluated.

## 6. Evaluation and reported results
- Loop rates (summary of Table 1): R1-Distill-Qwen-14B 19.14% numerical / 37.14% statement on LoopBench; Qwen3-8B 18.86% / 10.43%; frontier closed models ~5%. [paper via fetch summary; not re-checked]
- Temperature: statement loops for R1-Distill-Qwen-7B drop from 61.43% (T=0.1) to 44.86% (T=0.6) to 3.86% (T=1.0) while numerical loops persist at T=1.0 (14.86%). [paper via fetch summary, Tables 1, 6, 7]

## 7. What JouleServe-WS can take
- A labelled-loop taxonomy and the persistence trick (multiple consecutive alarms) that our detector already mirrors ("3 checks").
- A second baseline: a hidden-state probe detector, to compare earliness against our text-compression detector. Needs hidden-state export from SGLang (non-trivial, inferred).

## 8. What JouleServe must add beyond it
- Text-only, model-agnostic detection that needs no training and works on API-like logits-free setups; engine-level stop; energy accounting; agent retry policy.

## 9. Workstation -> edge
- Hidden-state probes add a GEMV per chunk; negligible versus decode. The harder part is accessing hidden states in a serving engine on Jetson.

## 10. Relevance to our current findings
- Confirms mechanistically that loops are a real, high-frequency mode of reasoning models and that greedy-like (low-T) decoding worsens statement loops. Our loops are in thinking text of Gemma-4, plausibly the statement-loop type. Detection earliness (~1,500 tokens before onset) is much smaller than the savings available at our median stop (35% of a 32K call, i.e. thousands of tokens), so a detector firing at onset is already useful. [inferred]
- No energy numbers: P5 would supply them.

## 11. Open questions / uncertainty
- Whether FPR 0.24-0.30 would be tolerable for agent tasks (our detector flagged 0 of 173 normal long calls). Models tested are not Gemma-4.

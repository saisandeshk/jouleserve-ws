# Dynasor / Certaindex — answer-stabilization signal used to early-exit reasoning and schedule reasoning programs inside SGLang

- **Source:** Efficiently Scaling LLM Reasoning with Certaindex (arXiv title v2); Yichao Fu, Junda Chen, ..., Ion Stoica, Hao Zhang; arXiv preprint 2412.20993v2 (May 2025), "Under review" on the PDF; https://arxiv.org/abs/2412.20993 ; code https://github.com/hao-ai-lab/Dynasor
- **Review depth:** partial. Abstract, introduction, Sections 2-3 and the evaluation text were read via PDF text extraction with keyword navigation; appendix experiments, Table 1 workload details, and the limitation section only skimmed. Code not read.
- **Category:** agent-aware scheduling (reasoning-program serving; early exit)
- **Code/artifacts:** repo above; implemented as ~500 lines in SGLang (Sec. 3.3, "Implementation"). [paper]

## 1. Summary
- "Probe-In-The-Middle": every N tokens (e.g. 64) the system appends a probe that forces an intermediate answer, then discards the probe tokens and resumes. If probed answers stay consistent, certainty is high and the request is terminated. [paper, Sec. 2.1, Fig. 4]
- Certaindex generalizes this to self-consistency, MCTS and Rebase. Dynasor uses it to (a) early-exit, (b) reallocate token budgets across requests, (c) gang-schedule requests of the same reasoning program.
- Claims up to 50% compute saved at equal accuracy in batch serving and up to 3.3x higher query rate / 4.7x tighter SLO in online serving (abstract, intro). [paper]

## 2. Problem and key insight
- Reasoning models overuse tokens (e.g. "78% fewer tokens" in an intro figure for accuracy vs usage; DeepSeek-R1 "3x more tokens than it actually needs", Fig. 2). Intermediate answers stabilise, regardless of whether they are correct. [paper]

## 3. Workloads
- Datasets named in the text: MATH-500, GSM8K, LiveCodeBench, ASDiv, Game24; algorithms CoT, SC, MCTS, Rebase; LLMs include Llama3.1-8B, Gemma, Phi, QwQ, DeepSeek-R1-distill family. Max token budget 16K in the ablation. [paper; exact per-experiment pairing not verified]
- Datacenter GPU serving; Poisson-style request-rate sweeps compared with SGLang and Parrot (Sec. 4). No agents with tools, no energy measurement (the word appears only in the impact statement). [paper]

## 4. Assumptions
- A question with a checkable, short final answer, so the model can be probed for an intermediate answer and consistency can be judged. Probes cost extra decode tokens (frequency is an ablation, T=32-320).
- Output is a reasoning answer, not a long tool-call body.

## 5. Controller / mechanism
- Signal: consistency of probed answers; stop when stable for a number of probes; mark as unconfident if answers keep changing. Scheduler: SGLang thin layer around the decode loop; reallocates budget toward uncertain requests and keeps program stages together. [paper]

## 6. Evaluation and reported results
- Headline numbers above; throughput is "equal average" tokens/s in online settings, gains come from earlier completion and higher turnover (Sec. 4, text near "Throughput"). [paper]

## 7. What JouleServe-WS can take
- A working SGLang integration pattern (decode-loop hook) for a mid-generation stop. Reimplement as baseline: periodic probe-and-stop with budgets. The hook location in SGLang is a template for our zlib-ratio detector.

## 8. What JouleServe must add beyond it
- A stop signal for loops that needs no probe and no answer (text compressibility), cheaper than probing.
- Energy as the objective, and agents with tool calls whose bodies (not answers) get capped.
- A retry policy after a stop.

## 9. Workstation -> edge
- Probing doubles as extra decode on a bandwidth-bound device, costly per probe on Jetson (inferred). Datacenter batching gains (3.3x) rely on large batches; edge batches are small.

## 10. Relevance to our current findings
- Same family of idea (stop reasoning when more tokens add nothing), but their signal fires on *converged correct-looking answers*; our capped calls are repetition loops, where answers may never converge or may be never emitted. Probing a loop would likely return the same answer and "certify" it, which is different from the cause we need to detect. [inferred]
- Their "tokens are wasted" argument is at the compute level; ours is board energy on a Jetson.

## 11. Open questions / uncertainty
- Whether Certaindex fires on a looping trace at all; whether SGLang changes since the paper break the 500-line patch.

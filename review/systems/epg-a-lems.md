# Energy per Successful Goal (EpG) / A-LEMS — goal-level energy accounting and the Orchestration Overhead Index

- **Source:** Energy per Successful Goal: Goal-Level Energy Accounting for Agentic AI Systems; Deepak Panigrahy (independent), Aakash Tyagi (Texas A&M); arXiv preprint 2605.22883, 20 May 2026; https://arxiv.org/abs/2605.22883
- **Review depth:** full text of the PDF converted locally with pdftotext (abstract, §1-4 skim, §6-8 read; appendices not read). No code seen.
- **Category:** energy-aware serving / measurement methodology
- **Code/artifacts:** none linked in the text I read **[paper]**. Experiments: 2,228 runs.

## 1. Summary
Defines EpG (total workflow energy including failed attempts, divided by successful goals) and OOI (agentic EpG over matched linear EpG). Empirically, agentic workflows cost 4.33x (888.1 J vs 205.3 J) over 827 matched goal pairs on reasoning tasks, but fall below 1.0x on single-tool tasks (§8.5).

## 2. Problem and key insight
Energy per inference is the wrong unit for agents because inference count is an implementation artefact. Normalise per successful goal, include retries (§1.1-1.2).

## 3. Workloads
Five reasoning families (factual QA, science QA, GSM8K basic, GSM8K multi-step, logical reasoning) and three tool-graph families (single calc, single db, two-tool chain), n=50 pairs per tool family (§8.1, Table 5). Not embodied, not code-as-action.

## 4. Assumptions
Binary success; "linear" baseline = one-shot call with no orchestration; failure injection at a fixed rate for the retry study; energy from Intel RAPL on a laptop CPU (i7-1165G7), Table 6.

## 5. Controller / mechanism
Measurement stack: 100 Hz RAPL, 2-sigma idle baseline subtraction, CPU-fraction process attribution, phase decomposition (planning/execution/synthesis/gap), 3-hash reproducibility protocol (§3-5). Reusable idea: EpG/OOI definitions and failure-inclusive accounting.

## 6. Evaluation and reported results (**[paper]**)
- Headline: 4.33x higher mean EpG (888.1 J vs 205.3 J), OOI 3.02-7.63x across reasoning families; GSM8K-M 7.63x, GSM8K-B 2.75x (§8.5, Fig. 10-11).
- Tool tasks: OOI below 1 for single-tool tasks, 1.55x for the two-tool chain (§8.5). The "linear" arm has no tool and must do arithmetic by generation.
- Retry study: failed attempts took 26.9% of agentic energy; a canonical failed attempt 2256.1 J vs 1358.4 J for the successful one (§1.3, §8.6).
- Local inference is Ollama/TinyLlama-1B (n=588 agentic runs); remote is Groq llama-3.3-70b (n=378), where RAPL sees only client-side orchestration energy (§8.1).

## 7. What JouleServe-WS can take
The metric definition (energy per successful goal incl. failures) is exactly P5's objective; adopt EpG and an OOI-like ratio "paradigm / matched baseline" with the same goal instances. Cite for the claim that per-goal accounting is the right unit.

## 8. What JouleServe must add beyond it
GPU/SoC rail energy (they exclude GPU); strong models (1B model is unrepresentative); real agent paradigms with code-as-action and step-wise tools; embodied tasks with long waits; concurrency; success checking at P1 strictness.

## 9. Workstation -> edge
Their measurements are on an x86 laptop with RAPL; nothing transfers directly. Jetson would need tegrastats/INA rails, and the 0.2-1.0 W tool-wait power they note is not representative of a loaded SoC.

## 10. Relevance to our current findings
- Supports the framing of option B (orchestration structure decides energy per success) but at toy scale and with the sign depending on whether tools replace generation, an analogue of step-wise vs program-writing.
- Does not compare code-as-action vs step-wise; its "agentic" is a plan/execute/synthesise pipeline. It is a measurement paper, single independent author plus one university author, no peer review noted: treat numbers as indicative.

## 11. Open questions / uncertainty
Unclear whether results hold with GPU inference or large models; code not seen; remote-regime energy is client-side only.

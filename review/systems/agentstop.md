# AgentStop — gradient-boosted supervisor that terminates local agent runs predicted to fail, to save energy

- **Source:** AgentStop: Terminating Local AI Agents Early to Save Energy in Consumer Devices; Dzung Pham, Kleomenis Katevas, Ali Shahin Shamsabadi, Hamed Haddadi; ACM CAIS '26 (San Jose, May 2026), arXiv 2605.15206; https://doi.org/10.1145/3786335.3813163 ; code https://github.com/brave-experiments/AgentStop
- **Review depth:** full text of the arXiv PDF read through Sections 1-7 (setup, default-agent measurements, start of the results); appendix, Figures 9-10 numbers and the later results (coding) not read in detail. Code not read.
- **Category:** energy-aware serving (agent-level supervisor; edge/on-device)
- **Code/artifacts:** public repo (Brave); engine llama.cpp (needs logprobs); data released per abstract.

## 1. Summary
- Trajectory-level early termination: after agent step k, an XGBoost classifier predicts "will this run fail?"; if so the run is killed. [paper, Sec. 3-4]
- Reports 15-20% less wasted energy for a Qwen3-30B-A3B agent with <5% task-utility drop on FRAMES/SimpleQA; ~19% less power with ~3% lower completion on SWE-Bench Verified with Qwen3-Coder-30B-A3B (abstract + intro; the 19%/3% figure is from the project page/search snippet, not re-verified in the body I read). [paper]
- It is the only reviewed work that both stops agents early and measures energy on a local device. It never looks inside a single LLM call.

## 2. Problem and key insight
- Failed agent runs consume more energy than successful ones (Fig. 3: later steps cost more in failed runs; QA failure wastage 352.4 mWh/task on FRAMES with the 30B MoE, Table 1). [paper]
- Insight: signals already produced during inference (smallest token logprobs, output length per step, token overlap between adjacent steps) predict failure early enough to save energy. [paper, Sec. 4.2]

## 3. Workloads
- Web QA (SimpleQA, FRAMES) with smolagents CodeAct, <=10 steps, <=512 output tokens per step; coding (SWE-Bench Verified, 500 tasks) with mini-swe-agent, <=100 steps, <=4096 tokens per step. [paper, Sec. 5.2]
- Models: Qwen3-30B-A3B-2507-Instruct, Qwen3-Coder-30B-A3B, Qwen3-1.7B; 4-bit via llama.cpp; run in **non-reasoning mode** ("crucial to efficient local deployment since reasoning models tend to generate a large volume of thinking tokens"). Qwen-recommended sampling parameters, not greedy. [paper]
- Hardware: Apple M1 Max, 64 GB unified memory; powermetrics at 100 ms, trapezoidal integration, baseline CPU subtracted. [paper, Sec. 5.3]
- Coding runs are 8-10 min, 50-60 LLM calls; mean energy 2715.6 mWh per run (Table 2); ~60% of energy in the first 10 steps (text near Fig. 6). [paper]

## 4. Assumptions
- Labelled training runs (per agent, task, step) are available; one GBDT per (agent, task, step). Savings are **simulated from one full run per task** (energy per step logged, then the stop is replayed), not measured with live stopping. [paper, Sec. 5.4]
- Stop decision only at step boundaries; the cost of a runaway inside one step is not controlled. Per-step caps (512/4096 tokens) bound the damage by design.
- No retry after a stop (a stopped run counts as failed).

## 5. Controller / mechanism
- Features: 10 smallest logprobs per step (exponentiated), output tokens per step, longest-common-sequence overlap between adjacent steps. GBDT inference <0.01 mWh (cited). Threshold tuned for the energy-vs-utility trade. [paper]
- Baselines: random exit, min-logprob, mean-logprob. AUC 0.6-0.7 in first 4-5 steps for the 30B MoE; no better than random for the 1.7B model (Fig. 8). [paper]
- Notable finding: stopping too aggressively hurts, because wrongly stopped successes turn into wastage (Fig. 9a). [paper]

## 6. Evaluation and reported results
- Metrics: energy wastage reduction, task utility drop. Headline numbers above. Evaluated on one laptop; no Jetson. [paper]

## 7. What JouleServe-WS can take
- The two metrics (wastage reduction, utility drop) and the "replay from one logged run" simulation method map directly onto P5's energy-per-successful-task evaluation.
- Baseline to reimplement: a step-level failure predictor on SGLang logprobs. Cheap to build; it is the natural comparison for a within-call stop.

## 8. What JouleServe must add beyond it
- Stopping inside a call (their granularity is the step), for thinking-on models with 32K caps, where one call can be most of the run's energy.
- Retry/recovery policy after the stop; they only terminate.
- Serving-layer integration (a stop hook in the engine) and Jetson power rails instead of laptop powermetrics.

## 9. Workstation -> edge
- Already on unified-memory hardware, so the energy-accounting approach transfers; on Jetson use tegrastats/INA rails. Logprobs from SGLang are available per token (inferred); extra D2H copies cost little on unified memory.

## 10. Relevance to our current findings
- Closest prior art for "stop wasteful agent compute, judge by energy". But its waste is failed trajectories in non-reasoning mode, whereas ours is a single decode that loops to a 32,768-token cap. Their step-level predictor would see a capped call only after the energy is spent. [inferred]
- Their repetition feature is step-to-step overlap, not within-call looping.

## 11. Open questions / uncertainty
- Whether their classifier would catch our loop calls at all (it sees only completed steps). Whether the 19%/3% SWE-Bench figures hold in the body (not re-read).

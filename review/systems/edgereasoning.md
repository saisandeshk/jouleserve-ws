# EdgeReasoning — latency/power/energy characterisation of reasoning LLMs on Jetson AGX Orin with token-budget control

- **Source:** EdgeReasoning: Characterizing Reasoning LLM Deployment on Edge GPUs; Benjamin Kubwimana, Qijing Huang (NVIDIA); arXiv preprint 2511.01866 (cs.DC, Oct 2025); https://arxiv.org/abs/2511.01866 ; code org https://github.com/edge-inference (referenced in the paper's reproducibility text)
- **Review depth:** partial. Abstract, Sections I-V (motivation, latency/power/energy models, budgeting and parallel-scaling evaluation), takeaways and table headers read from PDF text extraction; appendix tables and the quantisation section skimmed.
- **Category:** edge/on-device characterisation
- **Code/artifacts:** repo org above; vLLM engine; Jetson AGX Orin 64 GB, power modes 15 W/30 W/50 W/MAXN. [paper]

## 1. Summary
- Characterises reasoning vs non-reasoning models (DeepSeek-R1 distills 1.5B/8B/14B, Qwen2.5-7B, Llama3.1-8B, Gemma-7B, L1) on Orin: fitted analytic models for prefill and decode latency, power, and energy per token; then evaluates token-budgeting (prompt-based soft limit, hard truncation, L1 budget-aware model, non-reasoning) and parallel test-time scaling to map accuracy-latency/energy Pareto fronts. [paper, Sec. III-V]

## 2. Problem and key insight
- Reasoning on the edge must meet latency budgets; decode dominates. Takeaway #2: "Edge inference latency of reasoning LLMs is dominated by decode." Table VII: decode phase takes 192-569x longer than prefill, over 99.5% of inference time on full MMLU-Redux. [paper]

## 3. Workloads
- MMLU-Redux (150-question subset in Table II), AIME/Math500 (in the cost comparison), single-turn QA, no agents or tools. [paper]

## 4. Assumptions
- Single-request or parallel-sampling batches; no tool waits; no loop discussion (a keyword scan for loop/repetition/degeneration/greedy/temperature found nothing in the text). [paper, scan]

## 5. Controller / mechanism
- Not a controller. Provides latency model L = L_prefill + L_decode with L_decode(I,O) = nO + mIO + ...; a power model that grows logarithmically with length; and E = E_prefill + E_decode. Budget control is by prompt instructions, hard max-token limits, or the L1 model. [paper, Eq. 1-6]

## 6. Evaluation and reported results
- Table II (150 MMLU-Redux questions, Orin): DSR1-Llama-8B 61.7% acc, 143.3 s, 4205.5 J/question; Llama3.1-8B 58.3%, 2.5 s, 77.9 J; Qwen2.5-7B 60.8%, 0.6 s, 26.4 J; DSR1-Qwen-14B 80.6%, 207.0 s, 2599.2 J. [paper, Table II]
- Takeaway #5 prompt-based budgets are effective; #6 fine-tuned budget-aware models (L1) give the best control; #8 non-reasoning models are competitive at low budgets (<20 s). Takeaway #10 parallel scaling uses idle hardware. [paper; takeaway text only partly read]

## 7. What JouleServe-WS can take
- Methodology: Orin power-mode sweep, fitted energy-per-token models vs output length, and the accuracy-vs-energy Pareto presentation; reuse their analytic model to project energy of a capped call (32K tokens) from decode power.
- Budget arms (hard cap, soft limit) as baselines for "thinking budget" in P5.

## 8. What JouleServe must add beyond it
- Agents with tool calls and multi-call tasks; runaway calls specifically (they study average length, not capped tails); an online stop; Thor and MoE/hybrid models; thermal behaviour; energy per successful task.

## 9. Workstation -> edge
- Already edge. Their energy is GPU/board as measured on Orin 64 GB; our Thor/Orin 32 GB need re-fitted coefficients.

## 10. Relevance to our current findings
- Independent evidence on Jetson that decode, not prefill, is where time and energy go for reasoning models (>99.5% of time); our 67-69% capped-call energy share is a finer decomposition inside the decode. They show budgeting (hard limit) is the standard remedy but have no notion of detecting a runaway.

## 11. Open questions / uncertainty
- Whether hard limits in their experiments truncated loops vs long honest reasoning (not analysed in what I read).

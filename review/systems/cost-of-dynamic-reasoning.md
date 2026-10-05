# The Cost of Dynamic Reasoning — AI-infrastructure characterisation of CoT, ReAct, Reflexion, LATS and LLMCompiler agents

- **Source:** The Cost of Dynamic Reasoning: Demystifying AI Agents and Test-Time Scaling from an AI Infrastructure Perspective; Jiin Kim, Byeongjun Shin, Jinha Chung, Minsoo Rhu (KAIST); arXiv preprint 2506.04301 (v2, Jan 2026); https://arxiv.org/abs/2506.04301
- **Review depth:** partial. Read via arXiv HTML (v2) through a fetch tool that summarises; I queried it twice for exact figures/tables. I did not read the appendix or the code.
- **Category:** workload/benchmark (agent-paradigm characterisation incl. energy)
- **Code/artifacts:** https://github.com/VIA-Research/AgentBench (stated in paper) **[paper]**; engine vLLM 0.6.6.

## 1. Summary
Closest published work to option B on the serving side: runs the same serving stack (vLLM, A100) over five paradigms (CoT, ReAct, Reflexion, LATS, LLMCompiler) on HotpotQA, WebShop, MATH, HumanEval, and reports LLM calls, latency, GPU idle time, memory, accuracy and GPU energy per query. Main message: dynamic reasoning raises cost by orders of magnitude for diminishing accuracy.

## 2. Problem and key insight
Agents and test-time scaling make LLM invocations dynamic and many; prior serving work assumes single-shot requests. Insight: paradigm and iteration budget set cost; sequential scaling (Reflexion) gives poor accuracy per joule vs parallel scaling (LATS).

## 3. Workloads
HotpotQA (Wikipedia tool), WebShop, MATH (Wolfram/Python), HumanEval; ShareGPT as non-agentic baseline. Llama-3.1-8B-Instruct (1x A100 40GB) and 70B (8x A100 40GB); prefix caching on. Datacenter GPUs only; QA/web tasks, not embodied or long-wait tools.

## 4. Assumptions
Concurrency with prefix caching; no SLA targets (stated limitation); GPU energy only (CPU, DRAM, network excluded); tool latency task-specific.

## 5. Controller / mechanism
None; it is a characterisation. Reusable: the benchmark harness.

## 6. Evaluation and reported results (all **[paper]**, as extracted from text; figure values read via summary)
- LLM calls (Fig. 4): CoT 1; ReAct about 9.2x CoT; LATS 71.0 per request on average.
- Latency breakdown (Fig. 5): LLM inference 69.4%, tool execution 30.2%; GPU idle up to 54.5% for HotpotQA/MATH agents (Fig. 6); decode 74.1% of GPU execution time.
- Context growth (Fig. 8): HotpotQA input about 1,000 tokens grows 3-4x over iterations. Prefix caching cuts prefill latency by 60.1% on average and raises ReAct throughput 5.62x on average (Fig. 11); KV reduction 51.7% average, up to 63.5% (Fig. 12).
- Throughput (Fig. 11): ShareGPT 6.4 QPS vs ReAct HotpotQA 2.6 QPS and WebShop 1.2 QPS.
- Energy (Table III): per query ShareGPT 8B 0.32 Wh; Reflexion 8B 41.53 Wh (130.9x), LATS 8B 22.76 Wh (71.7x); ShareGPT 70B 2.55 Wh; Reflexion 70B 348.41 Wh (136.5x), LATS 70B 158.48 Wh (62.1x). Reflexion is about 1.8x (8B) / 2.2x (70B) the energy of LATS.
- Accuracy (HotpotQA, Fig. 13/Table III): Reflexion 8B 38%, LATS 8B 80%, Reflexion 70B 67%, LATS 70B 82%.
- Fig. 13: ReAct moderate accuracy with consistently low latency; Reflexion modest accuracy gains at high latency; LLMCompiler beats ReAct on HotpotQA but not WebShop; not run on MATH/HumanEval since DAG planning does not fit sequential reasoning.
- Iteration budget (Fig. 14): p95 latency keeps rising after accuracy saturates. Reflexion sequential scaling: 31x higher cost for same marginal accuracy at later points (Fig. 16).
- Energy per successful task is not the reported metric; energy is per query (not success-normalised) **[paper, as read]**.

## 7. What JouleServe-WS can take
Harness and methodology (per-paradigm LLM-call, token and idle-time breakdown); the Reflexion/ReAct/LLMCompiler implementations as reference points; the prefix-caching result as an expected upper bound for retained-state value when context grows 3-4x per call.

## 8. What JouleServe must add beyond it
Embodied closed-loop tasks with long real-time tool waits; whole-program (code-as-action) and step-wise tool calling as separate paradigms; energy per success; edge hardware and power modes; thinking-on models; concurrency of several agents on one device.

## 9. Workstation -> edge
Datacenter A100s, 8B/70B dense. On Jetson, unified memory removes the PCIe tier and batching headroom is small; their 54.5% GPU idle during tools would map to idle power on the SoC rather than freed capacity. Port requires re-measuring energy with board rails (they use GPU-only counters).

## 10. Relevance to our current findings
- Consistent with P5: Reflexion is the expensive end (130x a chat query; 5-13x more than step-wise in P5), and ReAct-style interleaved tool use is cheap. Their decode share (74.1%) matches P1's decode-dominated finding.
- It does not test code-as-action vs step-wise tool calling and its ReAct/Reflexion are QA-style short loops, so the P5 comparison (whole-program vs one-action-per-call on drone missions) is not covered **[inferred]**.
- Their prefix-caching gains (60% prefill reduction) come from a growing single conversation; that is exactly the step-wise pattern, whereas P1 rebuilds role prompts, which would earn little. This predicts why step-wise wins on serving cost.

## 11. Open questions / uncertainty
- I did not verify per-workflow token counts or the energy-measurement method beyond the summary (GPU counters assumed).
- Which "Reflexion" configuration (trial count) feeds Table III was not checked.

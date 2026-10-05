# TriAxialKV — per-token INT2/INT4 KV precision by role (instruction / tool call / observation) and recency, for agent inference

- **Source:** TriAxialKV: Toward Extreme Low-Precision KV-Cache Quantization for Agentic Inference Tasks; Hanzhang Shen, Haoran Wu, Yiren Zhao, Robert Mullins (Cambridge, Imperial); arXiv preprint (cs.LG), 16 May 2026; https://arxiv.org/abs/2605.17170 (HTML: arxiv.org/html/2605.17170v1)
- **Review depth:** partial. HTML full text read through the fetch tool's extraction (method, Tables 2-5, Fig 5 as summarized). Not read line by line; numbers below come from that extraction and should be re-checked in the tables before citing. No code read.
- **Category:** KV substrate (quantization), agent-aware; adjacent to edge
- **Code/artifacts:** integrated into an SGLang v0.5.10 fork; no standalone repo link found in the paper. [paper]

## 1. Summary
- Assigns each KV token a tag on three axes: temporal (older / turn-2 / turn-1 / current), modality (text / image), semantic role (inst, user, assistant, reasoning, tool_call, obs, delim). An offline calibration picks INT2 or INT4 per tag under an average-bit budget. [paper]
- Reports accuracy within about 1 point of BF16 on BFCL Memory (all models within +/-1.1 pt) and OSWorld, at 4.5x KV capacity; uniform 2-bit KIVI loses 4-5 points on BFCL. [paper, Tables 2-3]
- This is the closest published match to "KV precision as a capacity lever evaluated on tool-calling agents", but precision is fixed offline, not chosen at run time from memory pressure.

## 2. Problem and key insight
- Agentic prefills are long, mostly reused, and heterogeneous; per-token KV sensitivity spans more than 10x across tags. System prompts and tool schemas (semantic axis "inst") need 4-bit; old observations tolerate 2-bit. [paper]
- Ablation (Table 4, BFCL Qwen3-32B): drop the temporal axis 25.11 to 21.33; drop the semantic axis to 20.89. [paper]

## 3. Workloads
- BFCL Memory (function calling with memory) on Qwen3-14B/32B/235B-A22B, Falcon3-10B; OSWorld computer use on Qwen3-VL-8B/32B, InternVL3.5-38B. OSWorld trajectories average 11K prefill, 300 decode tokens. [paper]
- Qwen3-32B BFCL Memory: BF16 25.78, TriAxialKV 25.11 (-0.67). Qwen3-14B 25.11 to 24.22. OSWorld Qwen3-VL-32B 39.20 to 40.59. Note the small absolute BFCL Memory scores and the noise level of OSWorld; the paper does not (as extracted) give confidence intervals. [paper; inferred caveat]
- No reasoning-benchmark (AIME-style) evaluation of the scheme reported in the extraction. Not a real-time or closed-loop robotics agent.

## 4. Assumptions
- Discrete datacenter GPUs (B200 180 GB, H100 80 GB). Standard chat-template markers so a CPU tagger can label tokens. One-time calibration on 5% of a workload per model. Only INT2/INT4. [paper]

## 5. Controller / mechanism
- Offline: capture KV traces, measure per-tag attention-output MSE at 2 vs 4 bit, solve min sum D_k(b_k) s.t. average bits <= budget (enumeration for <=22 tags, greedy otherwise). Budget chosen as the smallest average bit-width where accuracy stabilizes (calibrated 2.7 bits; each 0.1-bit cut costs about 5% accuracy, Table 5). [paper]
- Runtime: a CPU tagger does one pass over the template; bit map lookup; two paged pools (INT2 and INT4) with a fused Triton decode kernel; INT2 keys per-channel (group 32), values per-token. [paper]
- Cadence: static per workload. No feedback from memory pressure, queue state or energy.

## 6. Evaluation and reported results
- Throughput on OSWorld: 1.52x BF16 on H100 and 1.32x on B200 for Qwen3-VL-32B; concurrency up 3.4-4.0x (Fig 5). KIVI uniform 2-bit: -4 to -5 points on BFCL; SGLang FP4: -7.11 to +4.22 (high variance). [paper]
- Energy: only a qualitative statement; no measurement found in the extraction. [paper, as extracted]

## 7. What JouleServe-WS can take
- The tag-by-role idea is cheap to reproduce: SGLang already marks the system/tool prefix; a role map for the P1 agent (system, 7 tool defs, user, tool result, thinking) is simple. Baseline: uniform FP8 (`--kv-cache-dtype fp8_e4m3`, supported in SGLang) vs. role-mixed FP8/INT4 if a kernel exists. Realistically, only FP8 is available on SGLang 0.5.20 for us; INT2/INT4 needs the fork.
- Evaluation recipe: BFCL-style tool calling plus an agent benchmark at matched capacity.

## 8. What JouleServe must add beyond it
- Choosing precision at run time from live pool occupancy; measuring energy per successful task (not throughput); closed-loop multi-step agent tasks on small models (7-26B, not 14-235B); interaction with the 38% fixed prompt (the paper's finding that the instruction/tool-schema tokens need 4-bit means the fixed prompt is the expensive part to compress, which pushes toward shrinking it rather than quantizing it).

## 9. Workstation -> edge
- Fused INT2/INT4 Triton kernels target Hopper/Blackwell; Orin (sm_87) and Thor (sm_110) support is unverified. FP8 KV on Orin (Ampere, no FP8 tensor cores) may be emulated and slow: **[inferred]; check the SGLang note that dequantization not fused with attention can be extremely slow.** Unified memory means the freed bytes also go back to weights/OS, so capacity gain translates directly.

## 10. Relevance to our current findings
- Supports the premise that capacity can be bought without losing tool-call quality, at least for 14B+ models on BFCL Memory. Does not test thinking-heavy Reflexion decode, which is where P1 runs spend their time.

## 11. Open questions / uncertainty
- Does the calibrated map transfer across tasks? Quality for small MoE (gemma-4-26B-A4B) and hybrid sliding-window models? Re-check Tables 2-5 numbers and whether the 1-point margins are within run-to-run noise.

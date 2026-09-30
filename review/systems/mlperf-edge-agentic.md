# MLPerf Edge Agentic — MLCommons single-stream agentic replay + BFCL accuracy benchmark for edge LLMs

- **Source:** "Edge Agentic Inference Benchmark for MLPerf Inference v6.1", MLCommons Edge LLM Taskforce; MLCommons blog, July 2026 (call for submission); results published with MLPerf Inference v6.1 (~16 Sep 2026). Links: https://mlcommons.org/2026/07/mlperf-inference-v61-edge-agentic/ ; https://mlcommons.org/2026/07/agentic-inference-for-mlperf-inference/ ; reference impl https://github.com/mlcommons/endpoints (Edge Agentic example; blog says `examples/10_Edge_Agentic_Example/`, the fetched repo URL was `examples/11_Edge_Agentic_Example` — directory number unstable); rules https://github.com/mlcommons/inference_policies ; NVIDIA result blog https://developer.nvidia.com/blog/tensorrt-edge-llm-completes-the-mlperf-edge-agentic-benchmark-6-4x-faster-on-jetson-agx-thor/
- **Review depth:** partial — MLCommons call-for-submission blog, NVIDIA submission blog, the endpoints example README (accuracy part), via a fetch summarizer. The inference_policies rules text and the performance-phase README/dataset were NOT read. Sources are thin on the performance dataset itself.
- **Category:** workload/benchmark
- **Code/artifacts:** mlcommons/endpoints (reference harness, OpenAI-compatible Chat Completions client; `inference-endpoint benchmark from-config ... --accuracy-only`). Trajectory dataset availability/license not verified; submission requires MLCommons membership, but the harness is public. Model Qwen3.6-27B is Apache 2.0.

## 1. Summary
Edge benchmark measuring an OpenAI-compatible endpoint in two phases. Performance: deterministic replay of 20 recorded software-engineering agent conversations (1,007 generated turns, SWE-bench-style), input growing to ~23.5K tokens. Accuracy: BFCL v4 single-turn (~995 samples). Reference model Qwen3.6-27B (Q4_K_M GGUF, ~16.5 GB) on Jetson AGX Thor 128 GB [MLCommons blog].

## 2. Problem and key insight
Edge agent use (coding copilots, robotics controllers, private assistants) needs fast token generation, efficient prefill over long shared histories, and valid tool calls within power/memory limits. Each request in a trajectory contains most of the previous conversation, so without prefix/KV reuse the shared history is re-prefilled every turn [NVIDIA blog].

## 3. Workloads
- Performance: 20 conversations, 1,007 turns (~50 turns/conversation on average [inferred: 1007/20]). Recorded coding-agent trajectories; model produces tool calls (bash), tool results come from the recording. Context window fixed 32,768; peak input ~23.5K; max new tokens 1,024; temperature 0, seed 42; reasoning OFF (reasoning-on gave 78.19% vs 86.23% on BFCL).
- Replay is deterministic; **target_concurrency = 1** (single in-flight request) [blog]. Whether inter-turn tool-wait delays are replayed was not stated; tool time is likely zero/absent [inferred]. So retained-state savings show as prefix-cache reuse only, with no pause durations.
- Inline accuracy: multiset IoU of executed bash tool calls vs ground truth.
- Accuracy set: BFCL v4 non_live 72% / live 17% / hallucination 11%; reference 86.23% overall; pass >= 83.64% (97% of reference) and >= 85.32% category-normalized.
- Metrics: per-turn TTFT, TPOT, end-to-end latency, ISL/OSL p50/p90/p99/max. Blog explicitly avoids throughput. No power metric in what we read.
- Hardware: reference Jetson AGX Thor; needs ~24 GB memory, Python 3.12+, llama.cpp or equivalent.

## 4. Assumptions
Single interactive user, single stream, fixed memory/power budget, hard context limit (no overflow), reasoning off, quantized model, tool outputs pre-recorded. Datacenter agentic benchmark (September) separately targets MoE, 100K+ contexts, concurrency sweeps [blog].

## 5. Controller / mechanism
None; it is a benchmark harness. Submissions may use any engine (NVIDIA used NVFP4, tree MTP, KV cache reuse).

## 6. Evaluation and reported results
NVIDIA TensorRT Edge-LLM on Thor: 1,007 turns in 24 min 36 s, 52.33 tok/s, median TTFT 247.12 ms, median TPOT 14.68 ms, BFCL 87.94%; 6.4x faster than llama.cpp reference (2 h 37 min) [NVIDIA blog]. Full accuracy run takes ~3 h on edge hardware [README].

## 7. What JouleServe-WS can take
- A standard, citable workload with growing context and prefix reuse: run the replay against SGLang (OpenAI endpoint) to report energy per replay, and TTFT with radix cache on/off.
- Harness (mlcommons/endpoints) can drive an SGLang server; add NVML/tegrastats power sampling around it.
- Caveat: 27B model at 32K: bf16 K2-Horizon-7B is a different model; the replay tokens come from Qwen tokenization, so replay by token counts/text rather than reusing token IDs [inferred].

## 8. What JouleServe must add beyond it
Concurrency > 1, real tool pauses, energy/thermal metrics, task success under SLO. The benchmark has none of them.

## 9. Workstation -> edge
It targets Thor directly, which makes it the natural edge validation workload. On WS the 32K window fits the ~25K-token KV pool only barely for one session.

## 10. Relevance to our current findings
Coding agent with reasoning off: short outputs (max 1,024), prefill/long history reuse matters far more than in our decode-dominated thinking runs. It is the opposite regime to P1's drone traces, so it is a useful "prefill-heavy" contrast case; but with concurrency 1 and no waits it exercises retention only trivially. P1 argues coding agents are not edge-plausible; MLCommons's own rationale lists coding copilots first.

## 11. Open questions / uncertainty
- Are pause times replayed? Is the trajectory set public and licensed? Directory number (10 vs 11) inconsistent. Rules doc not read. Nothing on power measurement rules.

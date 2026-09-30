# MLPerf Edge Agentic benchmark on Jetson AGX Thor via TensorRT Edge-LLM (NVIDIA submission)

- **Source:** "TensorRT Edge-LLM Completes the MLPerf Edge Agentic Benchmark 6.4x Faster on Jetson AGX Thor", NVIDIA developer blog (2026); https://developer.nvidia.com/blog/tensorrt-edge-llm-completes-the-mlperf-edge-agentic-benchmark-6-4x-faster-on-jetson-agx-thor/ ; code https://github.com/NVIDIA/TensorRT-Edge-LLM/tree/release/0.9.1-mlpinf
- **Review depth:** partial — vendor blog only (via fetch-and-summarize); the MLPerf benchmark spec and repo were not read. Not a paper.
- **Category:** workload/benchmark; edge/on-device; hybrid-model caching
- **Code/artifacts:** engine repo public (branch above); Qwen3.6-27B NVFP4 checkpoint on Hugging Face (centml/Qwen3.6-27B-NVFP4-W4A4-mlpinf). Benchmark trace availability: verify in MLPerf repo.

## 1. Summary
Multi-turn agentic benchmark on Thor: 20 conversations, 1,007 generated turns, context growing to ~23.5K tokens, plus a BFCL v4 accuracy phase. NVIDIA's run: 24 min 36 s, 52.33 tok/s, 6.4x faster than llama.cpp reference **[blog]**.

## 2. Problem and key insight
Reuse of KV and recurrent state across turns: ~96% of prompt tokens served from hot cache (0.5M of 13.6M prompt tokens prefilled). Qwen3.6-27B is hybrid (recurrent + full attention), so this is retained state for hybrid models on Thor **[blog]**.

## 3. Workloads
Multi-turn agent trajectories with growing context; tool-wait characteristics not stated (benchmark likely replays turns without real waits **[inferred]**).

## 4-5. Assumptions / mechanism
NVFP4 weights+activations, FP8 KV, KV+recurrent state reuse, tree-based MTP (8 draft steps, top-2, 16-node tree; ~40% decode gain over linear MTP) **[blog]**. Retention unbounded within run; no energy reporting extracted.

## 6. Results
See Summary. Baseline is the benchmark's llama.cpp reference.

## 7. What JouleServe-WS can take
Candidate workload and a target for "hot-cache hit rate" reporting; a Thor-native engine comparison (TensorRT Edge-LLM) for the later port.

## 8. What JouleServe must add
Energy, real tool waits, concurrency, and retention decisions (here retention is free and always on).

## 9. Workstation → edge
It is edge-native (Thor, 128 GB unified) so it shows retention is nearly free capacity-wise there; pressure appears only with concurrent sessions + co-located sims.

## 10. Relevance to our findings
Contradicts none: 96% reuse here vs 10-66% in P1 rebuilt-prompt Reflexion traces; shows prompt design drives reuse.

## 11. Open questions
Benchmark spec, tool timings, power methodology unknown. Blog claims not independently verified.

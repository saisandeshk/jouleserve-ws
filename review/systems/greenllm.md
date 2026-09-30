# GreenLLM — SLO-aware phase-separated DVFS for prefill/decode

- **Source:** GreenLLM: SLO-Aware Dynamic Frequency Scaling for Energy-Efficient LLM Serving; first author not captured in my extraction (verify); arXiv preprint, 2025; arXiv 2508.16449
- **Review depth:** partial — arXiv HTML via a summarizing fetch (method, hardware, workloads, headline numbers). No appendix/code read.
- **Category:** energy-aware serving
- **Code/artifacts:** no code statement found. Built on NVIDIA Dynamo v0.3.1 with TensorRT-LLM. Traces used: Alibaba ServeGen chat trace and Azure 2024 (both public, downsampled).

## 1. Summary
- Splits requests by length (prefill split), then picks SM clock separately for prefill (per request/batch optimization) and decode (dual-loop controller). Up to 34% total energy reduction vs the default NVIDIA governor on Azure traces with Qwen3-14B (10 to 34% across workloads); TTFT pass 94 to 100%, TBT pass 90 to 100%, under 3.5% additional violations.
- Decode energy 0.63 to 0.71x default (Qwen3-14B) and 0.64 to 0.80x (Qwen3-30B-MoE).

## 2. Problem and key insight
- Default DVFS drives high clocks under load. Prefill is compute-bound (latency about inverse in frequency), decode memory-bound (energy saved at lower clock with small TBT cost). Different clocks per phase, within SLO slack.

## 3. Workloads
- Alibaba ServeGen chat at 1, 3, 5, 8, 10 QPS; Azure 2024 at 1/8 and 1/5 of original rate; microbenchmarks (prefill 256 to 1024 token prompts at 200 to 30,000 TPS; decode 256 to 1024 tokens at 200 to 3000 TPS).
- Single-turn chat. Models: Qwen3-14B dense, Qwen3-30B-A3B MoE. Hardware: DGX-A100 (8x A100 40 GB), one node.

## 4. Assumptions
- Latency inversely proportional to clock; power cubic in clock; single-node; SLO TTFT under 400 ms (2 s long), P95 TBT at most 100 ms.
- Application clocks settable (root); memory clock pinned, autoboost off. Prefill and decode disaggregated.

## 5. Controller / mechanism
- **Prefill:** minimize energy s.t. TTFT with a queueing-aware model; quadratic latency fit t = aL^2 + bL + c; cubic power fit; clocks 210 to 1410 MHz.
- **Decode:** dual loop. Coarse: 200 ms TPS window mapped to a clock band via offline LUT (needs three consecutive intervals for hysteresis). Fine: 20 ms P95-TBT tracking with 15 MHz steps.
- Energy: NVML; active vs idle energy separated; profiled at reference clock (1410 MHz) then modeled **[paper]**. Sampling rate not stated.

## 6. Evaluation and reported results
- Baselines: DefaultNV, PrefillSplit (routing only). Results above.

## 7. What JouleServe-WS can take
- Measurement: active vs idle split, per-phase energy. Adopt: report prefill energy and decode energy separately using NVML cumulative counter differences around phases (SGLang metrics give timing).
- Their decode LUT idea (TPS bucket to clock) is a baseline only where clocks are settable; on A5000 no-root not reproducible. We can reproduce the analysis, not the control: run a workload sweep at concurrency levels and report energy/token vs batch.
- Baseline priority: optional (only as related-work comparison or if Prof. gives root on one GPU).

## 8. What JouleServe must add beyond it
- Multi-turn agent sessions and paused state; task-level SLO; long idle intervals (tool waits) where the relevant power is idle power not decode clock; hybrid models.

## 9. Workstation -> edge
- Orin/Thor clock levels are few, changed by nvpmodel/devfreq (root, slow), so a 20 ms control loop cannot exist. Decode on unified memory is bandwidth-bound and shared with CPU tools, so the decode-clock-insensitivity assumption may hold even better, but DRAM/EMC frequency (devfreq) is the more relevant knob. Board rails include CPU and DRAM.

## 10. Relevance to our current findings
- Our runs are decode-dominated (prefill 1 to 8%), which is exactly GreenLLM's favorable regime for decode DVFS; thinking-model long decode makes the P95 TBT SLO the binding constraint. But the SLO in agents is task time, so slack is larger than 100 ms TBT suggests.

## 11. Open questions / uncertainty
- Authors, code, sampling rate unverified. Whether TensorRT-LLM/Dynamo prefill/decode disaggregation assumptions matter for SGLang is unclear.

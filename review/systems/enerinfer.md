# EnerInfer — energy/throughput/thermal-aware DVFS control for on-device LLM decoding

- **Source:** EnerInfer: Energy-Aware On-Device LLM Inference; Bohua Zou, Nian Liu, Binqi Sun, ... Haibo Chen; arXiv preprint, June 2026 (submitted 22 Jun, rev. 24 Jun); https://arxiv.org/abs/2606.23001 (HTML: https://arxiv.org/html/2606.23001)
- **Review depth:** full text via arXiv HTML, read through a fetch-and-summarize tool (not verbatim). Appendices and exact table/figure numbers not independently checked; figures below are as extracted. Treat table/figure locations as unverified.
- **Category:** energy-aware serving; edge/on-device
- **Code/artifacts:** None public found. Integrated into an in-house LLM serving framework (phones/laptop) and RKLLM (Orange Pi) **[paper]**.

## 1. Summary
Controller that sets NPU and DDR (memory) frequency during token generation. Uses learned predictors of throughput and power (no per-model profiling on new models) to choose the lowest-energy frequency pair that still meets a QoE (tokens/s) target. Switches to model-predictive thermal control when shell temperature nears threshold. Claims up to 65% energy-efficiency gain on a phone, 12% laptop, 24% dev board **[paper, abstract]**.

## 2. Problem and key insight
- Insight: user reads/listens at ~4.8/3.3 tokens/s, so max-clock decode is wasteful; lowering NPU/DDR clocks keeps QoE while cutting energy and heat **[paper]**.
- Decode is memory-bound, so memory frequency matters as much as compute frequency. Joint (NPU, DDR) search space; predictors avoid exhaustive profiling.

## 3. Workloads
- Single-user chat/text-polish style generation, not agents. Models: LLaMA2-1.3B/7B, LLaMA3-3B, Qwen2-1.5B, Gemma2-2B, Pangu-pi; 300 synthetic models (varied hyperparameters) used to train predictors **[paper]**.
- Hardware: high-end phone, mid-tier phone, laptop (FP16), Orange Pi 5 Pro (Mali-G610, RKLLM). **No Jetson.**
- No tool waits, no multi-session concurrency, no KV retention.

## 4. Assumptions
- QoE = decode tokens/s floor, TTFT via max prefill frequency. Frequencies exclusively controllable (custom memory governor via PM-QoS-like voting; direct NPU freq) — needs privileged/vendor access.
- Room-temperature operation; component-level power not measurable on production devices (so power is predicted) **[paper]**.
- ~300 model profiles (~5 min each) needed to port to a new platform.

## 5. Controller / mechanism
- Predictors: random forests for peak throughput, scaled throughput (adds NPU/DDR freq), and power (inputs: 6 LLM hyperparameters + parameter count [+freqs]); thermal via linear regression on 20 s shell-temperature history plus predicted power **[paper]**.
- Accuracy: throughput MAPE 2.3-4.2%, power MAPE 1.5-2.2%, Kendall tau 0.90-0.96 (0.65 on the board), temperature MAE 0.16 C over 1-21 s horizon, R^2 0.988 **[paper]**.
- Bi-modal: energy mode normally; MPC thermal mode near threshold. dt=1 s, horizon N=21 steps; callback-based frequency updates during generation, event-triggered updates **[paper]**.

## 6. Evaluation and reported results
- Baselines: Default (max clocks/on-demand), Oracle, Deadline (minimum freq meeting speed), Ener (no thermal).
- Energy efficiency gain: 50-65% high-end phone; 26-27% mid phone; 10-15% laptop; 9-24% board. End-to-end device energy saving 4.2-11%. Thermal: 32.1% longer before threshold, 27.9% more tokens **[paper]**.
- Power measurement: in-house ADC monitor across shunt resistors per component (phone/laptop); FNIRSI FNB58 USB meter for total board power with idle subtracted (Orange Pi) **[paper]**.

## 7. What JouleServe-WS can take
- Methodology only: "energy-per-token at QoE floor" framing; the Deadline baseline (lowest freq meeting a speed target) is a cheap comparator.
- On A5000 without root, `nvidia-smi -lgc` is unavailable, but `nvidia-smi -pl` may or may not be; NVML clock queries work. EnerInfer's controller itself is **not** reproducible on WS (needs memory-clock control; A5000 GDDR6 clocks are not user-settable in practice **[inferred]**).
- Thermal predictor (linear regression on short history) is portable as a design; needs GPU temperature (NVML) rather than shell temp.

## 8. What JouleServe must add beyond it
Agent sessions, tool-wait idle attribution, retained-state decisions, task-level energy, multi-session batching. EnerInfer assumes a continuously decoding single stream; during tool waits the controller has nothing to do.

## 9. Workstation → edge
- Jetson has devfreq for GPU/EMC, nvpmodel, jetson_clocks; INA3221 rails give measured (not predicted) power, removing EnerInfer's main obstacle. Sampling is coarse (tens-hundreds ms) **[inferred]**.
- Jetson EMC freq is the direct analogue of DDR freq: highly relevant because unified DRAM is shared with co-located tools/sims.
- Port of predictors: retrain on Orin/Thor with ~hundreds of profile runs; hybrid models (GDN, SWA) not in training set.

## 10. Relevance to our current findings
Decode-dominated reasoning agents (P1) make decode-time frequency/EMC scaling the largest energy lever, more than KV retention (0.3-1.7% best case). EnerInfer's "slow decode is fine if throughput floor is met" maps to task-level SLOs with 13-115 s tool waits. Its long-thinking-decode case is not evaluated.

## 11. Open questions / uncertainty
- Board result is weak (Kendall tau 0.65); Mali/RK3588 differs from Jetson.
- No code; numbers unverified against tables. Whether idle/tool time is handled: not addressed.

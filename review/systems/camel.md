# Camel — Thompson-sampling bandit over GPU frequency x batch size to minimize EDP on Jetson AGX Orin

- **Source:** Camel: Energy-Aware LLM Inference on Resource-Constrained Devices; Hao Xu, Long Peng, Shezheng Song, ... Xiaoguang Mao; arXiv preprint (cs.NI), Aug 2025; https://arxiv.org/abs/2508.09173 (HTML https://arxiv.org/html/2508.09173)
- **Review depth:** full text via arXiv HTML through a fetch-and-summarize tool; details below are as extracted, not verbatim; table/figure numbers not verified.
- **Category:** energy-aware serving; edge/on-device
- **Code/artifacts:** none found/mentioned. Engine: llama.cpp **[paper]**.

## 1. Summary
Online bandit picks (GPU frequency, batch size) arms to minimize weighted energy-delay cost. Reports 12.4-29.9% EDP reduction vs default configuration on AGX Orin **[paper, abstract]**.

## 2. Problem and key insight
Optimal (freq, batch) differs per model and arrival rate; grid search is expensive. Higher clocks cut time but raise power; bigger batches raise throughput but add queueing wait. Latency decomposed as queue wait (b-1)/(2*lambda) + batch processing time **[paper]**.

## 3. Workloads
- Alpaca prompts, 1 s request interval, max 70 output tokens; Qwen2.5-3B and Llama3.2-1B, Q5_K_M; Jetson AGX Orin 32 GB **[paper]**.
- Not agentic: no tools, no multi-turn, no context growth, tiny outputs.

## 4. Assumptions
- Stationary request rate; cost signal per batch observable; frequency settable via sysfs (root). Short outputs so batching delay dominates. Thermal state not modeled.

## 5. Controller / mechanism
- Arms: 7 GPU freqs (306-930.75 MHz) x batch sizes 4-28 step 4 (42 arms). Hierarchical Gaussian: cost ~ N(theta, s1^2), theta ~ N(mu, s2^2); conjugate posterior updates, Thompson sampling **[paper]**.
- Cost = alpha*energy + (1-alpha)*latency (EDP-style). Control: `/sys/class/devfreq/` for GPU frequency; power sampled at 100 ms **[paper]**. Rail source (INA3221/tegrastats/jtop) not confirmed in my extraction; switch latency not reported.

## 6. Evaluation and reported results
- 12.4-29.9% EDP reduction vs default; vs grid search 49.45% (Llama3.2-1B) and 35.75% (Qwen2.5-3B) EDP improvement (as extracted; the "vs grid search" framing is likely about search cost/regret, verify). Best arms: (816 MHz, b=20) for Llama, (930.75 MHz, b=24) for Qwen **[paper]**.
- Note max listed freq 930.75 MHz is below Orin's max GPU clock (~1.3 GHz), so "default" may be constrained; verify.

## 7. What JouleServe-WS can take
- Bandit skeleton is small and reproducible; on A5000 the frequency knob is unavailable without root, so use knobs that are available: max batch/running requests, chunked-prefill size, admission cap (SGLang `--max-running-requests`, `--chunked-prefill-size`), power limit if permitted. Thompson sampling over these arms is a reasonable "tuned static" baseline.
- Measurement: 100 ms power sampling + EDP cost; on WS use NVML `nvmlDeviceGetTotalEnergyConsumption` (millijoule counter) instead.

## 8. What JouleServe must add beyond it
Task-level (not request-level) objective, retained-state actions, non-stationary agent arrivals, tool-wait idle energy attribution, thermal constraint, hybrid/long-context models. Camel's contextual-free bandit ignores state (context length, pending tool calls).

## 9. Workstation → edge
Directly Jetson: devfreq GPU control needs root/jetson_clocks; nvpmodel modes cap max clocks and CPU cores (see Arya & Simmhan doc). Real batches on edge agents are 1-4, so Camel's batch 4-28 range is outside our regime. Frequency-switch latency and thermal throttling override the sysfs setting under sustained load **[inferred]**.

## 10. Relevance to our current findings
Decode-dominated P1 runs: EDP lever is frequency during long decode with small batch; Camel's batching lever is weak for single-session drones. Useful as a "static frequency tuned per model" baseline.

## 11. Open questions / uncertainty
Rail/sampling details, baseline definition, and switch cost unconfirmed; no code; small models only.

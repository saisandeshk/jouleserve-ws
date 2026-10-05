# CarbonCall — carbon-aware function calling on Jetson AGX Orin with dynamic tool selection and runtime switching among quantized model variants

- **Source:** CarbonCall: Sustainability-Aware Function Calling for Large Language Models on Edge Devices; Varatheepan Paramanayakam, Andreas Karatzas, Iraklis Anagnostopoulos, Dimitrios Stamoulis; arXiv:2504.20348 v2 (cs.PF), 2 May 2025; venue not stated in the text I read
- **Review depth:** partial: abstract, method text (two-column PDF extracted, partly garbled), evaluation summary text. Per-figure numbers not read.
- **Category:** edge/on-device; energy-aware; runtime lever selection (weights, tools, power mode)
- **Code/artifacts:** no repo link found.

## 1. Summary
- Extends Less-is-More with (a) embedding + cross-encoder + NER tool selection with an adaptive number of tools, (b) a power-mode lookup table chosen from a 24-hour carbon-intensity forecast (Orin nvpmodel-like modes), (c) switching to a more heavily quantized LLM when tokens/s falls below 80% of the initial value. [paper]
- Abstract: up to 52% less carbon, 30% less power, 30% less execution time on a Jetson AGX Orin. Text: on average power -28%, time -30%, carbon -52%, TPS +25% versus default. [paper]

## 2. Problem and key insight
- Carbon intensity varies over time so minimum energy is not minimum carbon; combine tool reduction with power caps and model switching.

## 3. Workloads
- BFCL + GeoEngine random mix; Hermes2-Pro-8B, Llama3.1-8B, Qwen2-7B in several GGUF quantizations; Jetson AGX Orin; multi-week simulated CI traces. Single function calls / short dependent calls. [paper]

## 4. Assumptions
- Known CI forecast; model variants preloaded (memory for several variants); throughput threshold as the proxy for "pressure".

## 5. Controller / mechanism
- Inputs: CI forecast, TPS monitor, query. Actions: power mode (LUT), model quantization level (weights), tool subset. Updates when CI changes by >=10% of range to avoid oscillation. The trigger for quantization is throughput, not memory occupancy, and quantization is of weights not KV cache. [paper]

## 6. Evaluation and reported results
- Baselines: Default, Less-is-More (LiS), Gorilla-like. vs LiS: up to 47% less carbon, 14% less power, up to 20% better time. A "manageable TPS deficit in some cases". [paper]

## 7. What JouleServe-WS can take
- The run-time switching skeleton and the hysteresis rule. Only the tool-selection part is portable to the workstation; the power-mode part belongs to Jetson only.

## 8. What JouleServe must add beyond it
- KV-pool occupancy as the trigger; KV precision and context budget as actions; multi-agent concurrency; success measured over multi-turn tasks.

## 9. Workstation -> edge
- Already Orin. Switching weight variants is costly in unified memory (reload time and double residency); not an option for 26B models on Orin 64. [inferred]

## 10. Relevance to our current findings
- The only found edge work that picks a quantization level at run time. Shows that "run-time lever selection" has precedent for weights and tools; not for KV precision or context.

## 11. Open questions / uncertainty
- No venue confirmed; check whether switching overhead is counted; check per-figure numbers.

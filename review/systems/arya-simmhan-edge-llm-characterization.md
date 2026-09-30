# Arya & Simmhan — Understanding the Performance and Power of LLM Inferencing on Edge Accelerators (Jetson AGX Orin 64GB)

- **Source:** Understanding the Performance and Power of LLM Inferencing on Edge Accelerators; Mayank Arya, Yogesh Simmhan (IISc); PAISE 2025 (IPDPS workshop); https://arxiv.org/abs/2506.09554
- **Review depth:** full text via arXiv HTML through a fetch-and-summarize tool; numbers as extracted, section/table numbers not verified.
- **Category:** edge/on-device; workload/benchmark (characterization)
- **Code/artifacts:** not confirmed.
- Note: co-authored by our advisor's group; use as measurement precedent.

## 1. Summary
Characterizes latency, throughput, perplexity, power and energy of LLM inference on Orin AGX 64GB across models, batch size, sequence length, quantization and custom power modes.

## 2. Problem and key insight
Edge behavior differs from datacenter: memory frequency and memory capacity dominate; quantization can slow small models (dequant overhead).

## 3. Workloads
Phi-2 2.7B, Llama-3.1-8B, Mistral-Small-24B, DeepSeek-R1-Distill-Qwen-32B; batch 1-128, seq 128-1024; WikiText2, LongBench; FP32/FP16/INT8/INT4 (bitsandbytes). Non-agentic, offline batches.

## 4. Assumptions
Batch experiments, no tools, no concurrency with other processes.

## 5. Controller / mechanism
None (characterization). Nine custom nvpmodel-style power modes varying GPU freq (400-1301 MHz), CPU freq (1.2-2.2 GHz), cores (4-12), memory freq (665-3200 MHz) **[paper]**.

## 6. Evaluation and reported results
- Power via `jtop`, sampled every 2 s, trapezoidal integration per batch **[paper]** (coarse: cannot resolve sub-2 s phases like prefill).
- Phi-2 INT8: RAM -46% but 62% slower than FP16. Llama3.1 seq 128->1024: throughput 271->107 tok/s, latency 15 s->305 s. Low memory-frequency mode (PM-H): latency +370% vs MAXN, energy +72% while power -52% **[paper]**.
- Memory constraints limit large-model batch sizes (OOM behaviour detail not extracted).

## 7. What JouleServe-WS can take
Measurement recipe (jtop, power-mode grid), and the finding that EMC frequency is the key energy knob; baseline "power mode sweep" for the edge phase.

## 8. What JouleServe must add beyond it
Agent sessions, KV retention, concurrency, idle attribution, higher-rate power sampling (INA3221 is read via sysfs at faster rates than 2 s; tegrastats interval down to ~ms-scale **[inferred]**).

## 9. Workstation → edge
This is the edge data: 2 s sampling too coarse for tool-wait accounting; tool waits of 13-115 s are fine at 2 s, but per-call energy is not.

## 10. Relevance to our current findings
Long decode is memory-bound, so EMC/power mode dominates energy per task for P1 reasoning agents.

## 11. Open questions / uncertainty
Whether thermal throttling appears in runs; no agent workload.

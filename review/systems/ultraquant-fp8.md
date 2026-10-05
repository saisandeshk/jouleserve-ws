# UltraQuant and the vLLM FP8 KV study — 4-bit and 8-bit KV cache for context-heavy agents

- **Source A:** UltraQuant: 4-bit KV Caching for Context-Heavy Agents; Inesh Chakrabarti, David Limpus, Aditi Ghai Rana, Bowen Bao, et al. (AMD); arXiv:2606.20474 v3 (cs.LG), 11 Sep 2026.
- **Source B:** The State of FP8 KV-Cache and Attention Quantization in vLLM; Jonas Kübler, Eldar Kurtić, Lucas Wilkinson, et al.; vLLM blog, 22 Apr 2026; https://vllm.ai/blog/2026-04-22-fp8-kvcache (not peer reviewed).
- **Review depth:** A: PDF text extracted locally, read abstract, Sec 3, 6 and Table 2; kernels not read. B: blog read through the fetch tool's extraction only (partial).
- **Category:** KV substrate (quantization), datacenter agentic serving
- **Code/artifacts:** A: kernel "planned"; Ultra-TQ decode kernel upstreamed into vLLM mainline (per paper). B: in vLLM mainline.

## 1. Summary
- A: TurboQuant-style 4-bit KV (Hadamard rotation, asymmetric K/V) as quality anchor; vLLM FP8 KV as deployment anchor; on AMD MI355X, an FP4-approximation path. On adaptive-SLO replay of production Claude Code traces, 2.71x (MiniMax-M2.5) and 4.38x (Qwen3-235B) the qualified-request throughput of BF16, matching or exceeding FP8 at half the KV bytes. [paper, abstract]
- B: FP8 KV gives at most 1-2 points loss on reasoning (97-99% recovery on AIME25, GPQA, MATH500, LiveCodeBench for Qwen3-30B-A3B-Thinking); and a bug found: FP8 FlashAttention-3 on Hopper had needle-in-haystack falling from 91% to 13% at 128K until accumulation precision was fixed. [blog, as extracted]

## 2. Problem and key insight
- Long prefixes reused across many turns make KV capacity the throughput limiter for agents. Quality must be judged on multi-turn agent loops.

## 3. Workloads
- A: SWE-bench Lite fixed 100-task cohort (Table 2): MiniMax-M2.5 BF16 62, FP8 62, Ultra-TQ 61, UltraQuant 59; Qwen3-235B BF16 28, FP8 21, Ultra-TQ 27, UltraQuant 24. Also GPQA Diamond, GSM8K, AIME25 (within 2 points of BF16 except one model), RULER (MiniMax 74.03 vs 67.08 at one setting; per paper text), Gutenberg multi-turn serving. First and last two layers kept BF16 in KV-compressed runs. [paper, Sec 6]
- Caveat: 100 tasks, so a 21 vs 28 gap on Qwen is within plausible noise but is also a warning that FP8 is not always "free". [inferred]
- B: Llama-3.1-8B, Llama-3.3-70B, gpt-oss-20b, gemma-4-E2B, Qwen3-30B-A3B, Qwen3.5-27B, Kimi-K2.5; H100/B200/H200. No tool-calling benchmark.

## 4. Assumptions
- Large GPUs; high concurrency; FP8 helps when contexts exceed about 7K tokens (break-even), and recommended off for contexts below 7K, head_dim 256 prefill slowdown (1.6x), and hybrid sliding-window layers (`--kv-cache-dtype-skip-layers`). [blog]

## 5. Controller / mechanism
- Static dtype selection per deployment; no run-time switching.

## 6. Evaluation and reported results
- B, Hopper, Llama-3.1-8B under load (150 requests, concurrency 8): +14.9% throughput, -14.8% median ITL. [blog]

## 7. What JouleServe-WS can take
- FP8 KV is the practical baseline on SGLang (`--kv-cache-dtype fp8_e4m3`, per-tensor scales; docs warn it can be very slow when dequantization is not fused). Their quality protocol (reasoning + long-context + one agent benchmark) is a template. The 7K break-even matters: P1 windows are 12K, so gain is marginal in latency but the capacity effect remains.

## 8. What JouleServe must add beyond it
- Energy per successful task on Jetson; hybrid models (gemma-4 sliding window, Qwen3.8 DeltaNet): FP8 benefit is small on sliding-window layers per the blog; run-time precision choice.

## 9. Workstation -> edge
- Orin is Ampere (sm_87): no native FP8 attention; a fused kernel may not exist; Thor (Blackwell) supports FP8/FP4. **[inferred]; test before assuming the "2x pool" from FP8.**

## 10. Relevance to our current findings
- Supports the premise "double the pool ~ FP8" in quality terms for 20B+ models, with the exception that the only agent-level result (SWE-bench Lite) shows variance.

## 11. Open questions / uncertainty
- Venue of A not stated; AMD hardware; the Qwen FP8 result of 21/100 is unexplained in my read.

# agent-memory — persistent 4-bit KV cache per agent for multi-agent LLM inference on a unified-memory edge device

- **Source:** Agent Memory Below the Prompt: Persistent Q4 KV Cache for Multi-Agent LLM Inference on Edge Devices; Yakov Pyotr Shkolnikov; arXiv preprint 2603.04428 (v1, 17 Feb 2026, cs.LG); https://arxiv.org/abs/2603.04428 ; code https://github.com/yshk-mxim/agent-memory (stated in abstract; repo not opened).
- **Review depth:** partial text via pdftotext (abstract, §1, design, setup, TTFT results, vllm-mlx comparison); not read in full; code not inspected.
- **Category:** edge/on-device; agentic KV retention (disk-persistent)
- **Code/artifacts:** open source per abstract **[paper]**; built on MLX (mlx-lm 0.30), OpenAI-compatible API.

## 1. Summary
On an Apple M4 Pro (24 GB unified, ~10.2 GB cache budget) only 3 agents at 8K context fit in FP16. The system saves each agent's KV to SSD in Q4, reloads it directly into attention on resume, and overlaps reload with another agent's decode. TTFT falls up to 136x versus re-prefill. **[paper abstract, §1]**

## 2. Problem and key insight
- Evicting an agent costs a full re-prefill: 15.7 s at 4K context on Gemma 3 12B (about 260 tokens/s prefill on M4 Pro, ~40x slower than datacenter GPUs) **[paper §1]**.
- Q4 KV is 4x smaller (Gemma 3: 1,536 MB FP16 vs 432 MB Q4 at 4K) so 4x more agent contexts fit; multi-agent interleaving hides reload latency behind another agent's decode **[paper §1, §3]**.

## 3. Workloads
- Multi-agent workflows with isolated per-agent caches; contexts 1K-32K; Gemma 3 12B, DeepSeek-Coder-V2-Lite 16B (MoE, MLA), Llama 3.1 8B **[paper abstract]**. Benchmarks are synthetic TTFT sweeps (median of 3-6 passes), not tool-calling traces with real waits.
- Hardware: MacBook Pro M4 Pro, 24 GB LPDDR5X, 273 GB/s; SSD ~7 GB/s read **[paper §4]**.

## 4. Assumptions
- A **fixed** cache budget (24 GB - 6.8 GB weights - 7 GB OS/system = 10.2 GB) **[paper §1]**; the OS share is treated as constant.
- Fast SSD; single scheduler thread (MLX is not thread-safe), so effectively batch 1-2.
- Which agent runs next is known from the workflow order (interleaving).

## 5. Controller / mechanism
- Block pool with per-agent isolated Q4 KV in safetensors; BatchQuantizedKVCache for concurrent inference; "cross-phase context injection" reusing attention state across phases; hot (memory) and warm (disk) states **[paper abstract, §3]**.
- No eviction-policy research: evict-to-disk and reload on demand.

## 6. Evaluation and reported results
- TTFT reduction up to 136x (Gemma 22-136x at 4K-32K; DeepSeek 11-76x; Llama 24-111x at 4K-16K, 3-10x at 1K) **[paper abstract]**. Warm 4K Gemma: 577 ms, hot 719 ms vs 15.7 s cold **[paper §1]**.
- Perplexity with Q4 KV: -0.7% (Gemma), +2.8% (Llama), +3.0% (DeepSeek) **[paper abstract]**.
- vs vllm-mlx: FP16 prefix cache "fails under realistic multi-agent memory pressure", needing per-context server isolation at 8K+ and failing at 16K **[paper abstract, §4.4]**. Cold prefill is 2.3x faster in vllm-mlx at 4K (4,394 vs 10,235 ms) **[paper §4.4]**.
- No energy numbers.

## 7. What JouleServe-WS can take
- Reload-hidden-behind-decode overlap and Q4/FP8 KV as the capacity lever; the 4x capacity argument matches our simulator finding that FP8 KV recovers 10-34% under tight memory **[HANDOFF.md, our sim]**.
- A baseline for "evict to disk and reload" when the memory budget drops.

## 8. What JouleServe must add beyond it
- Time-varying budgets; knowledge of tool-wait length and of the burst; energy per task; a serving engine with real batching; hybrid-model state.

## 9. Workstation -> edge
- Already unified memory; Apple Silicon not Jetson, MLX not CUDA. On Orin/Thor an equivalent needs SGLang/llama.cpp hooks and NVMe. Same "host tier gains no capacity" point as mzCache.

## 10. Relevance to our current findings
- Supports the point that on small pools capacity, not policy, binds (P1 traffic simulation: gap to unlimited 33-64% at 8 agents), and that persisting state is cheap relative to recompute only when prefill is slow (Apple 260 tok/s). On Orin/Thor prefill is faster, so P1's measured prefill share (0.7-3.4% of board energy) limits the gain **[inferred]**.

## 11. Open questions / uncertainty
- Single-author preprint; no peer review found; code not checked. Memory pressure is static, so the title's "pressure" is capacity, not time-varying external demand.

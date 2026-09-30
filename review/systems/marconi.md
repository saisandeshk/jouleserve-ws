# Marconi — prefix-cache admission and FLOP-aware eviction for hybrid (Attention + SSM) LLMs

- **Source:** "Marconi: Prefix Caching for the Era of Hybrid LLMs"; Rui Pan, Zhuang Wang, Zhen Jia, Can Karakus, Luca Zancato, Tri Dao, Yida Wang, Ravi Netravali; MLSys 2025 (venue verified on the arXiv page); arXiv 2411.19379; code and traces: github.com/ruipeterpan/marconi (CC BY-NC per fetched summary, plus a Zenodo archive)
- **Review depth:** full text (arXiv HTML via fetch: problem, taxonomy, admission, eviction, evaluation, limitations). Not read: appendix derivations, repo code.
- **Category:** hybrid-model caching
- **Code/artifacts:** simulator-style prefix-cache implementation released with traces; built on an SGLang-like radix tree. Non-commercial license (CC BY-NC) limits reuse in a product; fine for research baselines.

## 1. Summary
- Prefix caching for hybrid models is hard because SSM state is updated in place and can only represent the *whole* prefix it was computed on; a partial overlap cannot reuse it (all-or-nothing). Naive fine-grained checkpointing (vLLM at 32-token blocks) creates huge, rarely hit entries that thrash memory. [paper §1-2]
- Marconi adds (1) **judicious admission**: checkpoint SSM state only at radix-tree branch-off points (shared "purely input" prefixes) and at the last decoded token ("input+output"), about 2 states per sequence; and (2) **FLOP-aware eviction**: utility `S(n) = recency(n) + alpha * flop_efficiency(n)`, flop_efficiency = FLOPs saved / bytes of state held. [paper §4]
- Reported: 4.5-34.4x higher token hit rate vs vLLM+ (up to 34.4x; abstract says "up to 71.1% or 617 ms lower TTFT"), and 19.0-219.7% higher hit rate than LRU-based SGLang+ [paper].

## 2. Problem and key insight
- Taxonomy of hit scenarios: **purely-input** reuse (system prompt, few-shot, instructions) vs **input+output** reuse (conversation history, agent trajectory). Different admission is needed for each.
- State size asymmetry: KV grows with length; SSM state is constant per sequence. Paper's example: a 10K-token sequence in a 7B hybrid holds 17.4 GB of state, 3.3x the Transformer equivalent (as reported; the exact accounting, per-sequence or per-cache, should be re-checked in the PDF).
- FLOP efficiency: for a 7B hybrid, SSM layers save about 200xL FLOPs per byte, Attention about (L+8192) per byte, so long sequences give disproportionately more savings per byte and should be retained preferentially over short ones (trade: up to 3.0% hit-rate loss on short sequences) [paper].

## 3. Workloads
- **LMSys** (multi-turn chat with long outputs), **ShareGPT** (multi-turn, short outputs), **SWEBench** (agentic software engineering). SWEBench is the only agentic one; tool pauses are not modeled: it is a cache-hit-rate study on token sequences, not a timing study [paper §5; inferred for pauses].
- Models: a 7B hybrid with {4 Attention, 24 SSM, 28 MLP} layers (1:6 attention:SSM); Jamba-1.5-Mini (12B active) for TTFT. Hardware: AWS p4d.24xlarge, 8xA100-40GB. Baselines: vLLM+ (32-token block checkpoints), SGLang+ (radix tree + LRU), vanilla.
- Traces public in the repo.

## 4. Assumptions
- Datacenter GPU memory pool as the cache; many concurrent sequences; objective is token hit rate and P95 TTFT. No CPU/SSD tier, no energy, no thermal.
- Sequence-level reuse structure is unknown in advance; branch points are learned online by speculative insertion into the tree before prefill.
- Requires either chunked state passing (materialize the second-to-last chunk) or a two-pass prefill (extra cost) to get the SSM state exactly at a branch point; the second occurrence of a purely-input prefix is a miss (checkpoint made then, used from the third) [paper limitations].
- Holds fixed: model, kernel, fixed cache size (evaluated across sizes).

## 5. Controller / mechanism
- **Admission:** speculative radix insertion of the incoming sequence to detect a new branch-off node; checkpoint there and at the end. "Reduces admitted SSM states from potentially hundreds per sequence to approximately two." [paper]
- **Eviction:** consider nodes with at most one child (intermediate nodes as well as leaves); do not refresh ancestor timestamps on a hit; score `recency + alpha*flop_efficiency`; `alpha` is grid-searched during a bootstrap window of 5-15x the initial evictions, parallelized on CPU (seconds, under one request's prefill/decode) [paper].
- One unified tree manages KV and SSM state together.
- Implementation: replays traces in a simulator plus GPU kernels for TTFT; no released vLLM/SGLang patch known [unverified].

## 6. Evaluation and reported results
- Token hit rate: 4.5-34.4x over vLLM+; 19.0-219.7% over SGLang+ (LRU) [paper].
- P95 TTFT: vs vanilla up to 36.9%/73.2%/46.8% (281-617 ms) across three datasets; vs vLLM+ 36.1%/71.1%/46.8% (103-617 ms).
- Limit: only 2 states per sequence reduces coverage for arbitrary prefix reuse; gains fade when cache is large or reuse is low.

## 7. What JouleServe-WS can take
- **Retention score for hybrids (should):** value of a retained node = recomputation FLOPs saved (or joules) divided by bytes held; this generalizes cleanly to an energy score (joules saved per byte). Use `flop_efficiency` as a baseline utility next to LRU/priority in a JouleServe simulator.
- **Admission rule (should, offline first):** only checkpoint recurrent state where a branch is known to exist. SGLang's `extra_buffer` (see `sglang-kv.md`) instead checkpoints on a fixed grid, so Marconi is the natural "smarter admission" comparison. Cheap sketch on 0.5.20: log per-turn shared-prefix lengths from a trace, then set `--mamba-track-interval` and `--mamba-max-states-per-path` per workload; true branch-point admission needs a scheduler patch (see `sglang-kv.md` §hooks).
- Methodology: replay recorded traces through a cache simulator first (cheap), then validate on the engine.
- Traces: LMSys/ShareGPT/SWEBench-derived, released in the repo.

## 8. What JouleServe must add beyond it
- Time dimension: Marconi has no notion of pause length, tool wait, or session lifetime; JouleServe needs an expected-return-time term (retain only if the session will return before the state would be evicted anyway).
- Objective: joules and SLOs instead of hit rate/TTFT; account for prefill being 1-8% of time in decoding-dominated agents, where hit-rate wins are irrelevant.
- SWA (Gemma-4): Marconi only covers Attention+SSM; sliding-window state is a different bounded-state problem (window-sized, evictable prefix). No equivalent analysis.
- A tier decision (retain / offload / drop), not only admit/evict.

## 9. Workstation to edge
- The state-size finding is the edge-relevant one: recurrent state per sequence is big and fixed, so on a 32 GB Orin with a 27B model, a few retained Qwen3.8 states can cost as much memory as thousands of KV tokens. Whether that is worth holding is a direct FLOPs/byte question.
- No unified-memory or power assumptions; CC BY-NC code; A100 kernel behaviour will differ on Orin (Ampere sm_87) and Thor.

## 10. Relevance to our current findings
- Our traces reuse only 10-31% of a rebuilt prompt in the same session, and reuse is of the *prefix up to the first differing role text*. For hybrid models, reuse requires an SSM checkpoint exactly at the shared boundary; a per-role rebuilt prompt puts the divergence point early and unpredictable, which is the worst case for grid checkpointing and the best case for Marconi-style branch admission (the system prompt boundary is a stable branch point).
- Decode-dominated runs make the hit-rate gains nearly irrelevant to energy; expect Marconi-like admission to matter only under concurrency with shared system prompts.

## 11. Open questions / uncertainty
- Exact size accounting for the 17.4 GB example; verify in PDF.
- Whether the released code runs on real GPU kernels or only the simulator; not checked.
- How Marconi's branch-point detection maps onto SGLang's page/chunk grid (branch points need not be grid-aligned; SGLang requires alignment to `lcm(mamba chunk size, page_size)`).

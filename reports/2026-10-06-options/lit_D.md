# Option D literature review (task D-E3): memory that changes over time

Date: 2026-10-06 (written 2026-10-05/06). Scope: LLM serving when memory availability changes at run time; unified-memory and on-device LLMs; LLM plus perception/vision co-serving; tool-aware pinning and admission. Per-system docs for the five closest works are in `review/systems/`: `prism-kvcached.md`, `morphserve.md`, `llms-mobile-context.md`, `nova.md`, `agent-memory-below-prompt.md`. `mzcache.md`, `continuum.md`, `infercept.md`, `tokencake.md`, `kvflow.md`, `cachescout.md` already exist and were not redone.

## Review depth key
- **Read** = PDF text read (not all appendices). **Skim** = abstract plus selected sections. **Abstract** = abstract/search snippet only; claims limited to the abstract.

## Table of all works found

| Name | Venue / year | Link | What it does | Platform | Agent-aware? | Energy? | Closeness to D | Depth |
|---|---|---|---|---|---|---|---|---|
| Prism (+ kvcached) | arXiv 2505.04021 v3, Jun 2026 | https://arxiv.org/abs/2505.04021 ; https://github.com/ovg-project/kvcached | Memory ballooning: virtual-memory KV pools resized at run time across co-located models; two-level scheduling | Datacenter (H100/A100) | No (agentic pipelines only motivate) | No | High (mechanism); kvcached supports SGLang up to 0.5.20 | Read |
| MorphServe | arXiv 2506.02006 v2, Jan 2026 | https://arxiv.org/abs/2506.02006 | Pressure-aware KV block resizing plus runtime INT4 layer swap | Datacenter (L4, A100) | No | No | Medium-high (elastic KV on pressure; self-generated) | Read |
| Elastic KV Cache for LLM Serving: a working reclamation mechanism, and why chunked prefill already closes the gap | arXiv 2608.23658, Aug 2026 | https://arxiv.org/abs/2608.23658 | CUDA-VMM reclamation of prefill reserve for KV; negative result (~1% TTFT) | Datacenter GPU | No | No | Medium (caution on value of reclaiming) | Abstract + skim via summarizer |
| vAttention | ASPLOS 2025; arXiv 2405.04437 | https://arxiv.org/abs/2405.04437 ; https://github.com/microsoft/vattention | CUDA VMM so KV stays contiguous in virtual memory, physical pages on demand | Datacenter | No | No | Low-medium (substrate) | Abstract |
| MuxServe | arXiv 2404.02015 (venue not verified) | https://arxiv.org/abs/2404.02015 ; https://github.com/hao-ai-lab/MuxServe | Spatial-temporal multiplexing of several LLMs on a GPU group, placement by popularity | Datacenter | No | No | Low-medium | Abstract |
| Aqua | ASPLOS 2025; arXiv 2407.21255 | https://arxiv.org/abs/2407.21255 | Offloads inference context to neighbour GPUs over NVLink during bursts | Datacenter, 8xH100 | No | No | Low (burst response, needs NVLink) | Abstract |
| Aegaeon | SOSP 2025 | https://ennanzhai.github.io/pub/sosp25-aegaeon.pdf | Token-level model auto-scaling to pool GPUs across models | Datacenter | No | No | Low | Abstract |
| LLMS (LLM as a System Service) | arXiv 2403.11805 (Mar 2024); likely ACM version DOI 10.1145/3774906.3800479 (unverified, 403) | https://arxiv.org/abs/2403.11805 | Chunk-wise KV compression/swap/recompute for app contexts under a memory budget | Mobile + Jetson Orin NX, TX2 | No (multi-app, not tool pauses) | Partly (recompute energy as motivation) | Medium-high (edge, Jetson, KV swap; budget is static) | Read |
| mzCache | arXiv 2609.01338, Sep 2026 | https://arxiv.org/abs/2609.01338 | Elastic eviction/restoration of weights and KV under phone multitasking | Mobile | No | Yes (total energy) | High (co-tenant pressure on unified memory); existing doc | Existing doc |
| Agent Memory Below the Prompt (agent-memory) | arXiv 2603.04428, Feb 2026 | https://arxiv.org/abs/2603.04428 ; https://github.com/yshk-mxim/agent-memory | Per-agent persistent Q4 KV on SSD, reload hidden behind other agents' decode | Edge (Apple M4 Pro, unified) | Partly (multi-agent) | No | Medium (edge agents; static budget) | Skim |
| Nova | arXiv 2509.21301, Sep 2025 | https://arxiv.org/abs/2509.21301 | Agentic VLM serving: SM partitioning across vision/prefill/decode, vision-encoder weight offload to save KV space | Single GPU (A6000, 4090) | VLM GUI agents (single step) | No | Medium (vision-vs-KV contention) | Read |
| MORI | arXiv 2606.00866, May 2026 | https://arxiv.org/abs/2606.00866 | Ranks agent programs by idleness; busiest in HBM, idlest in CPU DRAM; admission control per tier; SGLang 0.5.10 | Datacenter | Yes (tool-call idle windows) | No | Medium (agent-aware tiering and admission; capacity static) | Skim (abstract, §1, setup) |
| Continuum | arXiv 2511.02230 | https://arxiv.org/abs/2511.02230 | Tool-aware KV pinning with TTL | Datacenter | Yes | No | Medium (pinning); existing doc | Existing doc |
| InferCept, TokenCake, KVFlow, CacheScout (2608.14624), Adaptive KV Retention | various | see existing docs | Agent-aware retention/prefetch | Datacenter | Yes | No | Medium-low | Existing docs |
| Echo (arXiv 2609.05635; an earlier search snippet called it "DejaVu"; PDF title is Echo) | arXiv Sep 2026 | https://arxiv.org/abs/2609.05635 | Removes redundant host-device copies on unified-memory SoCs | Jetson | No | Yes (copy energy) | Low (unified-memory substrate) | Skim |
| NeuroPrefetcher | arXiv 2608.22643, Aug 2026 | https://arxiv.org/abs/2608.22643 | Storage-backed sparse LLM when model exceeds memory; notes Jetson cannot satisfy large allocations when free memory < ~1 GiB and that host offload adds no capacity on Jetson **[paper, search snippet and text grep]** | Jetson | No | No | Low-medium (Jetson memory facts) | Skim |
| HoliBench | arXiv 2609.12412, Sep 2026 | https://arxiv.org/abs/2609.12412 | Benchmark toolkit; dual-FM perception-planning on Jetson AGX Orin 64; standalone profiles predict co-resident pipeline latency and power within 1.2% / 2.5% (sequential co-resident execution) **[paper abstract]** | Jetson, servers | No | Yes | Low-medium (co-located models, energy) | Skim |
| Edge-Inference Governors Need Memory-Clock State | arXiv 2606.16106 | https://arxiv.org/abs/2606.16106 | EMC-clock-aware DVFS governor for co-running models on Orin | Jetson | No | Yes | Low | Abstract (search snippet) |
| Profiling Concurrent Vision Inference Workloads on Jetson | arXiv 2508.08430 | https://arxiv.org/abs/2508.08430 | Concurrent vision model profiling, GPU memory and throughput | Jetson | No | Partly | Low | Abstract (snippet) |
| EPD (encoder disaggregation in SGLang); ElasticMM (2507.10069); TCM-Serve (2603.26498); HorizonServe (2608.01785) | blog/arXiv | https://www.lmsys.org/blog/2026-01-12-epd/ etc. | Multimodal request scheduling, separating the vision encoder from LLM workers | Datacenter | No | No | Low (relevant to a vision burst design) | Abstract |
| Strait (2604.28175) | arXiv Apr 2026 | https://arxiv.org/abs/2604.28175 | Priority- and interference-aware DNN serving | Datacenter/on-prem GPU | No | No | Low | Abstract |

## What is covered
1. **Run-time resizable KV memory exists**: kvcached/Prism (open, Apache-2.0, SGLang 0.5.20), MorphServe (KVResizer), vAttention, and the Elastic KV negative result. All treat the other memory consumers as other **models the scheduler controls** or the engine's own load.
2. **Unified-memory and on-device KV management under a budget**: mzCache (co-tenant pressure, phones), LLMS (Jetson Orin NX/TX2, budget sweeps), agent-memory (Apple unified memory, multi-agent). Budgets are fixed per experiment, except mzCache where other apps cause pressure (the phone case is closest to D).
3. **Vision vs KV contention**: Nova names it and answers with encoder weight offload and SM partitioning; EPD/ElasticMM-type systems separate encoders into other workers.
4. **Tool-aware pinning/tiering and admission for agents**: Continuum, InferCept, TokenCake, KVFlow, MORI (admission control per memory tier). All assume the capacity of each tier is constant.

## What is still open for P5 (our reading; searches not exhaustive)
- I found **no work** where an agent's tool launches model inference or other memory-taking work **on the same device or engine**, so that the serving system could know a memory burst is coming and pin the paused context or throttle the burst. Searches for this ("tool call launches model inference same GPU memory interference", "VLM tool calls inside agents") returned only Continuum-type pinning papers and Nova.
- No work evaluates **retention vs admission vs pool resizing** together when memory demand changes during an agent's run, on Jetson Orin/Thor.
- No energy-per-task analysis of time-varying memory (mzCache reports total energy per request on phones only).
- Hybrid-model state (sliding-window, recurrent) under shrinking memory: kvcached claims support, no policy work found.
- Untested: whether kvcached works on JetPack CUDA; whether SGLang radix eviction under a shrinking limit keeps paused agents.

## Novelty paragraph (option D)
Run-time elastic KV pools are not new: Prism/kvcached already resizes pools on demand and runs on SGLang 0.5.20, and MorphServe resizes the KV cache on pressure. Tool-aware pinning is not new either (Continuum, MORI). What I did not find is the combination: an edge serving policy that knows a tool will take memory (a vision burst, a co-located perception model, a simulator) and uses that foreknowledge to pin a paused session, admit the burst at lower concurrency, or resize the pool, judged by energy per successful task on unified-memory devices. Existing elastic-memory work reacts to load it schedules itself and measures SLO attainment in datacenters. The honest weakness is size: on P1's traffic agent the burst costs 0.6% of LLM time at one agent per device, controllers beat the default by at most 2.4-9.9% in simulation, and a 2026 paper reports that reclaiming memory inside one engine gave about 1% TTFT. Novelty is plausible; a large effect is not yet shown, and may exist only where pools are small and agents many. Search was by web queries and not exhaustive.

## Biggest risk
The effect may be too small to publish (P1 numbers above), and any real novelty hinges on P1's answer about `ask_vlm` (own server vs separate model), which decides whether the contention is inside one engine.

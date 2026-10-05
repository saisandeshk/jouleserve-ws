# Track B — prior-work review: index and synthesis

> **Notes from P1's measurements (2026-10-03/04).**
> - **Thermal.** P1 saw no thermal throttling in 392 h of agent runs at room temperature. Thermal-aware systems (TAWS, EnerInfer) matter here only for hot enclosures.
> - **Runaways.** P1's 32K-capped thinking calls are repetition loops under greedy decoding. So the prior work that bears on option A is reasoning-length control and early exit, which is not yet reviewed. See [`../../reports/2026-10-04-drone-runaways/README.md`](../../reports/2026-10-04-drone-runaways/README.md).
>
> **Notes from P1's repository (2026-10-05;** [`../../reports/2026-10-05-p1-repo/README.md`](../../reports/2026-10-05-p1-repo/README.md)**).**
> - **F1 extends to traffic.** P1's traffic agent grows one context (56–82% of prompt tokens from cache), yet kept state saves 1–4% of LLM time: outputs are long (a median 424–999 tokens per call) and a generated token costs 117–312 prefilled ones in time on these Jetsons.
> - **F3 is narrower than we thought.** Traffic tools mostly return in 0.5–3 s; only the vision tool (median 53–158 s) and some data queries wait long. Physical drone flights remain the 10 s–10 min case.
> - **F4 holds.** Decode dominates (84–99% of LLM time); capped decodes take 38–69% of board energy on Thor gemma (33% on Orin 32 gemma-E4B traffic, 0–19% elsewhere).
> - **F5/H4: a live case.** `ask_vlm` sends 8–45 concurrent requests to the agent's own server; on a 12.4K-token pool (Orin 64) it evicts the paused agent context every time. The cost is small (0.6% of LLM time) because prefill is cheap, but it is the one memory-pressure mechanism at one agent per device.
> - **P1's paper is now the closest internal work** to option A: it reports the loops (offline detector) and a "stop at the first capped call" bound. Not cited by P1: INFERCEPT, Continuum, TokenCake, CacheScout, Adaptive KV Retention, or reasoning-length control.

Status: 2026-09-30. There is one doc per system in this folder, all following `_TEMPLATE.md`:
workloads, assumptions, controller, results, what JouleServe-WS can take, what JouleServe must
add, and workstation → edge. The docs were written by parallel reviewers from primary sources.

**Review depth warning.** Most docs were read through a fetch-and-summarize tool, not the raw
PDF. Re-check every number against the PDF before citing it in a paper. Each doc states its
own depth. TAWS is abstract-only.

## 1. Index

| Doc | System | Category | Depth | Baseline priority |
|---|---|---|---|---|
| [infercept.md](infercept.md) | INFERCEPT (ICML'24) | agentic KV retention | full | **must** |
| [continuum.md](continuum.md) | Continuum | agentic KV retention | full | **must** |
| [tokencake.md](tokencake.md) | TokenCake | agentic KV retention (multi-agent) | full | should |
| [adaptive-kv-retention.md](adaptive-kv-retention.md) | Adaptive KV Retention | agentic KV retention (long waits) | full | should |
| [cachescout.md](cachescout.md) | CacheScout | agent-transition-aware eviction | full | should |
| [kvflow.md](kvflow.md) | KVFlow | workflow-aware radix eviction + prefetch (SGLang) | full | **must** |
| [autellix.md](autellix.md) | Autellix | program-level scheduling and preemption | full | **must** |
| [parrot.md](parrot.md) | Parrot (OSDI'24) | semantic-variable app serving | full | optional |
| [kairos.md](kairos.md) | KAIROS | agentic energy-aware serving (closest energy prior art) | full | **must** |
| [festina.md](festina.md) | Festina | energy-aware serverless serving | partial | optional |
| [greenllm.md](greenllm.md) | GreenLLM | per-phase DVFS | partial | optional |
| [greenserv.md](greenserv.md) | GreenServ | energy-aware model routing | partial | optional |
| [dynamollm.md](dynamollm.md) | DynamoLLM (HPCA'25) | cluster energy management | partial | optional |
| [taws.md](taws.md) | TAWS | thermal-aware scheduling | abstract | optional |
| [enerinfer.md](enerinfer.md) | EnerInfer | on-device DVFS + predictive thermal | full | optional |
| [camel.md](camel.md) | Camel | Orin frequency × batch bandit | full | should |
| [agentserve.md](agentserve.md) | AgentServe | agent phases on a consumer GPU (A5000) | full | **must** (phase taxonomy) |
| [arya-simmhan-edge-llm-characterization.md](arya-simmhan-edge-llm-characterization.md) | Arya & Simmhan, PAISE'25 (Prof. Yogesh's group) | Orin characterization | full | should (measurement recipe) |
| [mzcache.md](mzcache.md) | mzCache | KV eviction/restore under unified memory (phones) | full | optional |
| [lmcache.md](lmcache.md) | LMCache | KV substrate / tiering | full | substrate |
| [sglang-kv.md](sglang-kv.md) | SGLang 0.5.20: RadixAttention, HiCache, unified hybrid radix cache, sessions, priority, retraction | KV substrate (**read from installed source**) | full + source | substrate (**must read**) |
| [marconi.md](marconi.md) | Marconi (MLSys'25) | prefix caching for hybrid models | full | should |
| [cachedattention.md](cachedattention.md) | CachedAttention (ATC'24) | multi-turn KV tiering | full | should |
| [pensieve.md](pensieve.md) | Pensieve (EuroSys'25) | stateful multi-turn serving | full | should |
| [cacheblend.md](cacheblend.md) | CacheBlend (EuroSys'25) | non-prefix KV reuse | full | optional |
| [sekv.md](sekv.md) | SeKV | KV compression (adjacent) | full | optional |
| [agentsysbench.md](agentsysbench.md) | AgentSysBench | agent workload characterization | partial | motivation |
| [mlperf-edge-agentic.md](mlperf-edge-agentic.md) + [mlperf-edge-agentic-tensorrt-edge-llm.md](mlperf-edge-agentic-tensorrt-edge-llm.md) | MLPerf Edge Agentic | edge agent benchmark (Thor) | partial | workload / contrast |
| [workloads-catalog.md](workloads-catalog.md) | — | candidate workloads + shortlist | — | — |

## 2. Comparison matrix (condensed)

| System | Workload / pauses | Platform | Actions | Objective | Agent-aware | Host tier | Energy | Thermal | Edge |
|---|---|---|---|---|---|---|---|---|---|
| INFERCEPT | augmented calls, pauses 1e-4–29 s, context accumulates | A100, vLLM | preserve / discard / chunked recompute / swap (min-waste) | throughput, latency | ✓ | swap | – | – | – |
| Continuum | SWE-bench, BFCL, OpenHands; tool ≈1–2 s; 6–11 turns | A100–B200, vLLM fork | TTL pin from a per-tool CDF; program FCFS | JCT | ✓ | LMCache (opt.) | – | – | – |
| TokenCake | multi-agent DAGs; calls 0.1–30 s | A100/H20, vLLM | offload + predictive upload; reserved pool | latency | ✓ | ✓ | – | – | – |
| Adaptive KV Ret. | human-approval waits ~30 min; τ2-bench | 4×H100 | HBM hold t*, host TTL | active goodput | ✓ | ✓ | – | – | – |
| CacheScout | AutoGen 6-agent; short outputs | vLLM | Markov-transition eviction + anchor prefetch | hit rate, TTFT | ✓ | partial | – | – | – |
| KVFlow | multi-agent workflows; outputs 32–256 | SGLang 0.4.4 | steps-to-execution radix priority + prefetch | latency | ✓ (graph) | ✓ | – | – | – |
| Autellix | ShareGPT, BFCL ReAct, LATS | vLLM | program-level LAS priority, preemption + swap | program latency | ✓ | swap | – | – | – |
| Parrot | apps with semantic variables | custom | DAG scheduling, prefix sharing | latency | ✓ (static) | – | – | – | – |
| KAIROS | SWE-bench V., DABStep, Terminal-Bench | H100, vLLM | GPU clock, concurrency cap, routing | power at a tok/s SLO | ✓ (context) | – (assumes retention) | ✓ | – | – |
| GreenLLM / Festina / DynamoLLM | chat traces | A100/H100 | clocks, SM%, placement, TP | energy at SLO | – | – | ✓ | – | – |
| TAWS | inference jobs | DC | placement, batch, V/f | throughput under thermal limits | – | – | partial | ✓ | – |
| EnerInfer | single-stream chat | phones, board | NPU + DDR DVFS, thermal MPC | energy/token | – | – | ✓ | ✓ | ✓ |
| Camel | Alpaca, 70 tokens | **Orin 32 GB**, llama.cpp | GPU freq × batch bandit | EDP | – | – | ✓ | – | ✓ |
| AgentServe | ToolBench ReAct / P&E | **A5000**, 5090 | resume-prefill budget, decode SM floor | TTFT/TPOT SLO | ✓ (phases) | – | – | – | ~ |
| Arya & Simmhan | LongBench, WikiText2 | **Orin 64 GB** | power modes, quant, batch | latency/energy | – | – | ✓ | – | ✓ |
| mzCache | 8–32K ctx under multitasking | phones (unified) | KV-chunk eviction, hybrid restore | TTFT, energy | – | ✓ | ✓ | – | ✓ |
| CachedAttention | ShareGPT multi-turn | A100 + DRAM + SSD | session KV tiers, queue-hint prefetch | TTFT, cost | ~ | ✓ | – | – | – |
| Pensieve | ShareGPT/UltraChat, think time ~60 s | A100 | chunk eviction by recompute cost, AoT swap | throughput | ~ | ✓ | – | – | – |
| CacheBlend | RAG chunks | A40 | non-prefix KV reuse + selective recompute | TTFT | – | ✓ | – | – | – |
| Marconi | hybrid-model prefix caching | — | FLOP-efficiency admission/eviction of SSM states | hit rate / TTFT | – | – | – | – | – |
| MLPerf Edge Agentic | 20 conversations / 1,007 turns, ctx ≤23.5K, concurrency 1 | **Thor**, TRT Edge-LLM | (harness only) | TTFT/TPOT + accuracy gate | – | – | – | – | ✓ |

| LMCache | QA/LongBench, dense only | H100, vLLM (SGLang connector) | chunk tiers, `lookup`/`move`/`pin`/`unpin`/`compress` | TTFT/throughput | – | ✓ | – | – | – |
| SGLang 0.5.20 | — | our WS | eviction policy (`lru`/`lfu`/`slru`/`priority`), sessions (soft/hard pin), request priority + preemption, `retraction_policy`, HiCache, `mamba_*`/`swa_*` sizing | — | sessions only | HiCache | – | – | – |

Substrate facts that matter (from `sglang-kv.md`, read from the installed 0.5.20 source):
- **There is no external pin/evict API.** The levers are:
  - `open_session`/`close_session` with an idle timeout. `--enable-session-radix-cache` gives a soft pin (session nodes are evicted last). `--enable-streaming-session` gives a hard pin (outside the tree; uses pool capacity).
  - Per-request `priority` with `--radix-eviction-policy priority`. A node's priority can only be raised.
  - A `register_radix_cache_backend` plug-in.
  - A sidecar can drive sessions, priority, admission and abort. **Arbitrary pin, priority lowering, "evict now" and per-session metrics need a minimal patch.**
- **Retraction in monolithic mode is pure recompute** of prompt + decoded tokens, minus tree hits. It is priced by `sglang:num_retracted_{input,output}_tokens_total`. Admission budgets `max_new_tokens × new_token_ratio`, starting at 0.7 and decaying. With 32K thinking outputs on a ~25K pool, **retraction is likely the first real cost under concurrency.**
- `TLRU` (on the docs site) is **not** in 0.5.20.
- The LMCache connector is **dense-only** (plain `RadixCache`), so it can't serve Gemma-4 or Qwen3.8.
- HiCache's host pool is pinned memory sized from free RAM. On Jetson it adds no capacity. The `direct` io backend works on our driver.

## 3. What the literature tells us (synthesis)

**F1. In P1's Reflexion drone workload, every published retention rule predicts "discard".**
- All the rules trade **holding cost** (memory × pause) against **resume cost** (re-prefilling the reusable prefix). This covers INFERCEPT's min-waste rule, Continuum's TTL `argmax_τ P(τ,f)·(T·η+Reload) − τ`, and Adaptive's break-even `t* = β3/α1`.
- On P1's drone traces, resume cost is tiny (prefill is 1–8% of LLM time, and only 10–31% of a CLGSCE prompt is reusable) and pauses are long (13–115 s).
- This matches our measured ceiling of 0.3–1.7%. **Classic retention is not a contribution on this workload as-is.**

**F2. How much retention is worth depends on the agent's prompt design, so the paradigm is an experimental factor.**
- Accumulating native tool-calling contexts reuse almost everything: MLPerf Edge Agentic gets 96% of prompt tokens from hot cache; in AgentSysBench, Claude Code has a 99% prefix-hit rate.
- Rebuilt prompts reuse little: DeepResearch ≈1%, P1 Reflexion 10–31%.
- CacheBlend-style non-prefix reuse is bounded at ≲2–3% of LLM time on P1's traces (see `cacheblend.md`).

**F3. Our pause regime (10 s to 10 min) sits in a gap in the literature.**
- Published pause regimes:
  - Continuum: tool pauses ≈1–2 s
  - TokenCake: 0.1–30 s
  - INFERCEPT: ≤29 s
  - Pensieve: 30–120 s of human think time (chat)
  - Adaptive KV Retention: ~30 min
- Adaptive's H100 calibration gives t₁ ≈ 1 s and **t\* ≈ 109 s**, which falls right inside P1's waits (13–115 s median, tail to 15 min).
- AgentSysBench's production trace: sessions are idle 80% of their lifetime, mostly for 1–10 min.
- **Time-aware retention for real-world tool waits (physical actuation, simulators) under edge costs is under-explored.**

**F4. Under concurrency, active state dominates, and nobody models long reasoning decodes.**
- Adaptive (Fig. 2): enforcing residency for 72 suspended contexts cuts active goodput by 41%.
- KAIROS's failure mode: queueing makes aggregate context exceed the pool, and recompute wastes energy.
- Autellix is the only scheduler that preempts, and it assumes short decodes and cheap CPU swap. Swapping a 32K-token thinking context (~4.5 GB for K2 Horizon 7B) goes unpriced.
- **Admission, preemption and retention for reasoning agents with tool phases is open.**

**F5. The host tier collapses on unified memory.**
- These all assume a separate host DRAM reached over PCIe:
  - INFERCEPT swap, TokenCake offload
  - Continuum with LMCache, Adaptive's host TTL
  - CachedAttention's and Pensieve's DRAM tiers
  - KVFlow's prefetch, SGLang HiCache
- On Jetson, "offload" frees no capacity and uses the same bandwidth decode needs. The choice reduces to **retain / drop + recompute / compress (/ NVMe)** (mzCache is the only unified-memory design reviewed).
- → JouleServe-WS must treat **"no host tier" as a first-class mode**. The WS PCIe tier is only a WS comparison.

**F6. Energy levers without root are scheduling levers.**
- Almost every energy controller needs root: clocks (GreenLLM, KAIROS, DynamoLLM), MPS (Festina) or TP reconfiguration.
- Levers we can reproduce on the WS without root:
  - admission and concurrency (batching: decode is bandwidth-bound, so energy per token falls with batch size)
  - consolidation across the 2 GPUs (KAIROS-style)
  - retention and preemption policy
- On Jetson, EMC/GPU DVFS and nvpmodel (root, slow) are the strong decode levers: a low EMC frequency gave +370% latency and +72% energy even though power fell 52% (Arya & Simmhan). This is an orthogonal axis that needs root.

**F7. Energy attribution across tool waits is a measurement gap.**
- None of the reviewed systems attributes idle or tool-wait energy to a session, or reports **energy per successful task** with tool phases.
- Method to adopt:
  - WS: the NVML cumulative energy counter (no root), with clocks, temperature and **throttle reasons** logged every run.
  - Jetson: INA3221 rails, sampled faster than jtop's 2 s.
- Report active vs idle energy separately, including idle energy during tool waits.

**F8. Hybrid models change what "state" is.**
- Both P1 models are hybrid (Gemma 4 sliding-window attention, Qwen3.8 Gated DeltaNet), and so is MLPerf Edge Agentic's model (Qwen3.6-27B).
- Recurrent state can only be reused at checkpoints (Marconi; SGLang's mamba radix cache every 256 tokens). Per-token splicing (CacheBlend, Pensieve's chunk eviction) does not apply.
- MLPerf shows hybrid-state reuse works on Thor.
- → **Hybrid-aware retention on edge** is a plausible angle; K2 Horizon (dense) is the clean full-attention baseline.

**F9. Hints are cheap, and our gateway can make them exact.**
- Published hints: queue lookahead (CachedAttention), inactivity × recompute cost (Pensieve), per-tool CDF (Continuum), elapsed-time proxy at 93% of oracle (INFERCEPT), EWMA + hint (TokenCake).
- A JouleServe gateway that also proxies MCP knows the **tool type, and for simulators the expected duration**. With long, rare tools, cold start is the practical problem.

**F10. KAIROS is the closest energy prior art, but it never decides paused-state retention.**
- KAIROS controls clock, concurrency and routing using aggregate context.
- It lumps active and paused state together, assumes retention, and has no task-success objective and no hybrid or edge treatment.
- Its thrashing failure mode is reproducible on the A5000 without clock control.

## 4. Baselines for JouleServe-WS (prioritized)

| Priority | Baseline | How on SGLang 0.5.20 (see each doc) | Effort |
|---|---|---|---|
| must | SGLang default (LRU radix) | as-is | 0 |
| must | Keep-all / pin-until-resume | session soft pin (`--enable-session-radix-cache`) or hard pin (streaming session); exact pin needs a small patch | S |
| must | Discard-on-pause | `close_session`, or a low priority under the `priority` eviction policy (exact evict-now needs a small patch) | S |
| must | INFERCEPT min-waste (unified-memory form: preserve vs discard; WS form adds swap) | gateway rule + HiCache | M |
| must | Continuum TTL (per-tool empirical CDF) | gateway TTL pin | M |
| must | Autellix PLAS (program-level least-attained service + anti-starvation) | gateway sets request priority; `enable_priority_scheduling` | S–M (2–4 d) |
| must | KAIROS-style concurrency cap with hysteresis (no clock) | gateway admission | S |
| must | AgentServe phase taxonomy (cold prefill / resume prefill / decode) | logging, plus an optional resume-prefill budget | S |
| should | KVFlow steps-to-execution radix priority (+ prefetch on WS) | eviction-policy hook | M (≈1 wk) |
| should | Adaptive KV Retention t\* hold time | gateway | S |
| should | Pensieve think-time eviction / CachedAttention queue hint | eviction hook | M |
| should | CacheScout Markov transition score | eviction hook | M (3–5 d) |
| should | TokenCake reserved pool for critical sessions | admission + pool partition | M |
| should | Camel-style bandit over software knobs (admission cap, chunked prefill, max running) | gateway | S |
| optional | Parrot, GreenServ routing, CacheBlend, SeKV, DVFS controllers (root / Jetson only) | — | — |

S = days, M = about a week. Effort estimates come from the reviewers and are rough.

## 5. Candidate workloads (ranked; see `workloads-catalog.md`)

1. **P1 CLGSCE (Reflexion, 12 tasks, real-time native AirSim sim).** Required for P1 alignment: a decode-dominated regime with rebuilt prompts.
2. **`aerogen_mcp`** (found on the Thor at `/media/ssd/drone/aeroeval/aerogen_mcp`, by another lab member, mayankarya).
   - Native tool-calling drone agent: accumulating context, 20 MCP tools, ≤40 turns / 80 tool calls.
   - Pure Python "sim" backend. It needs real-time pacing added, because it computes flight time but returns instantly.
   - Only 5 tasks. **Ask the author before using it.**
3. **τ²-bench** (MIT): native tool calling with an accumulating context; natural N parallel conversations; runs locally against an OpenAI endpoint with a user-simulator model. Tool waits are milliseconds, so **inject P1's measured wait distributions**.
4. **MultiUAV-Plat** (code GPL-3.0): drones, 75 sessions × ~20 sequential tasks, state carried over, light Python sim. Waits unspecified, so inject them.
5. **ALFWorld** (MIT): embodied text agent, 20–50 steps; inject waits.
6. **MLPerf Edge Agentic replay:** a prefill-heavy contrast case and an edge validation target on Thor. It is concurrency 1 by rule, so wrap it in our own multi-session driver.
7. Continuum SWE/BFCL traces: 70–93K tokens per program, too large for a 25K pool. Use only as a TP=2 cross-check.

## 6. Workstation → edge: cross-cutting changes

- **Memory:** there is no separate host tier, so offload = copy within the same DRAM. Co-located tools and simulators (AgentSysBench: 0.8–28 GB per sandbox) compete with KV.
- **Energy:** move from GPU-only NVML to board rails (INA3221), which include CPU, DRAM and the simulator.
- **Knobs:** nvpmodel, jetson_clocks, GPU/EMC devfreq (root, slow switches); thermal throttling becomes a real state variable.
- **Timing:** Orin has ~4× less memory bandwidth than an A5000, so decode is slower and prefill share rises. Recalibrate every cost model.
- **Models:** hybrid (Gemma 4, Qwen3.8), with separate state pools and checkpoint-granular reuse.
- **Engine:** P1 uses SGLang 0.5.16 containers on Thor; we use 0.5.20 on the WS. MLPerf used TensorRT Edge-LLM.

## 7. Where JouleServe can add something: hypotheses for Track A / M2 to test

- **H1 (reasoning agents under concurrency).** Phase-aware admission and preemption (long thinking decodes vs tool waits) lowers energy per successful task versus Autellix/KAIROS-style baselines. Gap: F4, F6.
- **H2 (time-aware retention in the 10 s–10 min regime under unified memory).** Hold time as a function of tool type/duration, recompute cost and active pressure, with exact gateway hints, beats Continuum TTL and Adaptive t\* once offload frees nothing. Gap: F3, F5, F9.
- **H3 (hybrid-state retention).** With hybrid models, checkpoint-granular retention and admission decisions differ from full-attention KV. Gap: F8.
- **H4 (tool-resource coupling, edge-only).** Co-located tools and simulators compete for unified memory and bandwidth, so retention and admission should depend on the running tool's footprint. This is the old N1 idea; it can only be tested on Jetson.
- **H5 (measurement).** Per-session energy attribution across tool waits, with energy per successful task as the headline metric. Gap: F7.

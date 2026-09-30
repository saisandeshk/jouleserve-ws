# JouleServe-WS — build plan and reference

Status: **v1.0** (2026-09-30). This is the master plan for the workstation build.
- Track A working notes and measurements: [`PLAN.md`](PLAN.md).
- Prior-work review (Track B): [`../review/systems/README.md`](../review/systems/README.md), with one doc per system.

---

## 0. What we are building and why

**JouleServe asks:** how should an edge LLM serving system manage the retained state of agent
sessions (KV cache and hybrid-model state) while those agents wait for tools, to minimize
**energy per successful task**?

**JouleServe-WS** is a complete, reusable research platform on the 2×A5000 workstation. It
runs real agent workloads as concurrent sessions against SGLang, puts a session-aware
**gateway** in front of the engine where retention, admission and preemption policies act, and
measures everything (energy, memory, cache, per-session phases) in one trace format. Policies,
workloads and telemetry are pluggable. Everything platform-specific (telemetry source, memory
model, power knobs) is isolated behind adapters, so moving to Orin/Thor is an adapter swap and
not a rewrite.

**"Complete" means:**
1. Real workloads run end to end: P1 CLGSCE (Reflexion) and at least one native tool-calling workload.
2. N concurrent sessions with controlled load, memory budgets and tool-wait behaviour.
3. Full telemetry, with energy per successful task and energy attributed across tool waits.
4. The "must" baselines from prior work, implemented in the same gateway.
5. At least one JouleServe policy, evaluated against those baselines.
6. Analysis scripts that produce the standard figures.
7. Edge adapters stubbed and dry-run tested.

**Not in scope on the WS:**
- DVFS/power-limit control: needs root. It's a Jetson axis.
- Thermal policy: the A5000's thermals are not the edge's.
- Claims about unified-memory contention: only measurable on Jetson.

## 1. What we know (inputs to the design)

**From Track A** (P1 Thor traces; our WS measurements; details in `PLAN.md`):
- P1's drone agent (Reflexion, thinking on, 32K max tokens) spends most of its time in **decode**: prefill is only 1–8% of LLM time. It rebuilds a role-specific prompt on every call, so only 10–31% of a CLGSCE prompt is reusable.
- Tool waits are real simulator time: 13 s / 37 s / 115 s median for B / A / AeroEval.
- **Perfect retention could save at most ≈0.3–1.7% of LLM time** in a single session.
- K2 Horizon 7B in bf16 on one A5000 gives a **KV pool of 25,427 tokens** and decodes at **36.5 tok/s**. One long-thinking P1 call (≈40K tokens) does not fit that pool.
- P1 has **no native tool-calling paradigm**; all runs are Reflexion.
  - A native tool-calling **drone** agent exists on the Thor: `aerogen_mcp`, by another lab member (mayankarya), with no results yet.
  - Its "sim" backend is pure Python. It computes flight time but returns instantly.

**From Track B** (see `review/systems/README.md` §3):
- **F1.** Every published retention rule predicts "discard" on P1 Reflexion as it stands.
- **F2.** How much retention is worth depends on the **agent paradigm and prompt design**: accumulating tool-calling contexts get 96–99% reuse; rebuilt prompts get 1–31%.
- **F3.** Our pause regime (10 s to 10 min) falls in a gap between published pause regimes. Adaptive KV Retention's break-even hold time is t\* ≈ 109 s on an H100, inside our range.
- **F4.** Under concurrency, **active long decodes** dominate. No scheduler handles 32K-token thinking decodes plus tool phases.
- **F5.** Offload to host memory frees nothing on unified memory, so **"no host tier" must be a first-class mode**.
- **F6/F7.** Without root, the energy levers are scheduling levers: admission, batching, consolidation, retention and preemption. **Nobody attributes tool-wait energy per session.**
- **F8.** Hybrid models change what "state" means. Recurrent state can only be reused at checkpoints (Marconi; SGLang's 256-token interval).
- **F9.** Our gateway can give *exact* tool-type and tool-duration hints.
- **F10.** KAIROS is the closest energy prior art, but it assumes retention and never decides it.
- **SGLang 0.5.20** has **no external pin/evict API**. It does have:
  - sessions: soft pin via `--enable-session-radix-cache`, hard pin via streaming sessions
  - per-request `priority` with a `priority` eviction policy
  - a cache-backend plug-in
  - admission through `/metrics`

  Retraction under memory pressure is **pure recompute**, and it is priced in `/metrics`.

**Hypotheses the platform must be able to test** (review §7):
- **H1:** phase-aware admission/preemption for reasoning agents
- **H2:** time-aware retention in the 10 s–10 min regime under unified memory
- **H3:** retention for hybrid-model state
- **H4:** tool-resource coupling (edge only)
- **H5:** per-session energy attribution across tool waits

## 2. Design principles

1. **Gateway first, engine patches last.** Policies live in an OpenAI-compatible gateway in front of SGLang. Only add a *minimal, documented* SGLang patch where a lever is missing (explicit pin, evict-now, per-session metrics).
2. **Zero changes to agents.** Each session gets its own base URL, `http://gw:PORT/s/<session_id>/v1`. P1's harness already takes `OPENAI_BASE_URL` from the environment, so the gateway knows the session and its phase without any agent-code edits.
3. **Same code on WS and edge.** Platform differences sit behind three adapters:
   - `DeviceTelemetry`: NVML ↔ tegrastats/INA3221
   - `EngineAdapter`: SGLang 0.5.20 on the WS ↔ the 0.5.16 container on Jetson
   - `MemoryModel`: discrete + host tier ↔ unified, no host tier
4. **One trace schema, a superset of P1's** (`run_meta.json`, `iterations.jsonl`, `server_kv.jsonl`, `device_samples.jsonl`), so WS runs line up with P1's Thor runs.
5. **Reproducible runs.** YAML config → run directory with a manifest (git SHA, package versions, server flags, GPU state, seeds), with clean start and teardown.
6. **The KV budget is an experimental knob,** set with `--max-total-tokens`. The physical pool only needs to be at least the largest budget we study.

## 3. Architecture

```
          ┌──────────────────── Workload layer ────────────────────┐
 Session  │ agent runners (unchanged code)        tools / sims      │
 driver ─▶│  P1 CLGSCE Reflexion | aerogen (native tool calling)    │
 N, mix,  │  τ²-bench | MultiUAV-Plat | ALFWorld | replay           │
 arrivals └───────┬──────────────────────────────────┬──────────────┘
                  │ OpenAI API  /s/<session>/v1      │ MCP (per-session servers)
          ┌───────▼───────────────┐   tool events   ┌▼───────────────┐
          │  JouleServe gateway   │◀───────────────▶│  MCP proxy     │
          │  sessions + phase FSM │                 │  tool timing,  │
          │  policy engine        │                 │  type, bytes   │
          │  admission queue      │                 └────────────────┘
          └───────┬───────────────┘
                  │ HTTP + control: priority, sessions, abort/pause, caps
          ┌───────▼───────────────┐      ┌──────────────────────────────┐
          │ SGLang 0.5.20         │─────▶│ Telemetry: NVML 10 Hz,       │
          │ K2-Horizon-7B (bf16)  │      │ /metrics 2–10 Hz, process    │
          │ EngineAdapter         │      │ sampler, gateway + tool logs │
          └───────────────────────┘      └──────────────┬───────────────┘
                                                        ▼
                                  Run store (P1-compatible) → analysis → figures
```

### 3.1 Serving backend (`jsw/engine/`)
- **Environment:** `~/legacy/jouleserve-ws/.venv` (SGLang 0.5.20, torch 2.13+cu126). Launch it with the `nvidia/cu13/lib` `LD_LIBRARY_PATH` recipe. Freeze the package list into `env/stack-freeze.txt`.
- **Launch profiles** (YAML):
  - `tp1`: one GPU, `--mem-fraction-static 0.88 --cuda-graph-max-bs-decode 16 --disable-prefill-cuda-graph`, pool ≈25K tokens
  - `tp2`: both GPUs, pool ≈170K tokens (to be measured)
  - `tp1x2`: two independent replicas, for parallel sweeps
  - Every profile runs with `--enable-metrics --enable-cache-report`, the `k2_horizon` reasoning and tool-call parsers, and an optional `--max-total-tokens` cap.
- **`EngineAdapter` interface:** `launch/teardown`, `health`, `metrics()`, `set_priority`, `open/close_session`, `abort`, and later `pin/evict` once patched.
- Record every retraction via `num_retracted_*_tokens_total`.

### 3.2 JouleServe gateway (`jsw/gateway/`)
- An async OpenAI-compatible reverse proxy (FastAPI or aiohttp), with streaming passthrough.
- **Session phase FSM:** `NEW → LLM_QUEUED → LLM_ACTIVE → TOOL_WAIT → … → DONE`.
  - Transitions come from request arrival and completion, and from MCP-proxy tool events.
  - If no tool event arrives, the gap between calls counts as a tool wait.
- **Policy hooks:**
  - `on_arrival` (admit / queue / priority)
  - `on_complete` (retain decision: keep, soft pin, hard pin, TTL, discard, and HiCache offload on the WS)
  - `on_tool_start/end` (with tool type and expected duration)
  - `on_tick` (pressure-driven actions from `/metrics`)
- **Logs:** a per-call record with session, role, phase times, queue delay, TTFT, decode time, prompt/cached/completion tokens, retained/evicted decisions, and the priority used.

### 3.3 MCP proxy and tool layer (`jsw/tools/`)
- Wraps per-session MCP servers (streamable-http or stdio) to timestamp every tool call and emit phase events to the gateway. It records tool name, arguments size and result size.
- A **process sampler** (psutil) for simulators and tools: CPU, RSS, and later GPU memory. This is the measurement groundwork for H4 on Jetson.
- **Tool-wait injection** for mock-tool workloads: sample from P1's measured per-tool distributions, or use a fixed or real-time pacing factor.

### 3.4 Workload adapters and session driver (`jsw/workloads/`, `jsw/driver/`)
- **Adapter interface:** `tasks()`, `start_session_env(sid)` (sims and MCP servers on per-session ports), `run_session(sid, base_url, task, seed) → verdict + trace`, `stop_session_env(sid)`.
- **Adapters, in priority order:**
  1. **`p1_clgsce`** (Reflexion, 12 tasks):
     - Build AirLib + `thor_headless.cpp` on x86 with g++/cmake, and patch in a port argument.
     - Run one sim + MCP server pair per session.
     - Use P1's agent code and settings unchanged (thinking on, `max_tokens` 32768, 3 iterations, temperature 0, seed 42).
  2. **`aerogen`** (native tool calling, drone). Add a real-time pacing factor to the sim backend. **Needs the author's OK.**
  3. **`tau2`** (τ²-bench): native tool calling, inject waits, plus a user-simulator model.
  4. `multiuav`, `alfworld`, `mlperf_replay`: later, as needed.
- **Session driver:**
  - Closed loop (fixed N) or open loop (Poisson session arrivals).
  - Task mixing: with temperature 0 and a fixed seed, sessions running the same instance would produce identical runs.
  - Staggered starts, and a bound by duration or task count.

### 3.5 Telemetry (`jsw/telemetry/`)
- **`DeviceTelemetry` (NVML), 10 Hz:**
  - power
  - **cumulative energy counter** (`nvmlDeviceGetTotalEnergyConsumption`)
  - SM/memory clocks, temperature, **throttle reasons**
  - used memory, utilization
  - All of these work without root.
- **Server sampler:** `/metrics` at 2–10 Hz, covering full/SWA/mamba usage, queue, running, cache hit rate, evictions and retractions.
- All streams share one monotonic clock, anchored to wall time.
- **Energy attribution:**
  - Split active and idle energy at the device level.
  - Attribute each session's share of batched decode energy in proportion to its tokens in each step window.
  - Attribute idle energy during tool waits across the waiting sessions.
  - This is H5, and it is novel (F7).

### 3.6 Policies (`jsw/policies/`)
- **Interface:** `observe(state) → actions`, where `state` holds sessions, phases, pool usage, queue, predictions and costs, and `actions` are admit, priority, retain mode, TTL and preempt hint.
- **Cost model** (`jsw/costs/`), calibrated per device and profile:
  - prefill time and energy per token
  - decode time and energy per token as a function of batch size
  - idle power
  - bytes of state per token (dense KV, SWA and recurrent slots)
- **Baselines**, following review §4:
  - **must:** SGLang default; keep-all; discard-on-pause; INFERCEPT min-waste; Continuum TTL; Autellix PLAS; KAIROS-style concurrency cap (no clock control); AgentServe phase logging
  - **should:** Adaptive t\*; KVFlow; Pensieve/CachedAttention hints; CacheScout; TokenCake reserved pool; Camel-style bandit over software knobs
- **JouleServe policy v1:** chosen after M2 (§5), from H1 and/or H2 (plus H3 if we serve hybrid models).

### 3.7 Runner, store and analysis (`jsw/runner/`, `analysis/`)
- **YAML experiment:** engine profile × KV budget × policy × workload × N × arrival × seeds. The sweep expander skips runs that already exist, so sweeps can resume.
- **Run directory:** manifest, a P1-compatible per-session trace, gateway log, tool log, telemetry, and a summary JSON.
- **Metrics:**
  - energy per successful task
  - active / idle / tool-wait energy
  - wasted prefill (from evictions and retractions)
  - share of the pool held by paused sessions
  - queue delay, retraction count and recompute tokens
  - p50/p95 task time, success rate
- **Figures:** G1–G9 as defined in `PLAN.md` §2.4, plus the baseline-comparison frontier (energy per success vs p95 task time).

### 3.8 Emulation knobs (WS only)
- `--max-total-tokens` caps that mimic a device's KV budget. We label them as multiples of one session's peak (0.5×, 1×, 2×, 4×) and map them to Orin 32/64 and Thor afterwards.
- Host tier on/off: HiCache with the `direct` io backend, or off to mimic unified memory.
- Tool pacing factor, and optional injected waits.
- Optional co-located GPU memory "hog" process, as a rough stand-in for tool/sim memory pressure.

## 4. Repo layout (target)

```
jouleserve-ws/
  planning/        JOULESERVE_WS_PLAN.md (this), PLAN.md (Track A notes), decisions/
  review/          literature evidence; systems/ (Track B docs)
  env/             stack-freeze.txt, launch recipes, setup notes
  jsw/             engine/ gateway/ tools/ workloads/ driver/ telemetry/ policies/ costs/ runner/
  vendor/          p1_clgsce/ (snapshot of P1 code + thor_headless.cpp), aerogen_mcp/ (if approved)
  configs/         engine profiles, experiments/*.yaml
  analysis/        metrics, figures, reports
  data/            copied external traces (git-ignored)
  runs/            run outputs (git-ignored; summaries committed)
  tests/           unit tests (gateway FSM, cost model, attribution) + smoke tests
```

## 5. Milestones

Durations are rough and assume one person. P1 members may join after P1's submission.

| # | Milestone | Deliverables | Exit criterion | Est. |
|---|---|---|---|---|
| **M0** | Foundations | repo skeleton, env freeze, engine profiles (tp1/tp2), NVML + `/metrics` samplers, run manifest, smoke test | one request produces a complete run dir with energy numbers; tp2 pool size measured | ~1 wk |
| **M1** | Workloads + gateway v0 | pass-through gateway with a session FSM and call log; MCP proxy; P1 CLGSCE port (x86 sim, per-session ports, harness); session driver; `aerogen` adapter (if approved) with pacing | CLGSCE B5 passes end to end in one session with a full trace; N=4 concurrent CLGSCE sessions run; one aerogen mission runs through the `k2_horizon` tool parser | 1.5–2 wk |
| **M2** | Characterization + **decision gate** | E1: single session (12 CLGSCE tasks × 3 instances × 1 run; aerogen 5 tasks). E2: N ∈ {1,2,4,8,16} × budget multiples, for both paradigms. Offline headroom estimate. **Evidence pack** | the professor picks the direction (drone as-is / modify / adopt) and the hypothesis (H1–H5) | 1–1.5 wk |
| **M3** | Baselines | "must" baselines in the gateway, each checked for its qualitative behaviour; any minimal SGLang patch (pin / evict-now / per-session metrics) | every baseline runs on every workload in the standard sweep | ~2 wk |
| **M4** | JouleServe policy v1 | calibrated cost model; controller for the chosen hypothesis; ablations | beats the best baseline on energy per successful task at an equal or better success rate and p95, in the target regime | 2–3 wk |
| **M5** | WS evaluation | full sweeps, figures, draft write-up | reproducible from configs | 1–2 wk |
| **M6** | Edge readiness (in parallel, small) | Jetson `DeviceTelemetry` (from P1's `samplers.py`), Jetson engine profile (our `jouleserve/sglang:0.5.16-orin-cu126-sm87` image from hostov), `MemoryModel=unified` mode, checklist | dry run with recorded tegrastats; ready to go on first device access | ongoing |

**What we run first** (this week):
1. M0.
2. The CLGSCE port.
3. Ask the aerogen author, and the P1 team, before vendoring their code.
4. Resume the Track A plan in `PLAN.md` on the new infrastructure.

## 6. Edge plan (for later, when the devices are back)

1. **Environment.**
   - Our Orin SGLang image `jouleserve/sglang:0.5.16-orin-cu126-sm87` (from hostov), plus the P1 Thor container.
   - Same gateway, driver and workloads.
   - Reuse P1's `run_one.py` conventions and check for P1's busy markers, so we never collide with their runs.
2. **Telemetry adapter:**
   - INA3221 rails through tegrastats or sysfs, faster than jtop's 2 s
   - thermal zones, cooling state
   - GPU/EMC clocks, throttle ratio
   - Board energy covers CPU, DRAM and simulator energy.
3. **Recalibrate the cost models** per device and power mode. Orin has ~4× less memory bandwidth than an A5000, so prefill share rises and decode slows.
4. **Unified memory.**
   - Run `MemoryModel=unified` (no host tier). Offload becomes an accounting-only or compress option.
   - Measure how co-located simulators and tools contend for memory and bandwidth. This is H4, the edge-only hypothesis.
5. **Models.**
   - P1's hybrid models (Gemma-4-26B-A4B, Qwen3.8-27B), with SWA/mamba state pools and checkpoint-granular reuse (H3).
   - Keep K2 Horizon for continuity with the WS results.
6. **Power and thermal.**
   - Treat nvpmodel modes and ambient temperature as fixed experimental conditions (mode switches are slow).
   - Feed thermal state into the policy.
   - Optionally add root-gated DVFS as an orthogonal axis.
7. **P1 predictor.** If P1 delivers its predictor (remaining iterations and energy after iterations 1–2), plug it in as a gateway input for admission and retention.
8. **Validate.** Rerun the key WS experiments on Orin 32/64 and Thor, and report which WS conclusions carry over.

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| No retained-state opportunity in any workload | The platform still yields H1 (admission/preemption for reasoning agents) and H5 (energy attribution). Present the negative result with numbers. |
| K2 Horizon's tool calling is poor | Try its `json`/`xml` tool formats. Fall back to Ling 3.0 Tiny (hybrid) or another small AA model; the model is only a config value. |
| The AirLib x86 build fails with gcc | Use user-space clang (as P1 did on Thor), or reimplement the small SimpleFlight kinematics, flagged as lower fidelity. |
| SGLang levers are insufficient | Minimal patch behind `EngineAdapter`, documented and version-pinned. |
| GPU time (~30 GPU-h per full CLGSCE sweep) | Two independent tp1 replicas; one run per instance first; open-loop concurrency sweeps are shorter per data point. |
| Version drift from P1 (0.5.16 vs 0.5.20) | Record versions in every manifest, and cross-check one config on Thor later. |
| Code ownership (P1, aerogen author) | Ask before vendoring; keep attribution in `vendor/*/README`. |

## 8. Open decisions

| ID | Decision | Default / status |
|---|---|---|
| D6 | Use `aerogen_mcp` as the native tool-calling drone workload | pending the author's OK (ask) |
| D7 | Second native tool-calling workload | τ²-bench (MIT) |
| D8 | KV budget labels | multiples of one session's peak, mapped to devices afterwards |
| D9 | tp2 vs quantization vs FP8 KV for the concurrency sweeps | tp2 bf16 first (after tp1 characterization) |
| D10 | JouleServe policy focus | decided at the M2 gate (H1/H2/H3) |
| D11 | Minimal SGLang patch (pin / evict-now / per-session metrics) | only if M3 needs it |

## 9. Quick reference

- **WS:** `ssh saisandeshk@10.24.32.174`, repo at `~/jouleserve-ws`.
  - GPU0 ↔ cores 0–9, 20–29; GPU1 ↔ cores 10–19, 30–39.
  - No NVLink, no root.
- **Serve K2 Horizon on one GPU:**
  ```bash
  L=~/legacy/jouleserve-ws; export LD_LIBRARY_PATH=$L/.venv/lib/python3.11/site-packages/nvidia/cu13/lib:$LD_LIBRARY_PATH
  CUDA_VISIBLE_DEVICES=1 taskset -c 10-19 $L/.venv/bin/python -m sglang.launch_server --model-path IFM/K2-Horizon-7B \
    --tp-size 1 --context-length 65536 --mem-fraction-static 0.88 --cuda-graph-max-bs-decode 16 --disable-prefill-cuda-graph \
    --reasoning-parser k2_horizon --tool-call-parser k2_horizon --enable-metrics --enable-cache-report --port 30000
  ```
- **P1 device (Thor):** `ssh yash@10.24.24.79`. Look only. Never run anything whose command line contains P1's busy strings (see `PLAN.md` Appendix A).
  - Drone code map: `PLAN.md` Appendix A.
  - `aerogen_mcp`: `/media/ssd/drone/aeroeval/aerogen_mcp/`.
- **P1 trace copy:** `data/p1_thor_drone/` (125 Gemma runs, lightweight files).

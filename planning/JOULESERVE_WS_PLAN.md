# JouleServe (P5) — master plan

Status: **v2.0** (2026-10-12). This is the stable frame of P5: the question, the platform (the WS and the Jetsons), the
milestones and the decisions. It changes rarely.
- **Current work:** [`OPTIONS_PLAN.md`](OPTIONS_PLAN.md) v2.0 holds the schedule, the device protocol and the
  experiment rules; [`TRACKER.md`](TRACKER.md) holds task status; [`../HANDOFF.md`](../HANDOFF.md) holds the state of
  the day.
- **v2.0 (12 Oct):** P5 has five Jetsons.
  - Old M3–M5 (baselines, policy and WS evaluation for a retention controller) are replaced.
  - M6 (edge readiness) is active as the device platform.
  - M7–M9 are new (§5).
  - §6 now describes the devices in hand.
- **How we got here** (details in the dated reports and HANDOFF):
  - **30 Sep:** v1.0, a WS build plan for a retention and admission controller.
  - **1–4 Oct:** first evidence packs. P1's agents as built have no retained-state opportunity. A memory controller
    beats SGLang's default by at most ~10% (sim). P1's runaway calls are repetition loops.
  - **5 Oct:** P1's repository; traffic analysed. Kept state is worth 1–4% of LLM time, and capacity binds on the
    Orins. M3–M5 put on hold until the professor's direction decision (D12).
  - **5–6 Oct:** the options comparison (CMP-2), with WS experiments on P1's models. The gateway, the replayer, the
    runner and two policies were built from §3's design.
  - **10–11 Oct:** P1 submitted its paper (SIGMETRICS 2027; data at `0cc2311a`). It is decode-bound everywhere and has
    no multi-agent result.
  - **12 Oct:** the five Jetsons arrived; the meeting moved to Wed 14 Oct.
- **Other planning docs:** Track A working notes in [`PLAN.md`](PLAN.md) (historical). Prior work (Track B) in
  [`../review/systems/README.md`](../review/systems/README.md).

---

## 0. What we are building and why

**JouleServe asks:** how should an edge LLM serving system manage the retained state of agent
sessions (KV cache and hybrid-model state) while those agents wait for tools, to minimize
**energy per successful task**?

**Where it stands (12 Oct):**
- On P1's workloads the retained-state question is answered "little to gain" (RET).
- Which direction P5 takes (A, B, C, D or CAP) is the professor's call (D12, Wed 14 Oct). CMP-2 makes the case for
  each.

**JouleServe** is a reusable research platform on the 2×A5000 workstation and, since 12 Oct, on P5's five Jetsons. It
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

Status (12 Oct):
- **Built:** items 1–3 and 6, for recorded and replayed workloads. P1's own agents run on the Jetsons, not on the WS.
- **Waiting for D12:** items 4–5. They assumed the retention controller.
- **Active:** item 7, now the device platform (M6).

**Not in scope on the WS:**
- DVFS/power-limit control: needs root. It's a Jetson axis.
- Thermal policy: the A5000's thermals are not the edge's. On the edge too, P1 measured no thermal throttling in 392 h at room temperature (2026-10-03); only hot enclosures are open.
- Claims about unified-memory contention: only measurable on Jetson.

## 1. What we know (inputs to the design)

*As of 30 Sep: the inputs to the original design. The current evidence is in `HANDOFF.md` §4 and CMP-2.*

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

   The Jetson side is being built in M6 (§5): tegrastats telemetry with P1's power fields, P1's SGLang 0.5.16
   containers, and no host tier.
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
          │ SGLang 0.5.20 (WS),   │─────▶│ Telemetry: NVML 10 Hz (WS),  │
          │ 0.5.16 (Jetson)       │      │ tegrastats 5 Hz (Jetson),    │
          │ EngineAdapter         │      │ /metrics, gateway + tool logs│
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
- **Jetsons (since 12 Oct):** P1's images are used as they are: `jouleserve/sglang:0.5.16-orin-cu126-sm87` on the
  Orins, `lmsysorg/sglang:latest-cu130-runtime` on Thor-1. `env/launch_jetson.sh` starts them with P1's flags
  (OPTIONS_PLAN §4.1).

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
- **`DeviceTelemetry` (Jetson, M6):** tegrastats at 200 ms with P1's field names.
  - Board total: `power_VIN_mW` on Thor; VDD_GPU_SOC + VDD_CPU_CV + VIN_SYS_5V0 on the Orins (P1's
    `platform_total_power_mW`).
  - NVML (GPU-only) and board energies are compared only as ratios, never in absolute terms.
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

Durations assume one person. Old M3–M5 assumed a retention controller and are replaced (12 Oct).

| # | Milestone | Deliverables | Exit criterion | Status |
|---|---|---|---|---|
| **M0** | Foundations | repo skeleton, env freeze, engine profiles, NVML + `/metrics` samplers, run manifest, smoke test | one request produces a complete run dir with energy numbers | done (30 Sep–1 Oct) |
| **M1** | Workloads + gateway v0 | gateway with policy hooks and call log; trace replayer; aerogen driver; runner | P1's sessions replay as N concurrent agents | done (5–6 Oct). The CLGSCE port to the WS is superseded: P1's drone stack runs on the units |
| **M2** | Characterization + decision gate | evidence packs (1–5 Oct); the options comparison CMP-2 (6 Oct) | the professor picks the direction (D12) | done; the gate is D12, Wed 14 Oct |
| M3 | Baselines in the gateway (retention) | — | — | **replaced** 12 Oct. RET's negative result removed the controller this served; the baseline policies exist in the simulator and the replayer |
| M4 | JouleServe policy v1 (retention) | — | — | **replaced** by M8 |
| M5 | WS evaluation | — | — | **replaced** by M7–M8: evaluation moves to the devices, and the WS is the link |
| **M6** | **Device platform** (was "edge readiness") | P1's stack snapshotted and stopped; P5 folders and container convention; Jetson telemetry with P1's power fields; our stack on P1's SGLang 0.5.16 images; preflight protocol; unit equivalence; calibration | a replayed P1 session on an Orin 32 costs what P1 measured on that board (±15%), and every run passes preflight | **active**: the minimum by Mon 12 Oct 23:00 (C1); calibration of every model by ~16 Oct |
| **M7** | **Meeting-ready evidence** | corrected CMP-2 and deck; P1's clean sessions (loader, WS reruns); first device results (CAP-J1 with its anchor, the A-J1 pilot) | the professor decides D12 on correct numbers | due Wed 14 Oct (freeze 09:00) |
| **M8** | **The chosen direction on the devices** | the branch in OPTIONS_PLAN §7, each experiment's rule written before it runs | the branch's question answered on P1's devices, with repeats | after D12; 2–4 weeks |
| **M9** | Write-up | figures, a draft, and what goes to P1 | — | after M8 |

What runs now: OPTIONS_PLAN.md §3 (schedule) and TRACKER.md (status).

## 6. The devices (since 12 Oct)

P5 has five of P1's Jetsons (Sandesh, 12 Oct).
- **The units:** Thor-1 (`dream-thor-1`), Orin-64-1 (orin45) and Orin-32-1/2/3 (orin56/57/58). They hold P1's images,
  models and drone stack, and are reachable from the laptop and the WS as `ssh Thor-1`, `ssh Orin-64-1`,
  `ssh Orin-32-1/2/3`.
- **Their roles** (D19): capacity on the Orin 32s, A on Thor-1, calibration and then D on Orin-64-1. The WS drives,
  analyses and links.
- **References:** the inventory is in OPTIONS_PLAN.md §1.2; the rules are in `AGENTS.md` §4.

The edge plan of v1.0, item by item:
1. **Environment.** P1's images and models are used as they are. Our gateway and replayer run on the WS and drive the
   units over the LAN (OPTIONS_PLAN DEV-4). P1's busy markers no longer matter on P5's units, except when we run P1's
   own harness ourselves.
2. **Telemetry adapter.** tegrastats at 200 ms with P1's field names, plus sysfs clocks and thermal zones (DEV-3).
   Board energy includes CPU, DRAM and simulator energy.
3. **Recalibrated cost models**, per device and model (DEV-7). Orin has about 4× less memory bandwidth than an A5000,
   so prefill's share rises and decode slows.
4. **Unified memory.** `MemoryModel=unified` (no host tier). Co-located tools and models contending for memory is H4,
   the edge-only hypothesis, in the D branch (D-J1, D-J2).
5. **Models.** P1's hybrid models (Gemma-4-26B-A4B with sliding-window layers, Qwen3.8-27B with linear attention) are
   on the units; H3 only if a branch needs it. K2 Horizon is dropped: P1's models replaced it on the WS on 5–6 Oct.
6. **Power and thermal.** nvpmodel MAXN with the clocks locked, as found and as P1 ran. Mode, clocks and ambient
   temperature are fixed conditions. Root-gated DVFS stays out of scope unless a branch needs it.
7. **P1 predictor.** Not delivered; not planned.
8. **Validate.** Every device result carries its anchors: N = 1 against P1's measured runs on the same board, the WS
   on the same sessions, and the simulator where it applies.

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| No retained-state opportunity in any workload | **Happened** (RET, 3–6 Oct). The options comparison (CMP-2) offers five directions; the negative result is reported with numbers |
| K2 Horizon's tool calling is poor | Try its `json`/`xml` tool formats. Fall back to Ling 3.0 Tiny (hybrid) or another small AA model; the model is only a config value. |
| The AirLib x86 build fails with gcc | Use user-space clang (as P1 did on Thor), or reimplement the small SimpleFlight kinematics, flagged as lower fidelity. |
| SGLang levers are insufficient | Minimal patch behind `EngineAdapter`, documented and version-pinned. |
| GPU time (~30 GPU-h per full CLGSCE sweep) | Two independent tp1 replicas; one run per instance first; open-loop concurrency sweeps are shorter per data point. |
| Version drift from P1 (0.5.16 vs 0.5.20) | Record versions in every manifest. On the devices it is resolved: P1's own images are used |
| Device numbers disagree with P1's | DEV-3's side-by-side check with P1's sampler, and the N = 1 anchor (OPTIONS_PLAN §5.2); report relative numbers only if the anchor fails |
| The Orin 32 docker disks are full | Read-only containers that write only to the USB drives; no image pulls or loads there; move (never delete) files only with the owners' OK |
| The units are needed by others again | Agree a schedule through Sandesh; every device point can be restarted on its own |
| Code ownership (P1, aerogen author) | Ask before vendoring; keep attribution in `vendor/*/README`. |

## 8. Decisions

| ID | Decision | Status (12 Oct) |
|---|---|---|
| D6 | Use `aerogen_mcp` as the native tool-calling drone workload | used on the WS from a private copy (not vendored); extending it waits for mayankarya's OK (B-J1) |
| D7 | Second native tool-calling workload | τ²-bench (used in C-E1) |
| D8 | KV budget labels | superseded: P1's real pools are used, set with `--max-total-tokens` |
| D9 | tp2 vs quantization vs FP8 KV for the concurrency sweeps | FP8 KV became a research lever (CAP); tp2 only where a model needs it |
| D10 | JouleServe policy focus | replaced by D12 |
| D11 | Minimal SGLang patch (pin / evict-now / per-session metrics) | not needed so far |

Other decisions:
- D1–D5: `PLAN.md` §6.
- D12: the professor's direction decision (Wed 14 Oct). Its outcome will be D23.
- D13–D18: OPTIONS_PLAN.md Appendix R.
- D19–D22: OPTIONS_PLAN.md §9.

## 9. Quick reference

- **WS:** `ssh WS` (`saisandeshk@10.24.32.174`).
  - Repo `~/jouleserve-ws`, dev copy `~/jsw-dev`, runs `~/work/runs/`.
  - GPU0 ↔ cores 0–9, 20–29; GPU1 ↔ cores 10–19, 30–39.
  - No NVLink, no root.
  - Serving recipes: `AGENTS.md` §5 (K2) and §6c (P1's models).
- **Jetsons (P5's since 12 Oct):** `ssh Thor-1`, `ssh Orin-64-1`, `ssh Orin-32-1`/`-2`/`-3`, from the laptop or the WS.
  Inventory: OPTIONS_PLAN.md §1.2. Rules: `AGENTS.md` §4.
- **Thor-2** (`mayankarya@10.24.24.80`): P1's machine. Look-and-copy only.
- **P1's data:** local `data/edge-agent-bench` and WS `~/work/p1/edge-agent-bench`, both at `0cc2311a` (read-only).
  Drone code map: `PLAN.md` Appendix A. Trace copy: `data/p1_thor_drone/`.

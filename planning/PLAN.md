# JouleServe (P5) — working plan

> **Master plan:** [`JOULESERVE_WS_PLAN.md`](JOULESERVE_WS_PLAN.md). This file holds the **Track A working notes and measurements**. Track B (prior work) is in [`../review/systems/README.md`](../review/systems/README.md).

> **2026-10-01:** Track A's question is answered in [`../reports/2026-10-01-workload-opportunity/README.md`](../reports/2026-10-01-workload-opportunity/README.md): P1's agents as implemented have no retained-state opportunity; an accumulating-context drone agent (aerogen) does. Direction decision pending.
>
> **Later results** (current state: [`../HANDOFF.md`](../HANDOFF.md)):
> - **2026-10-03:** a memory controller does not beat SGLang's default
>   ([`../reports/2026-10-03-admission-sim/README.md`](../reports/2026-10-03-admission-sim/README.md)).
> - **2026-10-04:** P1's runaway calls are repetition loops, and P1's 3 Oct drone results
>   reproduce ([`../reports/2026-10-04-drone-runaways/README.md`](../reports/2026-10-04-drone-runaways/README.md)).
> - **2026-10-05:** P1's repository arrived (read-only clone in `data/edge-agent-bench`). The traffic agent
>   accumulates context, but kept state is still worth 1–4% of its LLM time; drone and traffic results in
>   [`../reports/2026-10-05-p1-repo/README.md`](../reports/2026-10-05-p1-repo/README.md). The repository has
>   no Thor drone tool-calling cell, so `data/p1_thor_toolcalling/` stays in use. The direction decision is
>   postponed with the professor meeting (D12 open).
> - **2026-10-06:** the options comparison ([`../reports/2026-10-06-options/README.md`](../reports/2026-10-06-options/README.md);
>   plan [`OPTIONS_PLAN.md`](OPTIONS_PLAN.md)). P1's models now run on the WS (gemma-4-E4B and granite-4.2-8b in
>   SGLang; gemma-4-26B only as a 4-bit GGUF in llama.cpp; recipes in `AGENTS.md` §6c). On the 26B, greedy decoding
>   loops on 77% of P1's loop prompts and Gemma's default sampling on none.

Status: **draft v0.4** (2026-09-30). This is a living document. Sections marked
`TBD` are deliberately thin until we reach them. Decisions are tracked in §6.

## 0. The question and the constraint

**Research question.** How should an edge LLM serving system manage the retained
state of agent sessions while those agents wait for tools? "Retained state" means the
KV cache and, for hybrid models, the sliding-window or recurrent state.

**Where the literature leaves us** (`review/`). The generic version is already taken:
- INFERCEPT, Continuum and TokenCake decide whether to keep, swap, evict or recompute during tool pauses.
- CacheScout predicts transitions between agent steps.
- Adaptive KV Retention weighs the opportunity cost of holding idle state.
- KAIROS controls power and concurrency for agent workloads.

A JouleServe contribution has to come from **edge-specific factors changing the best
action**: unified memory, shared bandwidth, thermal state, and what the running tool
itself needs from the device. It is judged by energy per successful task.

**Constraint right now.** The edge devices are with P1 until their deadline; the P1
drone sweep is currently running on a **Jetson AGX Thor**. P5 has a **2×A5000
workstation**. WS work must be useful once the edge devices come back. P1
(EdgeAgentBench) supplies the devices, the workloads (drone, traffic) and possibly a
trajectory predictor.

**Two tracks, in parallel:**

| Track | Question | Output |
|---|---|---|
| **A** | Do P1's drone workloads create a retained-state opportunity under concurrent sessions? | Evidence pack, then the professor decides the direction |
| **B** | What did prior work actually run, assume and build, and what must JouleServe add? | Per-paper extraction + WS→edge change list |

---

## 1. What we know about P1's drone workload (as of 2026-09-30)

**Structure** (full code map in Appendix A):
- 16 tasks = **12 CLGSCE** tasks + **4 AeroEval** tasks.
  - CLGSCE runs on a headless native AirSim SimpleFlight sim: C++, no Unreal, no GPU, real time. Tasks B5/13/29/37 are "basic"; A3/5/6/7/8/9/16/20 are "advanced".
  - AeroEval runs in Gazebo + Aerostack2 (ROS 2, Docker). Tasks: D1–D3 delivery and F1 farm survey.
- 3 instances per task × 3 runs.
- **Reflexion only** for drone, max 3 iterations.
- The graph is supervisor → generator (writes Python drone code) → execute in sim → evaluator → reflector.
- The LLM writes code; the tool runs it in the simulator in **real time**.
- Verification: deterministic checks plus an LLM evaluator for CLGSCE; a programmatic Gazebo trajectory check for AeroEval.
- Serving:
  - SGLang 0.5.16, flags `--max-running-requests 1`, `--max-total-tokens 80000`, `--context-length 65536`.
  - The KV cache is flushed before every run, and thinking is on.
  - `max_tokens` is 32768 for the latest runs; older runs used 16384.
- Models:
  - `gemma-4-26B-A4B-it` in bf16: 125 runs done.
  - `Qwen3.8-27B-FP8`: planned, no data yet.
  - **Both are hybrid-attention.**
    - Gemma 4 26B-A4B: 25 of 30 layers are sliding-window (window 1024).
    - Qwen3.8-27B: 48 of 64 layers are linear attention (Gated DeltaNet), plus a fixed recurrent state per session.

**First pass over the 125 Thor Gemma traces** (`data/p1_thor_drone/`; single session,
cache flushed, Reflexion, thinking on):

| Class | Runs | Workflow time p50 / p90 | LLM share p50 | Tool share p50 | LLM calls / run p50 | Tool wait p50 / p90 | Prompt tok p50 / p90 | Peak ctx per call p90 | Calls hitting `max_tokens` |
|---|---|---|---|---|---|---|---|---|---|
| B (basic) | 36 | 76 s / 163 s | 0.75 | 0.22 | 2 | 13 s / 20 s | 2.6K / 7.0K | 9.1K | 0 / 93 |
| A (advanced) | 72 | 615 s / 3758 s | 0.89 | 0.11 | 2 | 37 s / 87 s | 7.0K / 7.3K | 39.8K | 46 / 310 |
| D/F (AeroEval) | 17 | 3337 s / 4268 s | 0.96 | 0.03 | 20 | 115 s / 914 s | 2.6K / 21.9K | 31.1K (max 54.7K) | 27 / 272 |

**What this suggests** (a first reading, to be confirmed):
1. **The runs are dominated by LLM time, not tool time.** Long thinking decodes (up to the 32K cap) dominate. Tool waits are real sim time, from 13 s up to about 15 min.
2. **The prompts do not form a growing conversation.** Each LLM call is a fresh, role-specific prompt: generator, evaluator, reflector. Most of each prompt is a static system/schema block. The state that can be reused across a tool wait is therefore mostly a **shared prefix** of roughly 2–7K tokens, not a long session history. Cache reuse is low even within one session (11–33% of prompt tokens).
3. **Under concurrency, pressure will come mainly from active decode**, since each session peaks at up to 40–55K tokens, rather than from paused state. The classic "keep KV during tool wait" opportunity looks **weak for A/B as-is**. D/F is the most promising: long tool waits and 22K-token prompts.
4. **Upper bound on what retention could save in a single session** (Thor traces). "Prefill share" is the fraction of LLM time spent in prefill. "Reusable" is the fraction of prompt tokens that repeat a prefix of an earlier call in the same session.

   | Class | Prefill share | Reusable | Actually cached on Thor | Max saving from perfect retention |
   |---|---|---|---|---|
   | A | 1.0% | 31% | 14% | ≈ 0.3% of LLM time |
   | B | 7.9% | 10% | 11% | ≈ 0.8% |
   | D/F | 2.5% | 66% | 33% | ≈ 1.7% |

   Across sessions of the same role, the shared prefix is 16% of the prompt for A, 57% for B and 83% for D/F. Radix caching shares these prefixes across sessions anyway.
5. Caveats:
   - Thor timings (~27 tok/s decode) differ from the WS and from Orin.
   - This is one model.
   - The cache is flushed per run.
   - We have not yet measured what SGLang actually retains during waits with hybrid models.

---

## 2. Track A — is there anything to study?

### 2.1 Goal and decision gate

Produce evidence showing whether the drone workflow, run as **concurrent sessions** on a
KV-constrained server, creates an opportunity for better retained-state management.

- **Opportunity exists** → continue with the drone (and later traffic) workloads.
- **No or weak opportunity** → run the minimal experiments for two paths:
  - **A1: Modify.** Change the P1 workflows so an opportunity exists, in ways we can defend as realistic.
  - **A2: Adopt.** Take workloads other work uses, after de-risking them.

In both cases, all evidence goes to the professor, **who makes the final call**.

Concurrency is a firm workload decision; single-session runs only characterize a task's shape.

### 2.2 What "opportunity" means, operationally

The default policy (SGLang radix cache: keep everything, then evict LRU under pressure)
makes a costly mistake in any of these three ways:

1. **Recompute waste.** When a session resumes after a tool call, it re-prefills tokens that were evicted during the wait. In P1's design, "resume" means the next call of the same session, which shares a role or system prefix.
   `wasted_prefill = (prompt_tokens − cached_tokens) − tokens_never_seen_before`
2. **Blocking by idle state.** Requests queue while a large share of the pool is held by sessions that are waiting on tools.
3. **Admission loss.** Fewer sessions fit than could, if paused state were placed better.

The **headroom** is how much of (1)–(3) a better policy, oracle or simple, could recover.
If the headroom is small at realistic concurrency, there is nothing to study.

**Go/no-go criteria.** These are fixed *before* the concurrent runs; thresholds are TBD
with the professor. They apply at an edge-plausible concurrency N ≤ `N_edge` and an
edge-like memory budget:
- [ ] Paused sessions hold ≥ `X`% of the pool during saturation.
- [ ] Wasted re-prefill ≥ `Y`% of prefill work/energy, **or** queueing caused by idle state ≥ `Z`% of task time.
- [ ] Tool waits are long enough to matter (median wait ≥ ~one LLM step).
- [ ] A simple non-default policy recovers ≥ `W`% (energy per successful task or p95 task time).

### 2.3 How we run drone sessions on the WS (decided: the real closed-loop stack)

We run P1's own agent code, MCP servers, tools and simulators on the WS: all tasks, a
different model (D1), and the full metric set. There is no replay and there are no stubs.

**CLGSCE (12 tasks) — no admin needed.**
- The "AirSim" sim is **not Unreal**. `thor_headless` is a ~210-line native C++ program: AirSim SimpleFlight + FastPhysics + RPC server on port 41451. It has no rendering, no GPU, only a flat ground plane, and steps at ~333 Hz in real time. So tool calls block on wall-clock flight time.
- Port:
  1. Build AirLib + `thor_headless.cpp` on x86 with g++ 11 / cmake. clang isn't installed, and AirLib builds with gcc, as in the AirSim ROS wrapper.
  2. `pip install` the AirSim PythonClient deps (msgpack-rpc).
  3. Run the CLGSCE MCP server + `clgsce_subagents_mcp.py` against our SGLang.
- Concurrency: **one (sim, MCP server) pair per session**, each on its own ports. This needs a small patch: a port argument for `thor_headless` and a configurable port in the MCP server and wrapper. Each sim uses ~1 CPU core.

**AeroEval (4 tasks: D1–D3, F1) — needs a container runtime.**
- It runs Gazebo (Harmonic) + ROS 2 Jazzy + Aerostack2, from source in an image (`aerostack2/jazzy-headless:arm64`) that has no Dockerfile. The validator runs `docker run --runtime nvidia --device /dev/dri ...`.
- On the WS we need: Docker or podman (admin), or unprivileged Apptainer (user namespaces are enabled); **plus an amd64 image**, built or taken from upstream Aerostack2.
- Runs are long (~40 min on Thor), and N sessions means N Gazebo stacks.
- **Phase 2**, after CLGSCE.

**Harness.**
- Port P1's `final_sweep/_harness` (`sweep.py`, `run_one.py`, `samplers.py`, `p1_trace.py`, `verdicts.py`), keeping its **output schema** so WS runs line up with Thor runs.
- Replace the Jetson `DeviceSampler` (tegrastats/sysfs) with an **NVML sampler** that includes GPU energy counters.
- Remove the single-run busy check.
- Add an **N-session concurrent driver**. With temperature 0, top-k 1 and seed 42, identical task instances produce identical trajectories, so concurrent sessions draw **different tasks/instances**.
  - **Correction, 2026-10-04.** That holds for our WS greedy runs. On P1's Jetsons, 23–25% of drone prompts took more than one path in 3 repeats at temperature 0 (P1's deck).
  - **Update, 2026-10-05.** P1's paper traces the divergence to inputs (simulator noise fed back to the agent; a timestamp in every traffic prompt), except gemma-E4B on the Orin 32, where inference itself differs.

**Paradigm.**
- There is **no tool-calling paradigm** for drone on the P1 device: all 126 runs are `reflexion`, and the only switch is `P1_ENABLE_REFLEXION`.
- There is an unused **"constrained ReAct"** for AeroEval at `aeroeval_gazebo_subagents/repo_side/react_aeroeval_gazebo.py`. It picks the next protocol-allowed action from the last observation only, so the context doesn't grow.
- **Re-checked on 2026-09-30, including `/media/ssd`:** P1 has no native tool-calling implementation and no results for one; all 209 paradigm entries are `reflexion`. P1 also has a `find_toolcalling.sh` helper (Sep 28) that searched for the same thing.
- **Correction, 2026-10-01:** P1 started a CLGSCE tool-calling sweep at 00:17 in `/home/yash/final_toolcalling_thor79/`. Each attempt builds a fresh prompt and makes one `execute_and_observe` call, so context does not accumulate. Details in `HANDOFF.md` §2.
- Two native tool-calling agents by another lab member (mayankarya) exist on the Thor. Neither was ever run at scale, and neither has traces.
  - `/media/ssd/drone/aeroeval/aerogen_mcp/`: a **drone** agent with 20 MCP tools over AeroStack2, ≤40 turns / 80 tool calls, and context accumulating in one `messages` list. Its pure-Python `sim` backend computes flight time but returns instantly, so it needs real-time pacing. 5 tasks (radio tower); needs only `openai` + `mcp`; 828 KB.
  - `/media/ssd/deepstream-mcp/`: a video-pipeline agent.
- → **Reflexion for now.** A native tool-calling variant (the model emits `tool_calls`, and context accumulates across turns) would have to be written. It stays a Path A1 lever.

### 2.4 Steps

**A0 — WS environment** (see §5)
- [x] Serving stack: reuse `~/legacy/jouleserve-ws/.venv` (SGLang 0.5.20 on driver 560, hybrid model verified).
- [ ] Add the harness deps (nvidia-ml-py, matplotlib, LangGraph pieces for R2).
- [ ] Model decision (D1). Download and smoke-test the server.
- [ ] Pin each server and its harness to the NUMA node of its GPU:
  - GPU0 ↔ cores 0–9, 20–29
  - GPU1 ↔ cores 10–19, 30–39

**A0.5 — Mine P1's Thor traces**
- [x] Copy the lightweight traces (125 runs, 58 MB) to `data/p1_thor_drone/`.
- [x] First-pass aggregates (§1).
- [ ] Per-session timelines G1 from `phase_windows`.
- [ ] Measure prefix overlap between consecutive calls of a session, and between sessions.
- [ ] Also copy the `server_kv.jsonl` samples (367 MB) to look at KV usage over time. Needs a lighter copy window on the P1 device.
- [ ] Refresh the traces when P1's Qwen3.8 runs land.

**A1 — Port the closed-loop stack** (§2.3)
- [ ] Snapshot P1's code to the WS by read-only copy, without logs or venvs:
  - the CLGSCE dir
  - `final_sweep/_harness`
  - `HeadlessThor/thor_headless.cpp`
  - the AeroEval dir
- [ ] Build AirLib + `thor_headless` on x86. Patch in port arguments.
- [ ] Deps venv: langgraph 1.2.11, langchain-openai 1.6.0, langchain-mcp-adapters 0.3.2, mcp 1.29.1, openai 3.5.0, numpy, msgpack-rpc-python (P1's `airsim-thor` versions).
- [ ] NVML device sampler. Keep P1's server sampler and trace hooks.
- [ ] Single-session smoke test: B5 i1 passes its verifier end to end.
- [ ] N-session driver with task/instance mixing, and one (sim, MCP) pair per session.
- [ ] Phase 2: a container runtime + amd64 Aerostack2 image → AeroEval tasks.

**A2 — Instrumentation.** Reuse P1's schema (`iterations.jsonl`, `server_kv.jsonl`, `run_meta.json`) wherever possible, and add:
- *Per call:*
  - `session_id`, `call_index`, `role`
  - `t_req`, `t_first_tok`, `t_last_tok`
  - `prompt_tokens`, `cached_tokens`, `completion_tokens`
  - `tokens_never_seen_before`
  - tool-wait window
- *Server (`/metrics`, 2–10 Hz):*
  - `num_used_tokens`, `token_usage` (full / SWA / recurrent pools), `max_total_num_tokens`
  - `num_running_reqs`, `num_queue_reqs`, cache hit rate
  - `evicted_tokens_total` (P1 already patched this in)
- *Device (NVML, 10 Hz):*
  - power
  - **cumulative energy counter**
  - SM/memory clocks, used memory, utilization, temperature
- *Derived:*
  - `demand(t)`: sum over live sessions
  - `paused_state(t)`: sessions in a tool wait
  - pressure ratio `demand / pool_capacity`
- One monotonic clock across all streams.

**A3 — E1: single-session characterization on the WS** (shape, not contention)
- Grid: 16 tasks × instances, with P1's paradigm and settings. Cold vs warm cache labeled.
- Graphs:
  - **G1** One-session timeline: LLM prefill/decode vs tool-wait segments, with live context/state overlaid.
  - **G2** Per-call prompt/completion tokens and cached share, by role and task class.
  - **G3** CDFs of tool-wait duration vs LLM call duration; idle:active ratio per task.
  - **G4** Prefix overlap: within a session across a tool wait, and across sessions.
  - **G5** Break-even per call: re-prefill time vs the preceding tool wait. Shows where evict-and-refetch can hide behind the wait and where it can't.

**A4 — E2: concurrency × memory-budget sweep** (the core experiment)
- Load: N ∈ {1, 2, 4, 8, 16, 32} sessions, with a task mix per class (B / A / D-F / all).
- Memory budget: default, plus caps that mimic Orin 32 GB, Orin 64 GB and Thor after weights, tools and OS (numbers calculated in A0).
- Graphs:
  - **G6** Pool usage over time, stacked **active decode vs paused/retained state**, with queue length on a second axis (one panel per N).
  - **G7** Against N: tasks/min; p50/p95 task time; resume cache-hit rate; wasted-prefill fraction; queueing delay; GPU energy per successful task.
  - **G8** Heatmap of N × budget → wasted-prefill fraction and energy per task (where the opportunity lives).
  - **G9** Share of the pool held by paused sessions at each eviction or queueing event.
- **Inflection points to report:**
  - N where demand first exceeds the pool (evictions start)
  - N where queueing becomes persistent
  - where the resume hit rate drops sharply
  - where p95 task time and energy per task bend upward

**A5 — Headroom estimate** (small)
- [ ] Offline trace simulation: default LRU vs Belady-style oracle vs "evict paused first" vs "pin the shared prefix".
- [ ] One live run of the best simple policy at the most promising (N, budget).

**A6 — Evidence pack → professor**
- [ ] 1–2 page summary: verdict on the drone workload as it is, graphs G1–G9, whether the go/no-go criteria are met, WS→edge caveats (§4).
- [ ] If the verdict is weak or negative, include the A1 and A2 minimal-experiment results (§2.5), a recommendation and the risks.

### 2.5 If there is no opportunity: minimal experiments for the two paths

**Path A1 — Modify the P1 workflows.** Each lever needs a one-line realism argument for drones:

| Lever | Effect on opportunity | Realism argument |
|---|---|---|
| Accumulating-conversation agent (tool-calling / ReAct) instead of fresh per-role prompts | state grows across tool waits and reuse becomes large | the standard agent pattern; P1's deck lists these paradigms |
| Keep D/F-style long tool waits; add physical-time tools (transit, hover, capture) to CLGSCE | longer waits | real flight time |
| Richer observations (telemetry dumps, detections, map tiles) | faster context growth | perception output is large |
| Fleet: one agent per drone, served by one edge box | natural concurrency | ground-station edge node |
| Perception model sharing the GPU | memory competition with KV | on Orin/Thor, it's the same unified memory |
| Thinking budget (32K cap) | shifts the balance between active and paused pressure | edge deployments cap reasoning |

Minimal experiment: 3–4 representative tasks × 1–2 levers × E2 at 2–3 values of N. Compare the opportunity metrics with the unmodified workload.

**Path A2 — Adopt external workloads.**
- Candidates (to be confirmed by Track B):
  - INFERCEPT's augmentation workloads
  - Continuum's agent traces
  - TokenCake's multi-agent apps
  - AgentServe (ToolBench / ReAct / plan-and-execute)
  - KAIROS's agent benchmarks
  - Adaptive KV Retention (human-approval waits)
  - MLPerf Edge Agentic (Qwen3.6-27B on Thor, replayed trajectories)
  - AgentSysBench
- **De-risk checklist per candidate:**
  - code or traces public?
  - license?
  - runs locally without cloud APIs?
  - edge-plausible (P1 argues against coding agents)?
  - tool-wait and context-growth distributions?
  - is concurrency natural?
- Minimal experiment: the top 1–2 candidates through the same harness and E2 grid, producing G6–G8.

---

## 3. Track B — prior-work re-review (TBD)

- **B1** For each paper in `review/source_register.csv`, extract: workloads and traces, tool-wait model, concurrency and arrival model, assumptions (memory tiers, discrete GPU, **full-attention vs hybrid models**), controller design, baselines, metrics. `TBD`: extraction template.
- **B2** What JouleServe must add beyond each one. Feeds the novelty statement and baselines.
- **B3** Feed the A2 candidate list and de-risk checklist.
- **B4** Full-text extraction for CacheScout and Adaptive KV Retention (currently abstract-only).
- **B5 (new)** How prior KV-retention work handles **hybrid models** (sliding-window or recurrent state, which can't be partly evicted). Both P1 models are hybrid, so this may change the problem or open an angle.

## 4. WS → edge: what transfers (TBD, grows with Track A/B)

| Transfers (roughly) | Does not transfer |
|---|---|
| Calls per task, token counts, prefix structure | Absolute timings: A5000 ≈ 768 GB/s vs Orin 205 GB/s; Thor differs again |
| Tool-wait distribution (sim real time) | Energy: GPU-only NVML vs board-level rails |
| Where inflection points fall *relative to* the memory budget | Unified memory: "offload to host" is the same DRAM on Jetson |
| Relative ranking of simple policies (to be verified) | Thermal throttling; simulators (the AirSim sim on the CPU, Gazebo on the CPU/GPU) and tools contending on the same SoC |

To do: calibrate a Thor↔WS time-scaling factor from A0.5 plus our WS runs, so idle:active ratios can be mapped between devices.

## 5. Environment status (WS `10.24.32.174`, checked 2026-09-30)

**Hardware and base software**
- 2× RTX A5000 24 GB, **no NVLink**: the GPUs are on different sockets and NUMA nodes (topology shows `SYS`).
- 2× Xeon Silver 4410T (40 threads), 251 GB RAM, ~318 GB disk free.
- Driver **560.28.03 (CUDA 12.6)**, nvcc 12.6, gcc 11.4, cmake, ninja, git, tmux, htop.
- `uv` at `~/.local/bin`, with Pythons 3.10, 3.11 and 3.12.
- Internet access to HF, PyPI and GitHub.
- The Vulkan loader and the NVIDIA ICD are present, so headless Unreal/AirSim might work.

**Serving venv: reuse the legacy one (works, verified 2026-09-30)**
- Location: `~/legacy/jouleserve-ws/.venv`
  - Python 3.11, **SGLang 0.5.20**, **torch 2.13.0+cu126**, flashinfer 0.6.18, sglang-kernel 0.4.7.
  - The package list is in `~/legacy/jouleserve-ws/stack-freeze.txt`.
- Launch recipe (from hostov):
  ```bash
  L=~/legacy/jouleserve-ws
  export LD_LIBRARY_PATH=$L/.venv/lib/python3.11/site-packages/nvidia/cu13/lib:$LD_LIBRARY_PATH
  CUDA_VISIBLE_DEVICES=1 taskset -c 10-19 $L/.venv/bin/python -m sglang.launch_server ...
  ```
  Use `python -m ...`. The venv was moved, so its `bin/` entry-point shebangs may be stale.
- Smoke test passed with **`Qwen/Qwen3.5-0.8B`** on GPU 1. This is the same `qwen3_5` hybrid architecture as Qwen3.8: it booted in 106 s, served chat completions, and `/metrics` works.
- Known limitation: sgl_kernel's CUDA 13 kernels fail with `cudaErrorInsufficientDriver` on some paths, e.g. HiCache `--hicache-io-backend kernel`. Use `direct` for HiCache.
- Harmless noise: torchcodec/FFmpeg import errors at startup.
- Why not a fresh install: every SGLang ≥ 0.5.11 requires CUDA 13 (`cuda-python>=13`), which driver 560 can't run. The last CUDA 12 release (0.5.10) is older than what we have.
- P1 uses 0.5.16, so our version differs. Record it in every run.
- Other legacy venvs:
  - `.venv-sgl0516`: SGLang 0.5.16, torch 2.11, CUDA 13 build. Probably unusable on driver 560.
  - `.venv-workflow`: langgraph 1.2.12, mcp 2.2.0, openai 3.17. P1 uses langgraph 1.2.11, mcp 1.29.1, langchain-openai 1.6.0 and langchain-mcp-adapters 0.3.2; add these for R2.

**What the smoke test showed about hybrid models in SGLang** (relevant to Track A):
- The retained state of hybrid models lives in **separate pools**: `full_token_usage` (full-attention KV), `mamba_usage` / `mamba_available_tokens` (recurrent-state slots) and `swa_*`.
- The mamba pool had only ~314 slots, even for a 0.8B model with mem-fraction 0.6.
- Prefix reuse uses a mamba radix cache (`extra_buffer`) that **checkpoints state every 256 tokens** (`mamba_track_interval`). A repeated 53-token prompt got no cache hit.
- **Implication:** with hybrid models, what limits how many sessions can hold state, and how much reuse survives a tool wait, may be the state-slot pool and checkpoint granularity, not KV tokens. Measure this in E1/E2.

**K2 Horizon 7B on one A5000, bf16, measured 2026-09-30**
- Flags: `--mem-fraction-static 0.88 --cuda-graph-max-bs-decode 16 --disable-prefill-cuda-graph --context-length 65536 --reasoning-parser k2_horizon --tool-call-parser k2_horizon`.
  - The auto fraction of 0.70 leaves no room for KV.
  - At 0.90, the server hits OOM during graph capture.
- Weights take 17.0 GB. **KV pool: 25,427 tokens** (3.5 GB, 144 KiB/token).
- Decode: **36.5 tok/s** at batch 1, close to the bandwidth limit (~17 GB of weights read per token).
- Prefix cache: a repeated 6.2K-token prefix gives 6,232 cached tokens and a TTFT of 0.09 s.
- A P1-style request (7K prompt + `max_tokens` 32768) is accepted. We have not yet tested what happens when generation exceeds the pool.
- Wall time: single-session decode speed is similar to Thor's Gemma (27 tok/s). P1's CLGSCE sweep took **~30 h** on Thor (A: 72 runs, 28.8 h; B: 36 runs, 1.0 h), so expect a similar order on the WS.

**We can install these ourselves** (`uv` venv): anything missing (LangGraph extras, nvidia-ml-py, matplotlib).

**Needs the admin:**
- ~~Driver upgrade~~: not needed; we reuse the legacy venv. A driver ≥ 580 would only let us match P1's 0.5.16 exactly.
- **Container runtime for AeroEval (phase 2)**: Docker + the nvidia container toolkit, or rootless podman (needs `uidmap`). Alternative with no admin: unprivileged Apptainer (user namespaces are enabled).
- Readable RAPL `energy_uj`, for CPU/package energy.
- GPU clock and power-limit control, and persistence mode. Only needed if we emulate slower clocks.
- `jq`, `nvtop`: nice-to-have.

## 6. Decisions

| ID | Decision | Status |
|---|---|---|
| D1 | Model on the WS: a small model from the AA list that is **bf16 and supported** | **decided: `IFM/K2-Horizon-7B`, bf16. Step 1 on a single GPU; TP=2, quantization or FP8 KV for concurrency still under discussion** |
| D2 | Load model: closed-loop N workers (default) vs open-loop arrivals (later) | default: closed-loop |
| D3 | Paradigm | **decided: Reflexion** (no tool-calling exists for drone); tool-calling is an A1 lever. *Superseded:* P1 has run a tool-calling sweep since 2026-10-01, and our step-wise runs use aerogen |
| D4 | Go/no-go thresholds (`X`, `Y`, `Z`, `W`, `N_edge`) | agree with the professor before E2 |
| D5 | How to run drone on the WS | **decided: the real closed-loop stack** (§2.3): CLGSCE first, AeroEval second |

**D1 details: the two models under 20B on the AA "small" list, both natively supported in SGLang 0.5.20**

| | K2 Horizon 7B (IFM) | Ling 3.0 Tiny (inclusionAI) |
|---|---|---|
| AA Intelligence Index | **21** | 15 |
| Architecture | dense, **standard full attention** (36 layers, 8 KV heads × 128) | MoE 7.9B / 1.3B active, **hybrid linear attention** |
| Retained state | plain KV, ~144 KiB/token (bf16), the same thing prior work assumes | small KV plus recurrent state (like Qwen3.8) |
| bf16 weights | 18 GB (large 250K vocab) | 15.8 GB |
| Fit | **TP=2**: a single A5000 leaves ~3 GB of KV, less than one P1 call at its peak (40–55K tokens ≈ 6–8 GB) | one GPU (~5–6 GB of state left), or TP=2 |
| SGLang | `xllm.py`; `--reasoning-parser k2_horizon --tool-call-parser k2_horizon` | `bailing_moe_v3.py` |
| License | Apache-2.0 | MIT |

Proposal: **K2 Horizon 7B, bf16, TP=2.** It is the best-scoring model under 20B, and its
classic KV cache gives a clean baseline against prior work. Hybrid-state behaviour stays
covered through P1's Gemma/Qwen models on the edge.

## 7. Proposed repo layout (created as needed)

```
planning/   PLAN.md, decision records
review/     literature evidence (carried over)
harness/    session driver (replay / live), metric collectors
analysis/   scripts that produce G1–G9
data/       copied P1 traces (git-ignored)
runs/       raw run outputs (git-ignored; summaries committed)
```

---

## Appendix A — P1 drone code map (P1 device `yash@10.24.24.79`, Jetson AGX Thor; look only)

**Sweep harness:** `/home/yash/final_sweep/_harness/`
- `sweep.py`, `run_one.py`, `instances.py`, `samplers.py`, `p1_trace.py`, `verdicts.py`
- `ensure_infra.sh`, `launch_aeroeval.sh`

**Results:** `/home/yash/final_sweep/<model>/<task>/instance_<i>/run_<k>/`
- `run_meta.json`, `iterations.jsonl`, `llm_calls.jsonl`, `mcp_calls.jsonl`
- `server_kv.jsonl`, `device_samples.jsonl`
- `task.txt`, `trajectory.json`, `transcript.log`

**Index:** `/home/yash/final_sweep/index.csv`

**CLGSCE (AirSim):** `/home/yash/agentic_aeroeval/vendor/CLGSCE/`
- Agent: `clgsce_subagents.py`, `clgsce_subagents_mcp.py`
- MCP server: `clgsce_mcp_server.py`, port 8001
- Tasks: `task_sets/{basic,advanced}.txt`
- Simulator: `/home/yash/airsim_thor_test/AirSim/HeadlessThor/thor_headless`
- Upstream: `github.com/ai-uavsec/CLGSCE`

**AeroEval (Gazebo/Aerostack2):** `/home/yash/aeroeval_gazebo_subagents/`
- Agent: `agent/gazebo_aeroeval_subagents.py`
- MCP servers: `mcp_servers/`
- Validation: `gazebo_validation/`
- Docker image: `aerostack2/jazzy-headless:arm64`

**SGLang launch:** `/home/yash/launch_gemma_it_sweep.sh`, `/home/yash/run_qwen_reflexion.sh`

**Conda envs:** `/opt/miniconda3/envs/{airsim-thor,aeroagent,sglang,vllm}`

**Safety note.** `run_one.py` refuses to start, and the sweep halts after 2 failures, if a
process command line contains `run_one.py`, `sweep.py`, `clgsce_subagents_mcp.py`,
`gazebo_aeroeval_subagents.py`, `run_16_reflexion` or `gz_farm_test`. Never run anything
with those names on the P1 device.

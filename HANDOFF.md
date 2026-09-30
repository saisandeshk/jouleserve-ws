# HANDOFF — jouleserve-ws

**Last updated:** 2026-09-30, ~21:00 IST, by a Claude Code session that reviewed the project
state. Rules, machines and recipes live in [`AGENTS.md`](AGENTS.md). This file holds the state
at the time of writing.

**Update this file at the end of every working session.** Replace stale facts rather than
appending history, which git already keeps.

---

## 1. The goal

**Long term (P5 / JouleServe).**
- We are building a serving-layer controller for Jetson-class edge devices.
- It decides what to do with an agent session's retained state (dense KV, SWA/recurrent state)
  while the session waits on a tool, such as a simulator flight, a sensor or an actuator. The
  options are keep, soft-pin, hold for a time-to-live, drop and recompute later, or change
  admission and preemption so that idle state does not block active work.
- **Headline metric:** energy per successful task, at an equal or better success rate and p95
  latency.
- **Where the contribution must come from.** The generic version ("keep KV across tool
  pauses") is already published: INFERCEPT, Continuum, TokenCake, Adaptive KV Retention,
  CacheScout; KAIROS for energy. So the contribution has to come from what is different at the
  edge:
  - unified memory (no host tier to offload to)
  - bandwidth and power shared with the tools and simulators
  - thermal state
  - hybrid models
  - tool waits of 10 s to 10 min that come from physical actuation

**Right now.** All edge devices are with P1 until their deadline, so P5 has only the 2×A5000
workstation. WS work must still pay off once the devices come back. That gives three strands:
1. **Track A: is there an opportunity at all?** This is the gating risk.
   - The question: does a realistic workload create enough retained-state pressure for a
     policy to matter? We start with P1's drone workflow, run as **concurrent sessions** under
     edge-like KV budgets.
   - P1's Thor traces say "barely" *for a single session of Reflexion as it stands*. That
     doesn't settle it, because concurrency changes the picture:
     - Under load, pressure will probably come from active 32K-token thinking decodes rather
       than paused state. That points toward admission and preemption (H1) more than classic
       retention.
   - If the opportunity is weak, there are two paths, and the professor decides between them:
     - **A1:** modify the workflow in defensible ways (e.g., native tool calling with an
       accumulating context, longer physical-time tools, a drone fleet sharing one box).
     - **A2:** adopt workloads other papers use.
2. **Track B: what did prior work actually do?** Their workloads, assumptions (host tier,
   discrete GPU, full attention), controllers and baselines. From that: what JouleServe must
   add, and what changes between the WS and the edge. A first pass is done.
3. **JouleServe-WS: the platform.** Answer both tracks on a reusable platform rather than one-off
   scripts:
   - an OpenAI-compatible gateway in front of SGLang, with a per-session phase FSM and policy
     hooks
   - NVML energy
   - P1-compatible traces
   - the must-have baselines
   - platform differences behind adapters (`DeviceTelemetry`, `EngineAdapter`, `MemoryModel`),
     so that moving to Orin/Thor is an adapter swap

**Sandesh's stated near-term intent** (2026-09-30, before this handoff):
1. Run one P1 workflow (drone) on the WS to see whether an opportunity exists, since small,
   quick workloads with no KV pressure are no use to us.
2. In parallel, re-review prior work: their workflows, assumptions and controllers, what
   JouleServe must add, and what changes from the WS to the edge.

Sandesh will set the concrete next plan after this handoff.

## 2. Situation as of 2026-09-30 ~21:00 IST

**P1 (EdgeAgentBench)**
- **Gemma-4-26B-A4B drone sweep:** finished at **20:26 today**. All 144 runs are done: 102
  pass, 38 fail, 4 partial.
  - The AeroEval tasks finished today, and almost all failed:
    - D3_OUTBACK: 8 fail, 1 partial.
    - F1_FARM_SURVEY: 9 fail (`validator_reject`), about 72 min per run.
- **Tool-calling CLGSCE sweep (Gemma):** **running** since 2026-10-01 00:17 in
  `/home/yash/final_toolcalling_thor79/`. At ~01:10, 18 of 108 runs were done.
  - The agent is `_harness/clgsce_openai_toolcalling.py`. It has the same shape as Reflexion
    minus the reflector: each attempt builds a *fresh* generator prompt, makes exactly one
    `execute_and_observe` tool call, then runs an evaluator (2 calls).
  - Measured on the 18 finished runs: 3 LLM calls and 2 tool calls per run, 0–1% cache
    reuse, prompts of at most ~5.6K tokens, prefill 3.5% (A) / 10.7% (B) of LLM time.
  - **So a sweep is live on the Thor: follow the busy-check rules strictly.**
- **Qwen3.8-27B:** 144 entries in the index, **0 runs** so far.
- **Traffic workload:** not yet located for P1.
  - mayankarya has a DeepStream camera/traffic query agent at
    `/media/ssd/Deepstream-Yolo-upstream/camera_query_agent/` (with `traffic_agent/`
    alongside). It is ReAct with an accumulating transcript and has 22 Thor traces.
  - Whether this is P1's traffic workload is unknown.
- **Predictor:** not started.

**WS**
- Idle: both GPUs near 0 MiB, no tmux sessions.
- HF cache holds `IFM/K2-Horizon-7B` and `Qwen/Qwen3.5-0.8B`. Legacy holds Qwen3.5-9B.
- The clone at `~/jouleserve-ws` tracks `origin/main`.

**This repo**
- The planning docs, the Track B review (`review/systems/`), `.gitignore` and the handoff docs
  (`AGENTS.md`, `CLAUDE.md`, `HANDOFF.md`) were committed and pushed to `origin/main` on
  2026-09-30. The WS clone was pulled to match.

**People**
- Sandesh works on P5 alone.
- P1 members join P5 after P1's submission deadline.
- The professor decides P5's direction at the M2 gate (`JOULESERVE_WS_PLAN.md` §5).

## 3. What exists

| Area | State | Where |
|---|---|---|
| Literature, legacy evidence | carried over (claim ledger, decision matrix, paper cards, source register) | `review/*.csv`, `review/paper_cards.md` |
| Track B per-system review | 30 docs (29 systems + a workloads catalog) + synthesis (F1–F10, baselines, H1–H5). Mostly fetch-and-summarize depth; TAWS is abstract-only | `review/systems/` |
| Master plan | v1.0: architecture, M0–M6, edge plan, risks | `planning/JOULESERVE_WS_PLAN.md` |
| Track A notes | draft v0.4: Thor trace first pass, WS env facts, decisions D1–D5 | `planning/PLAN.md` |
| P1 traces (lightweight) | 126 Gemma runs (A, B, D1, D2). **Missing:** D3/F1 (18 runs) and all `server_kv.jsonl` files (367 MB) | `data/p1_thor_drone/` (git-ignored) |
| WS serving stack | verified: SGLang 0.5.20; Qwen3.5-0.8B hybrid smoke test; K2 Horizon tp1 measured | `AGENTS.md` §5; logs in WS `~/scratch/` |
| Legacy WS assets | x86 sim binary, P1 code snapshot, runner, KV benchmarks | `AGENTS.md` §6 |
| JouleServe-WS code (`jsw/`, `configs/`, `analysis/`, `tests/`) | **not started** | — |
| M0 (skeleton, samplers, manifest, tp2 pool size) | **not started** | — |
| CLGSCE port, concurrent drone runs, go/no-go thresholds | **not started** | — |

## 4. What we know (headlines; details in the linked docs)

**P1 drone traces** (Thor, Gemma, single session, cache flushed; `PLAN.md` §1)

| Class | Workflow p50 | LLM share | Tool wait p50 | Peak context p90 | Max saving from perfect retention |
|---|---|---|---|---|---|
| B (4 tasks) | 76 s | 0.75 | 13 s | 9.1K | ≈0.8% of LLM time |
| A (8 tasks) | 615 s | 0.89 | 37 s | 39.8K | ≈0.3% |
| D/F (AeroEval) | 3337 s | 0.96 | 115 s | 31.1K (max 54.7K) | ≈1.7% |

- The runs are decode-dominated: thinking is on, with a 32K `max_tokens` cap, and prefill is
  only 1–8% of LLM time.
- The Reflexion roles (generator, evaluator, reflector) rebuild their prompts on every call,
  so only 10–31% of a CLGSCE prompt is reusable.
- **P1's paradigms don't accumulate context.** P1's tool-calling agent (see §2) passes the
  whole program as one tool argument. The AeroEval ReAct in Gazebo keeps only the last
  observation.
- **`aerogen_mcp` does accumulate** (verified 2026-10-01). It is a drone agent by mayankarya
  at `/media/ssd/drone/aeroeval/aerogen_mcp/`:
  - One `messages` list per mission gets every assistant turn and tool result appended;
    ≤40 turns and ≤80 tool calls.
  - 20 MCP tools. The system prompt is ~32K chars (~8K tokens) plus the tool schemas.
  - The pure-Python `sim` backend computes `flight_time_s` from distance and speed (max
    2 m/s) but doesn't wait for it, so waits need pacing.
  - Only 5 tasks; never run at scale.
  - The default model is o3-mini, and a random system-prompt prefix defeats caching. Both
    must change for our use.

**Track B** (`review/systems/README.md` §3)
- **F1:** every published retention rule says "discard" on P1 Reflexion as it stands.
- **F2:** paradigm decides reuse. Accumulating tool-calling contexts reuse 96–99% of the
  prompt; rebuilt prompts reuse 1–31%.
- **F3:** our 10 s–10 min pause regime is a gap in the literature. Adaptive's break-even hold
  time is t\* ≈ 109 s on an H100.
- **F4:** under concurrency, long active decodes dominate, and no published scheduler handles
  them.
- **F5:** the host tier collapses on unified memory.
- **F6:** without root, the energy levers are scheduling levers.
- **F7:** nobody attributes tool-wait energy per session.
- **F8:** hybrid state is only reusable at checkpoints.
- **F9:** the gateway can give exact tool hints.
- **F10:** KAIROS assumes retention and never decides it.
- **SGLang 0.5.20 has no external pin/evict API.** The levers are sessions (soft/hard pin),
  per-request priority with the `priority` eviction policy, and admission and abort.
  Retraction is pure recompute.

**WS measurements**
- K2 Horizon 7B (dense, bf16) on tp1: 17.0 GB of weights, a **25,427-token KV pool**
  (144 KiB/token), and **36.5 tok/s** decode.
  - A repeated 6.2K-token prefix is served from cache with a TTFT of 0.09 s.
- Hybrid models in SGLang keep separate pools (full/SWA/mamba). The mamba radix cache
  checkpoints every 256 tokens, so a repeated 53-token prompt got no cache hit.

**Legacy KV benchmarks** (Qwen3.5-9B on an A5000, Sep 22; `~/legacy/jouleserve-ws/benchmarker/`)
- **K4:** with no memory pressure and a 3 s pause, retain beats flush in all 36 cells, and
  their order never flips. Retaining saves 93 / 335 / 1478 ms for 512 / 2K / 8K prompts.
- **K5:** on a 16.2K pool, eviction is a sharp step. **One** competing 8K context evicts the
  held one completely (cached tokens are either 0 or 8000). Retraction never triggered, because
  the mamba model ran one request at a time.

## 5. Found in this audit, not yet reflected in the plans

1. **The CLGSCE port is further along than the plan says.**
   - The legacy x86 sim binary is built from a `thor_headless.cpp` that is byte-identical to
     P1's current source.
   - `airsim_wrapper.py`, `clgsce_subagents_mcp.py` and the prompts also match.
   - Still left:
     - re-copy `clgsce_mcp_server.py` and `clgsce_subagents.py` (changed on 2026-09-23)
     - copy `task_sets/advanced.txt` and P1's `final_sweep/_harness` (use a directory copy,
       per the busy-check rule)
     - patch the hard-coded RPC port 41451 and rebuild
     - replace P1's `pkill -x thor_headless` reset with an owned process group
       (`sim_handle.py`)
2. **A P1-style session does not fit one GPU's pool.**
   - One A-class call peaks at ~40K tokens (up to 55K for D/F), against a 25.4K pool on tp1.
     We haven't tested what SGLang does when a single decode outgrows the pool; most likely it
     retracts the request or aborts.
   - So concurrency sweeps with P1 settings need one of:
     - tp2: pool not measured yet; the plan estimates ~170K, about 4 A-class peaks
     - a lower `max_tokens`
     - FP8 KV or quantization (D9)
   - The cap on `max_tokens` is itself one of the A1 levers.
3. **Budget WS time.** P1's single-session CLGSCE sweep took ~30 h on the Thor (A class:
   28.8 h for 72 runs). Single-session decode speed on the WS is similar, so a full single-run
   grid is on the order of a GPU-day. Start with B plus a subset of A, one run per instance.
4. **The local P1 trace copy is behind.** It lacks D3/F1 (18 runs, finished today) and the
   `server_kv.jsonl` time series. The Thor looks idle between sweeps right now, which is the
   lighter copy window `PLAN.md` A0.5 asks for.
5. **Small doc drift.**
   - `PLAN.md` says "125 runs"; the copy has 126 run dirs, one with an empty `final_result`.
   - Legacy scripts hard-code `~/jouleserve-ws/...`, but the legacy tree now lives at
     `~/legacy/jouleserve-ws/`.

## 6. Next steps

Sandesh will set the concrete plan after this handoff. What the documents currently say to
do first (`JOULESERVE_WS_PLAN.md` §5, "what we run first"):
1. **M0:**
   - repo skeleton
   - `env/stack-freeze.txt`
   - engine profiles (tp1/tp2); measure the tp2 pool
   - NVML + `/metrics` samplers
   - run manifest and smoke test
2. **CLGSCE port.** The legacy assets make this mostly re-sync, port patch and harness work
   (§5.1).
3. **Permissions.** Ask the P1 team and the `aerogen_mcp` author before vendoring their code.
4. **Resume Track A** (`PLAN.md` §2.4) on the new infrastructure:
   - E1: single session
   - E2: N × budget sweep
   - headroom estimate
   - evidence pack for the professor

## 7. Open questions for Sandesh

Mark each one answered here, or move the answer into the plans as a D-number.

1. Reuse the legacy x86 sim binary and re-sync only the changed P1 files, rather than
   rebuilding from scratch? (Recommended.)
2. **Model and pool.** K2 Horizon 7B was chosen in D1, but P1-style sessions overflow a tp1
   pool. Which do we want?
   - tp2 bf16 as the default for concurrency sweeps
   - or also a hybrid model (the legacy Qwen3.5-9B, Qwen3.8's family) on the WS for H3
3. **Go/no-go thresholds (D4).** Has the professor given values for `X`/`Y`/`Z`/`W` and an
   edge-plausible `N_edge` (e.g., drones per ground-station box)?
4. **Traffic workload.** Where does it live (which device or repo), and is it in scope for P5
   before P1's deadline?
5. **Permissions and copying.**
   - Has anyone asked the P1 team about vendoring their code, or mayankarya about
     `aerogen_mcp`?
   - OK to pull D3/F1 and the `server_kv.jsonl` files from the Thor now, while it's idle?
6. **Timeline.** When is P1's submission deadline, when do the devices come back, and when
   are the ISP milestones or report due? Also: is the WS exclusively ours, or shared?
7. ~~**Git.** OK to commit and push the planning/review files and the handoff docs?~~
   Answered 2026-09-30: yes. Done.

## 8. Resume checklist for a new session

1. Read `AGENTS.md`, then this file (§2, §5, §7).
2. `git status` and `git log --oneline -5`. Check whether the WS clone is behind origin.
3. WS: `nvidia-smi; tmux ls`. Is anything of ours running?
4. Thor (read-only, busy-check safe): `tail -3 /home/yash/final_sweep/*/sweep.log` and
   `wc -l /home/yash/final_sweep/index.csv`, to see whether P1's state has changed.
5. Continue from §6, or from whatever Sandesh has set since. Update this file at the end.

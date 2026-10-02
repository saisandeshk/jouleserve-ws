# HANDOFF — jouleserve-ws

**Last updated:** 2026-10-02, after merging all reports into the shared doc and its repo copy
(`reports/2026-10-02-p5-evidence`). The step-wise D1 test (108 missions on the WS) ran ~00:05–01:32. Rules, machines, recipes and WS gotchas are in [`AGENTS.md`](AGENTS.md). This
file holds the state at the time of writing.

**Update this file at the end of every working session.** Replace stale facts rather than
appending history, which git already keeps.

---

## 1. The goal

**P5 / JouleServe.**
- **What:** a serving-layer controller for Jetson-class edge devices. It decides what
  happens to an agent session's retained state (KV, and SWA/recurrent state for hybrid
  models) while the session waits on a tool: keep, drop and recompute, offload, or change
  admission so that idle state does not block active work.
- **Metric:** energy per successful task.
- **Where the contribution must come from:** generic "keep KV across tool pauses" is taken
  (INFERCEPT, Continuum, TokenCake, Adaptive KV Retention, CacheScout; KAIROS for energy).
  It must come from what the edge changes: unified memory, shared bandwidth and power,
  thermal state, hybrid models, and 10 s–10 min physical tool waits.
- **Resources:** the edge devices are with P1 until their deadline. P5 has the 2×A5000
  workstation, and WS work must pay off later.

## 2. Situation as of 2026-10-01 ~06:20 IST

- **Evidence pack (the main output of the night).**
  - Report: [`reports/2026-10-01-workload-opportunity/README.md`](reports/2026-10-01-workload-opportunity/README.md)
    (figures, data JSON and methods beside it).
  - Shareable doc: **"JouleServe (P5): drone workload evidence and options"**, a Claude Doc at
    https://claude.ai/code/artifact/474eee56-2e2f-44f9-8b97-f7bb51b588c7.
    - On 2026-10-02 it was rewritten to merge all three reports, at Sandesh's request: what P5
      asks, the ceiling formula, P1's workloads, P1's agents, the step-wise evidence, costs,
      options A/B/C, decisions and next steps.
    - It has two new charts drawn from rows (the ceiling per agent; output per step) and keeps
      the policy-simulation chart.
    - Its repo copy is
      [`reports/2026-10-02-p5-evidence/README.md`](reports/2026-10-02-p5-evidence/README.md).
      Keep the two in sync.
    - It is private until Sandesh shares it from its Share menu.
  - It answers the Track A question and recommends a direction. **Nothing has been shown to
    the professor yet.**
  - **Teaching guide** (2026-10-02, at Sandesh's request): **"JouleServe (P5): a teaching
    guide"**, a Claude Doc at https://claude.ai/code/artifact/36c2319c-b866-44f2-8dcf-42c02cdfd18c.
    - It is for a new intern who knows LLM basics, and has 20 sections: inference and the KV
      cache, hybrid state, agents, energy, the retention ceiling, the design space, prior work
      in depth, Orin/Thor, the controller architecture, evaluation, the roadmap, P1 and its
      tasks one by one, the evidence, the options, a self-test and a glossary.
    - It has no repo copy (export it from the doc's menu if needed).
    - One open comment in it asks Sandesh how many drones per device to plan for.
- **P1 mentor feedback (2026-10-01)** was that P1's drone set is 12 CLGSCE + 4 AeroEval tasks,
  and that aerogen is not P1's workload. The answer is
  [`reports/2026-10-01-p1-task-overview/README.md`](reports/2026-10-01-p1-task-overview/README.md):
  where AeroEval lives, the full task inventory, per-task numbers, what can be used, and
  questions for the mentor (its §7).
- **Step-wise test (2026-10-02, ~00:05–01:32):**
  [`reports/2026-10-02-stepwise-d1/README.md`](reports/2026-10-02-stepwise-d1/README.md).
  It is the deciding test for option B in the task overview (§6–7). Sandesh takes both reports
  to the P1 mentor on the morning of 2026-10-02.
- **Sandesh** said (2026-10-01) that they have their own idea of how to approach the next
  step and will share it. The report's options and decisions (§6–7) are input to that
  discussion, not a plan.
- **WS: idle.** The 2026-10-02 runs finished at 01:32 and everything was torn down: both GPUs
  are back to 15–47 MiB, with no tmux sessions.
  - Runs are in `~/work/runs/`, copied to local `data/ws_runs/` (git-ignored).
  - The aerogen private copy is at `~/work/aeroeval/` (see `AGENTS.md` §6b).
- **P1 (Thor), checked 2026-10-01 23:00.**
  - The Gemma Reflexion sweep is complete: 144 runs, 102 pass, 4 partial, 38 fail. On
    2026-10-01 P1 wrote a dataset README for it (`/home/yash/final_sweep/drones_README.md`),
    which looks like release packaging.
  - A **tool-calling CLGSCE sweep** has been running since 2026-10-01 00:17
    (`/home/yash/final_toolcalling_thor79/`). It covers 12 CLGSCE tasks × 3 instances × 3
    runs = 108 runs. At 23:00, 35 were done (all instance 1) and 27 had passed. About 46 h
    remain, so the Thor is busy until about the night of 2026-10-03. All 35 runs were copied
    to `data/p1_thor_toolcalling/` at 23:10, without `server_kv` or `device_samples`.
  - Qwen3.8: 144 run folders are laid out, but there are no runs. Predictor: not started.
    The Thor is live, so follow the busy-check rules.
- **Repo:** tonight's harness, analysis and report are committed and pushed. The WS clone is
  pulled.

## 3. What was built overnight (JouleServe-WS pieces)

| Piece | Where | Notes |
|---|---|---|
| Telemetry samplers | `jsw/telemetry/samplers.py` | NVML at 10 Hz (power, **energy counter**, clocks, throttle) and SGLang `/metrics` at 2 Hz (incl. `kv_used_tokens`, `kv_evictable_tokens`, `evicted_tokens_total`, queue) |
| aerogen driver | `jsw/workloads/aerogen_driver.py` (+ `aerogen_peek.py`) | Runs mayankarya's agent unmodified, patching the client and MCP call at runtime. Logs per LLM call and per tool call. N closed-loop session slots, manifest per run |
| Cost calibration | `jsw/costs/calibrate.py` | Idle power, cold/warm prefill time and energy against length, decode J/token against batch |
| Analysis | `analysis/sessions.py`, `report_figures.py`, `headroom_sim.py`, `sim_validate.py`, `p1_cache_misses.py`, `doc_charts.py` | One session model for P1 traces and WS runs; figures; trace-driven policy simulator checked against live runs; Claude-Doc chart modules |
| Launch / queues | `env/launch_k2_tp1.sh`, `env/queue*.sh` | Queues are the record of what ran overnight |
| Step-wise D-task test (2026-10-02) | `jsw/workloads/delivery_check.py`, `env/launch_qwen35_tp1.sh`, `env/queue_stepwise_d.sh`, `analysis/stepwise_ceiling.py`, `analysis/p1_per_task.py` | Driver flags: `--effort think\|nothink`, `--task-file`, `--world-prompt`, `--runtime-prompt`, `--top-k`. P1's task texts live on the WS in `~/work/tasks/`. K2 is pinned to revision `f846b1e` |

Not built yet: the gateway, policies in a live engine (the simulator stands in for now), a
Jetson telemetry adapter, and the CLGSCE port.

## 4. What we know (details, figures and caveats in the report)

**P1's agents create no retained-state opportunity** (Thor traces, Gemma-4-26B-A4B).
- Reflexion: 143 runs; tool-calling: 35 runs (instance 1, as of 2026-10-01 23:00).
- **Pooled over all calls**, the ceiling P/(P+r·O) at the Thor's r ≈ 67 is 2.1% (Reflexion)
  and 0.6% (tool calling).
- **Per task**, the prefill-share bound is 0.3–14%. It exceeds 4% only on the 1–3 min basic
  tasks, and it is 0.3–3.2% on every task longer than 10 min.
- **Observed savings** are ≤0.9% per task class, and 2.1% on one task (B37).
- **Batching** would lower r. At the WS's batch-16 energy ratio (r ≈ 8) the Reflexion ceiling
  would be ~15%, but that is untested.
- Prompts are rebuilt on every call (0.4–31% from cache), and decode is 90–99% of LLM
  time.
- The tool-calling agent has the same shape (a fresh prompt per attempt, one tool call
  carrying the whole program, then two evaluator calls).
- **Thinking-cap runaway dominates P1's tool-calling sweep.**
  - 50 of 176 LLM calls hit the 32,768-token cap. Those calls take 78% of all LLM time
    (16.9 of 21.6 h at ~27 tok/s decode).
  - Every one of the 8 failures includes a capped call; P1 labels most of them
    `malformed_call`.
  - A6–A9 and A20 runs take 80–110 min, against 7–36 min under Reflexion.
- That concurrency does not change this is *argued*, not measured.
- Anomaly: most same-role resumes missed the cache (A 73/116, D/F 105/182), often after a
  32K decode, which is possibly Gemma sliding-window state.

**AeroEval and aerogen** (details in the task overview report).
- The original AeroEval has 5 missions. P1 wrote 6 variants (2026-09-04) and kept 4 (D1–D3,
  F1). The dropped ones are the large-area and perception missions (est. 15–25 min flights).
- P1's AeroEval runs rarely fly: D1 flew 8 times in 9 runs, and F1 never, because the LLM code
  validator rejected first. Gazebo runs at a real-time factor of 10.
- **The cause is the paradigm, not the task size.** All of P1's agents (Reflexion, tool
  calling, the early ReAct) synthesize whole programs with fresh prompts.
- aerogen_mcp is mayankarya's step-wise tool-calling rewrite of AeroGen. It shares AeroEval's
  world prompts, not P1's tasks or agent. Our aerogen numbers characterize that paradigm.

**A step-wise agent on P1's own delivery tasks keeps its steps short** (WS, 2026-10-02).
- **Setup:** aerogen's loop with P1's D1–D3 texts and world files; Qwen3.5-9B thinking on/off,
  greedy and sampled; K2 low/high; 108 missions.
- **Steps:** after a tool result the model writes a median of 55–99 tokens (p90 ≤ 394).
  Thinking concentrates in the first, planning call: a median of 545–5,147 tokens, and one
  greedy runaway to 24K.
- **Ceiling** at the Thor's r ≈ 67: 56–72% of post-wait LLM time, and 20–72% of mission LLM
  time.
- **Private state** is only 3–16% of mission LLM time; the rest is the shared prompt.
- **Missions:** 72% deliver everything, but only 27% pass the strict check, because the sim has
  no buildings and the model flies through them.
- **Caveats:** the models are proxies for Gemma, the waits are paced at 50×, and N ≤ 2.

**aerogen has it** (WS, K2-Horizon-7B, real-time flight pacing, random anti-cache prompt
prefix removed).
- Low effort, 15 missions: 88% of time is waiting on flights, 93% of prompt tokens come from
  cache, and keeping state saves 33% of LLM time. **12% of that is private state**; the rest
  is the 9.1K-token system prompt that all sessions share.
- Medium and high effort: 2.3–2.5× the energy per mission. Their contexts hit the one-GPU
  pool, so their quality can't be judged here.

**Concurrency** (live, low effort, one run per configuration).
- Energy per passed mission: 27.8 kJ at N=1 (GPU1) and **12.6 kJ at N=8** (GPU0), with
  5.8× the throughput.
- N=2 and N=4 drew long missions, some of which outgrew the pool, so live per-run energy
  swings with trajectories (N=2: 40.0 kJ per passed mission). The fixed-mission simulation
  shows 2.5–3.5× from N=1 to N=16.
- On the full pool, the shared prompt keeps pressure low.
- With the pool capped at 16.4K: queueing and 20.5K re-prefilled tokens per mission.
  Missions whose context exceeds the pool fail at any N.

**Simulator** (`analysis/headroom_sim.py`, run via `analysis/sim_validate.py`).
- Memory model: within 7–25% of live re-prefill on same-trajectory replays (N=2 and N=4
  runs).
- Energy model: −23% to +38%, so trends only.
- Policy results (10–30 W between calls):
  - drop-at-wait costs +6–11% on the full pool;
  - pinning everything stalls missions;
  - **an exact-ETA eviction oracle ≈ LRU, so eviction order shows no headroom.**
- **Admission policies are not simulated yet.** "Budget-aware admission beats the default"
  is the open hypothesis.

**WS costs** (K2, one A5000).
- Prefill 4,106 tokens/s at ~0.05 J/token.
- Decode 5.36 J/token at batch 1 and 0.38 J at batch 16, at a flat ~205 W.
- Idle 10–20 W; 20–32 W between calls under concurrency.

**Track B** synthesis (F1–F10, baselines, H1–H5) is unchanged: `review/systems/README.md`.

## 5. Still-valid notes from the 2026-09-30 audit

- **The CLGSCE port** (needed only if P1's agents run on the WS) is mostly done in legacy.
  The x86 sim binary matches P1's source. Left to do:
  - re-copy 2 changed files, `advanced.txt` and P1's harness;
  - patch the hard-coded RPC port 41451;
  - replace P1's `pkill -x thor_headless` reset.
- **P1-style sessions (40–55K tokens) do not fit a one-GPU pool.** They need tp2, a lower
  `max_tokens`, or FP8 KV.
- **P1's AeroEval agent, task sets and Reflexion harness** were copied read-only to
  `data/p1_aeroeval_src/` on 2026-10-01.
- **The local P1 trace copy has everything except the `server_kv.jsonl` time series.** D3/F1
  and the tool-calling runs were copied on 2026-10-01.

## 6. Next steps

Waiting on the P1 mentor's answers to the task overview (§9 there) and Sandesh's approach.
If B is chosen, start with the step-wise report's "Next" list: a building-aware sim guard,
the large farm tasks, memory-pressure runs with admission policies, and Gemma per step on a
device. Earlier candidates (report §6–7):
1. Take the merged doc to the professor and get the direction decision. The options are A,
   B and C as defined in the merged doc; the letters changed from the 2026-10-01 report,
   whose A is now B, whose C is now A, and whose A + τ² is folded into C.
2. Ask mayankarya about using and extending `aerogen_mcp`.
3. If A, first test the open hypothesis:
   - add admission policies to the simulator (concurrency caps per KV budget, queue vs
     evict, handling contexts that won't fit);
   - then build them in a gateway in front of SGLang;
   - repeat runs with seeds and confidence intervals;
   - grow the task set and add a hybrid model on the WS.

## 7. Open questions for Sandesh

1. Their plan for the next step (they said they have one).
2. The P1 mentor's answers to the task overview's §7: which 8 AeroEval tasks; whether a
   step-wise paradigm is in P1's scope; whether P5 may run P1's AeroEval tasks with a
   step-wise (aerogen-based) agent; drones per edge box.
3. Direction and scope decisions: report §7.
4. Go/no-go thresholds (D4) and an edge-plausible `N_edge` (drones per ground-station box).
5. Traffic workload: is mayankarya's DeepStream camera/traffic agent P1's traffic workload?
6. Timeline: P1's deadline, when the devices return, ISP milestones. Is the WS exclusively
   ours?

## 8. Resume checklist for a new session

1. Read `AGENTS.md`, then this file.
2. `git status`, `git log --oneline -5`.
3. WS: `nvidia-smi; tmux ls; ls ~/work/runs`.
4. Re-run the analysis if runs changed:
   - `rsync -a saisandeshk@10.24.32.174:~/work/runs/ data/ws_runs/`
   - `python3 -m analysis.report_figures && python3 -m analysis.sim_validate`
5. Thor, read-only and busy-check safe: `tail -3 /home/yash/final_sweep/*/sweep.log` and
   `ls /home/yash/final_toolcalling_thor79/gemma-4-26B-A4B-it-toolcalling`.

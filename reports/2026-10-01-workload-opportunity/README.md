# Do the drone workloads create a retained-state opportunity?

**JouleServe-WS evidence pack · 2026-10-01 · Sai Sandesh (P5)**, prepared with Claude Code.

Data: P1's Thor traces (read-only copies) and new measurements on the 2×A5000
workstation. Every number is labelled with where it was measured. Methods and
definitions are in the [appendix](#appendix-methods-definitions-reproducibility).

<!-- SUMMARY -->

---

## 1. What counts as an opportunity

A session that pauses for a tool holds KV state. The serving system can keep it, drop it
and recompute it later, offload it (CPU or SSD), or compress it. It can also change
admission and preemption for everyone else. **An opportunity exists when both hold:**

1. the best action changes with conditions we can observe (state size, wait length,
   memory pressure, how much of the state is reused), inside the realistic range; and
2. the best *fixed* rule loses meaningfully to an adaptive one. We compare against the
   best fixed rule, not only SGLang's default: if "always drop" is optimal, a controller
   has nothing to do.

Two quantities bound every retention-type policy (keep, pin, time-to-live, offload,
prefetch), and we report them for each workload:

- **Prompt tokens served from cache.** How much of each prompt repeats state the session
  already built.
- **LLM time saved by keeping state:** the prefill time that keeping all state avoids,
  as a share of the LLM time the session would spend if nothing were kept. No
  retention policy can save more than this.

A third quantity says how much memory is at stake: the **share of KV memory-time held
while waiting**, i.e. tokens held × seconds, summed while a session is between LLM calls,
over the same sum including the calls themselves.

## 2. P1's drone workloads, as implemented

**Data.**
- **Reflexion:** 143 Gemma-4-26B-A4B runs from P1's final sweep on the Jetson AGX Thor
  (SGLang 0.5.16, one session at a time, cache flushed before each run, thinking on,
  `max_tokens` 32,768). By class: basic B 36 runs (33 pass), advanced A 72 (61 pass),
  AeroEval D/F 35 (8 pass).
- **Tool calling:** the first 18 runs of P1's new tool-calling sweep (started 2026-10-01
  00:17; B 12, A 6, all pass).

![Where session time goes](figures/time_split.png)

![Retention value](figures/retention_value.png)

**What the traces show.**

1. **Decode dominates.** Thinking decodes take 71–94% of session wall time, and prefill
   is 1–10% of LLM time. A Reflexion generator call writes a median 8,061 tokens (p90:
   the 32,768 cap). 115 of 1,030 Reflexion calls hit the cap.
2. **Prompts are rebuilt on every call.** Each role (generator, evaluator, reflector)
   builds a fresh prompt, so only 11% (B), 14% (A) and 31% (D/F) of prompt tokens repeat
   earlier state.
   - P1's tool-calling agent has the same shape. Each attempt starts a fresh prompt and
     makes exactly one `execute_and_observe` call carrying the whole program, followed by
     an evaluator. Reuse is 6% (B) and 0.4% (A).
3. **Keeping state is worth at most 0.9% of LLM time** (B 0.87%, A 0.16%, D/F 0.84%;
   tool calling 0.28% and 0.01%).
   - The structural reason is cost: on the Thor, prefill runs at ≈1,805 tokens/s and
     decode at ≈28 tokens/s. Recomputing a token costs about 1/65 of generating one, and
     these sessions are over 90% decode.
4. **Concurrency does not rescue it.**
   - Paused sessions hold 0.1–27% of KV memory-time, and only a small part of that state
     is ever reused. Dropping it frees the memory at almost no cost.
   - Offloading it spends PCIe transfers to avoid a recompute that is nearly free, and on
     Jetson's unified memory "offload to CPU" frees nothing at all.
   - SGLang's default already drops idle state first: unreferenced cache counts as free
     space for admission, and LRU evicts it first.
   - Not flushing between tasks shares the static prompt parts across sessions
     automatically, but that is capped by the prefill share (≤10% of LLM time) and needs no
     decisions.
5. **What P1 *does* stress is active decode.** A-class calls peak at a median 21.7K
   tokens (max 40K), and D/F at 54K. Under concurrency these long decodes are what fill
   the pool. The lever there is admission and batching, not retention (H1):
   - on the WS, decode energy per output token falls **14×** from batch 1 to batch 16
     (5.36 → 0.38 J, §5);
   - so packing more concurrent decodes into the same memory is worth far more than
     keeping paused state.
6. **One anomaly worth checking on the devices.** A same-role call with an almost
   identical prompt should hit the cache, yet most missed:
   - A: 73 of 116 missed, 38 of them right after a 32K-token decode;
   - D/F: 36 of 71 missed.

   Our guess is that Gemma's sliding-window state is lost after long decodes (a
   hybrid-state effect, H3). It is not verified. The cost is small today (0.3% and 1.0%
   of LLM time).

![Two sessions on one clock](figures/timelines.png)

*Left:* a P1 Reflexion session is one long decode ramp and a short wait. The next call
starts from a smaller, rebuilt prompt. *Right:* an aerogen mission (§4) holds the same
growing context through every flight leg, and each LLM step appends a little to it.

![Durations](figures/durations_cdf.png)

## 3. What the prior work ran

| Property | Almost all prior work | P1 drone agents |
|---|---|---|
| Context | Grows across turns (ReAct, tool calling, chat): INFERCEPT, Continuum, Autellix, Pensieve, Adaptive KV Retention (τ²-bench), KAIROS, AgentServe, CacheScout. KVFlow and TokenCake reuse fixed per-agent prefixes | Rebuilt for every role call; 0.4–31% reused |
| Output length | Tens to hundreds of tokens, reasoning off, so prefill-heavy | Thinking on, up to 32K; 71–94% of time is decode |
| Tool waits | Real tools take ms to ~2 s (Continuum: 0.9 s SWE-bench, 1.9 s BFCL). **Long waits are synthetic**: INFERCEPT's chatbot/image/TTS 17–29 s (estimated), Pensieve 60 s think time, Adaptive KV Retention ~30 min lognormal, TokenCake's latency table | Real simulator time: median 17 s (B), 72 s (A), 113 s (D/F); tail to ~15 min |
| Load | Poisson or closed-loop arrivals, tens to hundreds of sessions | One session |
| Hardware | Datacenter GPUs with large host DRAM over PCIe | Thor (unified memory) |

P1's workloads sit outside the regime these systems target on both axes that matter
(reuse and output length). Injected waits are standard practice in the strongest prior
work, so pairing a standard workload with measured drone waits is methodologically
accepted. Details per system are in [`review/systems/`](../../review/systems/README.md).

## 4. A drone agent that does: `aerogen_mcp` on the WS

<!-- AEROGEN -->

## 5. Serving costs on the WS, and what changes on the edge

Measured on one A5000 with K2-Horizon-7B (bf16, SGLang 0.5.20, nothing else running):

![WS costs](figures/ws_costs.png)

<!-- COSTS -->

**What changes on Orin/Thor** (from `review/systems/README.md` §6):
- **Speed:** Orin has ~4× less memory bandwidth than the A5000, so decode is slower and
  the same tool wait is relatively shorter. On the WS we therefore report results against
  the wait/LLM-time ratio, not only absolute seconds.
- **Memory:** unified memory means there is no host tier, so "offload" is a copy inside
  the same DRAM. Only keep, drop and recompute, compress, or NVMe remain. Co-located
  simulators and perception models compete with KV (H4, edge only).
- **Energy:** the WS measures GPU-only energy (NVML). Jetson rails measure the whole
  board, including CPU, DRAM and the simulator. Idle power during tool waits becomes a
  board-level quantity.
- **Models:** all edge models are hybrid (Gemma-4 sliding window; Qwen3.8 linear
  attention), with separate state pools and checkpoint-granular reuse. K2-Horizon-7B is a
  dense full-attention model: a clean baseline, not the edge model.

## 6. Options

| Option | Primary workload | Why | Risks | Effort to first result |
|---|---|---|---|---|
| **A (recommended)** | A native tool-calling drone agent with an accumulating context (`aerogen_mcp` style), with paced physical waits | Keeps the edge/drone story and P1's devices. Its waits come from flight physics, not an invented distribution. It is the regime where retention decisions are live (§4). Its sim is pure Python, so it runs on the WS and on Jetson unchanged | Only 5 tasks today (needs a task set, or CLGSCE tasks ported to it). Owner's OK needed. K2's tool use is decent, but some manoeuvres are rejected and retried | Days: the harness from this report already runs it |
| **A + τ²-bench** | as A, plus τ²-bench as the comparability workload | τ²-bench is what Adaptive KV Retention (the closest long-wait competitor) evaluates on, so baselines can be compared like for like | τ²-bench needs a user-simulator model, and its waits are injected | ~1 week more |
| **B** | τ²-bench (or BFCL / ALFWorld) with injected waits | Safest comparability, established tasks, live pass/fail | Weak edge story; every wait is synthetic | ~1 week |
| **C** | P1's agents as they are | No new workload. The lever is admission and batching of long thinking decodes (H1), which P1's future predictor can drive | Not a retained-state paper: it becomes session-aware energy management, closer to KAIROS | Days |

In every option, P1's Reflexion/tool-calling agents stay in the evaluation as the
decode-dominated contrast. A controller has to recognise that retention is worthless
there and not make things worse.

## 7. Decisions needed

1. **Workload direction:** option A, A + τ²-bench, B or C (above).
2. **How P1 is used:** agree that P1's current agents are the decode-dominated contrast
   case for retention, and the source of devices, measured waits and (later) the
   predictor, rather than the primary retention workload.
3. **Scope of "state management":** retention only, or retention plus admission and
   batching (the lever P1 does stress)?
4. **aerogen:** ask mayankarya for permission to use and extend `aerogen_mcp`, and
   decide how to grow its task set (new radio-tower/survey tasks, or ports of CLGSCE
   tasks).
5. **WS model:** keep dense K2-Horizon-7B as the clean baseline, and add a hybrid model
   (e.g. Qwen3.5-9B, the Qwen3.8 family) so that hybrid state (H3) is exercised before the
   devices return.
6. **Go/no-go thresholds** for the next stage (the X/Y/Z/W/N_edge of `planning/PLAN.md`
   §2.2), now that we have measured reference points.

---

## Appendix: methods, definitions, reproducibility

### A1. Definitions

- **Session:** one task attempt (P1: one run of a task instance; aerogen: one mission).
- **LLM time:** the sum of LLM call durations.
  - **Prefill** on the Thor is P1's measured time to first token.
  - On the WS it is modelled: uncached prompt tokens ÷ the calibrated cold-prefill rate
    (4,106 tokens/s), capped at the call duration. Client-side TTFT is not a clean prefill
    measure there, because the tool-call parser only emits a tool call once it is
    complete.
  - **Decode** is the rest of the call.
- **Tool wait:** a tool call longer than 0.5 s. Bookkeeping tools (connect, arm, get_pose,
  validate) return in milliseconds and are excluded from wait statistics, but not from
  session time.
- **Prompt tokens served from cache:** Σ cached prompt tokens ÷ Σ prompt tokens, from
  SGLang's `cached_tokens` usage field.
- **KV memory-time.** During a call, (prompt + completion/2) × duration. Between calls,
  (prompt + completion of the last call) × gap, i.e. what a keep-everything policy holds
  while the session waits. We report the paused share.
- **LLM time saved by keeping state:** Σ cached tokens ÷ cold-prefill rate, divided by
  (LLM time + that amount). It uses the rate of the device the trace came from (Thor
  1,805 tokens/s, WS 4,106 tokens/s).

### A2. aerogen setup on the WS

- **Agent:** `aerogen_mcp` by mayankarya, a private copy from the Thor
  (`/media/ssd/drone/aeroeval`, snapshot 2026-10-01). It is not vendored into this repo.
  - One `messages` list per mission; ≤40 turns, ≤80 tool calls.
  - 20 MCP tools over an AeroStack2-shaped API, with the pure-Python kinematic `sim`
    backend and the radio-tower world.
  - The deterministic mission validator runs over the executed trace.
- **Changes to the author's code:** one 6-line hook. The sim's `_advance(dt)` now sleeps
  `dt / AEROGEN_PACE_SPEEDUP` seconds, so tool calls take real flight time; all runs use
  real time (speed-up 1.0).
- **Changes at runtime, by the driver** (`jsw/workloads/aerogen_driver.py`):
  - removes the agent's random system-prompt prefix (it exists to defeat cloud prompt
    caching);
  - sets sampling to K2's model-card values (temperature 1.0, top-p 0.95, seed 42 + run);
  - sets reasoning effort (low or high) and `max_tokens` (16,384);
  - streams responses, and logs every LLM call and tool call with monotonic timestamps.
  - K2's chat template requires a thinking field on every assistant message, and SGLang
    forwards only `reasoning_content`, so the reasoning is replayed under that field.
- **Server:** SGLang 0.5.20, K2-Horizon-7B bf16, tp=1 on one A5000.
  - `--mem-fraction-static 0.88`, giving a KV pool of **25,427 tokens**.
  - `--context-length 65536`, `k2_horizon` reasoning and tool parsers, metrics and cache
    report on.
  - Two independent replicas: GPU1 port 30000 (low effort), GPU0 port 30001 (calibration,
    then high effort).
- **Runs:**
  - Single session with the cache flushed before each mission (E1).
  - Closed-loop concurrency with N session slots and staggered starts (E2). The cache is
    flushed at the start of each run only.
  - Each run directory holds `manifest.json`, `events.jsonl`, `nvml.jsonl` (10 Hz),
    `sglang_metrics.jsonl` (2 Hz), and per mission `llm_calls.jsonl`,
    `tool_calls.jsonl`, `mission.json`, `summary.json`.

### A3. Reproduce

```bash
# WS: serve, calibrate, run (see env/*.sh)
env/launch_k2_tp1.sh 1 30000                       # GPU1
python -m jsw.costs.calibrate --base-url http://127.0.0.1:30001/v1 --gpu 0 --out calib.json
python -m jsw.workloads.aerogen_driver --out runs/e1_low_n1 --runs 3 --concurrency 1 \
    --effort low --flush-each --flush-start --gpu 1
python -m jsw.workloads.aerogen_driver --out runs/e2_low_n4 --runs 3 --concurrency 4 \
    --stagger-s 20 --effort low --flush-start --gpu 1
# local: copy runs to data/ws_runs/, then
python3 -m analysis.report_figures      # figures + report_data.json
python3 -m analysis.headroom_sim        # policy headroom estimate
```

### A4. Data

- `data/p1_thor_drone/`: P1 Reflexion sweep, lightweight files. Copied 2026-09-30, with
  D3/F1 added 2026-10-01.
- `data/p1_thor_toolcalling/`: the first 18 runs of P1's tool-calling sweep (2026-10-01).
- `data/ws_runs/`: the WS runs in this report.

All three are git-ignored. The Thor copies are read-only copies of P1's files.

### A5. Limitations

- **Different platforms.** The P1 numbers come from Gemma-4-26B-A4B (hybrid) on a Thor
  with SGLang 0.5.16. The aerogen numbers come from K2-Horizon-7B (dense) on an A5000 with
  SGLang 0.5.20. Ratios (reuse, time shares) transfer better than absolute times.
- **Small task set.** aerogen has 5 tasks in one world, so this is a feasibility signal,
  not a benchmark. Sampling at temperature 1.0 gives run-to-run variation. The P1 tool-calling
  sample is the first 18 runs of a sweep in progress.
- **GPU-only energy.** WS energy is NVML GPU energy, with no CPU, DRAM or simulator.
- **Low-effort history mismatch.** K2's re-rendered history uses the high-effort think tag,
  so for low effort each turn's last output is re-prefilled (a few hundred tokens).
- **The simulator is a model.** It is checked against the live concurrency runs, but it
  ignores batching's small per-step slowdown and SGLang's retraction path.

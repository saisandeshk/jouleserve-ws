# Tracker — P5 options (G1 the even-handed case, G2 the WS versions)

**Updated:** 2026-10-05 (IST). Plan: [`OPTIONS_PLAN.md`](OPTIONS_PLAN.md) (v1.0, approved 2026-10-05).
**Stop point:** report to Sandesh when G1 (CMP-2) is done; otherwise keep working.

How to use it:
- Update the status, output and notes of a task when it moves; add one line to the log below.
- Status: `todo`, `doing`, `done`, `blocked`, `dropped`. A task is `done` only when its "done when"
  (plan §2.4, §3) is met and its output is in the repo or in `data/ws_runs/`.
- Results go into the comparison doc (`reports/2026-10-06-options/README.md`). This file only points to them.
- New tasks get the next ID in their stream and a row here; plan changes go into `OPTIONS_PLAN.md`.

## Now

- **2026-10-06 01:25:** A-E1 running on E4B (both GPUs); then RET-E1 (GPU0) and D-E2 -> C-E1 (GPU1), unattended
  (`env/queue_wave2b.sh`). P1's data is on the WS (Sandesh's permission, 2026-10-06), cloned from GitHub at `3c47ebc`.
- **Earlier, wave 0 done, wave 1** (2026-10-06, 00:05). GPU1: B-E1 on gemma-4-E4B through the gateway. GPU0: granite
  (smoke done). Next without P1 data: C-E1 (τ²-bench), A-E5 (batching), the 26B FP8 attempt.
- Unblocked 2026-10-06: P1's data may be copied to the WS (Sandesh).

## G2 shared base

| ID | Task | Wave | Depends | Status | Output | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| S1a | Serve gemma-4-26B-A4B 4-bit on one GPU; smoke (chat, thinking, `gemma4` tools, pool, `/metrics`) | 0 | — | dropped | `env/derive_gemma26b_fp8.py`, `env/launch_model.sh` | No 26B stand-in runs on Ampere in SGLang 0.5.20: the 4-bit MoE kernel is SiLU-only (Gemma uses GELU); the FP8 MoE kernel needs fp8e4nv (sm89+). bf16 (52 GB) exceeds both GPUs. On the way: CUDA-12 NCCL preload makes TP=2 work; text-only and Marlin-safe derived checkpoints. D13 outcome: A-E1 on E4B; the 26B test waits for a Jetson |
| S1b | Serve gemma-4-E4B; smoke incl. images | 0 | — | done | `env/launch_model.sh gemma-e4b`, `~/work/logs/smoke_gemma_e4b.json` | Pools: 63,509 full + 50,807 SWA tokens at 0.88; thinking on/off, `gemma4` tool calls, images, /generate exact lengths, abort on disconnect all work |
| S1c | Serve granite-4.2-8b; smoke; pool size | 0 | — | done | `env/launch_model.sh granite8b`, `~/work/logs/smoke_granite.json` | Pool 26,467 tokens at 0.88 (P1's Orin 32 granite pool: 26-27K; Orin 64's 32,768 needs a higher mem fraction) |
| S1d | Record the recipes and gotchas; check FP8 `--kv-cache-dtype` on Ampere | 0 | S1a–c | doing | `env/launch_model.sh` comments | Recipes recorded in the launcher; AGENTS.md §6b update and FP8 KV check (CAP-E1) pending |
| S2 | Gateway v0 (routes, streaming, call log, hooks, abort) | 1 | — | done | `jsw/gateway/server.py`, `tests/test_gateway.py` | v0: routes, streaming, aggregation, call log, hooks, abort, tool-tagged routes, pythonic tool-call fallback (`jsw/gateway/pythonic.py`); ~0.3 ms per call |
| S3 | Trace replayer (`/generate`, exact lengths, real prefix reuse, tool gaps, burst injection) | 1 | S2, S5 | done | `jsw/workloads/replay.py`, `analysis/replay_sets.py` | Tested live on granite: exact lengths; prompt = previous prompt + fresh IDs (P1's thinking agents drop reasoning: cached = previous prompt, as P1's data shows); bursts from vitals; --no-reuse; horizon cut |
| S4 | Streaming loop detector, parity with offline flags | 0 | — | done | `jsw/policies/loop_detector.py`, `tests/test_loop_detector.py` | Fires at the offline position on all recorded Thor calls; reproduces 121 + 127 |
| S5 | Runner and manifest, shared run format | 0 | — | done | `jsw/runner/run.py`, `env/sync_ws.sh` | Manifest, events, calls, NVML/metrics samplers, energy over a window, teardown check |
| S6 | Analysis helpers: loop replay, live vs simulator | 2 | A-E1, RET-E1 | doing | `analysis/{a_e1,b_e1,b_e2,c_e1,d_e2,ret_e1}.py` | Written; run as each experiment finishes |

## G1 evidence

| ID | Option | Task | Wave | Depends | Status | Output | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CMP-1 | all | Comparison doc skeleton from existing evidence | 0 | — | done | `reports/2026-10-06-options/README.md` | Skeleton with today's evidence and literature for A, B, C, D, CAP; [pending] slots for this week |
| A-E1 | A | Do the loops survive sampling? Pilot (60 + 40), then full | 1 | S1a, S4, S5 | doing | `a_e1.json`, `env/queue_g0_chain2.sh` | E4B: 0 loops on all 100 Thor prompts under greedy and 0 on its own 5 Orin 32 loop prompts (greedy and sampled): reproduction fails on E4B. P1's 26B via llama.cpp (4-bit GGUF): greedy loops on 18 of 24 Thor loop prompts so far (reproduces) and 5 of 16 controls; sampled arm running |
| A-E2 | A | Stop and retry: R1 resample, R2 nudge, R3 lower budget | 2 | A-E1 | todo | `env/queue_a_e2.sh`, `analysis/a_e2.py` | Queued on GPU1 (llama.cpp 26B) after the GPU1 tail: resample / nudge / budget on the prompts that loop under greedy |
| A-E3 | A | Literature: reasoning-length control, early exit, repetition, serving-side reasoning | 0 | — | done | `reports/2026-10-06-options/lit_A.md`, 6 review docs | Partly covered: Word Salad Chopper, AgentStop, Fail-Fast, Dynasor; open: engine-side stop + retry + energy per success on Jetson |
| A-E4 | A | Traffic's capped tool calls (analysis only) | 2 | — | todo | comparison §A | No replay possible (tool results not recorded) |
| A-E5 | A, sim | Decode batching: Gemma-4 MoE vs dense, 4K–32K context | 3 | S1 | doing | `jsw/costs/calibrate2.py`, `~/work/runs/calib/granite8b_tp1_gpu0.json` | Granite (dense): prefill 4.2K tok/s; decode 27 ms/step at batch 1, +4.5% at batch 16; 5.3 -> 0.41 J/token (13x). E4B (MoE-free, SWA) pending |
| B-E1 | B | Gemma (E4B, 26B-4bit) as a step-wise agent on D1–D3 | 1 | S1a, S1b | done | `reports/2026-10-06-options/b_e1.json` | E4B keeps steps short: after a tool result median 63 (greedy) / 68 (sampled) tokens, max 539; planning call 1.2-1.6K; 0 capped; strict pass 9/11 greedy, 7/13 sampled. 9 of 33 missions ended at the first call (E4B wrote the call as text; gateway conversion bug open) |
| B-E2 | B | Redo the step-wise projections with Gemma's step sizes | 3 | B-E1 | doing | `analysis/b_e2.py` | Projection at Thor gemma-26B and Orin 32 E4B prices |
| B-E3 | B | Literature: agent design (code-as-action, ReAct, plan-and-execute, drone agents) | 0 | — | done | `reports/2026-10-06-options/lit_B.md`, 4 review docs | Direction known with energy (Cost of Dynamic Reasoning, Sustainable Agents, EpG); the exact comparison not found; fits P1 |
| C-E1 | C | τ²-bench: single-session shape and ceiling, then N sessions with injected waits | 2 | S1, (S3) | doing | `c_e1.json` | Airline (20 tasks, reward 0.50): context grows 182 tokens/step, 93.5% reuse, output median 333 (83% reasoning); ceiling 7.5% at E4B's Jetson r, 3.7-9.2% at traffic r, 16-19% at drone r: in between. Retail running; thinking-off airline (C's best case) queued |
| RET-E1 | RET | Live anchor: granite traffic replay at P1's pools, N = 1–8, 3 policies, vs simulator | 2 | S1c, S2, S3, S5 | todo | `env/queue_ret_e1.sh`, `analysis/ret_e1.py` | Queued on GPU0 after the 26B arm (~05:30) |
| D-E2 | D | Vision burst with N agents (E4B, 12.4K and 71K pools) | 3 | S3, D-P1 | doing | `d_e2.json` | 10 runs done: the burst evicts the paused prefix live (88-100% recomputed at 12.4K, P1's Orin 64: 90%); policies within -4..+8% but never engaged (admission raced the metrics poll; pin cannot help when the burst exceeds the pool). Capacity: 63.5K vs 12.4K pool at N=4 cuts energy per session 2.4x. Fair re-test (burst capped at 2, +-pin) queued (D-E2b) |
| D-E3 | D | Literature: unified memory, co-located models | 0 | — | done | `reports/2026-10-06-options/lit_D.md`, 5 review docs | Elastic KV (Prism/kvcached, MorphServe) and tool-aware pinning exist; tool foreknowledge on unified memory not found; effect may be small |
| CAP-E1 | CAP | FP8 vs bf16 KV: pool size and quality | 3 | S1d, A-E1, B-E1 | todo | `env/queue_cap_e1.sh` | Queued on GPU1 after C-E1: granite FP8 KV at N=8 (live capacity), E4B FP8 KV on A-E1 pilot and B-E1 D1 |
| CAP-E2 | CAP | Literature: KV quantization, prompt and tool-loading | 0 | — | done | `reports/2026-10-06-options/lit_CAP.md`, 5 review docs | Each lever studied; energy per task and a run-time controller across levers not found |
| CMP-2 | all | Full comparison, Sandesh's review | 4 | all | todo | comparison doc | Then merge into the evidence doc and the deck |

## G2 option versions

| ID | Option | Task | Wave | Depends | Status | Output | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A-P1 | A | Decode guard policy (three stop actions, consecutive-cap rule) | 2 | S2, S4 | doing | `jsw/policies/decode_guard.py` | Built; tested against a fake engine (stop at char 6,000, abort upstream, resampled retry, session stop after k caps) |
| D-P1 | D | Burst-aware memory policy (pin, burst admission, both) | 3 | S2, S3 | done | `jsw/policies/burst_memory.py` | Pin (priority eviction), burst admission k, both; evaluated by D-E2 |
| A-P2 | A | P1's CLGSCE agent live behind A-P1 | 4+ | A-P1 | blocked | — | Needs the 2 changed CLGSCE files from P1 and Sandesh's OK |
| C-P1 | C | τ²-bench through the gateway with published baselines | 4+ | C-E1 | todo | — | Only if C-E1 finds an opportunity |
| D-P2 | D | Simulator with a memory budget that changes over time | 4+ | D-E2 | todo | `analysis/admission_sim.py` | |
| B-P1 | B | Step-wise agent with a building-aware sim | 4+ | B-E1 | blocked | — | Needs mayankarya's OK to extend aerogen |
| CAP-P1 | CAP | Capacity-aware admission | 4+ | CAP-E1 | todo | — | Only if CAP-E1 finds a trade-off |

## Waiting on others

| What | From | Blocks | Since |
| --- | --- | --- | --- |
| Reply to `NOTES_FOR_P1.md`, especially which server `ask_vlm` calls | P1, via Sandesh | D-E2's design | 2026-10-05 |
| The two CLGSCE files changed on the Thor on 23 Sep | P1, via Sandesh (Thor off-limits) | A-P2 | — |
| Permission to extend aerogen | mayankarya | B-P1 | 2026-10-01 |
| Agreement on the A/P1 split (online stop) | P1, after 10 Oct | the A section's novelty claim | — |
| Traffic grades; Thor drone tool calling in the repository | P1 | traffic success in A, D, RET | — |
| Professor meeting date; direction D12 | Professor | the final choice | 2026-10-05 |

## Log (newest first)

- **2026-10-06 04:25:** A-E1 on E4B done (no loops anywhere: inconclusive); 26B on llama.cpp reproduces the loops under greedy;
  D-E2 first pass done (mechanism reproduced, policies did not engage; re-test queued); C-E1 airline done. All remaining
  experiments queued on the WS (GPU0: 26B sampled, RET-E1; GPU1: C-E1 retail, CAP-E1, D-E2b, E4B calibration + C-E1
  thinking-off, A-E2).
- **2026-10-06 01:25:** P1's repository cloned on the WS from GitHub (`3c47ebc`); our tool-calling copy moved with
  matching SHA-256 (756 files). The 5 Oct analyses rerun on the WS (ECC memory) give byte-identical `opportunity.json`
  and `caps.json`. B-E1 done. The 26B stand-in is impossible on Ampere in SGLang 0.5.20; A-E1 moved to E4B.
- **2026-10-06 00:05:** wave 0 done: models served and smoke-tested (E4B, granite; 26B 4-bit fails, FP8 next),
  gateway + decode guard + replayer + runner + loop detector built and tested, four literature reviews (Sonnet),
  comparison skeleton (CMP-1). Local laptop: power cuts and RAM bit flips (three P1 files corrupted in the page
  cache, disk copies intact); work committed often (`ad44fd8`).
- **2026-10-05 (late):** Sandesh approved the plan (D13–D17; CAP in; lean stated at the end). Wave 0 started.
- **2026-10-05:** plan v0.1 and this tracker written; WS clone pulled to `5373f35` and `~/jsw-dev` synced;
  feasibility checks recorded in plan §9. Waiting for Sandesh's approval.

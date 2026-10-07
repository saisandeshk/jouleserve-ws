# Tracker — P5 options (G1 the even-handed case, G2 the WS versions)

**Updated:** 2026-10-07 (IST), consistency pass after G1. Plan: [`OPTIONS_PLAN.md`](OPTIONS_PLAN.md) (v1.1; v1.0 approved
2026-10-05).
**Stop point:** report to Sandesh when G1 (CMP-2) is done; otherwise keep working.

How to use it:
- Update the status, output and notes of a task when it moves; add one line to the log below.
- Status: `todo`, `doing`, `done`, `blocked`, `dropped`. A task is `done` only when its "done when"
  (plan §2.4, §3) is met and its output is in the repo or in `data/ws_runs/`.
- Results go into the comparison doc (`reports/2026-10-06-options/README.md`). This file only points to them.
- New tasks get the next ID in their stream and a row here; plan changes go into `OPTIONS_PLAN.md`.

## Now

- **2026-10-06 08:40: G1 is done** (CMP-2, `reports/2026-10-06-options/README.md`). Stopped here to report to Sandesh, as
  agreed; nothing runs on the WS (servers torn down, GPUs idle). Its results were merged into the evidence doc, the
  teaching guide and the deck the same day. Next, after Sandesh's review: fold any review changes into those; G2's WS
  versions; optional B-E1 sampled re-run with the fixed gateway.

## G2 shared base

| ID | Task | Wave | Depends | Status | Output | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| S1a | Serve gemma-4-26B-A4B 4-bit on one GPU; smoke (chat, thinking, `gemma4` tools, pool, `/metrics`) | 0 | — | done (llama.cpp) | `env/derive_gemma26b_fp8.py`, `env/launch_model.sh` | No 26B stand-in runs on Ampere in SGLang 0.5.20: the 4-bit MoE kernel is SiLU-only (Gemma uses GELU); the FP8 MoE kernel needs fp8e4nv (sm89+). bf16 (52 GB) exceeds both GPUs. On the way: CUDA-12 NCCL preload makes TP=2 work; text-only and Marlin-safe derived checkpoints. D13 outcome: the 26B runs through llama.cpp v0.6.0 as a 4-bit GGUF (unsloth UD-Q4_K_XL, `env/launch_llamacpp.sh`), used for A-E1/A-E2 |
| S1b | Serve gemma-4-E4B; smoke incl. images | 0 | — | done | `env/launch_model.sh gemma-e4b`, `~/work/logs/smoke_gemma_e4b.json` | Pools: 63,509 full + 50,807 SWA tokens at 0.88; thinking on/off, `gemma4` tool calls, images, /generate exact lengths, abort on disconnect all work |
| S1c | Serve granite-4.2-8b; smoke; pool size | 0 | — | done | `env/launch_model.sh granite8b`, `~/work/logs/smoke_granite.json` | Pool 26,467 tokens at 0.88 on GPU0, 26,648 on GPU1 (P1's Orin 32 granite pool: 26-27K; Orin 64's 32,768 needs a higher mem fraction) |
| S1d | Record the recipes and gotchas; check FP8 `--kv-cache-dtype` on Ampere | 0 | S1a–c | done | `env/launch_model.sh`, AGENTS.md §6c | Recipes and gotchas in AGENTS.md §6c; FP8 KV: granite works (pool 2.0x on the same GPU), Gemma-4 cannot start on Ampere (CAP-E1) |
| S2 | Gateway v0 (routes, streaming, call log, hooks, abort) | 1 | — | done | `jsw/gateway/server.py`, `tests/test_gateway.py` | v0: routes, streaming, aggregation, call log, hooks, abort, tool-tagged routes, pythonic tool-call fallback (`jsw/gateway/pythonic.py`); ~0.3 ms per call |
| S3 | Trace replayer (`/generate`, exact lengths, real prefix reuse, tool gaps, burst injection) | 1 | S2, S5 | done | `jsw/workloads/replay.py`, `analysis/replay_sets.py` | Tested live on granite: exact lengths; prompt = previous prompt + fresh IDs (P1's thinking agents drop reasoning: cached = previous prompt, as P1's data shows); bursts from vitals; --no-reuse; horizon cut |
| S4 | Streaming loop detector, parity with offline flags | 0 | — | done | `jsw/policies/loop_detector.py`, `tests/test_loop_detector.py` | Fires at the offline position on all recorded Thor calls; reproduces 121 + 127 |
| S5 | Runner and manifest, shared run format | 0 | — | done | `jsw/runner/run.py`, `env/sync_ws.sh` | Manifest, events, calls, NVML/metrics samplers, energy over a window, teardown check |
| S6 | Analysis helpers: loop replay, live vs simulator | 2 | A-E1, RET-E1 | done | `analysis/{a_e1,b_e1,b_e2,c_e1,d_e2,ret_e1}.py` | All run; outputs in `reports/2026-10-06-options/*.json` and `figures/` (`analysis/options_figures.py`) |

## G1 evidence

| ID | Option | Task | Wave | Depends | Status | Output | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CMP-1 | all | Comparison doc skeleton from existing evidence | 0 | — | done | `reports/2026-10-06-options/README.md` | Skeleton with today's evidence and literature for A, B, C, D, CAP; [pending] slots for this week |
| A-E1 | A | Do the loops survive sampling? Pilot (60 + 40), then full | 1 | S1a, S4, S5 | done | `a_e1.json`, `figures/a_e1_loops.png` | 26B (4-bit, llama.cpp) on P1's Thor Reflexion prompts: greedy loops 23/30 (77%), Gemma's default sampling 0/30 (CI 0-11%) with 28/28 valid programs; rule: sampling removes the loops. E4B (SGLang) never loops, even on its own Orin 32 loop prompts: inconclusive for E4B |
| A-E2 | A | Stop and retry: R1 resample, R2 nudge, R3 lower budget | 2 | A-E1 | done | `a_e2.json` | Resample after an online stop: 17/17 re-looping calls recovered with valid output; 19.7K tokens vs 32.8K recorded (-40%); rule (<=50% cost) not met; sampling from the start cheaper. Nudge (greedy + note) re-loops 7/10. Budget dropped |
| A-E3 | A | Literature: reasoning-length control, early exit, repetition, serving-side reasoning | 0 | — | done | `reports/2026-10-06-options/lit_A.md`, 6 review docs | Partly covered: Word Salad Chopper, AgentStop, Fail-Fast, Dynasor; open: engine-side stop + retry + energy per success on Jetson |
| A-E4 | A | Traffic's capped tool calls (analysis only) | 2 | — | done | `a_e4.json` | Repeated capped `run_python` calls hold 31-33% of gemma traffic LLM energy; no replay possible (tool results not recorded) |
| A-E5 | A, sim | Decode batching: Gemma-4 MoE vs dense, 4K–32K context | 3 | S1 | done | `~/work/runs/calib/*.json` | Batch 1 -> 16 cuts J/token 13x (granite 5.3 -> 0.41) and 13.5x (E4B 3.40 -> 0.25); step +4.5% / +20%. 26B not calibratable in SGLang |
| B-E1 | B | Gemma (E4B, 26B-4bit) as a step-wise agent on D1–D3 | 1 | S1a, S1b | done | `reports/2026-10-06-options/b_e1.json` | E4B keeps steps short: after a tool result median 63 (greedy) / 68 (sampled) tokens, max 539; planning call 1.2-1.6K; 0 capped; strict pass 9/11 greedy, 7/13 sampled. 9 of 33 missions ended at the first call (E4B wrote the call as text; gateway conversion bug open) |
| B-E2 | B | Redo the step-wise projections with Gemma's step sizes | 3 | B-E1 | done | `b_e2.json`, `figures/b_e1_e2.png` | E4B step-wise 26-27 kJ per strict success vs P1's Reflexion 284-499 kJ measured (11-19x), Thor gemma-26B prices |
| B-E3 | B | Literature: agent design (code-as-action, ReAct, plan-and-execute, drone agents) | 0 | — | done | `reports/2026-10-06-options/lit_B.md`, 4 review docs | Direction known with energy (Cost of Dynamic Reasoning, Sustainable Agents, EpG); the exact comparison not found; fits P1 |
| C-E1 | C | τ²-bench: single-session shape and ceiling, then N sessions with injected waits | 2 | S1, (S3) | done | `c_e1.json`, `c_e1_nothink.json` | Thinking on: ceiling 7.5% (airline) / 9.9% (retail) at E4B's Jetson r: borderline. Thinking off (airline, same 10/20 reward): 75-token steps, ceiling 25% (WS 33%): opportunity |
| RET-E1 | RET | Live anchor: granite traffic replay at P1's pools, N = 1–8, 3 policies, vs simulator | 2 | S1c, S2, S3, S5 | done | `ret_e1.json`, `figures/ret_e1.png` | Ran narrower than planned (GPU time): Orin 32 granite at P1's pool only, N = 1, 4, 8, default and no-reuse (keep not run), 45 min per point. Anchor holds: simulator within 14% at every point (2% except N=4), FP8 run out of sample within 6%. Ranking degenerate: at N=8 the default keeps nothing (0/102 calls hit), so it ties with dropping state. Knee live: 57.2 -> 27.8 -> 38.4 kJ/session at N=1/4/8 |
| D-E2 | D | Vision burst with N agents (E4B, 12.4K and 71K pools) | 3 | S3, D-P1 | done | `d_e2.json` | Mechanism reproduced live (88-100% of the paused prefix recomputed at 12.4K). Pin + burst cap 2 cuts it to 37% at one agent but costs +11% energy per session; at 4 agents capacity dominates (+3..14%). Capacity: 63.5K vs 12.4K pool at N=4: 2.4x less energy per session |
| D-E3 | D | Literature: unified memory, co-located models | 0 | — | done | `reports/2026-10-06-options/lit_D.md`, 5 review docs | Elastic KV (Prism/kvcached, MorphServe) and tool-aware pinning exist; tool foreknowledge on unified memory not found; effect may be small |
| CAP-E1 | CAP | FP8 vs bf16 KV: pool size and quality | 3 | S1d, A-E1, B-E1 | done | `env/queue_cap_e1.sh`, `queue_cap_e1b.sh` | FP8 KV doubles granite's pool (53,296 vs 26,648, both GPU1); 8 agents live: 14.7 vs 38.4 kJ/session bf16 (-62%), 2.6x sessions/hour. Rule undecided: quality side could not run. Gemma-4 FP8 KV cannot start on Ampere in SGLang 0.5.20 (triton fp8e5; Gemma4 allows only triton/trtllm): quality pairs not run; the Orins are Ampere-class |
| CAP-E2 | CAP | Literature: KV quantization, prompt and tool-loading | 0 | — | done | `reports/2026-10-06-options/lit_CAP.md`, 5 review docs | Each lever studied; energy per task and a run-time controller across levers not found |
| CMP-2 | all | Full comparison, Sandesh's review | 4 | all | done (review pending) | comparison doc | Merged on 6 Oct into the evidence doc (rev 138, repo copy), the teaching guide (chapter 21) and the deck (v2.1) |

## G2 option versions

| ID | Option | Task | Wave | Depends | Status | Output | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A-P1 | A | Decode guard policy (three stop actions, consecutive-cap rule) | 2 | S2, S4 | done | `jsw/policies/decode_guard.py` | Run live in A-E1/A-E2 (stops, resample/nudge retries) on P1's 26B; not yet inside a live agent loop |
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

- **2026-10-07 (afternoon):** P1 pulled to `f6aabe4` (local + WS); a P1 audit for P1 (private, git-ignored
  `reports/2026-10-07-p1-audit/`). For P5: caveat added to CMP-2, the evidence doc and the deck: 36-70% of P1's Orin
  traffic runs are tool-faulted (1.7-4.2x energy), and RET-E1/CAP-E1 replayed 59-88% of them; Orin numbers to redo after
  P1's re-runs. `analysis/p1_repo.py` and `loop_prompts.py` follow P1's new drone layout (Thor tool calling now from the
  repo, 144 runs). Full doc refresh deferred until P1 freezes (Sandesh, 7 Oct).
- **2026-10-07:** consistency pass over the docs (no new results): plan version cited as v1.1, merge status stated as
  done, granite's bf16 pool labelled by GPU (26,467 GPU0, 26,648 GPU1), RET-E1's run scope, the Thor ban in AGENTS.md,
  stale next steps in HANDOFF. P1's GitHub `main` is at `d084f08` (ours: `3c47ebc`); not pulled, waiting for Sandesh.
- **2026-10-06 (after G1):** at Sandesh's request, every doc brought up to date: options plan v1.1 (outcomes §2.5, D18),
  master plan and Track A notes, review index (20 new docs), update notes in the dated reports, the evidence doc and
  its repo copy, the teaching guide, the deck (v2.1, 137 slides), HANDOFF, AGENTS and a README; WS runs backed up
  locally (SHA-256 checked).
- **2026-10-06 09:00:** CMP-2 checked by an independent review (Sonnet): 8 number fixes (pool 26,648; nudge counts;
  B's sampled range 7-14x; C's rule fires for retail at Thor's drone prices), outcomes of every rule stated, and
  wording that leaned outside §9 neutralised.
- **2026-10-06 08:40: G1 done.** RET-E1 finished (anchor holds; at 8 agents the default keeps nothing); CAP-E1 closed (FP8 KV
  -62% energy per session at 8 agents; quality undecided). CMP-2 complete with figures, lean (§9) and questions (§10).
  WS servers torn down. Stopped to report to Sandesh.
- **2026-10-06 07:05:** CMP-2 drafted. RET-E1's analysis fixed before its data arrived: the simulator now stops at the live
  run's span (live runs cut their last sessions), and takes its powers from NVML's energy counter like the live energy
  (the power reading runs 24% above the counter under load). Smoke test on CAP-E1's run: simulator within 6%.
- **2026-10-06 06:50:** A-E1 done (sampling removes the 26B's loops), A-E2 done, A-E5 done, C-E1 done (thinking decides),
  D-E2 done (policies cost more than recompute), CAP-E1 partly (FP8 doubles granite's pool; Gemma FP8 KV not on Ampere).
  RET-E1 running on both GPUs. Then CMP-2.
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

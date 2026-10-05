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

- **Wave 0 (setup)** started 2026-10-05 evening: S1 downloads, literature reviews in the background, S4, S5, CMP-1.

## G2 shared base

| ID | Task | Wave | Depends | Status | Output | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| S1a | Serve gemma-4-26B-A4B 4-bit on one GPU; smoke (chat, thinking, `gemma4` tools, pool, `/metrics`) | 0 | — | todo | `env/launch_gemma4_26b_awq_tp1.sh` | Settles D13; fallback FP8-dynamic over two GPUs |
| S1b | Serve gemma-4-E4B; smoke incl. images | 0 | — | todo | `env/launch_gemma4_e4b_tp1.sh` | P1's exact weights (Orin 32) |
| S1c | Serve granite-4.2-8b; smoke; pool size | 0 | — | todo | `env/launch_granite_tp1.sh` | RET-E1 needs pools of 27–33K |
| S1d | Record the recipes and gotchas; check FP8 `--kv-cache-dtype` on Ampere | 0 | S1a–c | todo | `AGENTS.md` §6b | Pin revisions, `HF_HUB_OFFLINE=1` |
| S2 | Gateway v0 (routes, streaming, call log, hooks, abort) | 1 | — | todo | `jsw/gateway/`, `tests/` | First check `/generate` output IDs, abort on disconnect |
| S3 | Trace replayer (`/generate`, exact lengths, real prefix reuse, tool gaps, burst injection) | 1 | S2, S5 | todo | `jsw/workloads/replay.py` | D14 |
| S4 | Streaming loop detector, parity with offline flags | 0 | — | todo | `jsw/policies/loop_detector.py`, test | 265 capped + 173 finished calls |
| S5 | Runner and manifest, shared run format | 0 | — | todo | `jsw/runner/` | Factor out of `aerogen_driver.py` |
| S6 | Analysis helpers: loop replay, live vs simulator | 2 | A-E1, RET-E1 | todo | `analysis/loop_replay.py`, `analysis/live_vs_sim.py` | |

## G1 evidence

| ID | Option | Task | Wave | Depends | Status | Output | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CMP-1 | all | Comparison doc skeleton from existing evidence | 0 | — | todo | `reports/2026-10-06-options/README.md` | Sandesh reviews the template (D16) |
| A-E1 | A | Do the loops survive sampling? Pilot (60 + 40), then full | 1 | S1a, S4, S5 | todo | `data/ws_runs/a-e1-*`, comparison §A | Reproduction check first (plan §2.4) |
| A-E2 | A | Stop and retry: R1 resample, R2 nudge, R3 lower budget | 2 | A-E1 | todo | `data/ws_runs/a-e2-*` | Stretch: grade in x86 AirSim with P1's checker |
| A-E3 | A | Literature: reasoning-length control, early exit, repetition, serving-side reasoning | 0 | — | todo | `review/systems/*.md`, novelty paragraph | Background subagent; verify against PDFs |
| A-E4 | A | Traffic's capped tool calls (analysis only) | 2 | — | todo | comparison §A | No replay possible (tool results not recorded) |
| A-E5 | A, sim | Decode batching: Gemma-4 MoE vs dense, 4K–32K context | 3 | S1 | todo | `data/ws_runs/calib-*` | Feeds the simulator's batching model |
| B-E1 | B | Gemma (E4B, 26B-4bit) as a step-wise agent on D1–D3 | 1 | S1a, S1b | todo | `data/ws_runs/b-e1-*` | Rule: median post-wait output ≤ 300 tokens |
| B-E2 | B | Redo the step-wise projections with Gemma's step sizes | 3 | B-E1 | todo | comparison §B | |
| B-E3 | B | Literature: agent design (code-as-action, ReAct, plan-and-execute, drone agents) | 0 | — | todo | novelty paragraph | Background |
| C-E1 | C | τ²-bench: single-session shape and ceiling, then N sessions with injected waits | 2 | S1, (S3) | todo | `data/ws_runs/c-e1-*` | Rule: ceiling ≥ 20% at a Jetson r |
| RET-E1 | RET | Live anchor: granite traffic replay at P1's pools, N = 1–8, 3 policies, vs simulator | 2 | S1c, S2, S3, S5 | todo | `data/ws_runs/ret-e1-*` | Rule: within ±15%, same ranking |
| D-E2 | D | Vision burst with N agents (E4B, 12.4K and 71K pools) | 3 | S3, D-P1 | todo | `data/ws_runs/d-e2-*` | Depends on P1's `ask_vlm` answer |
| D-E3 | D | Literature: unified memory, co-located models | 0 | — | todo | novelty paragraph | Background |
| CAP-E1 | CAP | FP8 vs bf16 KV: pool size and quality | 3 | S1d, A-E1, B-E1 | todo | `data/ws_runs/cap-e1-*` | Only if D17 says CAP is in |
| CAP-E2 | CAP | Literature: KV quantization, prompt and tool-loading | 0 | — | todo | novelty paragraph | Background; only if CAP is in |
| CMP-2 | all | Full comparison, Sandesh's review | 4 | all | todo | comparison doc | Then merge into the evidence doc and the deck |

## G2 option versions

| ID | Option | Task | Wave | Depends | Status | Output | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A-P1 | A | Decode guard policy (three stop actions, consecutive-cap rule) | 2 | S2, S4 | todo | `jsw/policies/decode_guard.py` | Evaluated on A-E2's prompts and live aerogen |
| D-P1 | D | Burst-aware memory policy (pin, burst admission, both) | 3 | S2, S3 | todo | `jsw/policies/burst_memory.py` | Evaluated by D-E2 |
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

- **2026-10-05 (late):** Sandesh approved the plan (D13–D17; CAP in; lean stated at the end). Wave 0 started.
- **2026-10-05:** plan v0.1 and this tracker written; WS clone pulled to `5373f35` and `~/jsw-dev` synced;
  feasibility checks recorded in plan §9. Waiting for Sandesh's approval.

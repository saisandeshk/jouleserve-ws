# Tracker — P5 work plan (v2.0, from 12 Oct)

**Updated:** 2026-10-12 (IST). Plan: [`OPTIONS_PLAN.md`](OPTIONS_PLAN.md) v2.0, approved by Sandesh on 12 Oct. The G1/G2 tasks of 5–11 Oct are closed (table near the end).

**Stop points.** Report to Sandesh:
- at checkpoint C1 (Mon 12 Oct 23:00);
- at checkpoint C2 (Tue 13 Oct 12:00);
- when the meeting materials (MTG-1) are ready;
- whenever a "done when" cannot be met.

Otherwise keep working.

How to use it:
- **When a task moves,** update its status and notes, and add one line to the log below.
- **Status values:** `todo`, `doing`, `done`, `blocked`, `dropped`, `waits D12`.
- **Done:** a task is `done` only when its "done when" holds and its output is in the repo, in `~/work/runs/` (WS) or
  in `data/ws_runs/` (local).
- **Results** go into CMP-2 (`reports/2026-10-06-options/README.md`). This file only points to them.
- **Specs and rules** are in the plan's sections, cited as "plan §x".

## Now

- **2026-10-12, evening.** Sandesh approved plan v2.0 (GATE done; RET-J1 added).
- **Docs:** the corrections that need no new data are applied (COR checklist) and pushed: CMP-2, the evidence doc's
  repo copy, HANDOFF, the review index and update notes in the dated reports. The device-results box (COR-1) and the
  artifacts (COR-3) follow the runs.
- **Running:** nothing yet, on the WS or the units.
- **Next:** SYNC-1, P1F-2, DEV-1 to DEV-5, aiming at C1 (Mon 23:00).

## Checkpoints (plan §3)

| ID | When | Passes if | If not |
| --- | --- | --- | --- |
| C1 | Mon 12 Oct 23:00 | (a) P1F-2's counts equal P1's summaries and the replay set is built; (b) one replayed session (any set) on Orin-32-1 done (DEV-4); (c) one loop prompt on Thor-1 done (DEV-4) | (a) only: P1F-3 overnight; CAP-J1 starts once (b) passes, in its late-start form (plan §5.2). (a) fails: fix first; P1F-3 moves to Tue |
| C2 | Tue 13 Oct 12:00 | Both CAP-J1 replicates have finished their N = 8 arms | One replicate: its numbers go to the meeting labelled "single replicate". None: no device number at the meeting; WS reruns plus "device platform ready" |
| F | Wed 14 Oct 09:00 | Results freeze; only complete, preflighted, WS-copied points analysed with plan §6's rules count | Incomplete points are labelled preliminary or left out |

## Before the meeting

| ID | Task | Where | Depends | Status | Done when | Notes, output |
| --- | --- | --- | --- | --- | --- | --- |
| GATE | Sandesh approves plan v2.0, including D19–D22 | — | — | **done** 12 Oct | approved | Plan, tracker and the corrected docs committed and pushed the same day |
| SYNC-1 | Pull `~/jouleserve-ws`; `env/sync_ws.sh` to `~/jsw-dev` | WS | GATE | todo | both at the pushed commit; `~/jsw-dev/REVISION` matches | On 12 Oct the clone was at `001dbd2`, `~/jsw-dev` at `09a4d5c` |
| P1F-1 | Pull the WS clone of P1 to `0cc2311a` | WS | — | **done** 12 Oct | HEAD `0cc2311a`, worktree clean | Fast-forward from `f6aabe40` (a fetch that outlived its ssh timeout raced the pull; no damage). Logs: `~/work/logs/p1pull_2026-10-12.log`, `p1ff_2026-10-12.log` |
| P1F-2 | Loader applies P1's selection rule; replay sets rebuilt (plan §5.1) | code local, run on WS | SYNC-1 | todo | our counts and pass rates equal P1's summaries for all 17 traffic configurations; a test pins it; clean Orin 32 granite and E4B replay sets with session counts | `analysis/p1_repo.py:191` skips every re-run folder; docstring lines 10–11 are stale. Copy `selection.py`'s logic with attribution; never import it in place. Check against P1's `traffic/grading/grades.csv` and `analysis/outputs/paper_tables/` |
| P1F-3 | RET-E1 and CAP-E1 on the clean sessions, plus `traffic_sim` (plan §5.1) | WS GPU0, GPU1 | P1F-2 | todo | 5 points run (bf16 at 25,358 tokens, N = 1, 4, 8; FP8 at 50,716, N = 4, 8); JSON and figure; rule outcome | 60-minute windows after 10 minutes of warm-up; J/token first (plan §6) |
| DEV-1 | Snapshot and stop P1's stack (plan §4.1) | all five units | GATE | todo | no GPU work; ports 30000, 8001, 41451 free; 10-min idle power saved; snapshot copied to the WS | Delete nothing. Leave P1 members' tmux sessions, k3s and Thor-1's legacy helper alone. ollama on Orin-64-1 through Sandesh if it is a system service |
| DEV-2 | P5 folders, container convention, image versions | all five | DEV-1 | todo | a read-only container prints its versions and exits on each unit; docker root unchanged (±10 MB); versions in AGENTS.md §3 | Orin-32-2 first (264 MB free). Orin-32-3's image `d4967327` differs from `05119cc6`. Caches (Triton, FlashInfer, torch, HF, `HOME`) go to `<p5>/cache` |
| DEV-3 | Jetson telemetry `jsw/telemetry/jetson.py` (plan §4.1) | code local; all five | DEV-2 | todo | within 1% of P1's own sampler over 5 min; median interval 200 ms ± 10%; samples merge with the WS call log | Thor `power_VIN_mW`; Orin `platform_total_power_mW` = VDD_GPU_SOC + VDD_CPU_CV + VIN_SYS_5V0 |
| DEV-4 | Our stack against SGLang 0.5.16; `env/launch_jetson.sh` | Orin-32-1, Thor-1 | DEV-2, DEV-3 | todo | one replayed granite session (Orin-32-1) and one loop prompt (Thor-1), end to end, run directories on the WS | Checks in plan §4.1 |
| DEV-5 | Preflight and teardown `env/jetson_preflight.py` | all | DEV-3 | todo | in use for every run from DEV-6 on | Seven checks (plan §4.1) |
| DEV-6 | Are the three Orin 32s interchangeable? | Orin-32-1/2/3 | DEV-4, DEV-5 | todo | idle power and decode J/token (batch 1, 8) per unit; verdict at ±3% | About 45 min per unit. Does not gate CAP-J1 (its replicates are within-unit): Orin-32-3 first, Orin-32-1/2 after their replicates |
| DEV-7a | Calibration: P1's 26B on Orin-64-1, FP8 and bf16 KV | Orin-64-1 | DEV-4, DEV-5 | todo | pools, idle, prefill and decode costs against batch and context | Report only |
| CAP-J1 | FP8 vs bf16 KV with several agents, with the N = 1 anchor (plan §5.2) | Orin-32-1/2/3 | DEV-4, DEV-5, P1F-2 | todo | both replicates (four arms each) and the anchor run; analysed with plan §6 by code committed first; outcome against the rules | About 2.5 h per point, 10 h per replicate. Orin-32-3: anchor, then spare |
| RET-J1 | Is kept state worth anything on the board? One agent, state dropped at every wait (`--no-reuse`), against the anchor on the same unit (plan §5.4) | Orin-32-3 | CAP-J1's anchor | todo | the run done and compared with the anchor by plan §6; verdict by the rule (< 5% holds) | About 2.5 h, right after the anchor |
| A-J1p | A-J1 pilot: 10 loop prompts, greedy and sampled (plan §5.3) | Thor-1 | DEV-4, DEV-5 | todo | 20 calls with loop flags and energy; result labelled indicative | Then the controls, until F |
| COR-1 | CMP-2 corrections (checklist below) and the device box | local | P1F-3; CAP-J1 for the box | doing | every checklist item fixed, or kept with a stated reason | 12 Oct: the corrections that need no new data are applied to CMP-2 (header, 12 Oct block, K1-K8, §3-§12). Kept, with reasons: A2's "71%" has no CMP occurrence; D-E2 has no per-token numbers (its 2.4x stays per session); RET's FP8 per-token gap is not computed; `ret_e1.png` still plots per session (note under it). Left: the numbers P1F-3 redoes, and the device box |
| COR-2 | Repo docs: HANDOFF, AGENTS, the evidence-doc copy, `review/systems/README.md`, dated reports, `planning/PLAN.md` | local | COR-1 | **done** 12 Oct | the stale items (checklist B) are gone; numbers match CMP-2 | AGENTS (machines, device rules), HANDOFF, master plan, plan pointers, the evidence doc's repo copy (now ahead of the Claude Doc, rev 171), the review index and update notes in the three dated reports. Redo after P1F-3 and the device runs |
| COR-3a | Deck v2.4: corrections, one device slide, one plan slide | artifact | COR-1, CAP-J1 | todo | published; renderer check clean | Scope to confirm with Sandesh (plan §11 item 2) |
| TRF-1 | Where is P1's final traffic agent? | Sandesh, with Priyanshu or Mayank | — | todo | host, folder and dependencies known | Thor-1 has an Aug–Sep version (`/media/ssd/Deepstream-Yolo-upstream/`); P1's code names the orchestration host .59. Not in mayankarya's home or on Thor-2's data disks |
| MTG-1 | Meeting materials (plan §8) | local | COR-1, CAP-J1, A-J1p | todo | CMP-2 box; deck v2.4; one-page device plan per option | Tue evening |

## At and after the meeting

| ID | Task | Depends | Status | Notes |
| --- | --- | --- | --- | --- |
| MTG-2 | The meeting: D12, agents per box, thresholds (D4), the split with P1 | MTG-1 | todo | Wed 14 Oct |
| MTG-3 | Record D12 as D23; turn the chosen branch (plan §7) into tasks with rules; master plan M8; HANDOFF | MTG-2 | todo | Same day |
| P1F-4 | Rerun `p1_opportunity`, `p1_caps` and `p1_repo_figures` on the final data | P1F-2 | todo | 25 configurations instead of 12 |
| P1F-5 | Why do granite and E4B evict KV on the Orins at one agent (52–68% of drone runs)? | P1F-2 | todo | Can now be checked on the units |
| TRF-2 | Copy P1's traffic agent, its sandbox image (`camera-agent-sandbox:1`, also on Thor-1) and data to the WS and the units | TRF-1 | todo | Look-and-copy only on Thor-2. Loading an image needs docker-root space, which the Orin 32s lack: Thor-1 or Orin-64-1 first |
| TRF-3 | Validate the agent at N = 1 against P1's recorded runs (pass rate, tokens) | TRF-2 | todo | |
| COR-3b | Evidence doc and teaching guide | MTG-2 | todo | Unless Sandesh wants them before the meeting |
| COR-4 | Notes for P1 (private, never in git) | — | todo | Kept in the git-ignored `reports/2026-10-07-p1-audit/notes_for_p1_2026-10-12.md`; passed to P1 through Sandesh |
| DEV-7b | Calibration of the other models (Thor-1 26B and granite; Orin 32 granite bf16 and FP8, E4B) | DEV-5 | todo | |

**Branch tasks (plan §7). They wait for D12;** the chosen branch gets specs and rules first.

| Branch | Tasks |
| --- | --- |
| CAP | CAP-J2 (FP8 vs bf16 on real tasks: traffic with P1's agent; the drone pair on Orin-64-1), CAP-J3 (other levers), CAP-J4 (capacity-aware admission, only if a gap remains) |
| A | A-J1 (full set, more seeds), A-J2 (pass rates under sampling with P1's harness), A-J3 (the decode guard in P1's agent loop), A-J4 (traffic retries with P1's agent) |
| D | D-J1 (the vision burst on Orin-64-1), D-J2 (co-located models) |
| B | B-J1 (E4B as a step-wise agent on an Orin 32; needs mayankarya's OK) |
| C | C-J1 (τ²-bench with E4B, thinking off, on an Orin 32) |

## COR checklist (12 Oct)

Sources:
- Claude's own check of the result files (M items);
- a read-only consistency sweep (Sonnet) of every doc (A–D items).

Locations are file:line as of 12 Oct, before any edit. Abbreviations: H = `HANDOFF.md`, AG = `AGENTS.md`, TR = this
file before 12 Oct, OP = `OPTIONS_PLAN.md` v1.2, JW = the master plan, PL = `planning/PLAN.md`, CMP = CMP-2, EV =
`reports/2026-10-02-p5-evidence/README.md`, RS = `review/systems/README.md`, P1R = `reports/2026-10-05-p1-repo/README.md`,
DR = `reports/2026-10-04-drone-runaways/README.md`, AS = `reports/2026-10-03-admission-sim/README.md`.

**Claude's check (M):**

| ID | What | Where | Fix |
| --- | --- | --- | --- |
| M1 | P1's FP8 natural pair is not in the docs. P1's gemma-26B Reflexion drone agent passed 96/117 (82.1%) on Thor with BF16 KV and 94/115 (81.7%) on Orin 64 with FP8 KV, on the 39 task-instances both ran; runs with a capped call rose from 33% to 42%; energy per success was 105 vs 92 kJ | CMP §7, §9; H | Add it with its caveats (device and pool differ; pass rate is coarse). State that CAP-E1's own rule reads it as "free configuration" |
| M2 | CAP's −62% leads everywhere, but energy per completed session is biased by sessions cut at the window's end | CMP top, §7, §9; H; EV; deck | Lead with J/token: −53% (3.95 → 1.87 J) at N = 8; −45% best against best (bf16 N = 4, 3.43 J). Keep −62% labelled |
| M3 | The loader bug is described as mixing re-runs with faulted originals; in fact it skips every re-run and misses the vision-task exclusion | H; TR; CMP §12 | Describe it correctly; P1F-2 fixes it |
| M4 | "The fix for P1 is one line" claims more than A-E1 measured | CMP §3 | "Removes the loops on a 4-bit stand-in (one seed, temperature 1.0); pass rate unmeasured" |
| M5 | D-E2: pinning recomputed 191,604 tokens against the default's 195,432 (100% of the prefix both times), so its −3.8% is noise; admit-4 (−4.05%) is missing from the table; at N = 1 three policies never engaged (115,573 tokens recomputed in every arm) | CMP §6; H; OP R.3 (record, unchanged) | Correct CMP and H; the verdict "within 5%" stands |
| M6 | B's 11–19× rests on 9 strict successes and stacks differences: E4B vs the 26B, a simulator without buildings, our checker vs P1's grader | CMP §4; H | State the base and the stacked differences |
| M7 | RET, CAP and D have one run per setting | CMP §11 | Say so next to each number |
| M8 | Per token, the simulator is within 6% of the live engine at every point (−1.4%, −4.6%, +5.8%); the 14.2% gap at N = 4 per session comes mostly from which sessions finished in the window (21 simulated, 18 live) | CMP §5; H | Add it next to RET's per-session numbers |

**Numbers that disagree (A):**

| ID | What | Where | Fix |
| --- | --- | --- | --- |
| A1 | P1 Reflexion kJ per success: "219–499" (and 5–13×) vs "499 (D1), 284 (D2)" (and 11–19×) | CMP:222, H:265, AS:72, EV:704 vs CMP:258, 83, TR:47, OP:253 | Find what 219 was (likely an older method); state one set with its method; label each ratio by agent and model |
| A2 | Online loop stop "43.5% / 35.7%" vs "31% / 36%"; capped calls "71% of LLM time (both agents)" vs "57% … 70%" | H:245, CMP:108, OP:50, EV:98 vs AS:15-17, DR:69; H:243 vs EV:419, AS:90 | Label the task sets: Reflexion on 16 tasks (P1R:432); tool calling on 12 tasks (104-run copy) |
| A3 | First-cap stop on Thor tool calling: 63.1% saved, 16 lost (our 104-run copy) vs 66.6% and 17 (P1's paper, 144 runs) | CMP:110, H:246, P1R:363 vs CMP:648 | Cite P1's 144-run numbers first; label ours |
| A4 | "Decode is 96–99% of LLM time" drops the exceptions | CMP:86, 132 vs RS:10, P1R:72; CMP:621-622 | "96–99% except Qwen2.5-VL (prefill 15–16%) and Devstral drone (22%)" |
| A5 | `ask_vlm`: "5% of calls, 62% of tool energy" vs P1's final 5.92% / 54.6% | EV:519, 524 vs CMP:654-655, EV:829, RS:19 | Use P1's final values |
| A6 | Orin 64 gemma overflow before the re-runs: 21% vs 17.5% | EV:432, P1R:483, CMP:427, OP:54 vs CMP:637 | Use P1's final 17.5% → 24.2%; label 21% as the 5 Oct value |
| A7 | D-E2 at 4 agents "+3..14%" vs "−3.8%" | TR:51 vs CMP:389, OP:255 | Gone from the rewritten tracker; CMP per M5 |
| A8 | Gateway conversion bug "open" vs "since fixed" | TR:46 vs CMP:266, OP:252 | Fixed (not re-run): rewritten tracker |
| A9 | P1's post-submission plan: MB1/MB4/MB5 vs MB4/MB5/MB6; the warm-cache arm | JW:12 vs H:24-26, CMP:650-656; EV:781-782 | MB4, MB5, MB6 (master plan rewritten 12 Oct); EV per CMP |
| A10 | Minor: "538–3,406" vs 536, and Devstral 112 | EV:207 vs P1R:223, 225 | Use P1R's values |

**Stale (B):**

| ID | What | Where | Fix |
| --- | --- | --- | --- |
| B1 | Meeting "Mon 12 Oct" | H:5-6, 77, 130, 148, 300, 329; TR:16, 90; OP:13; JW:13, 24; PL:16; EV:20, 42, 1022, 1049; evidence doc, teaching guide, deck | Wed 14 Oct |
| B2 | "WS down" | H:19-20, 38, 68, 102, 170, 174, 305; AG:242; TR:19, 74, 91; CMP:46, 589; EV:813, 960 (EV:1035 contradicts EV:813) | Back since 12 Oct |
| B3 | "Devices with P1" | AG:24, 54; H:101, 181-182, 312, 336; CMP:580-582; EV:154-155, 1013, 1036, 1056; PL:43-45; JW:246, 254. Also H:182 cites §7 Q6 (the Thor ban) instead of Q5 | P5 has five units since 12 Oct |
| B4 | "Thor off-limits" | AG:52, 65; H:7, 73, 179-180, 283, 337, 348; TR:86, 110; OP:341; JW:314 and PL:416 give look-only rules | Thor-1 is P5's (12 Oct); Thor-2 is look-and-copy only |
| B5 | Answered items shown as open: "reply pending" (EV:114, CMP:363, P1R:17-18); EV:238-239 vs H:112, EV:67; JW:3 vs JW:21; OP §1's open questions | as listed | Answered by P1's paper; OP rewritten 12 Oct |

**Summaries stronger than their sections (C), and CMP-2's internal contradictions (D):**

| ID | What | Where | Fix |
| --- | --- | --- | --- |
| C1 | RET "holds live" drops: narrowly at N = 4, ranking degenerate, narrower than planned | CMP:33, H:62-63, EV:38-39, AS:3-6 vs CMP:495, 498, 504-505 | Add the three caveats, plus M8 |
| C2 | "Drone runaways are a decoding setting", "they come from greedy decoding" | H:52, EV:100, RS:5, 29-30, CMP:577, 546-547, 90 vs CMP:159-163, 604-605 | "Greedy decoding loops on 77% of the loop prompts on a 4-bit stand-in; sampling on none (one seed); Reflexion prompts only" |
| C3 | B's "9 of 11 greedy, 7 of 13 sampled" hides 8 of 21 sampled missions lost to the bug | CMP:20-22, 255, H:56-57 vs CMP:265-267 | State the lost missions next to the rates |
| C4 | "Overflows roughly doubled" | CMP:49, 559; H:17-18; EV:961 vs CMP:637-638 | Orin 32 granite 10.6% → 21.2%; Orin 64 gemma-26B 17.5% → 24.2%; Orin 64 granite 14.3% → 19.0% |
| C5 | "P1 lists FP8 KV as untested", though P1 ran FP8 KV in some drone sweeps | H:23, CMP:51, 432, 451, RS:18, EV:830 vs CMP:659-661 | "Untested as a lever in P1's paper, though P1 ran FP8 KV in its held-out Orin 64 drone sweep" |
| C6 | "P1 ran FP8 KV on an Orin 64" stated as fact while P1's records hold no dtype | H:28-29, TR:53 vs CMP:436-438 | Now verified: the server still running on Orin-64-1 on 12 Oct had `--kv-cache-dtype fp8_e5m2` (SGLang 0.5.16 image) |
| C7 | The vision burst evicts "none on Thor", but Thor Qwen3.6 evicts in 17 of 81 runs | CMP:353, H:230 vs EV:506, 512 | Add it, with EV's explanation |
| C8 | A-E1 on E4B: "every call finished" | CMP:157-158 vs `a_e1.json` | In the Orin 32 arms 2–3 of 40 controls and 1–2 of 5 loop prompts hit the cap without looping; the "upper bound 11%" is the bound for n = 30 (about 6% for n = 60) |
| C9 | D-E2: "the best, pinning alone, −3.8%" | CMP:377, H:318-319, OP:255, CMP:83 vs `d_e2.json` | Per M5 |
| C10 | `ask_vlm` "confirms the agent's own model, so contention is inside one engine" | CMP:372-373 vs CMP:654-656, 670-671 | "Taken up in part: the vision tool is the agent's own model; the burst is not mentioned" |
| D1 | CMP-2: "reply pending" (362-363) vs answered (372-373, 654); "taken up" (654) vs "in part" (670-671) | CMP | Make them agree |

## Waiting on others

| What | From | Blocks | Since |
| --- | --- | --- | --- |
| Approval of plan v2.0 (D19–D22) | Sandesh | everything in plan §3–§5 | 2026-10-12 |
| Where P1's final traffic agent is, and what it needs | Priyanshu or Mayank, through Sandesh | TRF-2/3; CAP-J2 traffic, A-J4, D-J1 | 2026-10-12 |
| What the 6–10 Oct FP8 runs on the units were (MB5?), whether they are finished, and whether P5 may see the results | P1's mentor, through Sandesh | CAP-J1's framing; the split | 2026-10-12 |
| Agreement on the split with P1: MB4 (overlaps A-E1/A-J1), MB5 (overlaps CAP-E1/CAP-J1), MB6 (D) | P1, through Sandesh; the meeting | the A and CAP claims | 2026-10-10 |
| Direction D12 | the professor, Wed 14 Oct | plan §7 | 2026-10-05 |
| Permission to extend aerogen | mayankarya | B-J1 | 2026-10-01 |
| ~~The two CLGSCE files changed on the Thor on 23 Sep~~ superseded: P1's drone stack is installed on the units | — | — | closed 2026-10-12 |
| ~~The WS back up~~ back on 12 Oct | — | — | closed 2026-10-12 |

## Closed: G1 and G2 tasks (5–11 Oct, plan v1)

Specs and rules are in the plan's Appendix R. Corrections to these outcomes are in the COR checklist above.

| ID | Task | Outcome | Output |
| --- | --- | --- | --- |
| S1a–d | P1's models on the WS | E4B and granite in SGLang 0.5.20; the 26B only as a 4-bit GGUF in llama.cpp (D13); granite's FP8 KV doubles its pool; Gemma-4's FP8 KV fails on our A5000s in 0.5.20 | `env/launch_model.sh`, `env/launch_llamacpp.sh`, AGENTS §6c |
| S2 | Gateway v0 | done | `jsw/gateway/` |
| S3 | Trace replayer | done | `jsw/workloads/replay.py` |
| S4 | Streaming loop detector | done; matches the offline flags | `jsw/policies/loop_detector.py` |
| S5 | Runner and manifest | done | `jsw/runner/run.py` |
| S6 | Analysis helpers | done | `analysis/{a_e1,…,cap_e1,options_figures}.py` |
| CMP-1, CMP-2 | The comparison | done 6 Oct, Sandesh's review pending; corrections in COR-1 | CMP-2 |
| A-E1 | Do the loops survive sampling? | 26B 4-bit (llama.cpp): greedy loops 23/30, sampling 0/30 (one seed); E4B inconclusive | `a_e1.json` |
| A-E2 | Stop and retry | rule not met (10 of 29 at ≤ 50% cost); resampling recovers 17/17 | `a_e2.json` |
| A-E3, B-E3, D-E3, CAP-E2 | Literature reviews | done | `lit_A.md`, `lit_B.md`, `lit_D.md`, `lit_CAP.md` |
| A-E4 | Traffic's capped calls | 31–33% of gemma traffic LLM energy [P1-meas] | `a_e4.json` |
| A-E5 | Decode batching | batch 1 → 16 cuts J/token 13× (granite), 13.5× (E4B) | `~/work/runs/calib/` |
| B-E1 | E4B as a step-wise agent | rule met (median 63/68 tokens after a tool result); 9 of 33 missions lost to a since-fixed bug, not re-run | `b_e1.json` |
| B-E2 | Step-wise projections | 26–27 kJ per strict success (greedy) vs P1's Reflexion 284–499 kJ [proj] | `b_e2.json` |
| C-E1 | τ²-bench | thinking on: borderline; thinking off: 25% (opportunity) | `c_e1.json`, `c_e1_nothink.json` |
| RET-E1 | Live anchor for the simulator | within 14.2% per session (6% per token); ranking degenerate; narrower than planned | `ret_e1.json` |
| D-E2 | The vision burst with several agents | rule not met (within 5%; the policies' differences are noise) | `d_e2.json` |
| CAP-E1 | FP8 KV | pool ×2; −53% J/token at N = 8 (−62% per session, biased), −45% best against best; quality undecided | `cap_e1` JSON |
| A-P1 | Decode guard | built; not yet inside a live agent loop → A-J3 | `jsw/policies/decode_guard.py` |
| D-P1 | Burst-aware memory | built; evaluated by D-E2 | `jsw/policies/burst_memory.py` |
| A-P2 | P1's CLGSCE agent live behind A-P1 | superseded: P1's drone stack runs on the units → A-J2, A-J3 | — |
| C-P1, D-P2, B-P1, CAP-P1 | Later option versions | moved into the branches: C-J1, D-J2, B-J1, CAP-J4 | — |
| P1F-0 | P1's paper and final data read; docs and artifacts updated | done 10–11 Oct | `analysis/p1_final_figures.py`, CMP-2 §12 |
| P1F-6 | Gemma-4 FP8 KV: what P1 ran, and whether 0.5.16 runs it on the A5000s | closed 12 Oct: P1's server on Orin-64-1 used `fp8_e5m2` on SGLang 0.5.16. Gemma's FP8 runs on the device (DEV-7a, CAP-J2), so the A5000 question is dropped | — |

## Log (newest first)

- **2026-10-12:** the WS is back (idle; runs, models and venvs intact). P5 got five Jetsons (Thor-1, Orin-64-1,
  Orin-32-1/2/3), and the professor meeting moved to Wed 14 Oct.
  - **Device pass (read-only, all five units):** P1's servers, MCP servers and AirSim were still up; the Orin 32 docker
    SSDs are full; the models are at our pinned revisions; the clocks are locked; board power is readable without
    root.
  - **Mounts:** Sandesh fixed the three Orin 32 USB-drive mounts (fstab `ntfs-3g`).
  - **P1's mentor:** we may stop P1's things but delete nothing, and may use P1's code.
  - **P1F-1 done:** the WS clone of P1 is at `0cc2311a`.
  - **Corrections found:** the doc sweep (Sonnet) and our own check of the result files, in the COR checklist. CAP's
    −62% is −53% per token and −45% best against best; P1's FP8 natural pair is 82.1% vs 81.7%; the loader skips
    re-runs; several summaries overclaim.
  - **Docs:** plan v2.0 and this tracker rewritten; the master plan, AGENTS and HANDOFF updated. Sandesh approved the
    plan; RET-J1 added (kept state at one agent, on the board). The corrections that need no new data were applied to
    CMP-2, the evidence doc's repo copy, HANDOFF, the review index and the dated reports (notes), then pushed.

- **2026-10-10/11:** P1 submitted (SIGMETRICS 2027, data frozen 10 Oct 10:30 IST); local P1 clone pulled to `0cc2311a`
  (WS down, so the WS clone stays at `f6aabe4`). Read the paper and the final data: decode-bound everywhere (prefill
  0.7-3.9% of LLM time in 18 of 22 configurations); 776 tool-faulted Orin traffic runs replaced by re-runs (the 7 Oct
  caveat resolved in P1's data; overflow up to 28.1%); online stop left to "separate evaluation"; MB4/MB5/MB6 planned,
  overlapping A and CAP; our corrections 3 and 5 adopted, 1 and 4 in part, 2 not. Our FP8 claim corrected: P1 ran
  Gemma-4 FP8 KV on an Orin 64 (SGLang 0.5.16). `analysis/p1_final_figures.py` (3 figures); CMP-2 §12; evidence doc
  (rev 171) and repo copy; teaching guide (rev 184); deck v2.3; audit doc note; HANDOFF, AGENTS, plans, dated reports,
  review notes. New tasks P1F-1 to P1F-6.

- **2026-10-07 (afternoon):** P1 pulled to `f6aabe4` (local + WS); a P1 audit for P1 (private, git-ignored
  `reports/2026-10-07-p1-audit/`). For P5: caveat added to CMP-2, the evidence doc and the deck: 36-70% of P1's Orin
  traffic runs are tool-faulted (1.7-4.2x energy), and RET-E1/CAP-E1 replayed 59-88% of them; Orin numbers to redo after
  P1's re-runs (resolved in P1's data on 10 Oct: see above). `analysis/p1_repo.py` and `loop_prompts.py` follow P1's new drone layout (Thor tool calling now from the
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
  D-E2 done (policies cost more than recompute), CAP-E1 partly (FP8 doubles granite's pool; Gemma FP8 KV not on our A5000s).
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

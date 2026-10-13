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

- **2026-10-13, 05:25 IST.** C1 passed (12 Oct 19:10); **C2 passed at 05:17** (both CAP-J1 replicates complete).
- **Done:** P1F-1, P1F-2, P1F-3, DEV-1 to DEV-6, DEV-7a, A-J1p, CAP-J1 (with its anchor), RET-J1.
- **Running** (WS tmux; background waiters report the first failure or the end):
  - Orin-32-1/2/3: idle (CAP-J1 done 05:17, RET-J1 00:14, DEV-6 05:36).
  - Thor-1: A-J1's full set, 30 loop prompts and 20 controls, greedy and sampled (`aj1-thor-20261012T2229`, `q-thor`,
    ~8-9 h; it repeats the pilot's 10 loop prompts).
  - WS and Orin-64-1: idle.
- **Next:** A-J1's rules (~07:00-08:00); the CMP-2 device box (COR-1); MTG-1; F at Tue 23:00.

## Checkpoints (plan §3)

| ID | When | Passes if | If not |
| --- | --- | --- | --- |
| C1 | Mon 12 Oct 23:00 | (a) P1F-2's counts equal P1's summaries and the replay set is built; (b) one replayed session (any set) on Orin-32-1 done (DEV-4); (c) one loop prompt on Thor-1 done (DEV-4) | (a) only: P1F-3 overnight; CAP-J1 starts once (b) passes, in its late-start form (plan §5.2). (a) fails: fix first; P1F-3 moves to Tue |
| C2 | Tue 13 Oct 12:00 (**passed 05:17**: both replicates complete, all four arms each) | Both CAP-J1 replicates have finished their N = 8 arms | One replicate: its numbers go to the meeting labelled "single replicate". None: no device number at the meeting; WS reruns plus "device platform ready" |
| F | Tue 13 Oct 23:00 (meeting Wed 09:00-10:00) | Results freeze; materials (MTG-1) final by Wed 08:00; only complete, preflighted, WS-copied points analysed with plan §6's rules count | Incomplete points are labelled preliminary or left out |

## Before the meeting

| ID | Task | Where | Depends | Status | Done when | Notes, output |
| --- | --- | --- | --- | --- | --- | --- |
| GATE | Sandesh approves plan v2.0, including D19–D22 | — | — | **done** 12 Oct | approved | Plan, tracker and the corrected docs committed and pushed the same day |
| SYNC-1 | Pull `~/jouleserve-ws`; `env/sync_ws.sh` to `~/jsw-dev` | WS | GATE | **done** 12 Oct | both at the pushed commit; `~/jsw-dev/REVISION` matches | Both at `42f9437` (17:15 IST); the clone was at `001dbd2`, `~/jsw-dev` at `09a4d5c`. Re-sync before each WS run |
| P1F-1 | Pull the WS clone of P1 to `0cc2311a` | WS | — | **done** 12 Oct | HEAD `0cc2311a`, worktree clean | Fast-forward from `f6aabe40` (a fetch that outlived its ssh timeout raced the pull; no damage). Logs: `~/work/logs/p1pull_2026-10-12.log`, `p1ff_2026-10-12.log` |
| P1F-2 | Loader applies P1's selection rule; replay sets rebuilt (plan §5.1) | code local, run on WS | SYNC-1 | **done** 12 Oct | our counts and pass rates equal P1's summaries for all 17 traffic configurations; a test pins it; clean Orin 32 granite and E4B replay sets with session counts | `analysis/p1_selection.py` ports P1's `selection.py` (Mayank Arya, `577ef7a6`) and applies P1's `overrides.csv` (a faulted run is a fail, as P1's `apply_grades.py` writes it). All 17 cells equal P1's committed G2 (non-passing share), B5 (overflow share) and `suite_stats` (3,605 runs); 142 overridden runs, all in the Orin 64 gemma-26B and Devstral Reflexion arms, as P1's paper says. `tests/test_p1_selection.py` passes on the WS (`46cbcba`). `analysis/p1_repo.py` reads every run folder through the rule (9 more traffic cells). Clean replay sets in `~/jsw-dev/data/replay/` (6 Oct sets kept in `data/replay_2026-10-06/`): **Orin 32 granite** 189 clean runs (133 re-runs, all at pool 25,358; 11 without a trace), 165 sessions, 125 completed, 800 calls; **Orin 32 E4B** 252 runs, 248 sessions, 243 completed, 940 calls. P1's `suite_stats` per-class counts are over all 4,737 rows (before selection) |
| P1F-3 | RET-E1 and CAP-E1 on the clean sessions, plus `traffic_sim` (plan §5.1) | WS GPU0, GPU1 | P1F-2 | **done** 12 Oct | 5 points run (bf16 at 25,358 tokens, N = 1, 4, 8; FP8 at 50,716, N = 4, 8); JSON and figure; rule outcome | 60-minute windows after 10 minutes of warm-up; J/token first (plan §6) **Started 12 Oct 18:44** (early: C1 (a) passed and the WS was idle), `env/queue_p1f3.sh`: harness pinned to the GPU's NUMA node, pool set with `--max-total-tokens`, window held at 25,358 **Done 22:27** (`p1f3-ws-*-20261012T1844`, all five rc 0, windows complete, no errors; `analysis/p1f3.py` → `reports/2026-10-06-options/p1f3.json`). **J per generated token** (WS, NVML energy counter): bf16 N = 1, 4, 8: 5.64, 3.98, 3.44; FP8 N = 4, 8: 1.870, 1.870. FP8 against bf16: **−53% at N = 4, −46% at N = 8, −45.7% best against best** (3.44 → 1.87; CAP-E1 on 6 Oct: −53% at 8, −45%). Per completed session (prorated): bf16 33.9, 27.1, 24.4 kJ; FP8 13.1, 14.2 kJ; sessions in the hour 19, 23, 25 and 51, 47. At FP8 N = 8 the pool runs ~3.7 requests at a time (3.8 queued), so N = 8 behaves like N = 4. bf16 N = 8 keeps no state (0 of 169 calls hit the cache, as in RET-E1). **Simulator rule (±15% per session, ±10% per token, every point): fails.** It holds at the three bf16 points (+4.6, −6.9, −3.0% per session; +2.0, −1.5, +6.8% per token) and fails at both FP8 points (+24.6, +13.0% per session; +22.1, +17.4% per token): the simulator over-predicts FP8 energy, so its FP8/pool-doubling gains are conservative (cause not checked; its device model is calibrated on bf16 decode) |
| DEV-1 | Snapshot and stop P1's stack (plan §4.1) | all five units | GATE | **done** 12 Oct | no GPU work; ports 30000, 8001, 41451 free; 10-min idle power saved; snapshot copied to the WS | Delete nothing. Leave P1 members' tmux sessions, k3s and Thor-1's legacy helper alone. ollama on Orin-64-1 through Sandesh if it is a system service. Checked 12 Oct, 18:00 IST: all idle (no SGLang request in 30 min, no harness, AirSim hovering); no container has a restart policy; Thor-1's `ensure_infra.sh` (P1's harness) is a one-shot check, not a watchdog (its leftover shell parents the MCP server: stop both by PID). Last starts: Orin-64-1 AirSim 12 Oct 01:46 IST, Orin-32-1/2 servers 10 Oct ~10:40/12:00 IST. **12 Oct 18:15-18:21:** snapshots (`env/jetson_snapshot.sh`) on all five units in `<p5>/state/2026-10-12/`, copied to the WS `~/work/device_state/<unit>/2026-10-12/` (SHA-256 checked). Stopped: Thor-1 `p1-final-granite`, its MCP server, the `ensure_infra.sh` shell and `thor_headless`; the Orins' `sglang-benchmark` (and Orin-32-3's idle `sglang-orin`), the AirSim containers, and the MCP servers on Orin-32-1/2. **Not stopped:** the MCP servers on Orin-64-1 and Orin-32-3 run as `yash`, not our `mayankarya` login (idle, 0.1-0.4% CPU, port 8001 only; needs Sandesh); ollama (Sandesh: leave it). P1's live Orin 32 servers (started 7-10 Oct) ran FP8 KV at a 60,000 pool: not P1's traffic-sweep flags, which come from the runs' own records **12 Oct 21:10:** the two `yash` MCP servers are PID 866168 (Orin-64-1) and PID 238395 (Orin-32-3), both `clgsce_mcp_server.py`, parent PID 1 (outside yash's tmux sessions), on 127.0.0.1:8001; Sandesh stops them with sudo after saving their working folders to `<p5>/state/2026-10-12/` **Done 21:20:** Sandesh stopped both with sudo; port 8001 is free on both units and yash's tmux sessions are untouched. Their working folder, `/home/yash/agentic_aeroeval/vendor/CLGSCE` on both, is saved in `<p5>/state/2026-10-12/mcp_<pid>_cwd.txt` (copied to the WS) for an exact restart. The 9.8 GB held on Orin-64-1 is not in nvmap's iovmm clients (0 K; `nvmap_clients.txt`): cause unknown, no effect on any pool so far |
| DEV-2 | P5 folders, container convention, image versions | all five | DEV-1 | **done** 12 Oct | a read-only container prints its versions and exits on each unit; docker root unchanged (±10 MB); versions in AGENTS.md §3 | Orin-32-2 first (264 MB free). Orin-32-3's image `d4967327` differs from `05119cc6`. Caches (Triton, FlashInfer, torch, HF, `HOME`) go to `<p5>/cache` **12 Oct:** folders `runs state logs tmp bin cache` in each `<p5>`; a read-only container (`--rm --read-only --tmpfs /tmp --log-driver none`, caches in `<p5>/cache`) printed its versions on all five units; docker root unchanged (Orins 0 bytes, Thor-1 +98 KB). Both Orin builds carry the same versions (SGLang 0.5.16, torch 2.11.0, CUDA 12.6, flashinfer 0.6.14); Thor-1 SGLang 0.5.16 (torch 2.11.0+cu130, CUDA 13.0). Versions in AGENTS.md §3 and `configs/jetsons.json` |
| DEV-3 | Jetson telemetry `jsw/telemetry/jetson.py` (plan §4.1) | code local; all five | DEV-2 | **done** 12 Oct | within 1% of P1's own sampler over 5 min; median interval 200 ms ± 10%; samples merge with the WS call log | Thor `power_VIN_mW`; Orin `platform_total_power_mW` = VDD_GPU_SOC + VDD_CPU_CV + VIN_SYS_5V0 **12 Oct:** `jsw/telemetry/jetson.py` written (rails verbatim, `power_total_mw` as P1's Orin traffic vitals define it, VIN on Thor; trapezoid energy, gaps > 1 s flagged; WS-side start/stop; clock offset over one ssh session, round trip < 1 ms). 10-min idle readings parsed: Thor-1 25.1 W, Orin-64-1 10.3 W, Orin-32-1/2/3 11.2/11.2/11.1 W; about 4.9 samples/s. Left: the side-by-side with P1's sampler (staged on Orin-32-1 for the DEV-4 session) **Side-by-side (12 Oct, Orin-32-1, the DEV-4 session, 319 s):** ours 13,347 J, P1's sampler 13,346 J (+0.01%); median interval 214 ms (P1's 212 ms); no gaps; samples merge with the call log by the measured clock offset (−60 ms, round trip < 1 ms). Thor-1: root tegrastats adds ~35 ms per sample (241 ms in the DEV-4 loop run; P1's own Thor drone samples: 223 ms), so Thor-1 requests 180 ms (202 ms in a 20 s test; `configs/jetsons.json`) |
| DEV-4 | Our stack against SGLang 0.5.16; `env/launch_jetson.sh` | Orin-32-1, Thor-1 | DEV-2, DEV-3 | **done** 12 Oct | one replayed granite session (Orin-32-1) and one loop prompt (Thor-1), end to end, run directories on the WS | Checks in plan §4.1 **12 Oct:** `env/launch_jetson.py` (P1's flags per unit and model; granite's from P1's run records: triton, chunked prefill 2,048, CUDA graphs off, context 26,624, mem 0.80, parsers qwen3_coder/deepseek-r1), `env/dev4_checks.py` (the five API checks), `env/jetson_replay_point.sh`, `env/jetson_loop_point.sh`. Thor-1: P1's 26B up with P1's final drone flags (`p1-final-gemma-it`: pool 80,000, context 65,536, mem 0.65), loaded in 144 s despite 51 GB of host memory held outside any process. Orin-32-1: granite loads slowly from the NTFS USB disk (~85 s per shard) **API checks (12 Oct), Thor-1 and Orin-32-1, both pass:** exact lengths (64/32/16); cache hit on the shared prefix (1,564 tokens), none on fresh IDs; the runner's `/metrics` names present except `evicted_tokens_total` (not exported by 0.5.16); verified flush; a dropped client aborts its request. Gateway `--generate-stream` added (first-token time, for decode rates) **Both done end to end (12 Oct), run directories on the WS:** `dev4-o32a-replay-20261012T1849` (one clean granite session, 3 calls: prompt and output lengths equal P1's trace, cache hits 3,967 and 4,144 tokens, decode 8.5-8.6 tok/s, 1,481 board samples) and `dev4-thor-loop-20261012T1850` (P1's A16 loop prompt, greedy on P1's bf16 26B: the gateway's detector stopped it at 31,000 characters after 434 s, against P1's 32,768 tokens in 1,226 s; decode 25.1 tok/s against 26.7 in P1's record) |
| DEV-5 | Preflight and teardown `env/jetson_preflight.py` | all | DEV-3 | **done** 12 Oct | in use for every run from DEV-6 on | Seven checks (plan §4.1) **12 Oct:** `env/jetson_preflight.py` written (seven checks; P1's verified flush; `--no-temp` after a run) and passing on all five idle units; first use in DEV-4 Used before and after both DEV-4 runs (both passed) and in every night queue |
| DEV-6 | Are the three Orin 32s interchangeable? | Orin-32-1/2/3 | DEV-4, DEV-5 | **done** 13 Oct | idle power and decode J/token (batch 1, 8) per unit; verdict at ±3% | About 45 min per unit. Does not gate CAP-J1 (its replicates are within-unit): Orin-32-3 first, Orin-32-1/2 after their replicates **12 Oct 19:05:** Orin-32-3 first (`q-o32c`) **Orin-32-3 done 19:20** (`dev6-o32c-20261012T1905`): preflight and 10-minute idle passed, calibrate2 rc 0 (batch 8 at 8,000 tokens skipped: it does not fit the 25,358 pool). Its after-check was lost to a preflight bug (no `--out` folder without `--idle`; fixed in `d674269`) **Orin-32-1/2 done 05:36/05:24** (`dev6-o32a-20261013T0517`, `dev6-o32b-20261013T0506`; preflights before and after passed). **Verdict (`analysis/dev6.py`, committed before their data was read → `device/dev6.json`): interchangeable.** 10-minute idle with the server loaded 13.56 / 13.59 / 13.40 W (Orin-32-1/2/3; max 0.9% from the mean); decode J/token at batch 1, 1K context 4.74 / 4.78 / 4.92 (2.2%), batch 8, 1K 0.664 / 0.666 / 0.679 (1.4%), batch 1, 8K 5.11 / 5.10 / 5.27 (2.1%); all within ±3%. Orin-32-3 runs ~3% above the other two, inside the rule. So the spare unit's reruns can replace a point, and cross-unit claims are allowed |
| DEV-7a | Calibration: P1's 26B on Orin-64-1, FP8 and bf16 KV | Orin-64-1 | DEV-4, DEV-5 | **done** 12 Oct | pools, idle, prefill and decode costs against batch and context | Report only **Started early, 12 Oct 19:08** (the unit was idle): `env/queue_dev7.sh`, FP8 then bf16 KV, P1's flags (pool 60,000 requested), running requests up to 8; calibrate2 at batch 1/4/8, contexts 1,000/8,000/32,000, prefill 2,000/8,000/16,000 (`q-o64`). Since P1's server stopped, 9.8 GB of the unit's 62.8 GB stay in use with no process holding them (process memory about 1 GB; no zombie; k3s inactive, one old pause container); if SGLang builds a smaller pool than P1's 60,000, that is the reason to check **FP8 point done 19:35** (`dev7a-o64-fp8-20261012T1908`): SGLang built P1's full pool, **60,000 tokens**, so the held 9.8 GB did not cost pool; preflight and 10-minute idle passed; calibrate2 rc 0. After-check lost to the same preflight bug. bf16 point running **bf16 point done 20:02** (`dev7a-o64-bf16-20261012T1935`, preflight before and after passed). **Results** (board, P1's flags; JSONs in `reports/2026-10-06-options/device/`): pools **FP8 60,000** (P1's `--max-total-tokens` cap) and **bf16 55,417** (what fits), so at P1's flags FP8 buys only ~8% more pool on this unit; idle with the server loaded 12.9/12.8 W; prefill 0.030 J/token at 2K and 0.043-0.044 at 16K (~1,300 and ~1,060 tok/s), both dtypes; decode at batch 1 19.8/19.2 tok/s, 1.99/2.01 J/token (FP8/bf16), batch 8 at 1K context 0.57/0.51 J/token; batch 4 at 8K context gains nothing over batch 1 (~19-20 tok/s in total; CUDA graphs only up to batch 1 in P1's flags). One bf16 16K prefill repeat ran 41% slower (23.4 s against 16.6 s). For CAP-J2's drone pair: a capacity test on this unit needs the FP8 pool uncapped |
| CAP-J1 | FP8 vs bf16 KV with several agents, with the N = 1 anchor (plan §5.2) | Orin-32-1/2/3 | DEV-4, DEV-5, P1F-2 | **done** 13 Oct | both replicates (four arms each) and the anchor run; analysed with plan §6 by code committed first; outcome against the rules | About 2.5 h per point, 10 h per replicate. Orin-32-3: anchor, then spare **12 Oct 19:05:** replicates on Orin-32-1 (o32a: bf16n8, fp8n8, bf16n4, fp8n4) and Orin-32-2 (o32b: fp8n4, bf16n4, fp8n8, bf16n8); the anchor on Orin-32-3 after DEV-6 **Anchor passes (21:50,** `capj1-o32c-anchor-20261012T1920`, Orin-32-3, N = 1 bf16, 2-hour window, preflights passed, 212 ms samples, no gaps): 10 sessions matched with P1's; decode 8.50 against P1's 8.40 tok/s (**+1.2%**, rule ±10%), LLM-call energy per session 20.05 against 19.53 kJ (**+2.6%**, rule ±15%); 5.66 J/token, idle 13.7 W. **First arms done** (complete, no gaps): o32a bf16n8 3.23 J/token (14 sessions in 2 h, 21.5 kJ prorated); o32b fp8n4 1.79 J/token (25 sessions, 11.4 kJ). The comparison waits for each replicate's four arms. **13 Oct 00:04:** o32b bf16n4 done (3.26 J/token, 11 sessions in 2 h, 25.8 kJ prorated): the first pair on the board, Orin-32-2 at N = 4, **FP8 −45%** per generated token (3.26 → 1.79 J; single replicate, N = 8 pending). **Done 05:17: both replicates, all 8 arms** rc 0, preflights before and after passed, 2-hour windows complete, 213 ms samples, no gaps, SHA-256 (`analysis/device_runs.py --rules` → `reports/2026-10-06-options/device/device_rules.json`). J per generated token, board (o32a / o32b): bf16 N = 4 3.30 / 3.26, N = 8 3.23 / 3.20; FP8 N = 4 1.81 / 1.79, N = 8 1.79 / 1.77. FP8 against bf16: −45.0 / −45.1% at N = 4, −44.4 / −44.5% at N = 8, **best against best −44.4% / −44.5%** (bf16 N = 8 → FP8 N = 8). Per completed session (prorated): bf16 N = 8 21.5 / 21.3 kJ, FP8 N = 4 11.5 / 11.4 kJ; sessions completed in 2 h: bf16 11-14, FP8 25-26. **Rules:** (1) anchor passes, so the numbers are P1-comparable; (2) replicate spread 0.04 pp (limit 10 pp); (3) ≥ 25% in both replicates: **holds on the board**; (4) platform link: FP8/bf16 best 0.556 / 0.555 on the board against 0.543 on the WS (P1F-3), board/WS 1.02. bf16 N = 8 keeps no state (0 prompt tokens from the cache), as on the WS. Replay by token counts: says nothing about task success | 0.1-0.2% of `/metrics` scrapes on the units time out (skipped by `analysis/device_runs.py`) |
| RET-J1 | Is kept state worth anything on the board? One agent, state dropped at every wait (`--no-reuse`), against the anchor on the same unit (plan §5.4) | Orin-32-3 | CAP-J1's anchor | **done** 13 Oct | the run done and compared with the anchor by plan §6; verdict by the rule (< 5% holds) | About 2.5 h, right after the anchor **12 Oct 19:05:** queued on Orin-32-3 after the anchor **Started 21:50** (`retj1-o32c-noreuse-20261012T2150`; replay from 21:58) **Done 00:14** (preflights before and after passed, 2-hour window complete, 213 ms samples, no gaps, SHA-256). **Kept state is worth +3.2% J per generated token on the board** (anchor 5.66 → 5.84 J with state dropped at every wait; 8 sessions completed against 9): under 5%, so **"retention gains little on P1's workloads" holds on the board** (plan §5.4). Dropping state recomputes 2.9x the prompt tokens (273,175 against 93,178; 0 from the cache), which costs little because prefill is cheap. Single run per arm |
| A-J1p | A-J1 pilot: 10 loop prompts, greedy and sampled (plan §5.3) | Thor-1 | DEV-4, DEV-5 | **done** 12 Oct | 20 calls with loop flags and energy; result labelled indicative | Then the controls, until F **12 Oct 19:05:** started on Thor-1 (`aj1p-thor-20261012T1905`) **Done 21:14** (preflights before and after passed, idle 28.5/29.6 W; 34,460 board samples at 204 ms, no gaps; `analysis/a_j1.py`, committed before the data was read → `reports/2026-10-06-options/a_j1.json`). **Indicative only.** On P1's bf16 26B, P1's image and flags, Thor-1: **greedy (P1's protocol) loops on 5 of 10** of P1's Thor Reflexion loop prompts (Wilson 24-76%); the other 5 finish on their own (3,739-22,487 tokens) with valid programs. **Sampling (Gemma's defaults, seed 0) loops on 0 of 10** (0-28%); all 10 finish, 9 with valid programs. Rule 1 (reproduction at ≥ 80%) is not met even at the upper bound: "not reproduced: the 4-bit result stands alone" (the 4-bit stand-in looped on 77%). So P1's capped calls are not reproducible call for call at temperature 0 on P1's own setup; the full set repeats these 10 to see whether our own greedy runs repeat. **Diagnostic (added after the pilot, not a rule; `analysis/a_j1_prefix.py` → `a_j1_prefix.json`):** greedy is not repeatable on P1's setup. Our greedy outputs leave P1's recorded text after a median 188 characters, at near-tie wordings ("Task: Take off" against "Take off."); one of 10 (F1) matches P1's for all 33,000 characters through its loop; our own two greedy runs of A16's prompt (DEV-4, pilot) part after 188 characters. So "greedy loops on this prompt" is a probability, which the pilot puts at 5 of 10; the cause of the non-determinism is not checked. Board energy: greedy arm 305.8 kJ in 4,260 s (loops stopped by the detector), sampled 204.5 kJ in 2,820 s; per call median 34.4 and 18.0 kJ; decode 27.3 and 27.5 tok/s (P1's record 26.6). Caveat: a sampler left from the aborted first DEV-4 attempt (`dev4-thor-loop-20261012T1849`, one more root tegrastats) ran on Thor-1 from 18:47 until stopped at 22:30 (its file kept); a sensor reader, so its power is small, but the pilot ran beside it |
| A-J1f | A-J1, the rest before F: 30 loop prompts and 20 controls (`--select rfx`), greedy and sampled (seed 0) (plan §5.3; §3: "A-J1 continues until F") | Thor-1 | A-J1p | doing | 100 calls with loop flags and energy; rules by `analysis/a_j1.py` on this run alone | §5.3 put the rest after the meeting; started early on the idle Thor-1, same server. The pilot's 10 loop prompts run again inside it: a repeat of our own greedy and sampled calls **12 Oct 22:29:** started (`aj1-thor-20261012T2229`, `q-thor`; ~8-9 h) |
| COR-1 | CMP-2 corrections (checklist below) and the device box | local | P1F-3; CAP-J1 for the box | doing | every checklist item fixed, or kept with a stated reason | 12 Oct: the corrections that need no new data are applied to CMP-2 (header, 12 Oct block, K1-K8, §3-§12). Kept, with reasons: A2's "71%" has no CMP occurrence; D-E2 has no per-token numbers (its 2.4x stays per session); RET's FP8 per-token gap is not computed; `ret_e1.png` still plots per session (note under it). Left: the numbers P1F-3 redoes, and the device box **12 Oct 22:35:** P1F-3's numbers applied (an update block at the top, §7, §8's new P1F-3 table, §9, §11); the RET-E1 "FP8 within 6.4%" now says it was on the pre-re-run sessions; §9's lean wording per Sandesh (design space first, a controller only if a gap remains, P1's FP8 pair tested first by CAP-J2's drone pair); HANDOFF §7 Q3 and Q4 answered. Left: the device box (after C2) **13 Oct 05:50:** the device box "First results on P1's devices" is in CMP-2 (CAP-J1, anchor, RET-J1, A-J1 pilot, DEV-6, DEV-7a), with pointers in the top summary, §7, §8, §9 and §13, and a `[P1-dev]` source tag. Left: A-J1's full set into the box |
| COR-2 | Repo docs: HANDOFF, AGENTS, the evidence-doc copy, `review/systems/README.md`, dated reports, `planning/PLAN.md` | local | COR-1 | **done** 12 Oct | the stale items (checklist B) are gone; numbers match CMP-2 | AGENTS (machines, device rules), HANDOFF, master plan, plan pointers, the evidence doc's repo copy (now ahead of the Claude Doc, rev 171), the review index and update notes in the three dated reports. Redo after P1F-3 and the device runs |
| COR-3a | Deck v2.4: corrections, one device slide, one plan slide | artifact | COR-1, CAP-J1 | todo | published; renderer check clean | Scope to confirm with Sandesh (plan §11 item 2) **Sandesh, 12 Oct 21:10:** the deck is updated after all the runs are complete |
| TRF-1 | Where is P1's final traffic agent? | Sandesh, with Priyanshu or Mayank | — | todo | host, folder and dependencies known | Thor-1 has an Aug–Sep version (`/media/ssd/Deepstream-Yolo-upstream/`); P1's code names the orchestration host .59. Not in mayankarya's home or on Thor-2's data disks |
| MTG-1 | Meeting materials (plan §8) | local | COR-1, CAP-J1, A-J1p | todo | CMP-2 box; deck v2.4; one-page device plan per option | Tue evening **12 Oct 19:50:** the device plan per option drafted as CMP-2 §13 (§10 Q6 points to it); its result column fills after C2 |

## At and after the meeting

| ID | Task | Depends | Status | Notes |
| --- | --- | --- | --- | --- |
| MTG-2 | The meeting: D12, agents per box, thresholds (D4), the split with P1 | MTG-1 | todo | Wed 14 Oct, 09:00-10:00 |
| MTG-3 | Record D12 as D23; turn the chosen branch (plan §7) into tasks with rules; master plan M8; HANDOFF | MTG-2 | todo | Same day |
| P1F-4 | Rerun `p1_opportunity`, `p1_caps` and `p1_repo_figures` on the final data | P1F-2 | todo | 25 configurations instead of 12 |
| P1F-5 | Why do granite and E4B evict KV on the Orins at one agent (52–68% of drone runs)? | P1F-2 | todo | Can now be checked on the units |
| TRF-2 | Copy P1's traffic agent, its sandbox image (`camera-agent-sandbox:1`, also on Thor-1) and data to the WS and the units | TRF-1 | todo | Look-and-copy only on Thor-2. Loading an image needs docker-root space, which the Orin 32s lack: Thor-1 or Orin-64-1 first |
| TRF-3 | Validate the agent at N = 1 against P1's recorded runs (pass rate, tokens) | TRF-2 | todo | |
| COR-3b | Evidence doc and teaching guide | MTG-2 | doing | Teaching guide **done** 12 Oct, at Sandesh's request: rewritten from first principles in a new first tab (the 11 Oct guide kept as an archive tab); refresh after the runs and D12. Evidence doc after MTG-2 |
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

- **2026-10-13, 05:37:** DEV-6 done: the three Orin 32s are interchangeable (idle within 0.9%, decode J/token within
  2.2%). Only A-J1 (Thor-1) still runs.

- **2026-10-13, 05:25:** CAP-J1 done, **C2 passes**: FP8 −44.4% / −44.5% J per generated token best against best on
  Orin-32-1 / Orin-32-2 (spread 0.04 pp; "holds on the board"; WS P1F-3 −45.7%). DEV-6 running on Orin-32-1/2;
  A-J1 at 71 of 100 calls.

- **2026-10-13, 00:20:** RET-J1 done: kept state is worth +3.2% J per token on Orin-32-3 (< 5%: "retention gains little"
  holds on the board).

- **2026-10-13, 00:10:** CAP-J1's first pair on the board: Orin-32-2 at N = 4, FP8 −45% J per token (3.26 → 1.79 J;
  single replicate). A-J1 full set: 13 of 100 calls done. Left: RET-J1 (ends ~00:20), 5 CAP-J1 arms (end ~05:00),
  A-J1 (ends ~07:30-08:00), DEV-6 on Orin-32-1/2 (~05:50).

- **2026-10-12, 22:30:** P1F-3 done: FP8 −53%/−46% J per token at N = 4/8 (best against best −45.7%); the simulator
  holds on bf16 (within 7%) and fails on FP8 (over-predicts by 13-25%). A-J1 pilot done (indicative): greedy loops on
  5 of 10, sampling on 0 of 10; reproduction (≥ 80%) not met. CAP-J1's anchor passes (+1.2% decode, +2.6% energy).
  A-J1's full set started on Thor-1. A leftover DEV-4 sampler on Thor-1 stopped (file kept). `device_runs` skips
  scrape timeouts and unfinished points.

- **2026-10-12, 21:30:** Sandesh: the meeting is **Wed 14 Oct, 09:00-10:00**. F moves to Tue 23:00; MTG-1 final by Wed
  08:00 (plan §3 updated).
- **2026-10-12, 21:20:** DEV-1 done: Sandesh stopped the two `yash` MCP servers (port 8001 free on Orin-64-1 and Orin-32-3).
- **2026-10-12, 21:10:** Sandesh: deck after all runs; the lean's wording as recommended (design-space study first, a
  controller only if a gap remains, P1's FP8 pair as the main risk); meeting time (Wed 14 Oct 09:00-10:00, confirmed 21:30). Sandesh stops the two `yash` MCP servers with sudo.
- **2026-10-12, 20:05:** DEV-7a done: the 26B's pools at P1's flags are 60,000 (FP8, capped by P1's flag) and 55,417 (bf16);
  decode 2.0 J/token at batch 1 for both.
- **2026-10-12, 19:40:** DEV-6 on Orin-32-3 and DEV-7a's FP8 point done (pool 60,000); the after-checks of both were lost to a
  preflight bug (fixed, `d674269`). DEV-3's P1 sampler file copied in full (SHA-256 matched).
- **2026-10-12, 19:10:** C1 passes: (a) P1F-2; (b) one clean granite session replayed on Orin-32-1; (c) one P1 loop
  prompt stopped by the loop detector on Thor-1. DEV-3 (+0.01% against P1's sampler), DEV-4, DEV-5 done. Night queues
  started: CAP-J1 replicates (Orin-32-1, Orin-32-2), DEV-6 then anchor then RET-J1 (Orin-32-3), A-J1 pilot (Thor-1).

- **2026-10-12, 18:45:** DEV-2 done (versions in AGENTS §3); DEV-3, DEV-4 and DEV-5 code written and committed; P1's 26B
  up on Thor-1 with P1's flags; DEV-4 runs started.

- **2026-10-12, 18:30:** P1F-2 done (17 cells equal P1's outputs; 3,605 runs; clean replay sets built on the WS).
  DEV-1: snapshots on the WS, P1's stack stopped on the five units except two `yash`-owned MCP servers; idle readings
  running. Sandesh: P1's members know; ollama stays up.

- **2026-10-12, evening:** docs committed and pushed (`42f9437`); SYNC-1 done (WS clone and `~/jsw-dev` at `42f9437`);
  the teaching guide rewritten from first principles (new first tab, 19 chapters, two drawings; the old guide kept as an
  archive tab), at Sandesh's request.

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

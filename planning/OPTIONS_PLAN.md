# P5 work plan: corrected evidence, the Jetsons, the direction decision, and what follows

Status: **v2.0 (2026-10-12), approved by Sandesh on 12 Oct** (D19–D22; RET-J1 added the same day). This version
replaces v1.2's structure.
- **Why a new version:** four things changed after v1.2 (11 Oct):
  - The WS is back (12 Oct).
  - P5 has five Jetsons (12 Oct): Thor-1, Orin-64-1 and Orin-32-1/2/3.
  - The professor meeting moved to **Wed 14 Oct**.
  - A consistency sweep of the docs (12 Oct) found summaries that claim more than their evidence, and stale facts.
- **What it covers:**
  - everything from today to the meeting;
  - the device platform;
  - one branch per option after the direction decision (D12).
- **The record of G1/G2 (5–11 Oct)** is in Appendix R, unchanged: the criteria K1–K8 (D16), the experiment specs and
  rules fixed before those runs (D15), their outcomes, the shared base S1–S6 and decisions D13–D18. The code and CMP-2
  cite them.
- **Tracker:** [`TRACKER.md`](TRACKER.md), rewritten 12 Oct. It holds every task's status and "done when", and the
  correction checklist.
- **Master plan:** [`JOULESERVE_WS_PLAN.md`](JOULESERVE_WS_PLAN.md) v2.0. Its M3–M5 are replaced, M6 (the device
  platform) is active, and M7–M8 are new.
- **Rules for the machines:** `AGENTS.md` §3–§4 (device rules added 12 Oct).

Source tags as before: **[P1-meas]** measured on P1's Jetsons; **[WS-meas]** measured on the WS; **[dev-meas]**
measured by P5 on the Jetsons; **[sim]**; **[proj]**; **[lit]**.

---

## 0. The goal of this phase

P5 asks whether the serving layer on an edge box can cut the energy an LLM agent spends per successful task.

- **Settled:** the retained-state version of the question is answered "little to gain" on P1's workloads (RET).
- **Open:** CMP-2 compares five directions (A, B, C, D, CAP). Our lean is CAP with A's safety net, as several agents
  sharing one edge box.
- **The decision:** the professor chooses on Wed 14 Oct (D12).

This phase has three goals, in this order:
1. **Correct evidence on Wednesday.** Everything the professor sees is right:
   - the overclaims are fixed;
   - the capacity numbers are redone on P1's clean (re-run) sessions;
   - the lean's key number is measured on P1's own board.
2. **A device platform whose numbers line up with P1's.**
   - The five Jetsons run P1's engine, models and settings.
   - Board energy is read the way P1 reads it.
   - A check confirms that a replayed session costs what P1 measured on the same board.
3. **After the decision, the chosen direction runs on the devices.** Each experiment's rule is written before it runs.

What "fail-proof" means in this plan:
- Every task has a "done when" check.
- Every experiment has its decision rule and analysis method fixed before its data exists.
- Every device result is anchored three ways, where they apply:
  - to P1's measured runs on the same board;
  - to the WS, on the same sessions;
  - to the simulator.
- No difference is claimed unless a repeat has measured the noise.
- Three checkpoints with fixed fallbacks decide what reaches the meeting (§3).
- Nothing on the devices is deleted. Every run is copied to the WS (ECC memory) within the hour.

## 1. Where we start (12 Oct)

### 1.1 Evidence and what is wrong with it

CMP-2 ([`../reports/2026-10-06-options/README.md`](../reports/2026-10-06-options/README.md)) holds the comparison,
our lean (§9), the questions for the professor (§10) and P1's submission (§12). Errors found on 11–12 Oct (fixed by
COR-1; the line-by-line checklist is in TRACKER):

1. **P1's own data partly answers the FP8 quality question, and the answer works against the lean.**
   - P1 ran its gemma-26B Reflexion drone agent on Thor with a BF16 KV cache, and on Orin 64 with FP8 (`fp8_e5m2`,
     confirmed in the server still running on Orin-64-1 on 12 Oct).
   - On the 39 task-instances both ran: 96/117 passes (82.1%) with BF16, 94/115 (81.7%) with FP8 [P1-meas].
   - Device and pool differ too (80K vs 60K tokens), and pass rate is a coarse measure. Still, there is no sign of a
     loss. CAP-E1's own rule then reads "capacity is a free configuration choice".
2. **CAP's headline −62% is the most favourable reading of the measurement.**
   - The 45-minute runs were GPU-saturated, so energy per completed session mostly counts how many sessions finished.
     Energy spent on sessions still running at the window's end is charged to the finished ones.
   - Per generated token, the same pair gives −53% (3.95 → 1.87 J). Best against best (bf16 at 4 agents, 3.43 J/token)
     gives −45% [WS-meas].
3. **The loader bug is not the one the docs describe.**
   - `analysis/p1_repo.py:191` skips every re-run folder. A refresh would read only P1's originals, faulted ones
     included, and none of its re-runs.
   - It also misses P1's rule that drops the 7 vision tasks for text-only models.
4. **Summaries claim more than their own sections:**
   - A-E1: a 4-bit stand-in, one seed, pass rate unmeasured.
   - RET: held narrowly at 4 agents, and the ranking test was degenerate.
   - D-E2: the "best policy" is noise, and a −4.1% row is missing.
   - B: 8 of 21 sampled missions were lost to a since-fixed bug.
   - "Overflows roughly doubled": only Orin 32 granite doubled.
5. **Stale facts:** the meeting date, the WS "down", the devices "with P1", and answered questions still shown as open.

What needs a board, by CMP-2 §9's own objections:
- every capacity number comes from the WS or the simulator;
- A's loop result is a 4-bit llama.cpp stand-in;
- FP8 KV for Gemma-4 failed on our A5000s;
- the vision burst and unified-memory contention can only be measured on a device.

### 1.2 Machines (device pass of 12 Oct, look-only)

| Unit | Access | Board, software | Free disk | Models on disk (revision) | Found running at 12:30 |
| --- | --- | --- | --- | --- | --- |
| **Thor-1** | `ssh Thor-1` = `dream-thor-1`, `yash@10.24.24.79` | AGX Thor dev kit, L4T R38.4, 14 cores, 126 GB; image `lmsysorg/sglang:latest-cu130-runtime` (build `fdebc938`); docker root on `/` | `/` 72 GB (92% used); a 1.8 TB USB disk, not mounted | in yash's HF cache: gemma-4-26B-A4B-it bf16 (`4d7ae498`), granite-4.2-8b (`f8de16cd`), Devstral-Small-2, Qwen3.6-35B-A3B-FP8, Qwen3.8-27B-FP8; no E4B | P1's granite server (`p1-final-granite`: bf16 KV, 80,000 tokens, mem 0.65, one request), P1's CLGSCE MCP server and AirSim (`thor_headless`); P1's granite pipeline wrote files until 01:19 on 12 Oct |
| **Orin-64-1** | orin45, `mayankarya@10.24.24.45` | AGX Orin 64 GB, L4T R36.4.4, 12 cores, 63 GB; `jouleserve/sglang:0.5.16-orin-cu126-sm87` (`05119cc6`); docker root on the SSD | `/` 8.7 GB, SSD 24 GB, HDD (ext4) 1.4 TB | gemma-4-26B-A4B-it bf16 (`4d7ae498`, HDD), Qwen3.8-27B-FP8 (SSD); no granite, no E4B | P1's 26B server (FP8 KV `fp8_e5m2`, 60,000 tokens, mem 0.95, SWA ratio 0.2), AirSim container, MCP server; ollama and k3s (other teams); P1 wrote files until 01:47 on 12 Oct |
| **Orin-32-1** | orin56, `.56` | AGX Orin 32 GB, R36.4.4, 31 GB; image `05119cc6` | `/` 2.8 GB, SSD (docker root) 1.9 GB (100%), USB `/media/hdd` 1.7 TB | gemma-4-E4B-it (`ee0ef602`) and E4B base (SSD); granite (`f8de16cd`, USB) | P1's granite server (FP8 KV, 60,000 tokens, mem 0.85, CUDA graphs off), MCP server; mayankarya's tmux sessions |
| **Orin-32-2** | orin57, `.57` | same; image `05119cc6` | `/` 2.2 GB, **SSD 264 MB (100%)**, USB `/media/hdd2` 1.5 TB | granite (`f8de16cd`, inside P1's folder on the SSD) | same server; AirSim container, MCP server |
| **Orin-32-3** | orin58, `.58` | same; **image `d4967327` (29.9 GB), a different build of the same tag** | `/` 6.1 GB, SSD 1.9 GB (100%), USB `/media/hdd` 1.6 TB | granite (`f8de16cd`), Ministral-3-8B, MiniCPM5-2B (SSD) | same server, plus P1's `sglang-orin` container (up 2 weeks); AirSim, MCP |
| Thor-2 | `mayankarya@10.24.24.80` (`dream-thor-2`) | — | — | — | someone's `sweep-llm` server (Qwen3.6, up 2 days). **Look-and-copy only** (it holds P1's traffic agent) |
| WS | `ssh WS` | 2× A5000, no sudo | `/` 131 GB | P1's E4B and granite (SGLang), the 26B GGUF (llama.cpp) | idle. P1's clone `~/work/p1/edge-agent-bench` at `0cc2311a` (pulled 12 Oct). Stale: `~/jouleserve-ws` at `001dbd2`, `~/jsw-dev` at `09a4d5c` |

Common to the five units on 12 Oct:
- **Power and clocks:** nvpmodel MAXN, clocks locked at maximum as during P1's runs (Orin GPU 1,300.5 MHz, EMC
  3,199 MHz; Thor checked by Sandesh).
- **Network and time:** NTP-synchronised, about 1 ms from the WS.
- **Telemetry:** board power is readable without root, through tegrastats and the INA3221 sensors. Password-free sudo
  rules exist for root tegrastats (Thor, Orin 32s), nvpmodel and jetson_clocks (Orin 32s), and cache clearing.
- **Docker:** our accounts are in the docker group. The units are docker-swarm workers that nobody targets.
- **P1's leftovers:** no P1 harness or sweep is running, but P1's servers, MCP servers and AirSim are still up.
- **USB drives:** fstab entries fixed by Sandesh on 12 Oct (`ntfs3` → `ntfs-3g`; backups in
  `/etc/fstab.bak-2026-10-12`).

### 1.3 Permissions (12 Oct)

- **P1's mentor:**
  - P5 may stop anything of P1's on the five units, but delete nothing.
  - P5 may use P1's code and environments.
- **Sandesh:**
  - The five units are P5's; no time-sharing schedule with other teams exists yet.
  - Nobody targets them through the swarm.
  - ollama on Orin-64-1 may be stopped.
  - Thor-1 is open to P5 (the 5 Oct ban protected P1's live sweep, which is over).
  - Thor-2: look-and-copy only; never run experiments there.
- **Sudo:** anything needing it goes through Sandesh.

## 2. Work streams

| Stream | Purpose | Before the meeting | After |
| --- | --- | --- | --- |
| **SYNC** | WS clones current | SYNC-1 | — |
| **COR** | Corrections: CMP-2, repo docs, artifacts | COR-1, COR-2, COR-3a (deck) | COR-3b (evidence doc, teaching guide), COR-4 (notes for P1) |
| **P1F** | P1's final data | P1F-2 (loader), P1F-3 (WS reruns) | P1F-4, P1F-5 |
| **DEV** | The device platform (master plan M6) | DEV-1 to DEV-6; DEV-7 on Orin-64-1 | DEV-7 for the other models |
| **J** | Experiments on the devices | CAP-J1 with its anchor; RET-J1; A-J1 pilot | the chosen branch (§7) |
| **TRF** | P1's final traffic agent | TRF-1 (ask where it is) | TRF-2 (copy), TRF-3 (validate) |
| **MTG** | The meeting | MTG-1 (materials) | MTG-2 (the meeting), MTG-3 (record, replan) |

Task rows (machine, dependencies, status, "done when") are in TRACKER. The specs below say what each task does and how
its result is judged.

## 3. Schedule to the meeting, with checkpoints

Times are IST.
- Claude does the work unless a row says otherwise.
- Long jobs run in WS tmux queues, so a laptop drop stops nothing.
- The device runs are driven from the WS.

| When | WS | Thor-1 | Orin-64-1 | Orin-32-1 | Orin-32-2 | Orin-32-3 |
| --- | --- | --- | --- | --- | --- | --- |
| Mon 12 Oct, afternoon | **Gate: Sandesh approves this plan.** Then commit and push, SYNC-1, P1F-2 | DEV-1, DEV-2 | DEV-1, DEV-2 | DEV-1, DEV-2 | DEV-1, DEV-2 (container test first: 264 MB free) | DEV-1, DEV-2 (image check) |
| Mon evening | P1F-2 → replay sets; DEV-3/DEV-4 code | DEV-3; DEV-4 (one loop prompt) | DEV-3 | DEV-3; DEV-4 (one replayed session) | DEV-3 | DEV-3 |
| **C1: Mon 23:00** | checkpoint (below) | | | | | |
| Mon night (from about 00:00) | P1F-3: GPU0 bf16 arms, GPU1 FP8 arms | A-J1 pilot | — | CAP-J1 replicate 1: four arms (about 10 h) | CAP-J1 replicate 2: four arms in the reverse order (about 10 h) | DEV-6; CAP-J1 anchor (N = 1); RET-J1; then spare |
| Tue 13 Oct, morning | P1F-3 analysis | A-J1 controls (beyond the pilot) | DEV-7 (26B calibration) | replicate 1 ends about 10:00 | replicate 2 ends about 10:00 | spare: rerun any point that failed |
| **C2: Tue 12:00** | checkpoint (below) | | | | | |
| Tue afternoon | COR-1, COR-2 | A-J1 continues until F | DEV-7 done | DEV-6 | DEV-6 | free |
| Tue evening | CAP-J1 and anchor analysis (§6 rules); MTG-1: CMP-2 box, deck v2.4 | | | | | |
| **F: Wed 14 Oct 09:00** | results freeze | | | | | |
| Wed | MTG-2 (the meeting), MTG-3 | | | | | |

**C1, Mon 23:00.** Three checks:
- (a) P1F-2's clean run counts equal P1's summaries, and the Orin 32 granite replay set is built.
- (b) One replayed session (any replay set, the 6 Oct one is fine) on Orin-32-1 has completed with exact lengths and
  telemetry (DEV-4).
- (c) One loop prompt on Thor-1 has streamed through the loop detector (DEV-4).

| Outcome | What follows |
| --- | --- |
| All three pass | The night runs start: CAP-J1, the A-J1 pilot, P1F-3 |
| (a) passes, (b) or (c) fails | P1F-3 runs overnight. The device fix continues on Tue morning. CAP-J1 starts as soon as (b) passes, in its late-start form (§5.2) |
| (a) fails | Fix it first, since everything downstream reads it. P1F-3 slips to Tue |

**C2, Tue 12:00.** Both CAP-J1 replicates have finished their N = 8 arms. If only one has, its numbers go to the
meeting labelled "single replicate". If neither has, the meeting gets the WS reruns and the line "device platform ready,
first device runs under way", and no device number is shown.

**F, Wed 09:00: results freeze.**
- A device point counts only if:
  - its run finished;
  - it passed preflight;
  - its data is on the WS;
  - it was analysed with the §6 rules.
- Anything else is labelled preliminary or left out.
- The meeting's time on Wednesday is not known; F assumes a daytime meeting.

## 4. The device platform (DEV; master plan M6)

### 4.1 Setup

**DEV-1. Snapshot and stop P1's stack (all five units).**
- **Snapshot** into `<p5>/state/2026-10-12/` on each unit, with a copy on the WS:
  - `docker ps -a`;
  - `docker inspect` of every running container (P1's exact server flags);
  - `ps` of P1's processes;
  - `df`, `free`, one minute of tegrastats.
- **Stop:**
  - P1's SGLang containers and AirSim containers (`docker stop`), including `sglang-orin` on Orin-32-3;
  - P1's MCP servers and Thor-1's `thor_headless`, by PID, selected with `ps | grep '[p]attern'` (never `pkill -f`
    over ssh);
  - ollama on Orin-64-1 (through Sandesh if it is a system service).
- **Leave alone:**
  - P1 members' tmux sessions;
  - k3s on Orin-64-1 (another team's; DEV-6's idle baseline shows whether it matters);
  - Thor-1's legacy P5 root helper `/usr/local/sbin/jouleserve-thor`.
- **Delete nothing:** no `docker rm`, `rmi` or `prune`, and no file deletions outside P5's folders. The snapshot
  allows P1's stack to be restarted exactly if P1 asks.
- **Done when**, on each unit:
  - no GPU work (tegrastats GR3D at 0%);
  - nothing listening on ports 30000, 8001 or 41451;
  - a 10-minute idle power reading is saved.

**DEV-2. P5 folders, container convention, image versions.**
- **Folders (`<p5>`):**
  - `/media/hdd/p5` on Orin-64-1, Orin-32-1 and Orin-32-3;
  - `/media/hdd2/p5` on Orin-32-2;
  - `~/p5` on Thor-1.

  Each holds `runs/`, `state/`, `logs/`, `tmp/` and `bin/`.
- **Container convention.** The Orin 32 docker roots are full (0.3–1.9 GB free), so:
  - existing images only: no `docker pull`, `build` or `load` on the Orins;
  - `docker run --rm --read-only --tmpfs /tmp --log-driver none --network host`;
  - the model folder mounted read-only from where P1 keeps it, with `HF_HUB_OFFLINE=1`;
  - every write goes to `<p5>` through a bind mount: `HOME`, and the Triton, FlashInfer, torch and HF caches, point
    to `<p5>/cache` (a read-only root otherwise breaks kernel compilation; the cache also saves the slow first JIT on
    the next run);
  - container names `p5-<task>`.
- **Versions:** for each image digest, record SGLang, torch, CUDA and flashinfer. Compare Orin-32-3's `d4967327` with
  Orin-32-1/2's `05119cc6`. Record Thor's `latest-cu130-runtime` build.
- **Done when**, on all five units:
  - a read-only container starts, prints the versions and exits (the server itself starts in DEV-4);
  - the docker root's free space is unchanged (±10 MB);
  - the versions are recorded in AGENTS.md §3.

**DEV-3. Jetson telemetry: `jsw/telemetry/jetson.py`, our own code, written to P1's schema.**
- **How it runs:**
  - on the unit's own Python (stdlib only, nothing installed), started and stopped by the runner over ssh;
  - `tegrastats --interval 200`, as root through the existing password-free rule where there is one;
  - each line stamped with `t_mono` and `t_wall` on receipt;
  - plus sysfs GPU clocks (min, max, current) and thermal zones;
  - output: JSONL in the run directory.
- **P1's field names:**
  - Thor: `power_VIN_mW` is the board total.
  - Orin: `platform_total_power_mW` = VDD_GPU_SOC + VDD_CPU_CV + VIN_SYS_5V0. Checked against P1's own samples:
    5,570 + 3,581 + 5,241 = 14,392 mW.
  - Every rail is kept verbatim, with `power_total_source`.
- **Energy:** the trapezoid rule over the samples. A gap over 1 s is flagged and marks the run.
- **Done when:**
  - 5 minutes side by side with P1's own sampler (a scratch copy of
    `data/p1_aeroeval_src/final_sweep/_harness/samplers.py`) give board energies within 1%;
  - the median sample interval is 200 ms ± 10%;
  - the runner merges the samples with the WS-side call log by wall clock, with the NTP offset recorded at start and
    end.

**DEV-4. Our stack against SGLang 0.5.16.**
- **Launcher:** `env/launch_jetson.sh <unit> <model> <kv> <pool> [flags]` starts the server container with P1's flags
  (from DEV-1's `docker inspect`) and records the pool it actually got.
- **Where things run:** the gateway and the replayer stay on the WS and drive the unit over the LAN.
- **Checks:**
  - `/generate` with `input_ids`, `ignore_eos` and `max_new_tokens` gives exact lengths;
  - cache hits appear as expected by default, and none with `--no-reuse`;
  - the `/metrics` names our runner reads exist;
  - `/flush_cache` works with P1's verified-empty check;
  - a client disconnect aborts the request;
  - on Thor-1, `loop_replay` streams a 26B call through the `gemma4` reasoning parser into the loop detector.
- **Done when** one replayed granite session on Orin-32-1 and one loop prompt on Thor-1 have completed with exact
  lengths, metrics and telemetry, and both run directories are on the WS. Any replay set will do (the 6 Oct one), so
  DEV-4 does not wait for P1F-2.

**DEV-5. Preflight and teardown: `env/jetson_preflight.py`, before and after every device run.** A failed check stops
the run.
1. **Quiet:** no container or GPU process other than ours, and no foreign process above 5% CPU.
2. **Clocks:** GPU min = max = the locked frequency found on 12 Oct; nvpmodel MAXN.
3. **Disk:** at least 5 GB free in `<p5>`, and the docker root no lower than at DEV-2.
4. **Time:** NTP synchronised; the WS–unit offset recorded.
5. **Temperature:** GPU below 50 °C at the start; otherwise wait.
6. **Server:**
   - model and pool as specified;
   - KV cache flushed and verified empty, by P1's method: wait for idle, `/flush_cache`, used tokens 0 and still 0 a
     second later;
   - one discarded warm-up request after the model loads.
7. **Idle baseline:** 5 minutes of board power before the run and after it.

Teardown, after every run:
- stop our containers;
- check the unit is back to idle;
- `rsync` the run to the WS;
- write SHA-256 sums and record the copy in the manifest.

**DEV-6. Are the three Orin 32s interchangeable?**
- **Setup:** the same container and model on each unit (granite bf16, P1's flags).
- **Measures:** 10 minutes of idle power; decode J/token and tokens/s at batch 1 and 8 (`calibrate2` on the board).
  About 45 minutes per unit, in parallel.
- **Rule:**
  - The units are interchangeable if idle power and decode J/token agree within ±3%.
  - If not, comparisons stay within one unit.
- **When:** CAP-J1 runs each replicate within one unit, so DEV-6 does not gate it. DEV-6 runs on Orin-32-3 first, and
  on Orin-32-1/2 after their replicates. Its verdict decides whether the spare unit's reruns can replace a point, and
  whether cross-unit claims are allowed after the meeting.

**DEV-7. Device cost calibration.** It feeds the simulator and A's and D's numbers.
- **Measures:**
  - idle power;
  - prefill J/token (2K–16K prompts);
  - decode J/token at batch 1–8 and contexts of 4K–32K.
- **Before the meeting:** P1's 26B on Orin-64-1, with FP8 KV (as P1 ran it) and bf16 KV, pools recorded.
- **After:** the 26B and granite on Thor-1; granite (bf16 and FP8) and E4B on the Orin 32s.
- **Report only.**

### 4.2 Run records and data flow

- **On the unit,** each device run writes `<p5>/runs/<run>/`:
  - a manifest: unit, image digest, SGLang version, model and revision, server flags, pool, clocks, nvpmodel,
    temperatures, preflight results, and the git SHA of our code;
  - `device_samples.jsonl` and the server metrics.
- **On the WS,** `~/work/runs/<run>/` holds the call log (gateway) and the session log (replayer).
- **Copy:**
  - within an hour of the run's end, the unit side is copied into the WS run directory and checked by SHA-256;
  - runs are backed up to local `data/ws_runs/`.
- **Analysis** runs on the WS (`~/work/venv-analysis`), never on the laptop, whose RAM flipped bits on 5 Oct.
- **Run names:** `<task>-<unit>-<arm>-<YYYYMMDDTHHMM>`, for example `capj1-o32a-fp8n8-20261012T2330`.

## 5. Experiments before the meeting

### 5.1 P1F-2 and P1F-3: P1's clean sessions, on the WS

**P1F-2. The loader applies P1's selection rule.**
- **The rule comes from P1's `analysis/edgebench/selection.py`** (stdlib only). It is copied into our code with
  attribution, never imported in place: importing it writes `__pycache__` into P1's clone.
  - Per task, the latest re-run of generation `topup`, `topupB`, `topup2` or `cap8000` replaces the original.
  - An overflowed original is kept.
  - `_ceilretry` runs are excluded.
  - Text-only models (granite, Devstral) drop the 7 vision tasks.
  - `no_supersede.csv` is honoured.
- **Done when:**
  - our run counts and pass rates equal P1's committed ones for all 17 traffic configurations (P1's
    `traffic/grading/grades.csv` and `analysis/outputs/paper_tables/`);
  - a test pins that;
  - the replay sets are rebuilt from the clean Orin 32 granite (and E4B) sessions, with the session counts recorded.

**P1F-3. WS reruns: RET-E1 and CAP-E1 on the clean sessions, with §6's rules,** so the WS numbers line up with
CAP-J1's.
- **Points:**
  - granite at P1's re-run pool (bf16, 25,358 tokens) at N = 1, 4 and 8, on GPU0;
  - FP8 KV at the same bytes (50,716 tokens) at N = 4 and 8, on GPU1;
  - 60-minute windows after a 10-minute warm-up;
  - `traffic_sim` on the same sessions.
- **Rule:** the simulator anchor holds if live and simulated energy agree within ±15% per completed session (RET-E1's
  rule) and within ±10% per generated token, at every point.

### 5.2 CAP-J1: FP8 vs bf16 KV with several agents, on P1's Orin 32s

**Question.** On P1's board, with P1's engine and P1's granite, does an FP8 KV cache (twice the pool in the same
memory) cut energy per generated token when several traffic agents share the box, as it did on the WS?

**Workload.**
- P1's clean Orin 32 granite traffic sessions (P1F-2), replayed by token counts with the S3 replayer.
  - The text is synthetic, so this measures cost, not task success.
  - Recorded tool waits are kept at 1× speed.
- The replay is closed-loop with N agent slots.
- The same seed (11, as in RET-E1 and CAP-E1) is used in every arm, so every arm draws the same sessions in the same
  order.
- **Replayer settings:** `--warm 600 --horizon 7800 --grace 300`. Sessions start for 130 minutes; the measured window
  runs from minute 10 to minute 130; sessions still running 5 minutes after the horizon are cut.
- **The agent's window is held at the bf16 pool in both arms** (`--ctx 25358`), as CAP-E1 held it at 26,624. So FP8
  changes only how many agents fit at once, not how long one session may grow. The window effect (fewer overflow
  failures) belongs to CAP-J2 and to P1's MB5.

**Server.**
- **Image:** on each unit, the image P1 ran there: `jouleserve/sglang:0.5.16-orin-cu126-sm87`, digest `05119cc6` on
  Orin-32-1/2 (both replicates), `d4967327` on Orin-32-3 (anchor and spare). DEV-2 records the SGLang version in each.
- **Model:** granite-4.2-8b `f8de16cd`.
- **Flags:** P1's flags from DEV-1's snapshot (context 65,536; CUDA graphs off; mem 0.85). Only three things change
  per arm:
  - the KV dtype;
  - the pool, set exactly with `--max-total-tokens`: bf16 25,358 (P1's re-run pool); FP8 `fp8_e5m2` 50,716 (the same
    bytes);
  - the running-request limit, raised from P1's 1 to N.

  P1's traffic records do not keep server flags, so the snapshot is the source.

**Arms and units.**

| Run | Unit | Order of its points | Purpose |
| --- | --- | --- | --- |
| Replicate 1 | Orin-32-1 | bf16 N = 8, FP8 N = 8, bf16 N = 4, FP8 N = 4 | all four arms on one unit, so best against best never crosses units |
| Replicate 2 | Orin-32-2 | FP8 N = 4, bf16 N = 4, FP8 N = 8, bf16 N = 8 | the same four arms in the reverse order, on another unit: it measures the noise, including order and thermal drift |
| Anchor | Orin-32-3 | bf16 N = 1, one request at a time (P1's setting) | does a replayed session cost what P1 measured on this board? |
| Spare | Orin-32-3, after the anchor | reruns any point that failed preflight or broke | keeps both replicates complete |

Each point takes about 2.5 h: a 10-minute warm-up that is not counted, a 120-minute measured window, the 5-minute grace,
and preflight and teardown (DEV-5). A replicate takes about 10 h.

**Late start.** If the replicates cannot start by Tue 02:00, they cannot finish by C2. Then:
- each replicate runs its N = 8 pair first;
- the N = 4 points run if they can still finish before F;
- best against best becomes "at N = 8 only", labelled so.

**Measures.**
- Board energy over the window.
- Generated tokens, from the gateway log.
- Prompt tokens computed and cached.
- Sessions completed, cut by the window, and overflowed.
- Retractions (`/metrics`).
- The idle baseline and the pools actually allocated.

**Decision rules (fixed now; analysis per §6):**
1. **Anchor first.**
   - **Compare:** at N = 1, the replay against P1's measured runs of the same sessions on the Orin 32s. P1's records
     do not name the unit (the agent called `127.0.0.1`), so sessions are matched by task and run, not by unit.
   - **Pass:**
     - the median per-call decode rate is within ±10%;
     - the median LLM-call board energy per session is within ±15%, integrated over the call intervals on both sides.
   - **On pass:** CAP-J1's numbers count as P1-comparable.
   - **On fail:** they are reported as relative only (FP8 against bf16 on our replay), with the gap explained.
2. **Noise.**
   - Each replicate gives its own FP8/bf16 J/token ratios: at N = 4, at N = 8, and best against best.
   - If the two replicates' best-against-best ratios differ by more than 10 percentage points, no effect smaller than
     that difference is claimed.
3. **The capacity effect on the board.** For each replicate, compare FP8's best J/token (over N = 4, 8) with bf16's
   best:

   | FP8's best below bf16's best by | Verdict |
   | --- | --- |
   | ≥ 25% in both replicates | **holds on the board** |
   | 10–25% | **weaker on the board** |
   | < 10% | **absent**: the lean loses its central number, and we say so |
4. **Platform link:** the board's effect is reported next to the WS rerun's (P1F-3), as a ratio.

**What it cannot show.**
- The replay says nothing about task success.
- FP8's cost in success rate stays measured only by P1's natural pair (§1.1) until CAP-J2 (§7).

### 5.3 A-J1: do P1's drone loops survive sampling on P1's own setup? (Thor-1)

**Question.** On P1's exact setup, do the drone loops reproduce under greedy decoding, and does Gemma's default
sampling remove them? P1's exact setup means:
- the bf16 gemma-4-26B-A4B-it, revision `4d7ae498`;
- the SGLang image P1 used on Thor-1;
- P1's flags, read by `docker inspect` from the container P1 served those runs with. Thor-1 keeps three stopped
  gemma containers (`p1-final-gemma-it`, `p1-gemma4-26b-a4b-it`, `p1-gemma4-26b-a4b`); DEV-1 picks the one whose dates
  and flags match the replayed runs. P1's drone setting was context 65,536, pool 80,000, one request at a time, with
  the `gemma4` parsers;
- the Thor itself.

This replaces A-E1's 4-bit llama.cpp stand-in.

**Prompts.**
- A-E1's sets (`analysis/loop_prompts.py`): 30 of P1's Thor Reflexion calls that looped, and 20 long calls that
  finished.
- **Pilot before the meeting:** the first 10 loop prompts.
- **After the meeting:** the rest, and the controls.

**Arms.**
- **Greedy, as P1 ran it:** temperature 0, top_k 1, seed 42, thinking on, `max_tokens` 32,768. Each call stops when
  the online detector fires, since only "does it loop" is asked.
- **Gemma's defaults:** temperature 1.0, top_k 64, top_p 0.95. Each call runs to its end (32,768 at most).

**Measures.** For each call:
- the loop flag;
- the finish reason;
- output tokens and time;
- board energy;
- whether the final program parses and calls only P1's drone API.

**Time.**
- P1's 26B generates a median 26.6 tokens/s on Thor [P1-meas].
- The pilot takes about 3 h.
- The full set takes about 14 h with one sampling seed.

**Decision rules (fixed now):**
1. **Reproduction:** greedy loops on ≥ 80% of the prompts that looped on P1's Thor. P1 traced repeat divergence at
   temperature 0 to its inputs, so close to 100% is expected. If it falls short, the 4-bit result stands alone and we
   say so.
2. **Sampling removes the loops:**
   - the sampled arm loops on ≤ 10% of the prompts, with the Wilson 95% bounds reported;
   - and, in the full set, the controls do not get worse (finish rate, valid programs).
3. **The pilot is indicative only:** 0 of 10 still has a 95% upper bound of 28%.
4. **Overlap:** this overlaps P1's planned MB4 (capped-call replays). The split goes to the meeting (§8).

### 5.4 RET-J1: is kept state worth anything on the board? (Orin-32-3)

**Question.** On P1's Orin 32, at one agent, how much energy does keeping state between tool calls save, against
dropping it at every tool wait? One agent is the setting where SGLang's default can keep state; at 8 agents on the WS
it kept none (RET-E1: 0 of 102 calls hit the cache).

**Design.**
- The anchor's sessions, seed, pool and settings (bf16, N = 1, one request at a time), with `--no-reuse`: fresh token
  IDs for every prompt, so nothing can be reused.
- It is compared with CAP-J1's anchor run on the same unit (Orin-32-3), which keeps state (SGLang's default).
- About 2.5 h, right after the anchor.

**Measures.** J per generated token and LLM-call energy per session (§6); prompt tokens computed and cached in both
runs.

**Rule (fixed now).** The value of kept state is (no-reuse − default) / default, in J per generated token.

| Value of kept state | Verdict |
| --- | --- |
| < 5% | "retention gains little on P1's workloads" holds on the board |
| 5–10% | reported as measured |
| ≥ 10% | the claim is restated with the device number |

For reference, P1's own data puts the cache's saving on traffic at 1.1–4.2% of LLM time [P1-meas].

### 5.5 DEV-7 on Orin-64-1

Report only (§4.1). It also records the 26B's pools with FP8 and bf16 KV at P1's flags, an input to CAP-J2's drone
pair.

## 6. Metrics and analysis rules (fixed before any device data; D21)

1. **Energy source.**
   - Jetsons: board energy from P1's total-power field (Thor VIN; Orin the sum of three rails), integrated over the
     200 ms samples.
   - WS: the NVML energy counter, GPU only.
   - WS and Jetson energies are never compared in absolute terms, only as ratios.
2. **Fixed-window runs.**
   - **The measured window** runs from the end of warm-up to the horizon. A call that straddles either edge counts
     with the share of its output tokens generated inside the window (prorated by time).
   - **Primary metric:** J per generated token over the measured window.
   - **Secondary metric:** energy per completed session, prorated: J/token × the mean generated tokens of the
     completed sessions.
   - **Raw energy per completed session** (window energy / completed sessions) is reported only for continuity with
     CMP-2, labelled as biased by the sessions cut at the window's end.
   - Sessions per hour are reported.
3. **Best against best.** Configurations are compared at their best N among the N values run.
4. **Ties and noise.**
   - Differences under 2% are ties (D18).
   - No difference smaller than the measured repeat spread (CAP-J1's two replicates) is claimed.
   - With a single run per point, "single run" is stated next to the number.
5. **Idle share.** Active energy (above the idle baseline × the window) is reported next to total board energy,
   because a Jetson's idle draw is a large share. Thor-1 idled at about 28 W with P1's server up.
6. **Completeness.** A point counts only if:
   - preflight passed before and after the run;
   - the telemetry has no flagged gap;
   - the run reached its window;
   - its data is on the WS with checksums.
7. **Code before results.** The analysis code is committed before its results are reported. A rule changed after the
   data exists is reported as a change, with both readings.

## 7. After the meeting: one branch per option

Rule for every branch:
- the chosen branch's experiments get full specs and decision rules in this plan (as G1's did in Appendix R);
- Sandesh approves them before they run;
- the sizes below are first estimates.

| Branch | Experiments (device, size) | Needs | Overlap with P1 |
| --- | --- | --- | --- |
| **CAP** (the lean; the default if D12 confirms it) | **CAP-J2**, FP8 against bf16 on real tasks: (1) traffic with P1's agent on the Orin 32s at N = 1, 4 and 8 (energy per successful task, overflow failures); (2) the drone pair on one device (Orin-64-1, gemma-26B Reflexion through P1's harness on the unit, matched tasks), which removes the device difference from §1.1's 82.1% vs 81.7%. **CAP-J3**: the other levers (tool-schema length, output caps, window size) as a design-space study. **CAP-J4**: capacity-aware admission (CAP-P1), only if a gap remains after the best static setting. About 1–2 weeks of the three Orin 32s plus Orin-64-1 | TRF for traffic; P1's drone harness (installed on the units) | MB5 (FP8 window probe) |
| **A** | **A-J1** full (Thor-1, about 14 h, then 2 more sampling seeds). **A-J2**: pass rates under sampling with P1's drone harness (Thor-1; 12 CLGSCE tasks × 3 instances × 2 arms, about 30 h). **A-J3**: the decode guard (A-P1) live inside P1's agent loop (Thor-1). **A-J4**: traffic's repeated capped tool calls with P1's agent, and a retry policy | TRF for A-J4 | MB4 (capped-call replays) |
| **D** | **D-J1**: the vision-tool burst on Orin-64-1 at its real pool, with real unified-memory contention (P1's agent, or the replayer's image bursts). **D-J2**: co-located models on one board | TRF for the real bursts | MB6 (the vision tool) |
| **B** | **B-J1**: E4B as a step-wise agent on an Orin 32 (P1's model on P1's board), tasks D1–D3 | mayankarya's OK to extend aerogen (D6) | P1's agent design |
| **C** | **C-J1**: τ²-bench with E4B, thinking off, on an Orin 32, with the user simulator on the WS; then N sessions with injected waits | — | none |

Common to every branch after the meeting:
- P1F-4 (rerun `p1_opportunity`, `p1_caps` and `p1_repo_figures` on the final data);
- P1F-5 (why granite and E4B evict KV on the Orins at one agent);
- TRF-2 and TRF-3;
- COR-3b and COR-4;
- DEV-7 for the other models;
- repeats of any device point a paper will cite (at least two runs per point).

If the professor wants more evidence before choosing, the first experiments of the CAP and A branches run for one more
week (CAP-J2's drone pair, A-J1 in full), and we report again.

## 8. The meeting (Wed 14 Oct)

**Materials (MTG-1, Tue evening):**
- **CMP-2,** corrected (COR-1), with a box "First results on P1's devices" (CAP-J1, the anchor, the A-J1 pilot) and the
  WS reruns (P1F-3).
- **The deck, v2.4:** the corrections, one device-results slide and one plan slide (COR-3a).
- **A one-page device plan per option** (§7 condensed). It replaces CMP-2 §10 Q6, which the devices answer.

**Questions** (CMP-2 §10, updated):
1. **Direction:** which option or combination?
2. **Scope:** is capacity and concurrency an acceptable continuation of the retained-state question?
3. **Agents per edge box:** this sets the memory pressure in CAP and D. P1's paper ran one ("batch size is one").
4. **Thresholds** (D4) for the chosen option.
5. **The split with P1:**
   - who runs MB4, MB5 and MB6;
   - whether P5 offers P1 the sampling and step-wise results;
   - what P5 may claim.
6. **Device time:** the units are in hand. Which branch gets them first?

**After (MTG-3, the same day):**
- record D12's outcome as D23;
- turn §7's chosen branch into tasks with rules;
- rewrite the master plan's M8;
- update HANDOFF.

## 9. Decisions

D12 remains the professor's direction decision. Its outcome will be D23. New decisions in this plan:

| ID | Decision | Status |
| --- | --- | --- |
| D19 | **Device roles.** The three Orin 32s for capacity: two run full replicates in opposite orders (every arm of a replicate on one unit), the third runs the anchor and stands by as a spare. Thor-1 for A (P1's bf16 26B and P1's drone stack). Orin-64-1 for calibration, then D and the Gemma FP8 drone pair. The WS for development, the driver and gateway, analysis (ECC), and the link between WS and device | approved 12 Oct |
| D20 | **Device protocol.** P1's images, models and server flags, with the pool set by `--max-total-tokens`; MAXN with clocks as found (locked); KV flush verified; warm-up; a quiet unit checked before each run (DEV-5); board energy as P1 defines it (DEV-3); P1's stack stopped while P5 measures; nothing deleted | approved 12 Oct |
| D21 | **Metrics for fixed-window runs** (§6). J per generated token first; energy per completed session prorated; raw per-session only for continuity; configurations compared at their best N; no difference claimed below the measured repeat spread. Applies to the CMP-2 corrections too | approved 12 Oct |
| D22 | **Scope before the meeting:** COR-1/2/3a, P1F-2/3, DEV-1 to DEV-6, DEV-7 on Orin-64-1, CAP-J1 with its anchor, RET-J1, the A-J1 pilot, MTG-1; checkpoints C1, C2 and F (§3) | approved 12 Oct |

## 10. Risks and fallbacks

| Risk | Fallback |
| --- | --- |
| Device setup slips | Checkpoints C1 and C2 (§3). The WS reruns (P1F-3) and the corrections carry the meeting without device numbers |
| A container cannot start on Orin-32-2 (264 MB free on its docker root) | Replicate 2 moves to Orin-32-3 (the anchor then runs after it, or on Orin-32-1 after replicate 1). If space is needed, ask (through Sandesh) to move, not delete, P1's files off that SSD |
| Orin-32-3's image has a different SGLang | It runs only the anchor and within-unit reruns, and the version is recorded. If it must host a replicate, label it |
| The three Orin 32s differ (DEV-6) | Comparisons only within a unit: each CAP-J1 replicate is on one unit; the spare's reruns replace a point only if DEV-6 says the units are interchangeable |
| Our replayer or gateway disagrees with SGLang 0.5.16 | Fix in DEV-4 (small API differences). Else drive SGLang directly without the gateway, reading tokens from the responses |
| Our board energy disagrees with P1's | DEV-3's side-by-side check with P1's sampler, and CAP-J1's anchor. If the anchor fails, report relative numbers only |
| Too few sessions complete in a window | J per token is the primary metric. Longer windows after the meeting |
| Thermal drift on long runs | Temperatures logged; cool-down before each run; replicate 2 runs in the reverse order. P1 saw no throttling at room temperature |
| Someone else's job lands on a unit (swarm, k3s, another account) | Preflight's quiet check stops the run; rerun the point |
| P1 already measured FP8 against bf16 on these units: the 6–10 Oct runs used FP8 KV at 60,000 tokens (`e2`, `rx45`, `rx57`, `ministral_e2`, `e2_qwen`) | Ask the mentor before the meeting what these were (MB5?). CAP-J1 is the multi-agent complement (P1 ran one agent); credit P1 and agree the split |
| The WS goes down mid-run (it drives the units) | That point is lost and rerun. If it recurs, move the driver to Thor-1 (Python 3.12, a venv in `~/p5`) |
| The laptop drops | All orchestration runs in WS tmux; nothing depends on the laptop |
| P1's final traffic agent cannot be found, or needs services we cannot reproduce (camera feeds, the orchestration host .59) | The traffic parts of CAP, A and D stay replays (no success measure); the drone parts use P1's harness, which is on the units |
| The professor wants more evidence before choosing | One more week of the CAP and A branches' first experiments (§7) |
| P1 needs the units back | Agree a schedule through Sandesh; every point is restartable on its own |

## 11. Open items

**For Sandesh:**
1. ~~Approve this plan, including D19–D22.~~ Approved 12 Oct.
2. **Artifacts:**
   - the deck v2.4 before the meeting (corrections, device results, plan);
   - the evidence doc and the teaching guide after D12 (COR-3b), unless you want them earlier.
3. **The lean's wording, given P1's FP8 pair (§1.1).**
   - Default: keep the lean and present the pair as its main risk.
   - Alternative: "a design-space study first, a controller only if a gap remains".
4. The meeting's time on Wednesday, which sets the freeze F.
5. Thor-1's legacy P5 root helper `/usr/local/sbin/jouleserve-thor`: leave it alone (the default)?
6. Sudo, if needed:
   - stopping ollama on Orin-64-1;
   - pausing k3s there, if DEV-6 shows it disturbs the idle baseline.

**For P1 or the mentor (through Sandesh):**

7. Where is P1's final traffic agent (TRF-1)? What does it need: its sandbox image, data, and services on .59?
   - Thor-1 has an Aug–Sep version in `/media/ssd/Deepstream-Yolo-upstream/` (`traffic_agent`, `camera_query_agent`).
8. The 6–10 Oct runs on the units (FP8 KV, 60,000 tokens):
   - Are they MB5?
   - Are they finished?
   - May P5 see their results?
9. Who runs MB4, MB5 and MB6? Do we offer P1 the A-E1/A-J1 and B results?
10. Only if DEV-2 fails: may P5 move (not delete) P1's files off a full Orin 32 SSD?

## Appendix R. Record of G1 and G2 (5–11 Oct; plan v1.0–v1.2)

Kept unchanged from v1.2 so the rules that were fixed before the G1 runs stay on record; the code and CMP-2 cite them.
Section numbers inside this appendix (§2.4, §2.5, §7, §8) refer to v1.2, which git keeps
(`git show e93f103:planning/OPTIONS_PLAN.md`). Its other sections (why, the options as of 5 Oct, the outline, the
order of work, the WS protocol, risks, Sandesh's answers and the feasibility checks of 5 Oct) are superseded by this
version or by `AGENTS.md`, and are left to git.

### R.1 Criteria K1–K8 (v1 §2.2; D16)

| # | Criterion | What counts |
| --- | --- | --- |
| K1 | **Prize** | Share of P1's measured energy (or energy per success) at stake, and on which configurations |
| K2 | **Evidence strength** | Measured on P1's devices > measured on the WS > simulated > projected > literature; sample sizes |
| K3 | **Novelty** | Against Track B prior work (plus this week's reviews) and against P1's paper |
| K4 | **Edge specificity** | Why it matters on a Jetson; whether the WS can show it or it needs a device |
| K5 | **Generality** | Whether it holds beyond P1's two workloads, its agents and its models |
| K6 | **Feasibility** | What is built, what is left, the risk of not finishing within the ISP |
| K7 | **Dependence on P1** | Devices, data, code, agreement, overlap with P1's paper |
| K8 | **Risk** | What would kill it |

### R.2 Evidence tasks and their decision rules (v1 §2.4; D15)

Each task names its decision rule. The thresholds are proposals for Sandesh to confirm (D15).

| ID | Option | Question | Method (short) | Decision rule (proposed) | Needs | Effort |
| --- | --- | --- | --- | --- | --- | --- |
| **A-E1** | A | Do Gemma-4's loops survive sampling? | Replay P1's recorded capped prompts and finished controls; greedy (P1's) vs Gemma's default sampling | See spec | S1, S4 | 3 h + 3–10 GPU-h |
| **A-E2** | A | After an online stop, does a retry finish usefully, and at what cost? | Same prompts: stop where the detector fires, retry three ways, check the output | See spec | A-E1, S4 | 4 h + 2–4 GPU-h |
| **A-E3** | A | What does reasoning-length and early-exit work already cover? | Literature review, review docs in `review/systems/` | Novelty paragraph for A with the closest 3–5 works | — | 4–6 h (background) |
| A-E4 | A | What are traffic's capped tool calls? | Analysis of P1's traffic traces only (arguments, tools, sizes); no replay possible | Report only | — | 2 h |
| A-E5 | A, sim | How well do long decodes batch on Gemma-4 (MoE) vs dense models? | `jsw/costs/calibrate.py`: J/token against batch 1–16 at 4K/16K/32K context | Report; feeds the simulator's batching model | S1 | 2 h + 2 GPU-h |
| **B-E1** | B | Does P1's own model keep its steps short in a step-wise agent? | aerogen driver with gemma-4-E4B (P1's weights) and the 4-bit 26B on D1–D3 | See spec | S1 | 3 h + 4 GPU-h |
| B-E2 | B | What do the step-wise projections become with Gemma's step sizes? | Rerun `stepwise_ceiling` and the Thor projection with B-E1's runs | Report | B-E1 | 2 h |
| B-E3 | B | What does agent-design literature say (code-as-action, ReAct, plan-and-execute, drone agents)? | Short literature review | Novelty paragraph for B | — | 2–3 h (background) |
| **C-E1** | C | Does τ²-bench have a retained-state opportunity? | τ²-bench on the WS, single sessions, then injected waits through S3 | See spec | S1, (S3) | 6–8 h + 4 GPU-h |
| **RET-E1** | RET, D, CAP | Do the simulator's results hold on a live engine? | Replay P1's granite traffic runs live on granite at P1's pool sizes, N = 1–8, three policies; compare with the simulator | See spec | S1, S2, S3, S5 | 4 h + 6–8 GPU-h |
| **D-E2** | D | Is the vision burst worth more than 0.6% with several agents? | Replay P1's Orin 32 E4B traffic runs on E4B with real image bursts at small pools; default, pin, burst admission | See spec | S1–S3, D-P1 | 5 h + 4–6 GPU-h |
| D-E3 | D | What does unified-memory and co-located-model work cover? | Short literature review (mzCache and newer) | Novelty paragraph for D | — | 2 h (background) |
| **CAP-E1** | CAP | Does an FP8 KV cache cost quality on these agents? | Pool size and loop/finish rates with FP8 vs bf16 KV on A-E1 controls and a B-E1 subset | See spec | S1, A-E1, B-E1 | 2 h + 3 GPU-h |
| CAP-E2 | CAP | What does KV quantization and prompt/tool-loading work cover? | Short literature review | Novelty paragraph for CAP | — | 2 h (background) |
| **CMP-1** | all | Comparison doc skeleton from existing evidence | Write §2.1's outline with today's numbers | Sandesh reviews the template | — | 4 h |
| CMP-2 | all | Full comparison | Fill from all tasks above | Sandesh's review | all | 6–8 h |

Outcomes: R.3.

#### A-E1 — do the loops survive sampling?

- **Prompts:** P1's recorded capped Thor prompts. All have full `messages`:
  - 122 Reflexion calls (repository), 121 of which our detector flags as loops;
  - 143 tool-calling calls (`data/p1_thor_toolcalling/`): 127 at 32,768 tokens, all loops, plus 16
    evaluator calls at 1,024 that are not runaways and are left out;
  - controls: the 173 long Reflexion calls that finished on their own.
- **Model:** the 4-bit gemma-4-26B-A4B on one GPU (D13). gemma-4-E4B (P1's exact weights) is a check on its own
  5 capped drone generator prompts from Orin 32.
- **Arms:**
  - greedy as P1 ran it (temperature 0, top_k 1, seed 42, thinking on, `max_tokens` 32,768);
  - Gemma's default sampling (temperature 1.0, top_k 64, top_p 0.95, from its `generation_config.json`),
    3 seeds.
- **Measures:** loop flag (online detector, S4), finish reason, output tokens, time, NVML energy, whether the
  final output parses as Python and calls only P1's drone API.
- **Cost control:** the greedy arm stops when the detector fires, since only "does it loop" is asked. Pilot
  first: 60 loop prompts + 40 controls × 1 seed, then the full set.
- **Decision rule (proposed):**
  - **Reproduction check first:** greedy on the WS must loop on ≥ 50% of the prompts that looped on the Thor.
    If it does not, the quantized stand-in does not reproduce P1's behaviour: the result is inconclusive and
    we say so (fallback in §7).
  - **"Sampling removes the loops"** if sampled runs loop on ≤ 10% of those prompts (Wilson 95% interval
    reported) and the controls do not get worse (finish rate, valid programs).
  - Between the two: sampling reduces but does not remove loops; an online stop is still needed as a guard.

#### A-E2 — stop and retry

- **Prompts:** A-E1's looping prompts under greedy.
- **Stop:** where the online detector fires (median 35% of the call on the Thor).
- **Retry variants:** R1 the same prompt resampled with Gemma's defaults; R2 greedy with a short nudge
  appended ("your previous attempt repeated itself; write the final program now"); R3 a lower `max_tokens`.
- **Measures:** does the retry finish; tokens and energy to finish, against P1's recorded path; valid program
  (parses, P1's API only).
- **Stretch:** execute the program in our x86 headless AirSim (legacy build) and grade it with P1's
  deterministic checker (`data/p1_aeroeval_src/final_sweep/_harness/verdicts.py`) for a real pass or fail.
  Feasibility not yet checked.
- **Decision rule (proposed):** "stop and retry preserves runs" if ≥ 70% of retries end with a valid program at
  ≤ 50% of the recorded call's energy. This is the part of A that P1's paper does not have: P1 gives only
  an upper bound for stopping at the first cap.

#### B-E1 — P1's own model in a step-wise agent

- **Setup:** the existing aerogen driver (`--task-file`, `--world-prompt`, `--runtime-prompt`) on P1's D1–D3
  task texts, 3 instances each, 50× pacing, strict checker. SGLang's `gemma4` tool-call and reasoning parsers.
- **Configurations:** E4B and 26B-4bit; thinking on (P1's setting); greedy and sampled. 9 missions each.
- **Measures:** output tokens per step after a tool result, planning-call length, runaways, delivered-all and
  strict pass, prompt growth and reuse.
- **Decision rule (proposed):** if the median output after a tool result is ≤ 300 tokens (the Thor break-even
  for re-prefilling a 20K context), B's projection holds for P1's model family. Above it, the projection is
  redone with Gemma's sizes (B-E2).

#### C-E1 — τ²-bench

- **Setup:** `sierra-research/tau2-bench` (MIT, active) in its own venv. The agent model on one GPU (gemma-4-E4B
  or Qwen3.5-9B, thinking on and off); the user simulator on the same server or the other GPU.
  Domains: airline, retail, telecom; 20–50 tasks, single session.
- **Measures:** calls per task, prompt growth per step, output per step, cache reuse, task reward, and the
  ceiling P/(P + r·O) at the WS's r and at the Jetsons' r (52–312).
- **Then:** replay the runs through S3 as N sessions with waits injected from P1's distributions (flights:
  median 17–113 s; traffic tools 0.5–3 s; vision tool 53–158 s).
- **Decision rule (proposed):** C has a retained-state opportunity worth a full comparison if the per-step
  ceiling at a Jetson r is ≥ 20% of LLM time. If it is below 10%, C collapses for the same reason traffic does.

#### RET-E1 — live anchor for the simulator (also D's and CAP's baseline)

- **Workload:** P1's granite-4.2-8B traffic runs (Orin 64 and Orin 32 granite: the configurations where
  capacity binds), replayed by S3 on granite-4.2-8B on one A5000. The model and the token counts are P1's;
  only the GPU differs.
- **Pools:** P1's real pools (32,768 and 26–27K tokens) and half of them, as far as the WS pool allows
  (measured in S1).
- **Policies run live:** SGLang's default; keep (soft pin with `--enable-session-radix-cache` and
  open/close session); no reuse (a unique cache salt per call, the "drop at every wait" bound).
- **N:** 1, 2, 4, 8 agents; 2 h per point to start.
- **Simulator side:** `traffic_sim` with a WS granite device model fitted with `calibrate.py`.
- **Decision rule (proposed):** the anchor holds if live and simulated energy per completed task agree within
  ±15% at every point, and the three policies rank the same. If not, the negative result is restated with the
  live numbers.

#### D-E2 — the vision burst with several agents

- **Workload:** P1's Orin 32 gemma-E4B traffic runs, which include 50 `ask_vlm` calls, replayed on gemma-4-E4B
  (P1's weights, multimodal).
  - During each recorded `ask_vlm` window S3 sends the recorded number of concurrent image requests (running
    requests: median 23).
  - Their size is set so that peak KV matches the vitals stream.
- **Pools:** 12.4K tokens (Orin 64 gemma's) and 71K (Orin 32 E4B's).
- **Policies:** default; pin the paused context during the tool (session soft pin or priority); admit the
  burst at most k requests at a time; both (D-P1).
- **N:** 1, 2, 4 agents.
- **Measures:** recomputed tokens after the tool, energy per completed run, the tool's own time (admission
  slows it), run time.
- **Decision rule (proposed):** D's prize at N agents is the best policy against the default in energy per
  completed run. It is reported next to the 0.6% single-agent number. If it stays < 5% at 4 agents, D's live
  case is small.
- **Depends on P1's answer** about which server `ask_vlm` calls. If it is a separate server, the emulation
  becomes a second SGLang server sharing the GPU (still option D, a different mechanism).

#### CAP-E1 — FP8 KV quality

- **Setup:** check which `--kv-cache-dtype` values SGLang 0.5.20 accepts on Ampere (to check in S1). Pool size
  with FP8 vs bf16 KV for granite and E4B.
- **Quality:** A-E1's finished controls and a B-E1 subset with FP8 KV: loop rate, finish rate, valid programs,
  delivered/strict pass.
- **Decision rule (proposed):** no measurable degradation means capacity is a free configuration choice: a
  finding to report to P1, and CAP weakens as a research option. Degradation means a run-time trade-off
  exists (a CAP or D angle).

### R.3 Outcomes against the decision rules (v1 §2.5, 2026-10-06)

Details, numbers and caveats: the comparison doc, §3–§8. [WS-meas] unless marked.

| Task | Rule | Outcome | Verdict |
| --- | --- | --- | --- |
| A-E1 | Reproduction: greedy on the WS loops on ≥ 50% of the Thor loop prompts; then "sampling removes the loops" if sampled runs loop on ≤ 10% of them and the controls do not get worse | E4B (SGLang) never loops, even on its own Orin 32 loop prompts. A 4-bit GGUF of P1's 26B through llama.cpp (D13's outcome): greedy loops on 23/30 loop prompts (77%, CI 59–88%) and 6/20 controls; Gemma's default sampling on 0/30 and 0/20, 28/28 valid programs (one seed) | 26B: **sampling removes the loops**; E4B: inconclusive (no reproduction) |
| A-E2 | Stop and retry preserves runs if ≥ 70% of retries end valid at ≤ 50% of the recorded call's energy (tokens as the proxy) | Resample: 17/17 re-looping calls recovered, 28/29 valid overall, but only 10/29 at ≤ 50% cost (median 19.7K vs 32.8K tokens). Nudge: 7 of 10 retries loop again. Budget: dropped | **Not met**: a safety net, costlier than sampling from the start |
| A-E4 | Report only | Repeated capped `run_python` calls hold 33% (Thor gemma) and 31% (Orin 32 E4B) of traffic LLM-call energy [P1-meas] | — |
| A-E5 | Report only | Batch 1 → 16 cuts energy per token 13× (granite) and 13.5× (E4B) | — |
| B-E1 | Short steps if the median output after a tool result is ≤ 300 tokens | E4B: median 63 (greedy) / 68 (sampled); strict pass 9/11 and 7/13; 9 of 33 missions lost to a tool-format bug (fixed, not re-run) | **Met** |
| B-E2 | Report only | 26–27 kJ per strict success greedy, 35–40 sampled, vs P1's Reflexion 284–499 kJ (Thor prices) [proj] | — |
| C-E1 | Opportunity if the ceiling is ≥ 20% of LLM time at a Jetson r; collapses if < 10% at every r | Thinking on: 7.5% / 9.9% at E4B's r, 16–24% at Thor's drone r (retail ≥ 20%). Thinking off (airline): 25% at E4B's r | Thinking on: **borderline** (the rule fires for retail only at Thor's drone prices); thinking off: **opportunity** |
| D-E2 | D is worth more than the burst's 0.6% if the best policy beats the default by > 5% at 4 agents | Mechanism reproduced (88–100% of the paused prefix recomputed at 12.4K). Best at 4 agents: pin, −3.8%; pin + cap 2 cuts recompute to 37% at one agent but costs +11% | **Not met**: within 5% |
| RET-E1 | Anchor holds if live and simulated energy per completed task agree within ±15% at every point and the policies rank the same | Run narrower than specified (GPU time): Orin 32 granite only, P1's pool only (no half pools, no Orin 64), N = 1, 4, 8, two policies (default, no reuse; keep not run), 45 min per point. Within 14.2% at every point (2% except N = 4); FP8 run out of sample within 6.4%. Ranking: a tie in both, because at N = 8 the default keeps nothing (0/102 calls hit) | **Met** on the points run (ranking degenerate) |
| CAP-E1 | No measurable FP8 degradation means capacity is free configuration; degradation means a trade-off | FP8 KV doubles granite's pool (53,296 vs 26,648) and cuts energy per session 62% at 8 agents. Gemma-4 FP8 KV cannot start on our A5000s in SGLang 0.5.20, so the quality pairs did not run (P1 ran it on an Orin 64 with SGLang 0.5.16: not an Ampere-wide limit, corrected 11 Oct) | **Undecided** (quality side not measured) |

### R.4 Shared base S1–S6 (v1 §3.1)

| ID | Piece | Where | What it does | Done when | Effort |
| --- | --- | --- | --- | --- | --- |
| **S1** | P1's models on the WS | `env/launch_*.sh`, `AGENTS.md` §6b | Download and pin: gemma-4-26B-A4B 4-bit (17.2 GB), gemma-4-E4B (16.0 GB), granite-4.2-8b (17.6 GB); offline mode. Smoke tests: chat, thinking on/off, the `gemma4` tool parser, images (E4B), `/metrics` fields (SWA pool), pool size at the chosen mem fraction, FP8 KV dtype options | Each model serves a tool call and reports its pool; recipe and gotchas in AGENTS.md | 4–6 h |
| **S2** | Gateway v0 | `jsw/gateway/` | Async OpenAI-compatible proxy in front of SGLang. Per-session routes `/s/<sid>/v1/...` and a native `/s/<sid>/generate` passthrough. Streams upstream even when the client does not, so policies can watch tokens. Per-call log (P1-compatible superset). Policy hooks `on_request` (forward, delay, modify, reject), `on_chunk` (continue or abort), `on_complete`, `on_tick` (`/metrics`). Abort through `/abort_request` and disconnect | Unit tests with a fake upstream; K2 and Gemma smoke; added latency measured (target < 5 ms per call) | 8–10 h |
| **S3** | Trace replayer | `jsw/workloads/replay.py` | Plays recorded runs (P1 traffic and drone via `analysis/p1_repo.py`, WS aerogen runs) as N closed-loop agents against the gateway. SGLang's native `/generate` with synthetic token IDs gives exact prompt lengths. Each call's prompt is the previous prompt + the previous **generated** IDs + a synthetic tool result, so prefix reuse is real. Outputs held to the recorded length (`ignore_eos`, `max_new_tokens`). Tool gaps replayed as waits. Optional vision-burst injection. Seeds and task mix as in the simulator | Replays one P1 run with prompt and output lengths within 1% and cache hits as expected; runs N = 8 | 8–10 h |
| **S4** | Streaming loop detector | `jsw/policies/loop_detector.py` | The online detector of `analysis/p1_loops.py` (4,000- and 16,000-character windows, every 1,000 characters, fires after 3 checks below 10%) as an incremental class shared by the analyses and the gateway | Reproduces the offline flags exactly on P1's 265 capped and 173 finished calls | 2 h |
| **S5** | Runner and manifest | `jsw/runner/` | One run directory format, manifest (git SHA, versions, server flags, model revision, GPU state, seeds), sampler start/stop, teardown check; factored out of `aerogen_driver.py` | aerogen driver, replayer and A-E1 all write the same format | 3 h |
| S6 | Analysis helpers | as built: `jsw/workloads/loop_replay.py` (A-E1/A-E2 replays), `analysis/{a_e1,a_e2,a_e4,b_e1,b_e2,c_e1,d_e2,ret_e1,cap_e1,options_figures}.py` | A-E1/A-E2 tables and figures; live-vs-simulator comparison for RET-E1 and D-E2 | Figures for the comparison doc | 4 h |

Open technical checks for S2/S3, made at the start of S2: whether `/generate` returns the output IDs for an
`input_ids` request; whether a client disconnect aborts the request in 0.5.20; how `ignore_eos` interacts with
Gemma's three EOS IDs.

### R.5 Decisions D13–D18 (v1 §6)

D12 stays the professor's direction decision (open). New decisions in this plan:

| ID | Decision | Status |
| --- | --- | --- |
| D13 | Stand-in for gemma-4-26B-A4B on the WS: the 4-bit compressed-tensors checkpoint (`cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`, 17.2 GB) on one GPU; FP8-dynamic over two GPUs as fallback | **outcome 2026-10-06:** neither runs on Ampere in SGLang 0.5.20 (4-bit MoE SiLU-only; FP8 MoE needs fp8e4nv). The 26B runs through llama.cpp as a 4-bit GGUF (unsloth UD-Q4_K_XL) for A-E1/A-E2; gemma-4-E4B elsewhere |
| D14 | The replayer drives SGLang's native `/generate` with synthetic token IDs and recorded lengths. Text effects (loops, tool parsing) are outside its scope; A-E1/A-E2 replay real text instead | **approved** 2026-10-05 |
| D15 | The decision rules in §2.4 | **approved** 2026-10-05 |
| D16 | The comparison criteria K1–K8 and template (§2.1–2.3) | **approved** 2026-10-05 |
| D17 | Capacity (CAP) as its own option in the comparison | **approved** 2026-10-05 |
| D18 | RET-E1's comparison method, fixed before its data arrived: the simulator stops at the live run's span (the live run cuts its last sessions), takes its powers from NVML's energy counter like the live energy (the power reading runs 24% above it), and a difference under 2% counts as a tie in the ranking | **taken** 2026-10-06 during G1 (Claude); for Sandesh to confirm |

### R.6 Earlier labels W1–W9 (v1 §10)

The options first offered to Sandesh on 2026-10-05 map to this plan as follows:

| Earlier label | This plan |
| --- | --- |
| W1 | A-E1 |
| W2 | A-E2, A-P1 |
| W3 | S3, RET-E1 |
| W4 | D-E2, D-P1 |
| W5 | A-E5 |
| W6 | CAP-E1 |
| W7 | A-P2 |
| W8 | A-P1's thinking-budget hook, after A-E3 |
| W9 | C-E1/C-P1, B-E1/B-P1 |

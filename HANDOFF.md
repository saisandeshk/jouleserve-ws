# HANDOFF — jouleserve-ws

**Last updated:** 2026-10-11 (IST). **P1 submitted its paper on Sat 10 Oct** (SIGMETRICS 2027, under double-blind review;
data frozen at 10:30 IST) and pushed its final data. We pulled it into the local clone (`0cc2311a`, at Sandesh's request),
read it, and on 10-11 Oct brought every P5 doc, the artifacts and the deck up to it. **The professor meeting is Mon
12 Oct:** the direction decision (D12) is taken there, with the deck and CMP-2. The WS was down and the Thor is
off-limits, so the numbers from P1's final data are P1's own summaries, not our re-analysis.

- **What P1's submitted paper and final data mean for P5** (CMP-2 §12, and the evidence doc's new section):
  - **RET's premise holds on P1's whole corpus** (4,757 runs, 25 configurations, 8 models, 3 Jetsons, 1,468 h,
    68.9 kWh): generation is 77.9-99.6% of LLM energy; prefill is 0.7-3.9% of LLM time in 18 of the 22 configurations
    with a prefill/decode split (exceptions: Qwen2.5-VL 15.1-15.9%, Devstral drone 22.4% with its prefix cache off).
  - **KV evictions at one agent:** 21-68% of drone runs in 6 of 8 configurations; on Thor Reflexion they come with the
    loops (46 of 48 evicting runs contain a capped call). Why granite and E4B evict on the Orins is not checked yet.
  - **The 7 Oct tool-fault caveat is resolved in P1's data:** P1 replaced 776 faulted Orin traffic runs with re-runs
    (142 remain, only in the Orin 64 gemma-26B and Devstral Reflexion arms, which we do not use). Pass rates rose (Orin 32
    granite 16.4% → 51.3%, Orin 32 E4B 33.7% → 73.0%, Orin 64 granite 22.2% → 58.7%) and window overflows roughly
    doubled (up to 28.1%). Granite's faulted runs used 1.4-1.6× the energy of their own re-runs (the 7 Oct "1.7-4.2×"
    was partly task mix). Our Orin replays (RET-E1, CAP-E1, `traffic_sim`) are redone on the clean sessions once the WS
    is back; the sim-vs-live anchor stands, and the direction holds: more capacity pressure, not less.
  - **Overlap with P1:** the paper reports the loop finding offline (stopping at the first capped call saves 50.2% and
    loses 22 runs on Thor Reflexion drone) and leaves an online policy to "separate evaluation"; greedy decoding is not
    discussed. It lists FP8 KV, shorter tool schemas and bounded outputs as untested levers, says "batch size is one"
    (no multi-agent result), and describes the vision tool as the agent's own model. P1's post-submission plan has MB4
    (capped-call replays; overlaps A-E1/A-E2), MB5 (BF16 vs FP8 window probe; overlaps CAP-E1) and MB6 (the vision tool;
    D). Who runs what needs agreeing with P1 (CMP-2 §10 Q5). P5 is not cited.
  - **Our five corrections** (`NOTES_FOR_P1.md`, sent 5 Oct): (3) and (5) adopted, (1) and (4) in part, (2) not.
  - **A correction of ours:** "Gemma-4's FP8 KV cannot run on Ampere (the Orins)" was wrong as stated. P1 ran it on an
    Orin 64 (SGLang 0.5.16, triton backend, pool 60,000 at a 65,536 context); it failed on our A5000s with SGLang 0.5.20.
  - **Our lean does not change** (CMP-2 §9): CAP with A's safety net, as multi-agent consolidation on one edge box.
- **Updated 10-11 Oct:** figures `analysis/p1_final_figures.py` (three `p1final_*` PNGs in
  `reports/2026-10-06-options/figures/`, from P1's committed summaries); CMP-2 (update at the top, §7 FP8, new §12); the
  evidence doc and its repo copy; the teaching guide; the deck (v2.3); a note in the P1 audit doc; this file, TRACKER,
  AGENTS, the plans and the dated reports. Revisions in §2 "Artifacts".
- **Public repo, still:** P1's paper is under double-blind review, so its title and P1's figures stay out of git; write
  "P1's submitted paper (SIGMETRICS 2027)". The private artifacts may name it.
- **P1's clones:** local `data/edge-agent-bench` at `0cc2311a` (one corrupt pack object, a Qwen3.8 `device_samples`
  file; the worktree is fine); the WS clone `~/work/p1/edge-agent-bench` is still at `f6aabe4` (pull it when the WS is
  back). Since 7 Oct the drone sweeps live in `drones/edge_devices/final_sweep_*` (plus `rtx_6000_pro/`,
  `baseline_models/`); `analysis/p1_repo.py` follows that layout but **does not yet apply P1's supersede rule** (per
  task the latest re-run replaces the original, but an overflowed original is kept), so a refreshed traffic load would
  mix re-runs with faulted originals. Fix it before rerunning any analysis on the final data.
- **P1 audit (7 Oct, for P1, not P5 work):** private Claude Doc "P1 drone audit and review check (EdgeAgentBench @
  f6aabe4)", https://claude.ai/code/artifact/813c66c9-0521-4430-91e6-60be5a3e0c4d (rev 25 adds a note that it was not
  re-run against `0cc2311a`), with a git-ignored local copy in `reports/2026-10-07-p1-audit/` (never pushed). Scripts
  and tables on the WS in `~/work/p1audit/`. Its findings stay out of this public repo.
- **The comparison doc** (G1's output): [`reports/2026-10-06-options/README.md`](reports/2026-10-06-options/README.md),
  CMP-2. Every option A, B, C, D, CAP (and RET, the negative result) with the same template, criteria K1-K8, the
  evidence of 5-6 Oct, figures, our lean stated once (§9), questions for the professor (§10) and P1's submission (§12).
  Task status in [`planning/TRACKER.md`](planning/TRACKER.md) (plan [`planning/OPTIONS_PLAN.md`](planning/OPTIONS_PLAN.md)).
- **What the WS tests of 5-6 Oct found** (details in CMP-2):
  - A: P1's drone runaways are a decoding setting: on P1's 26B (4-bit, llama.cpp) greedy decoding loops on 23/30 of
    P1's loop prompts, Gemma's default sampling on 0/30. An online stop + one resample recovers 17/17 looping calls
    at 60% of the capped cost; nudging fails. Traffic's repeated capped tool calls hold 31-33% of gemma traffic LLM
    energy; batching cuts energy per token 13x at batch 16.
  - B: P1's E4B as a step-wise agent writes a median 63-68 tokens after a tool result; 9/11 strict passes greedy;
    11-19x less energy per strict success than P1's Reflexion (projected).
  - C: tau2-bench with thinking on: kept state worth 7.5-9.9% of LLM time at E4B's Jetson price; thinking off: 25%.
  - D: the vision-burst eviction reproduces live; pinning + a burst cap stop it but cost 11% more energy.
  - CAP: FP8 KV doubles granite's pool and cuts energy per session 62% at 8 agents (live; quality unmeasured); a 5x
    pool cuts it 2.4x at 4 agents; Gemma-4's FP8 KV failed on our A5000s in SGLang 0.5.20 (P1 ran it on an Orin 64).
  - RET: the simulator behind "no policy beats the default" holds live within 14% (RET-E1, granite traffic at P1's
    Orin 32 pool, 1-8 agents); at 8 agents the default keeps no state at all (0 of 102 calls hit the cache).
- **Built for G2** (shared base and two option prototypes): gateway (`jsw/gateway/`, policy hooks, tool-tagged routes,
  pythonic tool-call fallback), streaming loop detector, decode guard (A-P1), burst-aware memory policy (D-P1), trace
  replayer (`jsw/workloads/replay.py`), P1-prompt replayer (`loop_replay.py`), runner/manifests, calibration
  (`jsw/costs/calibrate2.py`), launchers for P1's models (`env/launch_model.sh`, `env/launch_llamacpp.sh`).
- **WS:** temporarily unreachable on 10-11 Oct. Last known state (6-7 Oct): idle, all runs in `~/work/runs/` (copies of
  the analyses' JSONs and figures are in the repo), P1's data in `~/work/p1/`. Analyses run there in
  `~/work/venv-analysis` (`python -m analysis.<name>`).
- **Laptop RAM is unreliable** (5 Oct): three P1 files read back with bit flips from the page cache (disk copies
  intact), plus power cuts and restarts. Process data on the WS (ECC) when it is up; commit often.
- **The Thor is off-limits** until Sandesh says otherwise (5 Oct): no access at all, not even read-only.
- **History:** P1's repository arrived Mon 5 Oct ([`reports/2026-10-05-p1-repo/README.md`](reports/2026-10-05-p1-repo/README.md),
  five corrections in [`NOTES_FOR_P1.md`](reports/2026-10-05-p1-repo/NOTES_FOR_P1.md)); the options were tested on the
  WS on 5-6 Oct (CMP-2); P1 was pulled to `f6aabe4` and audited for P1 on 7 Oct; P1 submitted on 10 Oct. The professor
  meeting planned for 5 Oct moved to 12 Oct; nothing has been shown to the professor yet.

Rules, machines, recipes and WS gotchas are in [`AGENTS.md`](AGENTS.md). This file holds the state at the time
of writing. **Update it at the end of every working session.** Replace stale facts rather than appending history,
which git already keeps.

---

## 1. The goal

**P5 / JouleServe.**
- **What:** a serving-layer controller for Jetson-class edge devices. It decides what happens to an agent
  session's retained state (KV, and SWA/recurrent state for hybrid models) while the session waits on a
  tool: keep, drop and recompute, offload, or change admission so that idle state does not block active
  work.
- **Metric:** energy per successful task.
- **Where the contribution must come from:** generic "keep KV across tool pauses" is taken (INFERCEPT,
  Continuum, TokenCake, Adaptive KV Retention, CacheScout; KAIROS for energy). It must come from what the
  edge changes: unified memory, small KV pools, model-backed tools on the same server, hybrid models, and
  physical tool waits. P1 measured no thermal throttling at room temperature (434 h by 5 Oct), so thermal state is out
  unless hot-enclosure runs show otherwise.
- **What the evidence now says** (§4): on P1's workloads, drone and traffic, a retention or admission
  controller is not a contribution; the energy is in runaway decodes, and the edge effect with large numbers
  is capacity. The direction is open (§6).
- **Resources:** the edge devices were with P1 until its submission (Sat 2026-10-10); when they come back to P5 is
  open. P5 has the 2×A5000 workstation, under its full control (temporarily unreachable on 10-11 Oct).

## 2. Situation as of 2026-10-11

- **P1's repository** (`dream-lab/edge-agent-bench`): read-only clone in `data/edge-agent-bench` (git-ignored; HEAD
  `0cc2311a`, P1's submitted state, pulled 10 Oct at Sandesh's request; our analyses of 5-6 Oct used `3c47ebc`, the
  7 Oct audit `f6aabe4`). Its remote is P1's GitHub: never push, never write in it, never run its `make` targets in
  place (`AGENTS.md` §4).
  - **Final data** (P1's summaries at `0cc2311a`): 4,757 runs, 25 configurations (8 drone, 17 traffic), 8 open models,
    3 Jetsons, 1,468 h, 68.9 kWh, plus cloud models and an RTX PRO 6000 as references; drone and traffic graded; Thor
    drone tool calling is now in the repository (all 144 runs). P1's supersede rule (latest re-run per task, an
    overflowed original kept) decides which traffic runs count.
  - **Our loader** `analysis/p1_repo.py` (cache in `data/p1_cache/`) follows the 7 Oct layout but not yet the supersede
    rule; the analyses are `p1_opportunity.py`, `p1_caps.py`, `traffic_sim.py`, `p1_repo_figures.py`, and
    `p1_final_figures.py` (10 Oct; plots P1's committed summaries, no loader).
  - **People:** P1's analysis and paper are written by Mayank Arya (`mayankarya`, also aerogen's author);
    drone runs by Aayushi, traffic runs by Priyanshu.
  - **P1's submitted paper** (SIGMETRICS 2027, submitted Sat 10 Oct, under double-blind review; title kept out of this
    public repo): a benchmark, a measurement study, a two-layer cost model (a per-call cost per device plus a
    device-independent path model), policies (energy per success, an attempt budget, choosing a configuration) and the
    corpus. One request in flight, temperature 0, the cache flushed per run, SGLang 0.5.16. What it says on each P5
    option, and P1's post-submission plan (MB4, MB5, MB6): CMP-2 §12 and the summary at the top of this file.
  - **Corrections for P1** (`NOTES_FOR_P1.md`, sent by Sandesh on 5 Oct; no direct reply, the paper answers them):
    (1) `ask_vlm` is a burst of requests to the agent's own server: in part (the paper now calls the vision tool "the
    agent's own model reading images", but does not mention the burst or its evictions); (2) the loop threshold misses
    long-period loops: not adopted; (3) the drone Orin 32 caps are 1,024-token evaluator calls: adopted; (4) Orin 64's
    context guard truncates calls the 8,000-token rule does not count: in part; (5) Devstral's prefix cache is off:
    adopted.
- **The professor meeting is Mon 12 Oct.** Nothing has been shown to the professor yet; the deck (v2.3) and CMP-2 are
  ready for it.
- **Public repo:** `saisandeshk/jouleserve-ws` is public and holds P1's unpublished numbers in `reports/` (Sandesh's
  choice, 5 Oct). P1's own figures (deck and repository) are kept out of git (`reports/*/p1_figures/` is git-ignored), and
  since 10 Oct so is the title of P1's submitted paper. `gh` is not logged in on this machine (HTTP 401); the public API
  (`curl https://api.github.com/repos/saisandeshk/jouleserve-ws`) shows the visibility.
- **Artifacts** (all private until Sandesh shares them from their Share menu):
  - **Evidence doc**, "JouleServe (P5): drone and traffic evidence, and options":
    https://claude.ai/code/artifact/474eee56-2e2f-44f9-8b97-f7bb51b588c7 (revision 171; repo copy
    `reports/2026-10-02-p5-evidence/README.md`, keep in sync). 5 diagrams, a native chart of kept-state value, our
    figures and P1's deck figures. **6 Oct (rev 127-138):** "Tested on the workstation, 5-6 Oct", the options table with
    CAP, our lean. **11 Oct (rev 140-171):** an update that replaces the 7 Oct tool-fault caveat, the FP8 Gemma
    correction, the meeting date, and a new section "P1's submitted paper and final data (10 Oct)" with the three
    `p1final_*` figures.
  - **Teaching guide**, "JouleServe (P5): a teaching guide":
    https://claude.ai/code/artifact/36c2319c-b866-44f2-8dcf-42c02cdfd18c (revision 184; no repo copy). Chapter 18
    (the traffic workload), §16 P1, §19.5–19.7 traffic evidence, chapter 20 (five options, the lean), chapter 21
    (testing the options on the workstation), self-test 22 and glossary 23. **11 Oct:** the FP8 correction everywhere,
    the meeting on 12 Oct, P1's submission, the outcome of our corrections, two log lines, and a subsection at the end
    of chapter 16, "The submitted paper and final data (10 October)", with the three figures. One open comment in it
    (ours) asks how many drones per device to plan for.
  - **Reference deck** (Slides artifact): https://claude.ai/artifact/QrFXoAwDssEtftYgGnxVm8, v2.3 (artifact
    version 15, 140 slides). v2.3 (11 Oct): new slides `p1-overlap` (what P1's paper covers per option, MB4/MB5/MB6),
    `p1-final-data` (re-run figure) and `find-p1-final` (prefill and eviction figures); `p1-paper` rewritten for the
    submitted paper; cover, glance, changelog, P1, findings, options, status and plan slides updated. v2.2 (7 Oct): the
    tool-fault caveat. v2.1 (6 Oct): the WS test slides and `opt-cap`.
    - The single main reference, updated weekly: a new log slide (section 13, newest first), the
      at-a-glance slide and the changelog; matured results move into Findings.
    - **Style:** IBM Plex Sans, off-white with one blue accent, dark dividers; body text 28 px (14 pt),
      small text 24 px (12 pt).
    - **Slide sources:** a working copy lives in `data/p5deck/` (git-ignored; synced with v2.3 on 11 Oct). Before
      editing in a new session, re-read the changed files from the artifact if someone may have edited it in the
      browser.
    - **Figures:** uploaded as artifact assets; the blob-id → local-file map is `data/p5deck/blobs_2026-10-05.json`,
      `blobs_2026-10-06.json`, `blobs_2026-10-10.json` and `env/render_slides.py`'s `BLOBS`.
    - **Visual check** (Sandesh approved it): `python3 env/render_slides.py data/p5deck <out> [ids]`. It
      uses the Playwright headless shell if present, else Brave (`/opt/brave.com/brave/brave`) headless; it
      is approximate and flags overflow and overlaps.
  - **P1 audit doc** (for P1, private): https://claude.ai/code/artifact/813c66c9-0521-4430-91e6-60be5a3e0c4d (revision
    25: a note that it predates P1's submission).
- **WS** (P5's own machine with full control; it is **not** one of P1's "workstation" lanes): temporarily unreachable on
  10-11 Oct. Last known state (6-7 Oct):
  - Idle (GPUs at 47/15 MiB, no tmux server). 68 run directories in `~/work/runs/`, backed up to local
    `data/ws_runs/` (SHA-256 checked, 2,343 files).
  - Clone `~/jouleserve-ws` on `main` (pull the 10-11 Oct commits when it is back); `~/jsw-dev` is the synced dev copy
    (`env/sync_ws.sh`, stamp in `~/jsw-dev/REVISION`).
  - Models on disk (pinned, offline): gemma-4-E4B, granite-4.2-8b, the 4-bit 26B checkpoints that do not run in
    SGLang (derived text-only copies in `~/work/models/`), and the 26B GGUF (Hugging Face cache, unsloth) served by
    `~/work/llama.cpp`; K2 and Qwen3.5 from before. Recipes: `AGENTS.md` §6c.
- **Thor: off-limits** (Sandesh, 5 Oct): no ssh at all, not even read-only, until Sandesh says otherwise.
  Use P1's repository and our local copies.
- **P1's devices:** P1's runs ended with the data freeze on 10 Oct. When the Jetsons come back to P5 is not written down
  (§7 Q6).

## 3. What is built (JouleServe-WS pieces)

| Piece | Where | Notes |
|---|---|---|
| Telemetry samplers | `jsw/telemetry/samplers.py` | NVML at 10 Hz (power, **energy counter**, clocks, throttle) and SGLang `/metrics` at 2 Hz |
| aerogen driver | `jsw/workloads/aerogen_driver.py` (+ `aerogen_peek.py`) | Runs mayankarya's agent unmodified (runtime patches), N closed-loop session slots, manifest per run. Flags for P1's tasks: `--effort think\|nothink`, `--task-file`, `--world-prompt`, `--runtime-prompt`, `--top-k` |
| Delivery checker | `jsw/workloads/delivery_check.py` | Strict check of P1's D1–D3 over a sim trace (order, descent + 10 s hold, return, no flight through a building) |
| Cost calibration | `jsw/costs/calibrate.py` | Idle power, cold/warm prefill, decode J/token against batch |
| Analysis (WS and P1's Thor copies) | `analysis/sessions.py`, `report_figures.py`, `headroom_sim.py`, `sim_validate.py`, `p1_cache_misses.py`, `doc_charts.py`, `p1_per_task.py`, `stepwise_ceiling.py` | One session model for P1 traces and WS runs; ceilings (`stepwise.json` also holds r = 90 ceilings) |
| Admission/retention simulator | `analysis/admission_sim.py`, `admission_figures.py` | N drones per box, per-model state layouts, 12 policies + unlimited memory; Thor and WS device models |
| P1 runaway analysis | `analysis/p1_runaway.py`, `analysis/p1_loops.py` | Two-agent comparison; online loop detector replay, stop-rule savings, cross-check of P1's drone numbers |
| **P1 repository analyses** (2026-10-05) | `analysis/p1_repo.py` (loader), `p1_opportunity.py`, `p1_caps.py`, `traffic_sim.py`, `p1_repo_figures.py` | All 12 configurations: value of kept state, idle gaps, vision-tool bursts, prefix reuse; capped calls, loops and four stop rules; N traffic agents per device at real KV pools; energy by phase |
| P1 final-data figures (2026-10-10) | `analysis/p1_final_figures.py` | Plots P1's committed summaries at `0cc2311a` (prefill share, drone evictions) and a sourced table of 7 vs 10 Oct values (tool faults, pass rates, overflows); writes `reports/2026-10-06-options/figures/p1final_*.png` |
| Slide renderer | `env/render_slides.py` | Visual check of the deck's slide files |
| Launch / queues | `env/launch_k2_tp1.sh`, `env/launch_qwen35_tp1.sh`, `env/queue*.sh` | K2 pinned to revision `f846b1e` |
| **Options work (5-6 Oct)** | `jsw/gateway/`, `jsw/policies/` (loop detector, decode guard, burst memory), `jsw/workloads/replay.py`, `loop_replay.py`, `jsw/runner/run.py`, `jsw/costs/calibrate2.py`, `env/launch_model.sh`, `env/launch_llamacpp.sh`, `analysis/{a_e1,a_e2,a_e4,b_e1,b_e2,c_e1,d_e2,ret_e1,cap_e1,options_figures}.py` | The shared base and option prototypes of `planning/OPTIONS_PLAN.md`; tests in `tests/` (run with the legacy venv: `python -m tests.<name>`) |

Not built: a Jetson telemetry adapter, the CLGSCE port, policies inside a live agent loop. Master plan M3–M5 should
not be built as planned: rewrite them after the direction decision.

## 4. What we know (details, figures and caveats in the reports)

**The WS tests of 5-6 Oct are in `reports/2026-10-06-options/README.md`, and P1's submitted paper and final data in its
§12** (summaries at the top of this file). What follows is the evidence from before them, on P1's data as of 5 Oct;
P1's final data confirms its direction (decode-bound everywhere, more capacity pressure after the re-runs), and the
absolute numbers below are not yet redone on it.

**Kept state is worth little on P1's agents, drone or traffic** (P1's measured runs, one agent per device;
`reports/2026-10-05-p1-repo` §2).
- **Drone:** the cache saved 0.2–0.5% of LLM time on Thor; the ceiling P/(P+r·O) is 0.9–2.6% on Thor and
  3.5% on Orin 32 E4B (Devstral 23%; pooled 2.1% and 0.6% at r ≈ 67 in the earlier reports; per task 0.3–14%). Prompts are rebuilt per call.
- **Traffic:** contexts only grow (every prompt repeats the previous one; up to 106K tokens on Thor; 56–82%
  of prompt tokens from cache), but the cache saved 1.1–4.2% of LLM time and the ceiling at each
  configuration's own r (117–312) is 1.7–7.2% (Qwen2.5-VL, which writes 107 tokens per call: 15% and 26%).
  Outputs are a median 424–999 tokens per call; idle gaps a median 1.0–2.8 s; the paused share of KV
  memory-time is 1–17%. No prefix is shared between sessions: the system prompt opens with the current time.
- **Energy by phase:** prefill is 0.7–3.4% of board energy everywhere except Devstral (21%) and Qwen2.5-VL (14%);
  decode in capped calls takes 38–69% of board energy on Thor gemma (traffic, drone), 33% on Orin 32 E4B traffic,
  0–19% elsewhere.
- **Devstral** (drone, Orin 64) is the one drone cell where retention could matter: no thinking, prefill 20%
  of LLM time, the prefix cache off (57% of each prompt repeats an earlier one; worth ~8.7% if it worked).

**The vision tool fills the KV pool at one agent per device** (§3 of the report).
- `ask_vlm` sends 8–45 concurrent requests (median 8–23) to the agent's own SGLang server.
- On Orin 64 gemma (12.4K-token pool) the burst reaches 99.5% of the pool and evicts the paused agent's
  context: all 62 following calls miss (90% of the prefix recomputed, 0.6% of LLM time). Orin 32 E4B: 12 of
  50. Thor: none. The live case for option D, but small because prefill is cheap.

**A memory controller does not beat SGLang's default, drone or traffic** (simulated).
- **Drone** (2026-10-03, 1–16 drones, 455 cells): no policy beats the best fixed rule by more than 9.9%;
  keeping state is worth 19–29% at 16 step-wise drones but the radix cache already keeps it; under tight
  memory the loss is capacity (an FP8 KV cache recovers 10–34%).
- **Traffic** (2026-10-05, 1–8 agents, 6 configurations at their real KV pools, ½/1/2×): the best of 12
  policies beats the default by at most 2.4% in all 48 cells without failures. On the Orins capacity binds:
  the gap to unlimited memory reaches 33–64% at 8 agents, energy per completed task stops falling after 2–4
  agents, and doubling the pool cuts it 31–46%. On Thor the pool is ample (2.2× gemma, 3.8× granite from 1
  to 8 agents).

**Capped calls are where the energy goes; drone = loops, traffic = repeated caps** (report §5).
- **Drone:** capped calls take 71% of LLM time on Thor (both agents). Our online detector flags 121 of 122
  Reflexion capped calls (P1's 144th run included) and 127 of 127 tool-calling calls capped at 32,768, and
  none of the long finished calls. The online loop stop saves 43.5% (Reflexion) / 35.7% (tool calling) of
  board energy (upper bound) and stops no finished call; P1's first-cap rule saves 50.2% / 63.1% but loses
  22 / 16 passing runs.
- **Traffic:** where text survives, few capped calls loop (16 of 21 on Thor gemma, 4 of 29 on Thor granite);
  on gemma most caps hit inside a tool call and the text is lost (137 of 158 on Thor). The waste is the
  retry: 121 of Thor gemma's 158 capped calls follow a capped call. Stopping a run at its second
  consecutive cap saves 27% (Thor gemma, 1 completed run lost) and 25% (Orin 32 E4B, 7 lost).
- **Orin 64's caps are the context guard** (budgets lowered near the window), not runaway decoding.
- **The likely cause of drone loops is greedy decoding** (P1 runs temperature 0; on the WS Qwen3.5 ran away
  only under greedy decoding). **Measured 6 Oct (A-E1):** on a 4-bit GGUF of P1's 26B, greedy loops on 23 of 30
  of P1's loop prompts and Gemma's default sampling on none.

**Earlier results that still stand.**
- **Two drone agents** (same 12 tasks, Thor): tool calling passes 67% at 231 kJ per success, Reflexion 87%
  at 79 kJ (2.9×).
- **P1's drone KV evictions are a side effect of the loops** (46 of the 48 evicting Reflexion runs
  contain a capped call, all 144 runs; 45 of 47 in our 143-run copy).
- **A step-wise agent on P1's delivery tasks keeps its steps short** (WS, 108 missions): median 55–99 output
  tokens after a tool result; ceiling at r = 67: 20–72% of mission LLM time, private state 3–16%; 72%
  deliver everything but only 27% pass the strict check.
- **Agent design is the big lever** (Thor costs, P1's D1–D3): P1's Reflexion 219–499 kJ per success
  (measured) against 22–68 kJ for the step-wise agent (projected): 5–13× (0.9–9.6× under the strict
  check); 4–16 step-wise drones per Thor against 2.
- **aerogen** (WS): kept state saves 33% of LLM time on its own tasks (12% private); 8 sessions per GPU
  used 2.2× less energy per passed mission than 1.
- **WS costs** (K2, one A5000): prefill 4,106 tokens/s at ~0.05 J/token; decode 5.36 J/token at batch 1,
  0.38 J at 16; idle 10–20 W.
- **P1's measurements quoted from its paper/deck:** no thermal throttling in 434 h (peak 81.3 °C; as of 5 Oct);
  repeat divergence at temperature 0 traced to inputs (timestamp, simulator noise), except gemma-E4B on
  the Orin 32 (inference).

**Track B** synthesis (`review/systems/README.md`): F1–F10 hold; traffic extends F1, F3 (waits of seconds)
and F4; H4 has a live but small case (the vision tool).

## 5. Still-valid notes from the 2026-09-30 audit

- **The CLGSCE port** (needed only if P1's agents run on the WS) is mostly done in legacy. Left to do:
  get the 2 files that changed on the Thor on 23 Sep (`clgsce_mcp_server.py`, `clgsce_subagents.py`; with
  the Thor off-limits they must come from P1); patch the hard-coded RPC port 41451; replace P1's
  `pkill -x thor_headless` reset. `advanced.txt` and P1's harness are now in `data/p1_aeroeval_src/`. P1's
  repository holds the agents' data but not their code.
- **What P1's traces allow us to replay** (checked 5 Oct):
  - Drone: every `llm_calls` record holds the full prompt `messages`, the reasoning and the output, with the
    decoding settings (temperature 0, top_k 1, seed 42). All 265 capped Thor calls have their prompts (122
    Reflexion in the repository, 143 tool calling in `data/p1_thor_toolcalling/`), so they replay exactly.
  - Traffic: the trace keeps the system prompt, the question and the assistant turns, but tool results are
    empty and the 7 tool definitions are absent. Traffic replays only by token counts (synthetic text). The
    traffic agent's code is not in the repository.
- **P1-style sessions (40–55K tokens) do not fit a one-GPU pool.** They need tp2, a lower `max_tokens`, or
  FP8 KV.
- **P1's AeroEval agent, task sets and Reflexion harness** are in `data/p1_aeroeval_src/` (read-only copies,
  2026-10-01).

## 6. Next steps

1. **Mon 12 Oct, the professor meeting:** take the direction decision (D12) with the deck (v2.3; sections 8 and 11)
   and CMP-2 (§9 lean, §10 questions, §12 P1's submission). Record the outcome as a decision (next free ID: D19), then
   rewrite master-plan M3–M5 and `planning/OPTIONS_PLAN.md`'s G2 for it.
2. **Agree the split with P1** (through Sandesh and P1's mentor): who runs MB4 (overlaps A-E1/A-E2) and MB5 (overlaps
   CAP-E1), and whether P1 gets the sampling result (A-E1) and the step-wise result (B) now that its paper is in.
3. **When the WS is back:** pull `~/jouleserve-ws` and `~/work/p1/edge-agent-bench` (to `0cc2311a`); make
   `analysis/p1_repo.py` apply P1's supersede rule (latest re-run per task, an overflowed original kept); then redo
   RET-E1, CAP-E1 and `traffic_sim` on the clean Orin traffic sessions (with the re-runs' smaller pools: Orin 32 granite
   25,358, E4B 66,376 tokens), rerun `p1_opportunity`, `p1_caps`, `p1_repo_figures` on the final data, and refresh
   CMP-2, the evidence doc, the deck and this file. Also check why granite and E4B evict KV on the Orins at one agent
   (52-68% of drone runs).
4. **If A (decode-side energy):** sampling vs greedy is answered on a 4-bit stand-in on the WS (A-E1: sampling
   removes the loops); repeat it on P1's bf16 26B on a Jetson when the devices come back. Still open: a retry policy for
   traffic's dropped tool calls (A-E4), the decode guard inside a live agent loop, and the split with P1, whose paper
   reports the loop finding offline and leaves an online policy to "separate evaluation".
5. **If CAP:** the levers P1 lists as untested (FP8 KV, shorter tool schemas, bounded outputs) measured by energy per
   success with several agents per device; FP8 quality; Gemma-4 FP8 KV on an Orin (P1 ran it with SGLang 0.5.16).
6. **If D (memory that changes over time):** the vision-burst replay is done (D-E2: the eviction reproduces; pinning
   plus a burst cap costs 11% more energy than recomputing at one agent, and at 4 agents the best policy, pinning
   alone, is 3.8% below the default, inside the 5% rule). P1 now takes the vision tool as the agent's own model
   (correction 1, in part). What is left: real unified-memory contention on a device.
7. **WS experiments as first offered on 5 Oct (W1-W9).** Superseded by `planning/OPTIONS_PLAN.md`; its §10 maps the
   labels to the plan's task IDs. W1 (sampling vs greedy), W2 (stop and retry), W3 (live trace replayer), W4 (vision
   burst), W6 (FP8 vs bf16 KV) and part of W9 (τ²-bench) ran as A-E1, A-E2, RET-E1, D-E2, CAP-E1 and C-E1. Not run:
   W5 (decode batching on Gemma-4 vs dense models), W7 (P1's CLGSCE agent live on the WS; needs 2 files from P1 and
   Sandesh's OK), W8 (thinking budget against energy per success).

## 7. Open questions for Sandesh

1. The outcome of the professor meeting (12 Oct): direction and scope (A, B, C, D, CAP), the go/no-go thresholds
   (D4), and `N_edge`.
2. The split with P1 (MB4, MB5) and whether to hand P1 the sampling and step-wise results (CMP-2 §10 Q5); whether to
   offer the online loop stop to P1 or keep it for P5.
3. Review of CMP-2: anything to change after the meeting?
4. The P1 mentor's answers to the task overview's §9: which 8 AeroEval tasks; whether a step-wise paradigm
   is in P1's scope; whether P5 may run P1's AeroEval tasks with a step-wise agent; drones per edge box.
5. Timeline: when the Jetsons return to P5 now that P1 has submitted, and the ISP milestones.
6. When the Thor ban lifts (since 5 Oct).

## 8. Resume checklist for a new session

1. Read `AGENTS.md`, then this file.
2. `git status`, `git log --oneline -5`. Before any `git push`, check the visibility:
   `gh repo view saisandeshk/jouleserve-ws --json visibility` (if `gh` is logged out: `curl -s https://api.github.com/repos/saisandeshk/jouleserve-ws`).
3. P1's data: `git -C data/edge-agent-bench log --oneline -3` (read-only; do not pull without Sandesh; `0cc2311a` is
   P1's submitted state).
4. WS, if reachable: `nvidia-smi; tmux ls; ls ~/work/runs`; copy runs with
   `rsync -a saisandeshk@10.24.32.174:~/work/runs/ data/ws_runs/`.
5. Thor: **off-limits** until Sandesh says otherwise (5 Oct). Use the repository and the local copies.
6. Deck work: check `data/p5deck/` exists (else restore it from the artifact with `Artifact` read), and
   that the renderer finds a browser.

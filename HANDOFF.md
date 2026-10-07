# HANDOFF — jouleserve-ws

**Last updated:** 2026-10-07 (IST), afternoon: a **P1 audit for P1** (not P5 work), below. Before it, the same morning,
a consistency pass over the docs. Latest P5 work (5-6 Oct): **G1 of the options plan is done**; reported to Sandesh, who
is reviewing it. At Sandesh's request every doc was brought up to date (artifact revisions in §2).
- **P1 audit (7 Oct, for Sandesh's P1-drone mentor and the professor's review of P1's paper):** private Claude Doc
  "P1 drone audit and review check (EdgeAgentBench @ f6aabe4)",
  https://claude.ai/code/artifact/813c66c9-0521-4430-91e6-60be5a3e0c4d, with a git-ignored local copy in
  `reports/2026-10-07-p1-audit/` (never pushed: P1's paper is double-blind until 10 Oct). Scripts and tables on the WS
  in `~/work/p1audit/`. It checks every item of the professor's review (traffic items too) and all 1,296 drone runs,
  with a prioritised re-run/fix list. Its findings stay in the private doc, not in this public repo.
- **Caveat on P5's Orin traffic results (7 Oct; Sandesh agreed to flag now, refresh after P1 freezes):** 36-70% of P1's
  Orin traffic runs hit a broken tool (missing sandbox image, full disk) and use 1.7-4.2x the energy of clean runs of
  the same task. RET-E1 and CAP-E1 replayed 59-88% faulted Orin 32 granite sessions; `traffic_sim` uses every run;
  D-E2 is barely exposed (4-9%). The sim-vs-live anchor stands; the absolute Orin capacity numbers (CAP's -62%, the
  knee, -31-46% from doubling the pool) are redone once P1's re-runs land. Flagged in CMP-2 (top and §9), the evidence
  doc (rev 139 + repo copy) and the deck (v2.2). The full refresh of every P5 doc waits until P1's data freezes.
- **P1 pulled (7 Oct, Sandesh's request):** both clones (local and WS `~/work/p1/edge-agent-bench`, now on `main`, no
  longer pinned) are at `f6aabe4`. That commit moved the drone sweeps to `drones/edge_devices/final_sweep_*` (plus
  `rtx_6000_pro/` and `baseline_models/`); `analysis/p1_repo.py` and `loop_prompts.py` follow the new layout (7 Oct;
  Thor drone tool calling now read from P1's repository, all 144 runs, so a refreshed cache differs from 5-6 Oct).
- **The comparison doc** (G1's output): [`reports/2026-10-06-options/README.md`](reports/2026-10-06-options/README.md),
  CMP-2. Every option A, B, C, D, CAP (and RET, the negative result) with the same template, criteria K1-K8, this
  week's evidence, figures, our lean stated once (§9) and questions for the professor (§10). Task status in
  [`planning/TRACKER.md`](planning/TRACKER.md) (plan [`planning/OPTIONS_PLAN.md`](planning/OPTIONS_PLAN.md) v1.1).
  Its results were merged into the evidence doc, the teaching guide and the deck on 6 Oct; the comparison itself
  stays a separate doc.
- **What this week found** (details in the doc):
  - A: P1's drone runaways are a decoding setting: on P1's 26B (4-bit, llama.cpp) greedy decoding loops on 23/30 of
    P1's loop prompts, Gemma's default sampling on 0/30. An online stop + one resample recovers 17/17 looping calls
    at 60% of the capped cost; nudging fails. Traffic's repeated capped tool calls hold 31-33% of gemma traffic LLM
    energy; batching cuts energy per token 13x at batch 16.
  - B: P1's E4B as a step-wise agent writes a median 63-68 tokens after a tool result; 9/11 strict passes greedy;
    11-19x less energy per strict success than P1's Reflexion (projected).
  - C: tau2-bench with thinking on: kept state worth 7.5-9.9% of LLM time at E4B's Jetson price; thinking off: 25%.
  - D: the vision-burst eviction reproduces live; pinning + a burst cap stop it but cost 11% more energy.
  - CAP: FP8 KV doubles granite's pool and cuts energy per session 62% at 8 agents (live; quality unmeasured); a 5x
    pool cuts it 2.4x at 4 agents; Gemma-4 FP8 KV cannot run on Ampere (the Orins) in SGLang 0.5.20.
  - RET: the simulator behind "no policy beats the default" holds live within 14% (RET-E1, granite traffic at P1's
    Orin 32 pool, 1-8 agents); at 8 agents the default keeps no state at all (0 of 102 calls hit the cache).
  - Our lean (doc §9): CAP with A's safety net, as multi-agent consolidation on one edge box; hand the sampling fix
    and the step-wise result to P1.
- **Built for G2** (shared base and two option prototypes): gateway (`jsw/gateway/`, policy hooks, tool-tagged routes,
  pythonic tool-call fallback), streaming loop detector, decode guard (A-P1), burst-aware memory policy (D-P1), trace
  replayer (`jsw/workloads/replay.py`), P1-prompt replayer (`loop_replay.py`), runner/manifests, calibration
  (`jsw/costs/calibrate2.py`), launchers for P1's models (`env/launch_model.sh`, `env/launch_llamacpp.sh`).
- **WS:** all runs in `~/work/runs/` (copies of the analyses' JSONs and figures are in the repo); servers torn down
  after RET-E1. Analyses run on the WS in `~/work/venv-analysis` (`python -m analysis.<name>`).
- **P1's data is on the WS** (Sandesh's permission, 6 Oct): `~/work/p1/` (GitHub clone, at `f6aabe4` since 7 Oct; tool-calling
  copy with matching SHA-256).
- **Laptop RAM is unreliable** (5 Oct): three P1 files read back with bit flips from the page cache (disk copies
  intact), plus power cuts and restarts. Process data on the WS (ECC); commit often. The 5 Oct analyses were
  re-run on the WS: byte-identical outputs.
- **The WS is back** (since 5 Oct 10:52; P5's own machine with full control).
- **`NOTES_FOR_P1.md` was sent** to P1 by Sandesh (5 Oct). P1's reply will come through Sandesh.
- **The Thor is off-limits** until Sandesh says otherwise (5 Oct): no access at all, not even read-only.
- **P1's repository arrived (Mon 5 Oct).** Sandesh cloned it to `data/edge-agent-bench`. We mapped it,
  reran our analyses on its drone and traffic data
  ([`reports/2026-10-05-p1-repo/README.md`](reports/2026-10-05-p1-repo/README.md)), and wrote five corrections
  for P1 ([`NOTES_FOR_P1.md`](reports/2026-10-05-p1-repo/NOTES_FOR_P1.md)).
- **Every doc was updated with it** (Sandesh asked: local docs, HANDOFF, both Claude Docs and the deck; traffic
  included; P1's figures allowed in the private artifacts; more plots and diagrams). See §2 for the state of
  each.
- **The professor meeting planned for Mon 5 Oct is postponed** (P1's deadline is Sat 10 Oct, and other lab
  projects are due too). No new date is set, so the direction decision (D12) stays open.

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
  physical tool waits. P1 measured no thermal throttling at room temperature (434 h), so thermal state is out
  unless hot-enclosure runs show otherwise.
- **What the evidence now says** (§4): on P1's workloads, drone and traffic, a retention or admission
  controller is not a contribution; the energy is in runaway decodes, and the edge effect with large numbers
  is capacity. The direction is open (§6).
- **Resources:** the edge devices are with P1 until their deadline (Sat 2026-10-10). P5 has the 2×A5000
  workstation, under its full control (back since 5 Oct, see below).

## 2. Situation as of 2026-10-06

- **P1's repository** (`dream-lab/edge-agent-bench`): read-only clone in `data/edge-agent-bench`
  (git-ignored; HEAD `f6aabe4`, pulled 7 Oct at Sandesh's request; our analyses of 5-6 Oct used `3c47ebc`). Its remote is
  P1's GitHub: never push, never write in it, never run its `make` targets in place (`AGENTS.md` §4).
  - **Data:** 2,055 runs, 434 h, 21.3 kWh. 3 graded drone cells (Thor gemma-26B Reflexion, 144 runs; Orin 64
    Devstral-24B tool calling, 144; Orin 32 gemma-E4B tool calling, 108) and 8 traffic cells (1,659 runs,
    ungraded). Thor drone tool calling is **not** in the repository: we keep using our copy
    `data/p1_thor_toolcalling/` (104 runs).
  - **Our loader** `analysis/p1_repo.py` reads all 12 configurations (cache in `data/p1_cache/`); the
    analyses are `p1_opportunity.py`, `p1_caps.py`, `traffic_sim.py`, `p1_repo_figures.py`.
  - **People:** P1's analysis and paper are written by Mayank Arya (`mayankarya`, also aerogen's author);
    drone runs by Aayushi, traffic runs by Priyanshu.
  - **P1's paper** ("Measuring the Task, Not the Trajectory", SIGMETRICS 2027, due Sat 10 Oct 17:30 IST):
    claims the loop finding (offline detector; "stop or retry at the first capped call", a 50.2% bound that
    loses 22 runs), the capacity finding (window overflows on the Orins) and the vision-tool energy finding.
    It assumes one request in flight, **dropped its early-abort plan** ("out of scope"), and deferred its
    KV-pool sweep (E4) and warm-cache arm (E5), which overlap P5.
  - **Corrections for P1** (`NOTES_FOR_P1.md`, **sent by Sandesh on 5 Oct**; P1 is reviewing): (1) `ask_vlm` is a
    burst of requests to the agent's own server, not a second model; (2) their loop threshold misses
    long-period loops (94 vs our 121 of 122); (3) the drone Orin 32 caps are 1,024-token evaluator calls;
    (4) Orin 64's context guard truncates calls their 8,000-token rule does not count; (5) Devstral's prefix
    cache is off (about 9% of its LLM time).
    - **Caveat on (1):** P1's microbenchmark (`analysis/microbench/mb6_vlm_tool.py` in P1's repository, not ours)
      calls "the vision-language model behind `ask_vlm`" at its own endpoint, run "with the agent model's server
      running and once without", so P1 thinks of it as a separate server. Our evidence is only the agent server's
      running-request counter. Both may hold where the agent model reads images (gemma, Qwen3.6; granite has no
      image tasks). Wait for P1's answer before building on (1).
- **The professor meeting is postponed** (no new date). Nothing has been shown to the professor yet.
- **Pushed to the public repo** (2026-10-05, Sandesh's choice after being asked about visibility).
  - `saisandeshk/jouleserve-ws` is public and now holds P1's unpublished numbers in `reports/`; all local
    commits up to the task-3 work are on `origin/main`.
  - `gh` is not logged in on this machine (HTTP 401); the public API (`curl
    https://api.github.com/repos/saisandeshk/jouleserve-ws`) shows the visibility.
  - P1's own figures (deck and repository) are kept out of git: `reports/*/p1_figures/` is git-ignored.
- **Docs updated 2026-10-05** (task 3): the evidence Claude Doc and its repo copy
  [`reports/2026-10-02-p5-evidence/README.md`](reports/2026-10-02-p5-evidence/README.md), the teaching guide
  Claude Doc, the deck (v2.0), this file, `AGENTS.md`, both plans, the review index and update notes in the
  dated reports. Revisions and slide counts: see "Artifacts" below.
- **Artifacts** (all private until Sandesh shares them from their Share menu):
  - **Evidence doc**, "JouleServe (P5): drone and traffic evidence, and options":
    https://claude.ai/code/artifact/474eee56-2e2f-44f9-8b97-f7bb51b588c7 (revision 139; repo copy
    `reports/2026-10-02-p5-evidence/README.md`, keep in sync). 5 diagrams, a native chart of kept-state value, our
    figures and P1's s394/s396/s398/s400/s401/s405 and window-budget figure. **6 Oct (rev 127-138):** the section
    "Tested on the workstation, 5-6 Oct" (results table, A-E1 and RET-E1 figures), the options table with CAP, our
    lean (CAP with A's safety net; it was A until 5 Oct), decisions, next steps and caveats updated. **7 Oct (rev 139):**
    a caveat after that section: P1's Orin traffic tool failures inflate the sessions our Orin results replay.
  - **Teaching guide**, "JouleServe (P5): a teaching guide":
    https://claude.ai/code/artifact/36c2319c-b866-44f2-8dcf-42c02cdfd18c (revision 165; no repo copy). Chapter 18
    (the traffic workload), §11 memory on a Jetson, §16 P1's repository, §19.5–19.7 traffic evidence. **6 Oct:** new
    chapter 21 (testing the options on the workstation: greedy vs sampling, stop and retry, the replayer, the
    simulator check, FP8 KV, thinking and tau2, the vision burst, NVML energy), chapter 20 rewritten (five options,
    the new lean), §12 and §15 status refreshed, 8 self-test questions and 10 glossary terms added; self-test and
    glossary are now 22 and 23. One open comment in it (ours) asks how many drones per device to plan for.
  - **Reference deck** (Slides artifact): https://claude.ai/artifact/QrFXoAwDssEtftYgGnxVm8, v2.2 (artifact
    version 13, 137 slides). v2.2 (7 Oct): the Orin traffic tool-fault caveat on `opt-cap`, and the changelog. v2.1 (6 Oct): 5 new slides (`find-ws-tests`, `find-ws-sampling`, `find-ws-anchor`,
    `find-ws-tau2-burst`, `opt-cap`), options, decision tree, lean, status, plan, log and related work
    (`rw-reasoning` filled) updated.
    - The single main reference, updated weekly: a new log slide (section 13, newest first), the
      at-a-glance slide and the changelog; matured results move into Findings.
    - **Style:** IBM Plex Sans, off-white with one blue accent, dark dividers; body text 28 px (14 pt),
      small text 24 px (12 pt).
    - **Slide sources:** a working copy lives in `data/p5deck/` (git-ignored; restored from the artifact
      on 2026-10-05 after a reboot wiped `/tmp`). Before editing in a new session, re-read the changed
      files from the artifact if someone may have edited it in the browser.
    - **Figures:** uploaded as artifact assets; the blob-id → local-file map is
      `data/p5deck/blobs_2026-10-05.json`, `blobs_2026-10-06.json` and `env/render_slides.py`'s `BLOBS`.
    - **Visual check** (Sandesh approved it): `python3 env/render_slides.py data/p5deck <out> [ids]`. It
      uses the Playwright headless shell if present, else Brave (`/opt/brave.com/brave/brave`) headless; it
      is approximate and flags overflow and overlaps.
- **WS** (P5's own machine with full control; it is **not** one of P1's "workstation" lanes): back since a
  reboot on 5 Oct 10:52.
  - **6 Oct 08:40: idle** (GPUs at 47/15 MiB, no tmux server, no stale lock files). 68 run directories in
    `~/work/runs/`, backed up to local `data/ws_runs/` (SHA-256 checked, 2,343 files).
  - Clone `~/jouleserve-ws` pulled to the latest `main`; `~/jsw-dev` is the synced dev copy (`env/sync_ws.sh`,
    stamp in `~/jsw-dev/REVISION`).
  - Models on disk (pinned, offline): gemma-4-E4B, granite-4.2-8b, the 4-bit 26B checkpoints that do not run in
    SGLang (derived text-only copies in `~/work/models/`), and the 26B GGUF (Hugging Face cache, unsloth) served by
    `~/work/llama.cpp`; K2 and Qwen3.5 from before. Recipes:
    `AGENTS.md` §6c.
- **Thor: off-limits** (Sandesh, 5 Oct): no ssh at all, not even read-only, until Sandesh says otherwise.
  Use P1's repository and our local copies.
- **P1's schedule** (P1's docs, 3 Oct): thor-1 runs gemma tool calling (99/144 on 3 Oct), then granite, then
  Devstral, to about Thu 8 Oct; P1's last runs end Thu 8 Oct ~16:40; some Orins are free from Tue 6 Oct "for
  re-runs". After the deadline nothing is written down.
- **Sandesh's** earlier idea for the next step (1 Oct) is superseded by events; they choose among the WS
  options in §6 instead.

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
| Slide renderer | `env/render_slides.py` | Visual check of the deck's slide files |
| Launch / queues | `env/launch_k2_tp1.sh`, `env/launch_qwen35_tp1.sh`, `env/queue*.sh` | K2 pinned to revision `f846b1e` |
| **Options work (5-6 Oct)** | `jsw/gateway/`, `jsw/policies/` (loop detector, decode guard, burst memory), `jsw/workloads/replay.py`, `loop_replay.py`, `jsw/runner/run.py`, `jsw/costs/calibrate2.py`, `env/launch_model.sh`, `env/launch_llamacpp.sh`, `analysis/{a_e1,a_e2,a_e4,b_e1,b_e2,c_e1,d_e2,ret_e1,cap_e1,options_figures}.py` | The shared base and option prototypes of `planning/OPTIONS_PLAN.md`; tests in `tests/` (run with the legacy venv: `python -m tests.<name>`) |

Not built: a Jetson telemetry adapter, the CLGSCE port, policies inside a live agent loop. Master plan M3–M5 should
not be built as planned: rewrite them after the direction decision.

## 4. What we know (details, figures and caveats in the reports)

**This week's results (5-6 Oct) are in `reports/2026-10-06-options/README.md`** (summary at the top of this file);
what follows is the evidence from before them, still valid.

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
- **P1's measurements quoted from its paper/deck:** no thermal throttling in 434 h (peak 81.3 °C);
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

1. **G1 is done; wait for Sandesh's review of the comparison doc** (`reports/2026-10-06-options/README.md`). Its
   results are already merged into the evidence doc, the teaching guide and the deck (6 Oct); fold in any review
   changes there too. Then, as Sandesh decides: start G2's WS versions of the options (`planning/TRACKER.md`, G2
   table); optional re-run of B-E1's sampled arm with the fixed gateway (removes the format-failure caveat); pass on
   P1's reply to `NOTES_FOR_P1.md` when it comes.
2. **When the professor meeting is rescheduled:** take the direction decision (D12) with the deck (section
   11) and the evidence doc. Then rewrite master-plan M3–M5 for it.
3. **When P1 pushes more data** (Thor drone tool calling, granite/Devstral drone, traffic grades): `git pull`
   in `data/edge-agent-bench` only if Sandesh agrees (it is P1's clone), then rerun `analysis.p1_repo`
   (`load(key, refresh=True)`), `p1_opportunity`, `p1_caps`, `traffic_sim`, `p1_repo_figures`, and update
   the report, the docs and the deck. **Pulled 7 Oct** (`f6aabe4`): new data includes the Thor drone tool-calling
   sweep, an Orin 32 Qwen2.5-VL and an RTX PRO 6000 gemma drone sweep, cloud baselines and graded traffic. The loader
   already follows the new layout. Rerun after P1's Orin traffic re-runs land (the 7 Oct caveat), then refresh every doc.
4. **If A (decode-side energy):** sampling vs greedy is answered on a 4-bit stand-in on the WS (A-E1: sampling
   removes the loops); repeat it on P1's bf16 26B on a Jetson after 10 Oct. Still open: a retry policy for traffic's
   dropped tool calls (A-E4), the decode guard inside a live agent loop, and the split with P1, whose paper claims
   the loop finding.
5. **If D (memory that changes over time):** the vision-burst replay is done (D-E2: the eviction reproduces; pinning
   plus a burst cap costs 11% more energy than recomputing at one agent, and at 4 agents the best policy, pinning
   alone, is 3.8% below the default, inside the 5% rule). What is left: P1's answer on which server `ask_vlm` calls,
   and real unified-memory contention on a device.
6. **WS experiments.** Superseded by `planning/OPTIONS_PLAN.md`; its §10 maps these labels to the plan's task
   IDs. The options as first offered on 5 Oct, with their usefulness as rated then:
   - **W1 (A, highest):** do Gemma-4's loops survive sampling? Replay the 265 capped Thor prompts plus finished
     long calls as controls, under P1's greedy settings and the model card's sampling. Needs a quantized
     gemma-4-26B-A4B (smoke test first); the greedy arm must loop on the WS for the comparison to count.
   - **W2 (A, high):** stop and retry. Abort where the online detector fires, retry, and check whether the
     retry finishes with a usable program, and at what cost. An increment on W1.
   - **W3 (both, high):** a live trace replayer. It plays P1's recorded runs (token counts, prefix
     structure, tool gaps) as N agents on a capped pool, to anchor the simulators' "default within 2.4%" and
     the capacity knee. It needs no agent code, so it also runs on a Jetson after 10 Oct.
   - **W4 (D, medium):** a vision burst on a 12.4K pool, built on W3. Compare the default, pinning the paused
     context and admitting the burst at lower concurrency, then N agents.
   - **W5 (calibration, medium-low):** decode batching on Gemma-4 (MoE) vs dense models; Qwen3.5 energy
     calibration folded in.
   - **W6 (capacity, medium):** FP8 vs bf16 KV, comparing pool size against loop and finish rates.
   - **W7 (A, after D12):** P1's CLGSCE agent live on the WS. Needs the 2 files from P1 and Sandesh's OK.
   - **W8 (low now):** thinking budget against energy per success. **W9 (B/C):** long step-wise missions,
     τ²-bench.
   - Suggested order: W1+W2 on GPU0 and W3 on GPU1 in parallel, then W4. One Gemma set-up serves W1, W2, W4
     and W5.

## 7. Open questions for Sandesh

1. Review of the G1 comparison doc (CMP-2): is it even-handed, is anything missing before the professor sees it,
   and may P1 get the sampling result (A-E1) and the step-wise result (B) before their deadline (doc §10 Q5)?
2. P1's reply to `NOTES_FOR_P1.md` (sent 5 Oct), especially on `ask_vlm`'s server. And: offer the online
   loop stop to P1's paper, or keep it for P5?
3. When will the professor meeting be rescheduled?
4. The P1 mentor's answers to the task overview's §9: which 8 AeroEval tasks; whether a step-wise paradigm
   is in P1's scope; whether P5 may run P1's AeroEval tasks with a step-wise agent; drones per edge box.
5. Direction and scope (A–D), the go/no-go thresholds (D4), and `N_edge`.
6. Timeline: when the devices return to P5 after 2026-10-10, and the ISP milestones.

## 8. Resume checklist for a new session

1. Read `AGENTS.md`, then this file.
2. `git status`, `git log --oneline -5`. Before any `git push`, check the visibility:
   `gh repo view saisandeshk/jouleserve-ws --json visibility` (if `gh` is logged out: `curl -s https://api.github.com/repos/saisandeshk/jouleserve-ws`).
3. P1's data: `git -C data/edge-agent-bench log --oneline -3` (read-only; do not pull without Sandesh).
4. WS, if reachable: `nvidia-smi; tmux ls; ls ~/work/runs`; copy runs with
   `rsync -a saisandeshk@10.24.32.174:~/work/runs/ data/ws_runs/`.
5. Thor: **off-limits** until Sandesh says otherwise (5 Oct). Use the repository and the local copies.
6. Deck work: check `data/p5deck/` exists (else restore it from the artifact with `Artifact` read), and
   that the renderer finds a browser.

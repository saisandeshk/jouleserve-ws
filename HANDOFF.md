# HANDOFF — jouleserve-ws

**Last updated:** 2026-10-05 (IST). Latest work:
- **P1's repository arrived (Mon 5 Oct).** Sandesh cloned it to `data/edge-agent-bench`. We mapped it,
  reran our analyses on its drone and traffic data
  ([`reports/2026-10-05-p1-repo/README.md`](reports/2026-10-05-p1-repo/README.md)), and wrote five corrections
  for P1 ([`NOTES_FOR_P1.md`](reports/2026-10-05-p1-repo/NOTES_FOR_P1.md), not sent).
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
  workstation (unreachable since 2 Oct, see below).

## 2. Situation as of 2026-10-05

- **P1's repository** (`dream-lab/edge-agent-bench`): read-only clone in `data/edge-agent-bench`
  (git-ignored; HEAD `3c47ebc`, Sun 4 Oct 19:02). Its remote is P1's GitHub: never push, never write in it,
  never run its `make` targets in place (`AGENTS.md` §4).
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
  - **Corrections for P1** (`NOTES_FOR_P1.md`, for Sandesh to forward before 10 Oct): (1) `ask_vlm` is a
    burst of requests to the agent's own server, not a second model; (2) their loop threshold misses
    long-period loops (94 vs our 121 of 122); (3) the drone Orin 32 caps are 1,024-token evaluator calls;
    (4) Orin 64's context guard truncates calls their 8,000-token rule does not count; (5) Devstral's prefix
    cache is off (about 9% of its LLM time).
- **The professor meeting is postponed** (no new date). Nothing has been shown to the professor yet.
- **Not pushed: our GitHub repo is PUBLIC.**
  - `gh repo view` reported `saisandeshk/jouleserve-ws` as public; it holds P1's unpublished numbers in
    `reports/`. All commits since 2026-10-04 are local only. Sandesh decides on visibility (private is
    advisable before P1's double-blind submission) and then pushes.
  - P1's own figures (deck and repository) are kept out of git: `reports/*/p1_figures/` is git-ignored.
- **Docs updated 2026-10-05** (task 3): the evidence Claude Doc and its repo copy
  [`reports/2026-10-02-p5-evidence/README.md`](reports/2026-10-02-p5-evidence/README.md), the teaching guide
  Claude Doc, the deck (v2.0), this file, `AGENTS.md`, both plans, the review index and update notes in the
  dated reports. Revisions and slide counts: see "Artifacts" below.
- **Artifacts** (all private until Sandesh shares them from their Share menu):
  - **Evidence doc**, "JouleServe (P5): drone and traffic evidence, and options":
    https://claude.ai/code/artifact/474eee56-2e2f-44f9-8b97-f7bb51b588c7 (repo copy above; keep in sync).
  - **Teaching guide**, "JouleServe (P5): a teaching guide":
    https://claude.ai/code/artifact/36c2319c-b866-44f2-8dcf-42c02cdfd18c (no repo copy). One open comment
    in it (ours) asks how many drones per device to plan for.
  - **Reference deck** (Slides artifact): https://claude.ai/artifact/QrFXoAwDssEtftYgGnxVm8, v2.0.
    - The single main reference, updated weekly: a new log slide (section 13, newest first), the
      at-a-glance slide and the changelog; matured results move into Findings.
    - **Style:** IBM Plex Sans, off-white with one blue accent, dark dividers; body text 28 px (14 pt),
      small text 24 px (12 pt).
    - **Slide sources:** a working copy lives in `data/p5deck/` (git-ignored; restored from the artifact
      on 2026-10-05 after a reboot wiped `/tmp`). Before editing in a new session, re-read the changed
      files from the artifact if someone may have edited it in the browser.
    - **Figures:** uploaded as artifact assets; the blob-id → local-file map is
      `data/p5deck/blobs_2026-10-05.json` and `env/render_slides.py`'s `BLOBS`.
    - **Visual check** (Sandesh approved it): `python3 env/render_slides.py data/p5deck <out> [ids]`. It
      uses the Playwright headless shell if present, else Brave (`/opt/brave.com/brave/brave`) headless; it
      is approximate and flags overflow and overlaps.
    - Reasoning-length control (slide `rw-reasoning`) is still a placeholder: that literature is unread.
- **WS:** unreachable since 2026-10-02 ~23:00 (last checked 2026-10-03 16:50; not checked since, at
  Sandesh's request). P1's schedule shows four "workstation" lanes (Sol/Terra runs from Sun 4 Oct): ask
  Sandesh whether ours is one.
- **P1's schedule** (P1's docs, 3 Oct): thor-1 runs gemma tool calling (99/144 on 3 Oct), then granite, then
  Devstral, to about Thu 8 Oct; P1's last runs end Thu 8 Oct ~16:40; some Orins are free from Tue 6 Oct "for
  re-runs". After the deadline nothing is written down.
- **Sandesh** said (2026-10-01) they have their own idea for the next step; not yet shared.

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

Not built: the gateway, live policies, a Jetson telemetry adapter, the CLGSCE port. The gateway and policy
milestones (master plan M3–M5) should not be built as planned: rewrite them after the direction decision.

## 4. What we know (details, figures and caveats in the reports)

**Kept state is worth little on P1's agents, drone or traffic** (P1's measured runs, one agent per device;
`reports/2026-10-05-p1-repo` §2).
- **Drone:** the cache saved 0.2–0.5% of LLM time on Thor; the ceiling P/(P+r·O) is 0.9–2.6% (pooled 2.1% and
  0.6% at r ≈ 67 in the earlier reports; per task 0.3–14%). Prompts are rebuilt per call.
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
  only under greedy decoding). Gemma under sampling is not measured.

**Earlier results that still stand.**
- **Two drone agents** (same 12 tasks, Thor): tool calling passes 67% at 231 kJ per success, Reflexion 87%
  at 79 kJ (2.9×).
- **P1's drone KV evictions are a side effect of the loops** (45 of 47 evicting Reflexion runs contain a
  capped call).
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
  re-copy 2 changed files, `advanced.txt` and P1's harness; patch the hard-coded RPC port 41451; replace
  P1's `pkill -x thor_headless` reset. P1's repository now holds the agents' data but not their code.
- **P1-style sessions (40–55K tokens) do not fit a one-GPU pool.** They need tp2, a lower `max_tokens`, or
  FP8 KV.
- **P1's AeroEval agent, task sets and Reflexion harness** are in `data/p1_aeroeval_src/` (read-only copies,
  2026-10-01).

## 6. Next steps

1. **Sandesh:** review the updated docs and deck v2.0, share them when ready, and decide whether and how to
   send `NOTES_FOR_P1.md` to P1 before Sat 10 Oct.
2. **Sandesh:** decide on the repo's visibility, then push the local commits.
3. **When the professor meeting is rescheduled:** take the direction decision (D12) with the deck (section
   11) and the evidence doc. Then rewrite master-plan M3–M5 for it.
4. **When P1 pushes more data** (Thor drone tool calling, granite/Devstral drone, traffic grades): `git pull`
   in `data/edge-agent-bench` only if Sandesh agrees (it is P1's clone), then rerun `analysis.p1_repo`
   (`load(key, refresh=True)`), `p1_opportunity`, `p1_caps`, `traffic_sim`, `p1_repo_figures`, and update
   the report, the docs and the deck.
5. **If A (decode-side energy):** test whether sampling removes the loops on Gemma (a device after 10 Oct,
   or a quantized Gemma on the WS); design a retry policy for dropped tool calls (traffic); review the
   reasoning-budget and early-exit literature (`rw-reasoning`); agree the split with P1, whose paper now
   claims the loop finding.
6. **If D (memory that changes over time):** the vision-tool burst is the case: replay it on the WS (a
   burst of concurrent requests while a long context is paused) and size what pinning or burst admission
   saves under small pools.
7. **When the WS is back:** Qwen3.5 energy calibration; one live memory-pressure run to anchor the
   simulators; one long mission (lawnmower or circles).

## 7. Open questions for Sandesh

1. Their plan for the next step (they said they have one).
2. **Send `NOTES_FOR_P1.md` to P1 before 10 Oct?** And: offer the online loop stop to P1's paper, or keep it
   for P5?
3. **The repo's visibility:** make it private before pushing?
4. When will the professor meeting be rescheduled, and is the WS one of P1's four "workstation" lanes? Is
   it back up?
5. The P1 mentor's answers to the task overview's §9: which 8 AeroEval tasks; whether a step-wise paradigm
   is in P1's scope; whether P5 may run P1's AeroEval tasks with a step-wise agent; drones per edge box.
6. Direction and scope (A–D), the go/no-go thresholds (D4), and `N_edge`.
7. Timeline: when the devices return to P5 after 2026-10-10, and the ISP milestones.

## 8. Resume checklist for a new session

1. Read `AGENTS.md`, then this file.
2. `git status`, `git log --oneline -5`. Before any `git push`, check the visibility:
   `gh repo view saisandeshk/jouleserve-ws --json visibility`.
3. P1's data: `git -C data/edge-agent-bench log --oneline -3` (read-only; do not pull without Sandesh).
4. WS, if reachable: `nvidia-smi; tmux ls; ls ~/work/runs`; copy runs with
   `rsync -a saisandeshk@10.24.32.174:~/work/runs/ data/ws_runs/`.
5. Thor: read-only and busy-check safe; prefer the repository to copies.
6. Deck work: check `data/p5deck/` exists (else restore it from the artifact with `Artifact` read), and
   that the renderer finds a browser.

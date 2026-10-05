# HANDOFF — jouleserve-ws

**Last updated:** 2026-10-05 (IST). Latest work, in order:
- 2026-10-04: reviewed P1's paper-meeting deck; found that the runaway calls are repetition loops; updated
  every doc with the drone findings; built the P5 reference deck to v1.0 (109 slides);
- 2026-10-05: **P1's repository arrived** (Sandesh cloned it to `data/edge-agent-bench`). Mapped it (task 1)
  and reran our analyses on its drone and traffic data (task 2):
  [`reports/2026-10-05-p1-repo/README.md`](reports/2026-10-05-p1-repo/README.md). **Task 3 (update every
  doc, the Claude Docs and the deck with it) waits for Sandesh's go.**

The professor meeting is on **Monday 2026-10-05**. Rules, machines, recipes and WS gotchas are in
[`AGENTS.md`](AGENTS.md). This file holds the state at the time of writing.

**Update this file at the end of every working session.** Replace stale facts rather than
appending history, which git already keeps.

---

## 1. The goal

**P5 / JouleServe.**
- **What:** a serving-layer controller for Jetson-class edge devices. It decides what
  happens to an agent session's retained state (KV, and SWA/recurrent state for hybrid
  models) while the session waits on a tool: keep, drop and recompute, offload, or change
  admission so that idle state does not block active work.
- **Metric:** energy per successful task.
- **Where the contribution must come from:** generic "keep KV across tool pauses" is taken
  (INFERCEPT, Continuum, TokenCake, Adaptive KV Retention, CacheScout; KAIROS for energy).
  It must come from what the edge changes: unified memory, shared bandwidth and power,
  hybrid models, and 10 s–10 min physical tool waits. P1 measured no thermal throttling at room
  temperature (below), so thermal state is out unless the hot-enclosure runs show otherwise.
- **Resources:** the edge devices are with P1 until their deadline (paper due Sat 2026-10-10).
  P5 has the 2×A5000 workstation, and WS work must pay off later.

## 2. Situation as of 2026-10-05

- **P1's repository** (`dream-lab/edge-agent-bench`) is a read-only clone in `data/edge-agent-bench`
  (git-ignored; HEAD `3c47ebc`, Sun 4 Oct 19:02; its remote is P1's GitHub: never push, never modify).
  - 2,055 runs: 3 graded drone cells (Thor gemma Reflexion, Orin 64 Devstral tool calling, Orin 32
    gemma-E4B tool calling) and 8 traffic cells (ungraded). Thor drone tool calling is **not** in it; keep
    using our copy `data/p1_thor_toolcalling/` (104 runs).
  - Our loader `analysis/p1_repo.py` reads all 12 configurations (cache in `data/p1_cache/`).
  - P1's analysis and paper are written by Mayank Arya (`mayankarya`, also aerogen's author).
  - **P1's paper now claims the loop finding** (offline detector, "stop at the first capped call" bound of
    50.2% that loses 22 runs) and **has dropped its early-abort plan** ("out of scope"). It assumes one
    request in flight. P1 deferred its KV-pool sweep (E4) and warm-cache arm (E5), which overlap P5.
  - Corrections for P1 (report §7): `ask_vlm` is a burst of requests to the agent's own server, not a
    second model; their loop threshold misses long-period loops; the drone Orin 32 caps are 1,024-token
    evaluator calls; Devstral's prefix cache is off (about 9% of its LLM time).

- **Not pushed: the GitHub repo is PUBLIC.**
  - `gh repo view` reports `saisandeshk/jouleserve-ws` as public.
  - It already holds P1's unpublished drone numbers in `reports/`. Today's work adds more P1
    material, including descriptions of P1's deck.
  - Today's commit is local only. Sandesh decides on visibility (private is advisable before
    P1's double-blind submission on 2026-10-10) and then pushes.
  - P1's deck figures are kept out of git entirely: `reports/*/p1_figures/` is git-ignored.
- **P1's paper meeting (2026-10-03).** P1 presented its results to the professor: the
  EdgeAgentBench deck, `~/Downloads/SIGMETRICS-2027-EdgeAgentBench.pptx`, slides 387–406.
  - P1's repository is `github.com/dream-lab/edge-agent-bench`. Sandesh gets access from the
    professor on Mon 2026-10-05.
  - Until then, do not clone it via anyone's credentials on the Thor (see `AGENTS.md` §4).
- **New analysis (2026-10-04):**
  [`reports/2026-10-04-drone-runaways/README.md`](reports/2026-10-04-drone-runaways/README.md),
  drone only. Headlines in §4.
- **Docs updated 2026-10-04 (Sandesh asked: "update all the docs, local and artifacts; content
  on drones only; include useful plots").**
  - **The evidence Claude Doc** (rev 85) and its repo copy
    [`reports/2026-10-02-p5-evidence/README.md`](reports/2026-10-02-p5-evidence/README.md):
    - new lead and summary items 7–10;
    - new sections "Runaway calls are repetition loops" and "P1's results of 3 October (drone)",
      with our loop figure and four of P1's drone figures cropped from the deck;
    - updated options A/B, decisions (new: offer the loop stop to P1's paper?), next steps and
      limitations.
  - **The teaching guide Claude Doc** (rev 56): status, §10 Heat (with P1's thermal figure), §14,
    §15 P1 status, §17.1 (loops, figures), §17.4, §18, two new self-test questions and three
    glossary rows.
  - **The dated reports** carry update notes pointing to the new report, and the admission-sim
    report §5 has the loop result.
- **The P5 reference deck (started 2026-10-04, at Sandesh's request)** is a Slides artifact:
  https://claude.ai/artifact/QrFXoAwDssEtftYgGnxVm8 (private until shared).
  - It is the single main reference, updated weekly.
  - **Style:** IBM Plex Sans, off-white with one blue accent, dark dividers; body text 28 px (14 pt), small text 24 px (12 pt).
  - **Built in batches,** with Sandesh's review after each:
    1. sections 0–1, front matter and introduction (v0.1);
    2. batch 1, sections 2–6: preliminaries, problem statement, research questions and
       hypotheses (v0.2, 2026-10-04; 34 slides in all);
    3. batch 2, sections 7–8: related work and P1 (v0.3, 2026-10-04; 59 slides in all). The
       related-work numbers were checked against the papers on 2026-10-04: all 25 held. Two
       wordings were dropped: MLPerf Edge Agentic's page names no device (do not say Thor), and
       Arya & Simmhan report a low memory clock raising latency 370% and energy 72% (not that
       memory "dominates"). Reasoning-length control (slide `rw-reasoning`) is a placeholder,
       still unread;
    4. batch 3, sections 9–13 plus the appendix: approach, findings, options, plan, status,
       the first weekly log (week of 28 Sep) and the appendix (v1.0, 2026-10-05; 109 slides).
       A final pass checked numbers and wording across all sections. Figures come from the
       reports (uploaded as artifact assets; `env/render_slides.py` maps their blob ids).
  - **Visual check before Sandesh sees a batch (Sandesh approved it):** `env/render_slides.py` renders
    the slide files with the Playwright-cached headless Chromium. It is approximate and flags
    overflow and overlaps.
  - **Slide sources:** the artifact itself. To change a slide, read its file from the artifact, edit it,
    and publish only the changed files.
  - **The agreed outline:** 14 sections plus an appendix. Preliminaries are a short refresher tied to our numbers, not basics. Related work goes two papers per slide, with a summary table and a placeholder for reasoning-length control. Traffic gets a placeholder in section 8.
  - **Weekly routine:** a log slide, the at-a-glance slide and the changelog updated in place, and matured results moved into Findings.
- **Doc links.**
  - Evidence doc: https://claude.ai/code/artifact/474eee56-2e2f-44f9-8b97-f7bb51b588c7.
  - Teaching guide: https://claude.ai/code/artifact/36c2319c-b866-44f2-8dcf-42c02cdfd18c (no
    repo copy).
  - Both are private until Sandesh shares them.
  - One open comment in the guide (ours) asks how many drones per device to plan for.
- **WS:** unreachable since 2026-10-02 ~23:00 when last checked (2026-10-03 16:50). It was not
  checked today, because Sandesh asked not to access the WS or the Thor this session.
  - P1's schedule shows four "workstation" lanes (Sol/Terra runs from Sun 2026-10-04).
  - Ask Sandesh whether our WS is one of them.
- **P1 (Thor), per the deck as of 2026-10-03 15:00.**
  - thor-1 (the Thor we read from) is booked back to back until about Thu 2026-10-08:
    1. Gemma tool calling, 99 of 144 runs. The sweep now covers the 4 AeroEval tasks too, so it
       does not end at 108.
    2. Then granite tool calling.
    3. Then Devstral tool calling.
  - P1's last runs end Thu 2026-10-08 16:40, and the paper is due Sat 2026-10-10 17:30.
  - Copies from the Thor would land mid-run, so wait for the repository instead.
  - Our local copy is unchanged: `data/p1_thor_drone/` (143 Reflexion runs) and
    `data/p1_thor_toolcalling/` (104 runs as of 2026-10-03 16:16).
- **P1's traffic workload (seen in the deck, not analysed; kept out of the shared docs for now
  at Sandesh's request).** It matters for P5 because it is the accumulating-context pattern our
  drone analysis said P1 lacked:
  - **The agent:** native tool calling, max 20 steps; 56–82% of prompt tokens come from cache.
  - **Contexts:** up to 104K tokens on the Thor.
  - **Memory binds at N = 1 on the Orins:** Gemma-26B on an Orin 64 is served with a
    12,288-token window, and 21% of its runs end by overflow; granite overflows in 11–14%.
  - **A co-located vision model:** `ask_vlm` runs on the same GPU. It is 5% of tool calls but
    62% of tool energy, at a median 73 s and 3.7 kJ per call, so tool time is not idle time.
  - **Capped calls are here too** (8K cap): 42% of LLM time on Thor Gemma.
  - **What this means for P5:** option D (memory that changes over time, H4) may have a live
    test case in P1's own workload. Analyse it when the repository arrives.
- **Sandesh** said (2026-10-01) they have their own idea for the next step; not yet shared.
- **Earlier in the weekend** (details in the reports):
  - the admission/retention simulation (2026-10-03, negative);
  - the step-wise D1–D3 test (2026-10-02);
  - the task overview for P1's mentor (2026-10-01);
  - the first evidence pack (2026-10-01).

## 3. What is built (JouleServe-WS pieces)

| Piece | Where | Notes |
|---|---|---|
| Telemetry samplers | `jsw/telemetry/samplers.py` | NVML at 10 Hz (power, **energy counter**, clocks, throttle) and SGLang `/metrics` at 2 Hz |
| aerogen driver | `jsw/workloads/aerogen_driver.py` (+ `aerogen_peek.py`) | Runs mayankarya's agent unmodified (runtime patches), N closed-loop session slots, manifest per run. Flags for P1's tasks: `--effort think\|nothink`, `--task-file`, `--world-prompt`, `--runtime-prompt`, `--top-k` |
| Delivery checker | `jsw/workloads/delivery_check.py` | Strict check of P1's D1–D3 over a sim trace (order, descent + 10 s hold, return, no flight through a building) |
| Cost calibration | `jsw/costs/calibrate.py` | Idle power, cold/warm prefill, decode J/token against batch |
| Analysis | `analysis/sessions.py`, `report_figures.py`, `headroom_sim.py`, `sim_validate.py`, `p1_cache_misses.py`, `doc_charts.py`, `p1_per_task.py`, `stepwise_ceiling.py` | One session model for P1 traces and WS runs; ceilings (`stepwise.json` also holds r = 90 ceilings since 2026-10-04) |
| Admission/retention simulator | `analysis/admission_sim.py`, `admission_figures.py` | N drones per box, per-model state layouts, 12 policies + unlimited memory; Thor and WS device models. `summary.json` holds the paradigm comparison under both success checks (2026-10-04) |
| P1 runaway analysis | `analysis/p1_runaway.py`, **`analysis/p1_loops.py`** (2026-10-04) | Two-agent comparison and fixed-cut savings; online loop detector replay, savings vs fixed cuts, cross-check of P1's drone numbers, eviction overlap |
| P1 repository analyses (2026-10-05) | `analysis/p1_repo.py` (loader), `p1_opportunity.py`, `p1_caps.py`, `traffic_sim.py`, `p1_repo_figures.py` | All 12 configurations: value of kept state, idle gaps, vision-tool bursts, prefix reuse; capped calls, loops and four stop rules; N traffic agents per device at real KV pools |
| Launch / queues | `env/launch_k2_tp1.sh`, `env/launch_qwen35_tp1.sh`, `env/queue*.sh` | K2 pinned to revision `f846b1e` |

Not built: the gateway, live policies, a Jetson telemetry adapter, the CLGSCE port. If the
negative result stands, the gateway and policy milestones (master plan M3–M5) should not be
built as planned; rewrite them after the direction decision.

## 4. What we know (details, figures and caveats in the reports)

**P1's traffic and the repo's drone cells** (2026-10-05, `reports/2026-10-05-p1-repo`; measured on P1's
runs unless marked simulated).
- **Traffic contexts accumulate** (prompts never shrink; 56–82% from cache), **but kept state is worth
  1–4% of LLM time** (ceiling 1.7–7.2% at each configuration's own r; Qwen2.5-VL 15% / 26%). Outputs are
  a median 107–999 tokens per call; idle gaps a median 1.0–2.8 s; no prefix is shared between sessions
  (the system prompt opens with the current time).
- **The vision tool fills the KV pool at one agent per device:** 8–45 concurrent requests to the agent's
  own server; on Orin 64 gemma it evicts the paused context before all 62 following calls (90% recomputed,
  0.6% of LLM time). Option D's live case, but small.
- **Many traffic agents per device (simulated, real KV pools):** no policy beats SGLang's default by more
  than 2.4% in 48 cells; on the Orins capacity binds (gap to unlimited memory up to 64% at 8 agents;
  doubling the pool cuts energy per completed task 31–46%).
- **Capped calls:** drone = loops (Thor Reflexion 121/122 incl. P1's 144th run; online stop 43.5%, no
  finished call stopped). Traffic = mostly not text loops where text survives; the waste is a cap inside a
  tool call followed by a retry that caps again (121 of 158 on Thor gemma). Stopping at the second
  consecutive cap saves 27% (Thor gemma, 1 run lost) and 25% (Orin 32 E4B, 7 lost).
- **Thermal** (P1's paper): 0 throttle samples in 434 h, peak 81.3 °C. **Repeat divergence** is traced by
  P1 to inputs (timestamp in the prompt, simulator noise), except gemma-E4B on the Orin 32.

**P1's drone agents leave no retained-state opportunity** (Thor traces, Gemma-4-26B-A4B; P1's
own deck agrees).
- **Pooled ceiling** P/(P+r·O) at the Thor's r ≈ 67:
  - 2.1% (Reflexion, 143 runs) and 0.6% (tool calling, 104 runs);
  - 1.6% and 0.5% at P1's energy price ratio of 90.
- **Per task:** 0.3–14%, and 0.3–3.2% on every task longer than 10 min.
- **Batching does not change it:** 0–1.3% in simulation with 1–16 drones.
- **Prompts are rebuilt every call;** decode is 90–99% of LLM time, and generated tokens carry
  97% of LLM energy (P1's fit and ours).

**Runaway thinking is where P1's energy goes, and every runaway is a repetition loop**
(2026-10-04, `analysis/p1_loops.py`).
- **Capped calls** take 57% (Reflexion) and 70% (tool calling) of LLM time on the 12 CLGSCE
  tasks, and 71% over Reflexion's 16 tasks.
- **They are loops.** 120 of the 121 capped Reflexion calls and all 127 tool-calling calls capped
  at 32K end in repeating text. Their most repetitive 16K characters compress to 1–9%, against
  14–29% for calls that finished. No finished call (0 of 1,337) is flagged.
- **An online loop stop** fires at a median of 35% (Reflexion) and 44% (tool calling) into the
  call, and saves (upper bound, board energy):
  - 44% over Reflexion's 16 tasks;
  - 31% over Reflexion's 12 CLGSCE tasks;
  - 36% for tool calling;
  - stopping 0 finished calls in every case.

  A fixed 16K cut saves 34% / 27% / 34% and stops 14 / 14 / 32 finished calls.
- **The likely cause is greedy decoding:** P1 runs everything at temperature 0. On the WS, Qwen3.5
  ran away only under greedy decoding. Gemma under sampling is not measured.
- **Two-agent comparison** (same 12 tasks): tool calling passes 67% at 231 kJ per success, and
  Reflexion 87% at 79 kJ (2.9×).
- **P1's KV-cache evictions are a side effect of the loops.**
  - P1 reports evictions in 33% of drone runs at one request in flight. 45 of those 47
    Reflexion runs (and 40 of 44 tool-calling ones) contain a capped call, which overflows P1's
    80K-token pool cap.
  - This explains our 2026-10-01 same-role cache-miss anomaly, which costs 0.3–1.1%.
- **Overlap (updated 2026-10-05):** P1's paper reports the loops itself and suggests "stop or retry at
  the first capped call", but dropped its early-abort policy as out of scope. Option A must be an online,
  run-preserving stop evaluated as a control policy, plus the traffic retry case.

**P1's deck, drone side (2026-10-03; reproduced from our copy where marked).**
- **Reproduced from our copy:**
  - 71% pass;
  - 71% of LLM time in capped calls;
  - pass rate 39% with a capped call against 92% without;
  - failed runs: 29% of runs, using 63% of the energy;
  - 26% of prompt tokens cached, and prefill 1.8% of LLM time;
  - a generated token costs 74× a prefilled one in our regression, against P1's 75× average
    and 90× marginal.
- **Quoted from the deck:**
  - **No thermal throttling** at room temperature in 392 h: the hottest drone reading was 77 °C
    on the Thor, and no clock fell below 98% of its pinned value.
  - **Temperature 0 is not deterministic on Jetson:** 23–25% of drone prompts took more than one
    path in 3 repeats.
  - **Devstral-24B tool calling on Orin 64** passes 31%, with 0 cached tokens reported; we have
    no traces for it.
  - **P1 also has a replay-based cost model,** close in method to our admission simulator.

**AeroEval and aerogen** (task overview report).
- P1 kept 4 of 9 AeroEval-family missions (D1–D3, F1), the small ones.
- P1's AeroEval runs rarely fly: the LLM validator rejects first.
- aerogen is mayankarya's step-wise rewrite; it is not P1's workload.

**A step-wise agent on P1's delivery tasks keeps its steps short** (WS, 2026-10-02, 108
missions).
- **Steps:** median 55–99 output tokens after a tool result; thinking concentrates in the
  planning call.
- **Ceiling at r = 67:** 56–72% of post-wait LLM time and 20–72% of mission LLM time; private
  state 3–16%. At r = 90: 48–66%, 16–66% and 2–13%.
- **Missions:** 72% deliver everything, but only 27% pass the strict check (no buildings in the
  sim).

**A memory controller does not beat SGLang's default** (simulated 2026-10-03, 1–16 drones).
- **Policies:** no online policy beats the best fixed rule by more than 9.9% in any of 455 cells.
- **Keeping state:** worth 19–29% at 16 step-wise drones, but the radix cache already keeps it.
- **Under tight memory** the loss is capacity: an FP8 KV cache (configuration) recovers 10–34%.
- **Agent design** (Thor costs, P1's D1–D3):
  - **Energy per success:** P1's Reflexion uses 219–499 kJ (measured), against 22–68 kJ for the
    step-wise agent (projected). That is 5–13× counting delivered-and-returned missions, and
    **0.9–9.6× under the strict check**; the truth is probably in between until a
    building-aware sim exists.
  - **Drones per Thor:** 4–16 step-wise drones, against 2 of P1's.

**aerogen and concurrency** (WS, 2026-10-01).
- **Kept state:** saves 33% of LLM time on aerogen's own tasks (12% private).
- **Concurrency:** 8 sessions per GPU used 2.2× less energy per passed mission than 1.

**WS costs** (K2, one A5000).
- **Prefill:** 4,106 tokens/s at ~0.05 J/token.
- **Decode:** 5.36 J/token at batch 1 and 0.38 J at batch 16.
- **Idle:** 10–20 W.

**Track B** synthesis is unchanged (`review/systems/README.md`), apart from a thermal note.

## 5. Still-valid notes from the 2026-09-30 audit

- **The CLGSCE port** (needed only if P1's agents run on the WS) is mostly done in legacy. Left
  to do:
  - re-copy 2 changed files, `advanced.txt` and P1's harness;
  - patch the hard-coded RPC port 41451;
  - replace P1's `pkill -x thor_headless` reset.
- **P1-style sessions (40–55K tokens) do not fit a one-GPU pool.** They need tp2, a lower
  `max_tokens`, or FP8 KV.
- **P1's AeroEval agent, task sets and Reflexion harness** are in `data/p1_aeroeval_src/`
  (read-only copies, 2026-10-01).

## 6. Next steps

**Before Monday's meeting (2026-10-05):**
1. A one-page brief, if Sandesh wants it (local Markdown). It would cover:
   - the decision asked;
   - the negative memory-controller result;
   - the loop finding and its overlap with P1's early-abort plan;
   - the success-check sensitivity;
   - the permissions to ask for.
2. Sandesh decides on the repo's visibility, then pushes today's local commits.
3. Sandesh reviews deck v1.0 before sharing it (it is private until shared from its Share menu).
   From then on, update it weekly: a new log slide in section 13, the at-a-glance slide and the
   changelog; fill the traffic (section 8) and reasoning-length (section 7) placeholders when
   their inputs arrive.

**Now (2026-10-05):**
1. Task 3, on Sandesh's go: update the docs (evidence repo copy and Claude Doc, teaching guide, plans,
   review notes), the deck (traffic slide in section 8, findings, options, weekly log, at-a-glance,
   changelog) with `reports/2026-10-05-p1-repo`.
2. Send P1 the corrections in report §7 (Sandesh decides how, before P1's 10 Oct deadline).
3. When P1 pushes its Thor drone tool-calling cell or traffic grades, rerun `analysis.p1_repo` with
   `refresh=True` and the four analyses.
3. **If A:**
   - test whether sampling removes the loops on Gemma (a device, or a quantized Gemma on the WS);
   - agree with P1 how the loop stop relates to their early-abort policy;
   - review the reasoning-budget and early-exit literature.
4. When the WS is back:
   - Qwen3.5 energy calibration;
   - one live memory-pressure run to anchor the simulator;
   - one long mission (lawnmower or circles).
5. Rewrite the master plan's M3–M5 for the chosen direction, and record it as D12.

## 7. Open questions for Sandesh

1. Their plan for the next step (they said they have one).
2. **Should we offer the loop stop to P1's paper before 2026-10-10, or keep it for P5?**
3. **The repo's visibility:** make it private before pushing?
4. Is our WS one of P1's four "workstation" lanes in the deck schedule? Is it back up?
5. The P1 mentor's answers to the task overview's §9:
   - which 8 AeroEval tasks;
   - whether a step-wise paradigm is in P1's scope;
   - whether P5 may run P1's AeroEval tasks with a step-wise agent;
   - drones per edge box.
6. Direction and scope (A–D), the go/no-go thresholds (D4), and `N_edge`.
7. Timeline: when the devices return to P5 after 2026-10-10, and the ISP milestones.

## 8. Resume checklist for a new session

1. Read `AGENTS.md`, then this file.
2. `git status`, `git log --oneline -5`. Before any `git push`, check the visibility:
   `gh repo view saisandeshk/jouleserve-ws --json visibility`.
3. WS, if reachable: `nvidia-smi; tmux ls; ls ~/work/runs`.
4. Re-run the analysis if runs changed (§6). WS runs:
   `rsync -a saisandeshk@10.24.32.174:~/work/runs/ data/ws_runs/`.
5. Thor: read-only and busy-check safe. P1 is in its final week, so prefer the repository to
   copies.

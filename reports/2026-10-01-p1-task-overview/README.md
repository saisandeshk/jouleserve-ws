# P1's drone tasks: what AeroEval is, and which tasks can give P5 an opportunity

**2026-10-01 (late), updated 2026-10-02 · Sai Sandesh (P5)**, prepared with Claude Code.

This answers two questions from the P1 mentor's feedback ("P1's drone set is 12 CLGSCE + 4
AeroEval; aerogen is not relevant; AeroEval originally had 8 tasks and the easy 4 were
chosen"):
1. Are aerogen and AeroEval the same, and where are the AeroEval code and tasks?
2. Which P1 tasks can actually be used by P5, or create an opportunity?

**Sources.**
- Read-only copies from the P1 Thor (`yash@10.24.24.79`), copied without touching the running
  sweep: P1's AeroEval agent, task sets and harness are in `data/p1_aeroeval_src/`; the Thor
  traces are in `data/p1_thor_drone/` and `data/p1_thor_toolcalling/` (all git-ignored).
- P1's dataset README (`/home/yash/final_sweep/drones_README.md`, 2026-10-01).
- Per-task numbers: `python3 -m analysis.p1_per_task` (writes [`per_task.json`](per_task.json)).
  Everything marked *estimate* is worked out from task text, not measured.

## Answers in brief

1. **aerogen and AeroEval are related, but they are not the same thing, and the mentor is
   right that aerogen is not P1's workload** (§1).
   - **AeroEval** is the lab's evaluation pipeline and task set for **AeroGen**, an LLM that
     writes complete drone programs. It has 5 missions.
   - **P1's AeroEval agent** is Yash's re-implementation: Reflexion program synthesis, flown in
     Gazebo.
   - **`aerogen_mcp`** is mayankarya's tool-calling rewrite of AeroGen: the model flies the
     drone one tool call at a time. It reuses AeroEval's world and robot prompts but has its
     own 5 sample tasks, none of which is one of P1's tasks.
2. **Where things are:** P1's AeroEval agent is in `/home/yash/aeroeval_gazebo_subagents/`.
   The AeroEval task files are in that folder's `vendor/CLGSCE/aerodaas_integration/task_sets/`.
   aerogen is separate, in `/media/ssd/drone/aeroeval/` (§2).
3. **The task inventory** (§3):
   - The original AeroEval set has **5 missions**: delivery, farm survey, cable inspection,
     radio-tower search, and search-and-track.
   - On 2026-09-04 P1 wrote **6 variants**: 3 delivery and 3 farm.
   - That is **9 distinct missions**, of which P1 kept **4** (D1–D3 and F1). I could not find a
     list of exactly 8, so it is worth asking which 8 she means.
   - She is right about size. The dropped farm variants (lawnmower, concentric circles) and the
     dropped perception missions fly an estimated 15–25 minutes each, against about 1 minute
     for F1.
4. **With P1's agents, kept state is worth almost nothing, and bigger tasks do not change that**
   (§4–5).
   - The most any retention policy can save on a call is P / (P + r·O):
     - **P** is the reused prompt tokens, set by how the agent builds prompts;
     - **O** is the output tokens, set by how much the model thinks;
     - **r** is the cost of one output token relative to one prefilled token (≈ 67 on the Thor).
   - P1's agents rebuild the prompt on every call, so P is small, and they think for
     thousands of tokens, so O is large. The ceiling is 2.1% (Reflexion) and 0.6% (tool
     calling) of LLM time. Per task it is 0.3–14%, and 0.3–3.2% on every task longer than 10
     minutes.
   - The task does not enter P or O directly. With P1's agents a bigger task only means more
     thinking, so the ceiling falls. aerogen flies similar missions step by step and reaches
     37%.
5. **This leaves P5 three honest options** (§6):
   - **A:** keep P1's agents and change P5's question to decode-side scheduling;
   - **B:** keep P5's question and P1's tasks, but drive the tasks with a step-wise agent;
   - **C:** keep the question but move to standard agent benchmarks.

   I suggested B because it changes the least that matters. It rests on one unmeasured number:
   how much a thinking model writes per step. §7 sets out the test that measures it.

---

## 1. aerogen vs AeroEval

| | AeroGen + AeroEval (original) | P1's AeroEval agent (final sweep) | `aerogen_mcp` |
|---|---|---|---|
| Who | Lab's AeroDaaS work (CLGSCE repo, `aerodaas_integration/`, ICSOC experiment folders) | Yash (P1), 2026-08 to 09 | mayankarya, 2026-08-29 |
| What the LLM produces | One complete AeroDaaS/Aerostack2 program | One complete Aerostack2 program per attempt | One tool call per step (`takeoff`, `go_to_point`, `follow_path`, `hover`, `run_inference`, … 20 tools) |
| Loop | Generate → LLM code validator → trajectory validation (regex over the code, then an LLM judge) | Reflexion: generator → LLM code validator → **Gazebo flight + deterministic path checks** → reflector, with a supervisor; up to 3 generations | One growing `messages` list. The server rejects unsafe moves, and a deterministic validator checks the executed trace |
| Context across steps | Rebuilt per stage (a static ~11K-token prefix repeats) | Rebuilt per role call | **Accumulates** |
| Tasks | 5 missions (§3) | 4: D1–D3, F1 | 5 own samples in the radio-tower world: squares, an area survey over road nodes I40–I44–I20–I24, a radio-tower inspection, road following |
| Simulator | none (static validation) | Aerostack2 + Gazebo, **real-time factor 10** | Kinematic sim (we added real-time pacing), or a `ros2` backend that drives the real Aerostack2 `DroneInterface` |

- **What `aerogen_mcp` shares with AeroEval:** the robot, runtime and world prompts, which it
  reads from AeroGen's `orig/system_prompts/`, and the delivery world's road-node vocabulary.
- **What it does not share:** P1's tasks, P1's agent, or P1's Gazebo validation.
- **What our overnight aerogen measurements mean:** they describe a *step-wise tool-calling
  paradigm* on aerogen's sample tasks, not P1's workload.

## 2. Where the code and tasks are (Thor, read-only)

| What | Path on the Thor | Notes |
|---|---|---|
| P1's AeroEval agent (final sweep) | `/home/yash/aeroeval_gazebo_subagents/` | `agent/` (Reflexion subagents), `gazebo_validation/` (world specs, path checks), `mcp_servers/`, `config/worlds/` (`delivery`, `farm_survey`; RTF 10), `README.md` |
| AeroEval task sets | `…/aeroeval_gazebo_subagents/vendor/CLGSCE/aerodaas_integration/task_sets/` | `aerogen_aeroeval_{delivery,farm_survey,cable_inspection,radio_tower,search_track}.txt`, `aerogen_aeroeval_tasks.txt` (all 5), and P1's `p1_delivery_{ordered,checkpoint,outback}.txt` |
| Original AeroEval results | `…/aerodaas_integration/aerogen_aeroeval_results.csv` and `plot_script/aeroeval/` | Cloud-model runs, task ids 1–5. Prompts are ~12.8K tokens, of which ~11.3K is a cached static prefix |
| How P1 wires its 4 tasks | `/home/yash/final_sweep/_harness/instances.py` | D1–D3 from `p1_delivery_*.txt` with remapped nodes per instance; F1 = `farm_survey` with plot 20/14/26 m |
| P1's earlier versions | `/home/yash/agentic_aeroeval/` (2026-08-25), `/media/ssd/agentic_aeroeval/` (2026-08-29 to 09-04) | The 6 P1 variants were written here on 2026-09-04 (logs `/home/yash/AEROEVAL_TASK*_20260904_*.log`). Early ReAct agents are here and in `aeroeval_gazebo_subagents/repo_side/react_aeroeval_gazebo.py`; their actions are code-level (generate code / validate code / validate in Gazebo) |
| Other AeroEval sweeps | `/home/yash/AEROEVAL_COMPAT_SWEEP_THOR/`, `/home/yash/AEROEVAL_REFLEXION_SWEEP_THOR/` | Model compatibility and Reflexion runs on D1–F1 (Gemma, Qwen, Granite, Devstral, Nemotron, frontier) |
| `aerogen_mcp` and original AeroGen | `/media/ssd/drone/aeroeval/{aerogen_mcp,orig}` (mayankarya) | A copy is at `/home/yash/aeroeval_subagents/`. Our private WS copy is `~/work/aeroeval/` |
| Aerostack2 / Gazebo builds, DeepStream | `/media/ssd/drone/{aerostack2,aeroeval_gazebo,aerodaas_*}`, `/media/ssd/deepstream-mcp`, `/media/ssd/Deepstream-Yolo-upstream` | mayankarya's; the perception missions would need these |

## 3. AeroEval task inventory

Flight sizes and times marked *est.* are worked out from the task text and world constraints
(2 m/s maximum speed). Nothing in those columns is measured except D1's route.

| Mission | Origin | In P1's sweep | Gazebo world in P1's stack | Needs perception | Flight (est.) | Real flight time (est.) |
|---|---|---|---|---|---|---|
| Ordered 3-stop delivery (I22 → I34 → I43, descend to 1 m, hover 10 s, return) | AeroEval delivery, P1 variant | **D1** | delivery | no | ~645 m (P1's README route) | ~13 min (P1's README: "~770 s mission") |
| Delivery via checkpoint | P1 variant | **D2** | delivery | no | ~300–400 m | ~5 min |
| Two out-and-back deliveries | P1 variant | **D3** | delivery | no | ~800 m | ~10 min |
| Farm perimeter survey (20/14/26 m plot, camera inward) | AeroEval farm survey | **F1** | farm_survey | camera recording only | 56–104 m | ~1 min |
| Farm interior lawnmower survey | P1 variant (09-04) | no | needs a large-farm world (the current one is the small plot) | no | ~2 km, if it uses the 180 × 240 m area of the circles task (the size comes from the world prompt) | ~15–20 min |
| Concentric circles (radii 75/60/45/30 m at 1 m/s) | P1 variant (09-04) | no | needs a large-farm world | no | ~1.4 km | ~24 min |
| Radio towers: search 180 × 240 m, inspect each tower | AeroEval | no | none (towers have no coordinates) | yes (tower detection) | ~2 km + inspections | ~20+ min |
| Powerline cable following | AeroEval | no | none | yes (cable detection and follow) | open-ended | open-ended |
| Search 8 × 4 m area, then track a VIP | AeroEval | no | none | yes (VIP detection and tracking) | small area, then open-ended tracking | open-ended |

- **Gazebo is compressed.** P1 runs it at real-time factor 10, so the tool waits in P1's
  AeroEval traces are about 10× shorter than the real flights.
- **Small kept, large dropped.** P1 kept the delivery missions and the small farm plot. The
  dropped missions are the large-area ones and the ones that need perception models.

## 4. P1's 16 tasks, as P1 runs them (Thor traces, Gemma-4-26B-A4B)

**Bound** is the upper limit for *any* retention policy: the prefill share of LLM time. A
policy can at most remove prefill. **Observed** is what the cache hits in these runs actually
saved. The rows marked *flights* count real tool waits (> 0.5 s).

| Task | Reflexion pass | min/run | LLM calls/run | flights/run (median s) | LLM share of time | **Bound** | Observed | 32K-capped calls | Tool calling: pass, min/run, bound |
|---|---|---|---|---|---|---|---|---|---|
| B5 | 9/9 | 1.2 | 2.0 | 1.0 (17) | 73% | 9.9% | 0.0% | 0 | 3/3, 1.7, 10.9% |
| B13 | 9/9 | 1.0 | 2.0 | 1.0 (16) | 67% | 14.0% | 0.0% | 0 | 3/3, 1.4, 11.1% |
| B29 | 9/9 | 1.8 | 2.0 | 1.0 (15) | 83% | 6.1% | 0.0% | 0 | 3/3, 1.5, 9.7% |
| B37 | 6/9 | 2.8 | 4.3 | 1.8 (20) | 78% | 6.5% | 2.1% | 0 | 3/3, 2.4, 7.6% |
| A3 | 9/9 | 2.9 | 2.0 | 1.0 (44) | 73% | 4.0% | 0.0% | 0 | 3/3, 4.4, 3.9% |
| A5 | 9/9 | 10.0 | 2.3 | 1.0 (42) | 93% | 1.2% | 0.0% | 3 | 3/3, 4.5, 3.5% |
| A6 | 9/9 | 7.3 | 2.0 | 1.0 (47) | 89% | 1.7% | 0.0% | 0 | 1/3, 79.8, 0.4% |
| A7 | 8/9 | 36.4 | 6.0 | 2.1 (81) | 92% | 1.0% | 0.2% | 6 | 0/3, 85.5, 0.5% |
| A8 | 7/9 | 27.8 | 4.2 | 1.6 (73) | 93% | 0.9% | 0.1% | 5 | 3/3, 81.4, 0.6% |
| A9 | 9/9 | 31.8 | 5.6 | 1.8 (74) | 93% | 1.0% | 0.2% | 11 | 0/3, 110.0, 0.3% |
| A16 | 1/9 | 68.6 | 10.3 | 3.0 (80) | 94% | 0.8% | 0.2% | 21 | 3/3, 8.7, 2.3% |
| A20 | 9/9 | 7.6 | 2.0 | 1.0 (77) | 82% | 1.9% | 0.0% | 0 | 2/2, 92.2, 0.3% |
| D1 ordered | 5/9 | 67.5 | 20.3 | 0.9 (119) | 91% | 2.2% | 0.9% | 22 | not in sweep |
| D2 checkpoint | 3/8 | 19.5 | 11.1 | 0.6 (70) | 95% | 3.2% | 1.5% | 2 | not in sweep |
| D3 out-and-back | 0/9 | 57.0 | 19.4 | 0.4 (41) | 97% | 2.3% | 1.0% | 18 | not in sweep |
| F1 farm survey | 0/9 | 72.6 | 20.0 | 0.0 (–) | 100% | 2.1% | 0.6% | 27 | not in sweep |

- **Data:** Reflexion has 143 runs; one D2 run is missing from our copy, and P1's README
  counts 144. Tool calling has 35 runs, instance 1 only, as of 2026-10-01 23:00, and runs only
  the CLGSCE tasks.
- **The only tasks with a bound above 5% are the B tasks and A3**, which last 1–4 minutes. At
  14% of ~40 s of LLM time, B13's bound is about 6 s per run.
- **Every task longer than 10 minutes has a bound of 0.3–3.2%.** Their time is thinking
  decode: 50 of 176 tool-calling LLM calls, and 115 of 1,030 Reflexion calls, hit the
  32,768-token cap.
- **The AeroEval tasks rarely fly.**
  - D1 flew 8 times in 9 runs, and F1 never flew: the LLM code validator rejected every
    program first.
  - The physical wait that would make retention matter is mostly absent, and when it happens
    it is compressed 10× by Gazebo's real-time factor.

## 5. What decides whether kept state is worth anything

When a session pauses for a tool, keeping its KV state saves the prefill of the next call, and
nothing else. So the most any retention policy can save on one call is

  **saving ≤ P / (P + r·O)**

- **P** is the tokens of the next prompt that repeat what is already cached. This is set by
  how the agent builds its prompts.
- **O** is the tokens the next call generates. This is set by how much the model thinks.
- **r** is the cost of one output token relative to one prefilled token: ≈ 67 on the Thor
  (prefill ~1,811 tokens/s against decode ~27 tokens/s, Gemma-4-26B-A4B) and ≈ 112 on an A5000
  (K2-Horizon-7B: 4,106 against 36.5 tokens/s).

The task appears in neither P nor O. It decides how many calls and waits there are, and how
long each wait is. P and O come from the agent.

**Measured per-call values** (token-weighted over all calls; P taken as the whole prompt, so
this is an upper bound):

| Workload | Prompt per call (median) | Output per call (median) | Ceiling P/(P+r·O) | Measured saving |
|---|---|---|---|---|
| P1 Reflexion, 16 tasks (Thor, 1,030 calls) | 6.0K | 538 (generators ~8K) | 2.1% | ≤ 0.9% |
| P1 tool calling, 12 tasks (Thor, 176 calls) | 4.3K | 3.8K | 0.6% | ≤ 0.3% |
| aerogen, K2 low effort (WS, 211 calls) | 11.7K | 49 | 37% | 33% |
| aerogen, K2 medium / high effort (WS) | 14–18K | 55 | 19–22% | not computed |
| aerogen, low effort, at Thor's r (hypothetical) | 11.7K | 49 | ~50% | — |

**Why P1's agents score so low:**
1. **P is small.**
   - The model writes the whole flight program up front, and one tool call executes it.
   - Every role call (generator, evaluator, reflector) starts a new prompt, so 0–53% of
     prompt tokens come from cache. The high end is mostly a retry of the same prompt after a
     capped call.
   - There is no growing per-session context to retain.
2. **O is large.**
   - With thinking on, a generator call writes a median ~8K tokens.
   - Re-prefilling a 20K-token context costs ~11 s on the Thor, the time to decode ~300
     tokens, so recompute is negligible next to the decode.
3. **Bigger tasks make it worse.** A bigger task means more thinking and more calls that hit
   the 32K cap, so O grows and the ceiling falls. The B tasks (1–3 min) reach 6–14%; every task
   longer than 10 minutes is at 0.3–3.2% (§4).
4. **There is no memory pressure.** P1 runs one request at a time, and its contexts fit in
   memory (≤ 55K tokens, inside P1's 80K-token KV pool), so keeping everything is free.
   SGLang already does that.

**Similar missions, different agent.** aerogen flies the same kinds of missions (squares, area
surveys, road routes). It appends to one conversation and takes short steps, so P is large, O
is small, and the ceiling is 37%.

**What would.** An opportunity needs all four:
- **a context that accumulates** across tool calls, i.e. step-wise control;
- **many physical waits** per mission, tens of seconds to minutes each;
- **short per-step decodes**, low or no thinking per step, so prefill is a real share of LLM
  time;
- **memory pressure**: several drones per edge box, or perception and simulator models sharing
  the device memory (H4).

aerogen at low effort meets all four. On the WS it showed 93% prompt reuse, 88% of time
waiting on flights, and 33% of LLM time saved (12% private state).

**P1's tasks under a step-wise agent** (all *estimates*):

| Tasks | Steps per mission | Wait per step | Mission | Verdict |
|---|---|---|---|---|
| B5–B37 | 2–4 | seconds | < 1 min | Too small: nothing to retain over |
| A3–A20 (figure-8, squares; 5–9 m legs) | 5–16 | a few seconds | 1–3 min | Weak: many steps, but the waits are too short to matter |
| F1 farm perimeter | 5–6 | ~15–25 s | ~1–2 min | Weak |
| **D1–D3 deliveries** | ~6–14 (transit legs, descents, hovers) | 30–120 s | ~5–13 min | **Good:** the regime aerogen measured |
| **Lawnmower, concentric circles** | ~20–150 (sweep strips; circles as waypoint arcs) | 30–120 s | ~15–25 min | **Strongest:** contexts outgrow an edge KV pool, with many long waits |
| Radio towers, cable, search-and-track | many, with perception in the loop | variable | 20+ min, open-ended | Most realistic, exercising H4, but the most work (worlds plus analytics models) |

## 6. Three options for P5

There are two separate questions here.

1. **Is there anything to manage on P1's agents as they are?** No. Even dropping all state at
   every wait costs at most ~2% on the long tasks. That is a finding, and it should be reported.
2. **P5's research question is how to manage kept state that has value.** On P1's agents kept
   state has no value, so the question has nothing to apply to. P5 then has three honest
   choices:

| Option | Keeps | Changes | Strengths | Weaknesses |
|---|---|---|---|---|
| **A. P1's agents as they are** | P1's tasks and agents | P5's question, which becomes decode-side scheduling: admission and batching of long thinking decodes, and thinking budgets | Fully P1-aligned, needs no new agent, and the data supports it: 78% of tool-calling LLM time is in calls that hit the 32K cap | No longer about kept state; close to existing work (KAIROS) |
| **B. A step-wise agent on P1's tasks** | P5's question; P1's missions, worlds and devices | Only the agent loop: one flight action per tool call, with a growing conversation | Keeps both P1's tasks and P5's question. Step-wise tool calling is the standard agent design, and every prior KV-retention system evaluates on it | Not P1's agent. Depends on short per-step outputs (risk 2 below) |
| **C. Standard agent benchmarks** (τ²-bench, BFCL) with injected waits | P5's question | The workload | Easy to compare with prior work | Loses the drone story; every wait is synthetic |

**Why I suggested B.** It changes the fewest things that matter. It is not a way of tuning
P1's agent until P5 has something to do: it runs a different, widely used agent design on P1's
own missions. P1's agents stay in the evaluation as the case where a controller must do
nothing.

**Where B could be wrong:**
1. **The "manufactured opportunity" objection.** A reviewer may say we picked the agent that
   gives our system work. The defences:
   - step-wise tool calling is the standard agent design;
   - P1's own deck lists tool calling and ReAct, although both of P1's versions act on whole
     programs;
   - search and tracking missions naturally need decisions during the flight;
   - P5 would report both designs.

   This is the professor's call.
2. **B only works if each step's output stays short.**
   - aerogen already falls from 37% to ~20% at medium or high effort.
   - On the Thor, a model that wrote ~2K tokens per step would have a ceiling of ~8%; at ~8K
     tokens, ~2%. That is back where P1's agents are.
   - Nobody has measured how much P1's kind of model writes per step. That is the deciding
     number (§7).
3. **Memory pressure is a deployment question.** With one drone per device everything fits, so
   keeping everything is free whatever the agent. B becomes interesting only with several
   drones per box, or with perception models sharing memory.

## 7. The deciding test

Before anyone commits to B, measure what a thinking model writes per step on step-wise D1
missions:
- **Setup:** run the aerogen-style agent on P1's D1 task in P1's delivery world on the WS
  kinematic sim, with a thinking model (Qwen3.5-9B, already on the WS), thinking on and off.
  K2-Horizon-7B at low and high effort serves as a second model.
- **Report:** output tokens per step, prompt growth, realized cache reuse, and the resulting
  ceiling.
- **Decision rule:**
  - if per-step output stays at a few hundred tokens, B holds;
  - if it runs to thousands, A or C is the honest direction.

Results: [`../2026-10-02-stepwise-d1/README.md`](../2026-10-02-stepwise-d1/README.md).

## 8. What can be used under each option

1. **All 16 tasks, as P1 runs them: the contrast case (every option; the main workload in A).** This needs no work, and the data
   exists. A P5 controller must recognise that retention is worthless here and stay out of
   the way. The real energy lever on these tasks is the thinking budget, not retained state.
2. **D1–D3 and F1 with a step-wise tool-calling agent: P5's near-term opportunity workload (B).**
   - These are P1's own tasks, prompts and world.
   - aerogen's agent can probably take them by switching to the delivery world prompt and a
     matching world envelope (both are config overrides). This is not yet tried.
   - They would run now on the WS kinematic sim, with the pacing hook, and later in Gazebo
     through aerogen's `ros2` backend on the devices.
   - Effort: days.
3. **Lawnmower and concentric circles: the "huge" tasks.** P1's prompts for them already exist
   (2026-09-04). On the WS kinematic sim they are cheap. In P1's Gazebo stack they need a
   large-farm world (a `WorldSpec` change).
4. **Radio towers, cable, search-and-track: later.** They need Gazebo worlds and perception
   models (mayankarya's DeepStream/YOLO work). They are the best fit for the edge-only
   question of models competing for memory.
5. **CLGSCE tasks with a step-wise agent: low priority.** P1's CLGSCE MCP server exposes only
   whole-program tools (`execute_and_observe`, `validate_navigation_task`), so granular tools
   would have to be added over the AirSim wrapper. Even then the legs are short.

## 9. Questions for the mentor

1. **Which option: A, B or C (§6)?** The test in §7 should come first, if B is on the table.
2. **Which 8 AeroEval tasks?** I found 5 original missions and 6 P1 variants (§3).
3. **Is a step-wise paradigm in P1's scope?**
   - P1's deck lists tool calling, ReAct and Reflexion.
   - P1's tool-calling and ReAct agents both act at the level of whole programs.
   - Would P1 accept, or want, a ReAct/tool-calling agent with flight-level tools?
4. **Can P5's main workload be P1's AeroEval tasks run by a step-wise agent** (aerogen-based,
   with mayankarya's OK), keeping P1's agents as the contrast?
5. **How many drones should one edge box serve?** That sets the memory pressure.

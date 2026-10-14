# P5 plan: follow the energy

Status: **the current plan from 14 Oct 2026** (D24). It replaces [`OPTIONS_PLAN.md`](OPTIONS_PLAN.md) v2.0, which
stays as the record of 5–13 Oct. The flow is drawn in the artifact "P5 Follow-the-Energy Flow"
(https://claude.ai/artifact/VGdZ6v2fwacEiNRTc8ceDP, private). Task status: [`TRACKER.md`](TRACKER.md).

## 1. The direction (D23, the meeting of 14 Oct)

- **Follow the energy.** Find where P1's agents spend board energy, how much of it is avoidable, and what a serving
  system can do about it. Focus: energy, decode, and how well the device is used.
- **Out:** keeping or dropping an agent's state while it waits for a tool. The literature is saturated, and on P1's
  workloads it is worth 3.2% at most (RET-J1, board).
- **Allowed:**
  - KV memory as capacity (who fits, at what precision);
  - several agents per box;
  - changes to P1's agents that keep their core idea, each justified in the paper.
- **What the professor asked for:**
  - Does an opportunity exist, and what is the best achievable result?
  - A proposal, not a recommendation: a setting a user picks once is not a contribution (his example: FP8 KV).
  - Relevance: how the paper reads.
- **Target:** OSDI, abstract 1 Dec, paper 8 Dec 2026.
- **People:** P5 is Sandesh and his mentor. Her drone runs (on the units since 13 Oct, in `p5_osdi/`) and Sandesh's
  traffic work serve one thesis, which must hold across agent families.

## 2. Goal until the next meeting (date not fixed)

Bring three things:
1. **The energy waterfall** for P1's traffic and drone agents: where the energy went, how much was avoidable, and the
   best achievable energy per success on each board.
2. **A one-page thesis:**
   - the bucket we attack;
   - why the best fixed configuration (B*) cannot capture it;
   - the mechanism;
   - the claim, with a number.
3. **P1's traffic agent running live**, checked against P1's runs. First evidence for the mechanism if time allows.

## 3. The flow

P1's logs → waterfall → levers for each bucket → Q1 and Q2 for each lever (§5) → thesis on the largest bucket that
passes → mechanism → evaluation on traffic and drones, at one agent and at several → paper.

If no lever passes Q2, the fallback is a limit study (a measured design space).

## 4. The waterfall (definitions fixed before the numbers)

**Data**
- P1's final data (repository `0cc2311a`) with P1's selection rule (`analysis/p1_selection.py`).
- Traffic first (17 configurations), then drones (8).
- The mentor's drone runs form a separate column, never mixed with P1's.

**Measures**
- **Energy:** P1's board power integrated over each run, as in CAP-J1's anchor check.
- **Success:** P1's grade.
- **Headline metric:** energy per success = total board energy of all runs ÷ passing runs, per configuration.

**Buckets.** Each joule is counted once, in this order:

1. **Failed runs.** The cause is the first that matches: window overflow → a capped call → completed but graded
   wrong → other (tool fault, timeout). Two numbers each:
   - all their energy (the oracle bound: stop had we known at the start);
   - the energy after the first warning sign (the detectable bound).

   The warning signs are written into the analysis code before it runs, for example:
   - the first capped call;
   - a second consecutive cap;
   - the context past 80% of the window;
   - a repeated tool error.
2. **Degenerate decode in passing runs:** capped calls, minus what a median finished call of the same role costs.
3. **Idle during tool waits** in passing runs: board energy between LLM calls (on drones this includes the
   simulator, which P1 ran on the board).
4. **Prefill** in passing runs: call energy apportioned by prefill time.
5. **Decode in passing runs**, split two ways:
   - the batch-1 cost: what one-at-a-time decoding costs above decoding at batch k, priced with the board's cost
     curve at k = 4 and 8;
   - the floor: the same decode at batch k.
6. **Other:** the rest of each run (harness, setup).

**Output**
- One stacked figure per family (configurations side by side) and one table.
- The code lives in `analysis/` and is committed before its results are read.
- It is stated with its two caveats: batch k is only reachable if the pool allows it, and the oracle bound cannot be
  reached.

## 5. Decision rules

- **B\*, the best static configuration:** P1's agent and flags, plus every fixed setting that helps:
  - model-card sampling;
  - FP8 KV where the pool binds and the pass rate holds;
  - the best fixed number of agents per box;
  - P1's output caps.

  Each part is measured, not assumed: sampling's pass rate from the mentor's sample banks, FP8's from an FP8 bank.
- **Q1:** a lever is a fixed setting if one value is best in every condition we test (load, agents per box, task
  phase, model).
  - Fixed settings join B*.
  - They are reported as recommendations and offered to P1.
- **Q2:** a lever whose best value changes at run time is a candidate mechanism if a policy that adapts beats B* by
  **15% or more in energy per success, at the same pass rate**, and by more than the run-to-run spread.
  - It is bounded first from the logs and cost curves.
  - It runs on a board only after it passes the bound.
- **Fallback:** if no lever passes Q2, the paper becomes a limit study. Tell the professor as soon as that is clear.

## 6. Working rules

What went wrong before, and what we do now:

| Before | Now |
| --- | --- |
| Five options compared, no thesis | One thesis; the options are levers |
| Runs asked "is option X dead?" | Every run answers a question the thesis needs |
| Results against P1 as run | Results against P1 as run **and** against B* |
| A 143-slide deck and a 19-chapter guide, kept in sync | One figure and one page per step; the deck and guide stay frozen until the next meeting's materials |
| Two plans for one project | One plan (this file), shared with the mentor |

Kept from before:
- definitions and rules fixed before the data;
- every number labelled with its source, and "one run" where it is one;
- the device rules of `AGENTS.md` §4 for every P5 run.

New: each step has a time box. A step that overruns is reported, not silently extended.

## 7. Schedule

| When | Track A: analysis (WS) | Track B: platform |
| --- | --- | --- |
| 15 Oct | Plan agreed with the mentor; traffic waterfall code | Copy the traffic agent's code from Thor-2 |
| 16 Oct | Traffic waterfall done | Camera data after P1 replies (only what the final tasks use) |
| 17 Oct | Drone waterfall (P1's and the mentor's runs); Q1 and Q2 bounds | Bring the agent up (WS or an Orin) |
| 18–19 Oct | Thesis page; agreed with the mentor | Check one agent against P1's runs |
| After | Mechanism prototype; B* measured on a board | Ready for live evaluation |

Who does what:
- Sandesh (with Claude): traffic and the waterfall.
- The mentor: drones.
- Both: the thesis.

## 8. Decisions

| ID | Decision | Source |
| --- | --- | --- |
| D23 | The meeting of 14 Oct. Follow the energy (energy, decode, use of the device). Retention during tool waits is out. KV as capacity, several agents per box and justified agent changes are allowed. Target OSDI (abstract 1 Dec, paper 8 Dec) | Sandesh's account, 14 Oct |
| D24 | This plan replaces OPTIONS_PLAN v2.0 as the one current plan | Sandesh, 14 Oct |
| D25 | Results are measured at one agent and at several per box; the thesis states where it holds | Sandesh, 14 Oct |
| D26 | The waterfall and the thesis run in parallel; traffic before drones | Sandesh, 14 Oct |

## 9. Open items and carried-over issues

- **P1's traffic agent was found on Thor-2**, in `/media/ssd/Deepstream-Yolo-upstream/camera_query_agent/`:
  - `agent.py` (edited 6 Oct) and `agent_reflect.py`;
  - the tool servers `camera_mcp.py`, `sandbox_mcp.py` and `web_mcp.py`;
  - `deploy/`;
  - 60 GB of camera data in `fixtures/`.

  The code was copied to the WS on 14 Oct (`~/work/p1/traffic_agent/`; needs in
  `reports/2026-10-14-traffic-agent/`); the data waits for P1's reply.
- **The mentor's device runs.** Agree a common protocol for joint results:
  - a single-agent point run with the same server and driver (not P1's recorded runs);
  - the pool pinned with `--max-total-tokens`: two Thor-1 launches with identical flags gave 215,865 and 296,823
    tokens;
  - the simulators' own power separated from serving energy;
  - outputs on the USB P5 folders, results copied to the WS.
- **A-J1's "greedy is not repeatable" is unconfirmed.** Its replay did not clear the prefix cache between calls.
  Low priority while sampling is in B*.
- **Agents per box:** does the professor want to set this? D25 measures both until he does.

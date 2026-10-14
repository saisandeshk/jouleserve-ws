# Traffic candidates experiment (CAND-T1): plan and rules, fixed before the data

**15 Oct 2026, 00:40 IST.** This plan was written and committed before any run of this experiment. It tests the core of thesis
draft 1 (`planning/THESIS.md`) on the second agent family. It mirrors the mentor's first-of-k gate on drones.

## Question

On P1's traffic agent, does sending each agent call as k sampled candidates and keeping the first to finish (first-of-k)
cut board energy per successful task? The comparisons:
- against one sampled answer;
- against P1's greedy protocol;
- at an unchanged pass rate.

## Setup

- **Board and model:**
  - Thor-2;
  - P1's gemma-26B-A4B traffic server settings (`env/thor2/serve_gemma.sh`);
  - P1's agent, unchanged (`env/thor2/traffic_run.sh`).
- **Arms:**
  - **G, greedy (P1's protocol):**
    - P1's 3 recorded Thor runs per task;
    - plus our own greedy runs from TRF-3 on the same server, on the 9 tasks they cover.
  - **S1, one sampled answer:** Gemma's model-card sampling (temperature 1.0, top_p 0.95, top_k 64) through the P5
    gateway, k = 1.
  - **F4, first-of-4:** the same sampling, 4 candidates per agent call. The first to finish on its own wins; the others
    are cancelled.
  - The vision tool's calls go straight to the server in every arm.
- **Tasks:** instance A, 12 tasks, chosen from P1's recorded greedy outcomes before any of our runs.
  - **Controls (P1 3 of 3):** peak-count, class-mix, busiest-hour.
  - **Mixed (P1 1–2 of 3):** avg-per-minute, special-vehicle, heavy-vehicle, viz-class-vs-dwell, peak-start-end,
    viz-stacked-area.
  - **Failing (P1 0 of 3):** day-summary, first-last-sighting, unusual-vs-median.
  - **Left out:** viz-occupancy-heatmap. All 3 of P1's runs hit the 20-step limit at about 367 kJ, about 85 minutes
    each.
- **Repeats and order:** 2 repeats of S1 and F4, interleaved as S1 r1, F4 r1, S1 r2, F4 r2 to spread drift. That is 24
  runs per arm.

## Measures

- **Pass:** P1's grader (`traffic-grader-2026-10-07a`, run from a copy; it reproduces 336 of 336 of P1's Thor gemma
  grades).
- **Energy:** board energy per run (P1's sampler, `workflow_energy_j`), including every candidate's decode.
- **Energy per success:** the arm's total energy over its passes.
- **Other:** time, LLM calls, capped calls. From the gateway log:
  - how often the winner was not the first candidate;
  - the tokens decoded by cancelled candidates.

## Decision rules (fixed now)

1. **F4 against S1:**
   - **"First-of-k pays on traffic"** if F4's energy per success is at least 30% below S1's, with passes not lower by
     more than 1 of 24 (the mentor's G2 threshold).
   - **"Weaker"** for 10–30%.
   - **"Absent"** below 10%, and the thesis's candidates core loses its traffic support.
2. **S1 against G:** reported as measured: pass rate, energy per success and capped calls.
   - It is labelled cross-setup for P1's recorded runs, since they come from P1's box and P1's time.
   - It counts as same-setup where TRF-3 shows our greedy runs match P1's within their spread.
3. **Noise:** 12 tasks × 2 repeats is small. Differences of 2 passes or fewer are not read as effects. Each arm's
   repeat-to-repeat spread is reported beside its result.

## Amendment, 15 Oct 01:00 IST (before any CAND-T1 or CAND-T2 data)

**Why:** the bank analysis (`README.md` here, from the mentor's drone banks) now shows the following:
- **On Thor's mixture-of-experts gemma-26B:** first-of-4 raises the pass rate but costs 12–25% more energy per success,
  because extra streams are expensive (1.81× per step at 4).
- **On a dense model (E4B on the Orin):** it cuts energy per success by 70%.

So the dense case is the informative test on traffic, and a second gemma repeat is worth less than a dense arm.

**Changes:**
1. **CAND-T1, gemma-26B:** one repeat of S1 and of F4, not two. The tasks and the rules are unchanged, but with 12 runs
   per arm only differences larger than 2 passes or 25% energy per success are read.
2. **New CAND-T2, granite-4.2-8b (dense, P1's Thor flags), on Thor-2:**
   - **Calibration first:** its cost curve (`env/thor2/costcurve.py`; widths 1–16 at 4K and 16K contexts; the
     mentor's design, our sampler).
   - **Arms:** S1 and F4, one repeat each.
   - **Tasks:** 10 instance-A tasks, chosen now from P1's recorded granite runs.
     - Controls (P1 3 of 3): busiest-hour, avg-per-minute, stalled-vehicle.
     - Mixed or failing, several with capped calls: peak-count, class-mix, viz-class-vs-dwell, unusual-vs-median,
       peak-start-end, compare-periods, day-summary.
   - **G:** P1's 3 recorded Thor granite runs per task (cross-setup).
   - **Rules as for CAND-T1:**
     - "First-of-k pays on traffic" if F4's energy per success is at least 30% below S1's, with passes not lower by more
       than 1.
     - "Weaker" for 10–30%.
     - "Absent" below 10%.
     - Differences of 2 passes or fewer are not read as effects.
3. **Run order on Thor-2** (`env/thor2/cand_chain2.sh`): TRF-3 → gemma S1 → gemma F4 → granite server and cost curve →
   granite S1 → granite F4.

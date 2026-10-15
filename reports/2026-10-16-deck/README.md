# Deck section of 16 Oct, and the recheck of the drone campaign

**16 Oct 2026.** The reference deck (Slides artifact, private) gained a section "Drones and traffic together" (18 slides,
`jsc-*`) and its appendix (11 slides, `jsa-*`), placed after the drone campaign's own slides (`p5d-*`, left unchanged).
Deck version 207, 98 slides. Slide sources are in git-ignored `data/p5deck_v3/project/`; check them with
`python3 env/render_slides.py data/p5deck_v3 <out> [ids]`.

## Figures

| Figure | Made by | Data |
|---|---|---|
| `figures/waterfall.png`, `costcurve.png`, `candidates_traffic.png` | `analysis/deck_figures_1016.py` | our waterfall (P1's final data), cost curves (Thor-1, Orin-32-1 from the drone campaign; Thor-2 ours), CAND-T1/T2 |
| `figures/drone/{packing,loops,orin_wait,orin_granite_16bit}.png` | `recheck.py` (this folder) | the drone campaign's raw runs, recomputed |

## The recheck

`recheck.py` recomputes the drone campaign's numbers from read-only copies of its runs (WS
`~/work/mentor/p5osdi_20261016/`, SHA-256 in `SHA256SUMS`; copied 16 Oct 00:20–00:25). Output: `recheck.json`. Energy is
the trapezoid of the 200 ms board samples over the run's window, as in P1's harness.

**Confirmed** (to the stated precision):
- P1's single drone (Thor, gemma-26B, Reflexion, 63 runs of 21 missions): 17.3 expected passes, 131.1 kJ per success.
- Fleets on Thor: Reflexion 16/21 at 80.3 kJ (4 drones), 17/21 at 58.2 kJ (8); step-wise 10/14 at 130.5 kJ, 11/14 at
  103.2 kJ. Orin-32-1, E4B with P1's tool-calling agent: 35.7, 25.7, 29.0 kJ at 2, 4, 8 drones (17/36 each).
- Calls cut at 32,768 tokens: 94 in the six Thor runs, 4–20% of calls and 64–84% of LLM time. A repeated-text check
  flags all 94 (median trigger 5–7K tokens); stopping there frees 62–71% of LLM time (step-wise), 43–50% (Reflexion).
- Prefix reuse 92–96% for the step-wise agent, 22–26% for Reflexion (token-weighted).
- E4B on one Orin: a request is queued 0, 31, 63% of the time at 2, 4, 8 drones; queued with the pool ≥ 90% full 0, 10,
  21%.

**Different from the campaign's slides** (the deck uses the recomputed values):
1. **Every fleet run was greedy.** P1's tracer forces temperature 0, top-p 1, top-k 1, seed 42 and `max_tokens` 32,768
   on every call; the step-wise agent's requested sampling (temperature 0.6 on granite) never reached the server. The
   sample banks did sample (temperature 1.0, top-p 0.95, top-k 64, all 336 records). So the loop savings are measured
   against greedy decoding; on the same model, sampling looped on 0 of 50 of P1's loop prompts (A-J1).
2. **P1's time limits were not applied** in the fleets (2 h per mission, 30 min per call). Applied afterwards: Reflexion
   11/21 at 116.8 kJ (4 drones), 10/21 at 99.0 kJ (8); step-wise 7/14 at 186.4 kJ, 10/14 at 113.6 kJ. Eight drones
   still beat one (131 kJ), by 1.3× instead of 2.3×. The slowest mission grows from 84 min (one drone) to 208 min.
3. **Granite's 16-bit pool is 21,351 tokens**, not 22.7K. One drone's conversation alone reaches 21.3K; the two summed
   exceed the pool 75% of the run; 448K tokens were evicted.
4. **No FP8 granite run is in the copy**, so "44.9K tokens" and "fits for the first hour" cannot be checked; the deck
   drops them.
5. Next-call timing (10.6 s + distance at 2 m/s): within 4% for 188 of **193** moves (not 243). It holds by
   construction: the agent hovers 10 s and the simulator flies at 2 m/s.
6. Conversation growth: median **184** tokens per step over **682** step pairs (not 761); the next prompt's size is
   within 4% for 9 in 10 steps, but a no-growth guess does almost as well (84–95%).
7. Read-back of 15K tokens: E4B 15.3 s; the "20–30 s" is not reproduced, and granite's few calls do not fix it.
8. Retries rescued 2 of 36 missions on E4B (5.6%) but 17–27% on granite (not 0–7%).
9. The loop detector's exact rule is not in the copy. Our rules give 0–5 false alarms in 90 long normal calls,
   depending on the block size and repeat count.

**Caveats that stay:** one repeat per mission; the fleet server's pool is 296,823 tokens with 64 requests allowed,
against P1's 80,000 and one.

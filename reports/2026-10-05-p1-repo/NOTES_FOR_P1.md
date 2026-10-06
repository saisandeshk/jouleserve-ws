# Notes for P1 (EdgeAgentBench) from P5's reading of the repository

**2026-10-05 · Sai Sandesh (P5)**, prepared with Claude Code. Sent to P1 by Sandesh on 2026-10-05.

We read P1's repository read-only (`dream-lab/edge-agent-bench` at `3c47ebc`, 4 Oct 19:02) and reran
P5's analyses on it. P1's own numbers reproduce from the same files: cache hit rates, prefill shares, capped
shares, the loop rule and the stop-at-first-cap bound. Five points may matter for the paper before Sat 10 Oct.
Each has the number, how we got it and the code that reproduces it (P5's repository, `analysis/`).

## 1. `ask_vlm` is a burst of requests to the agent's own server, not a second model

- **What the paper says** (§7.2, appendix C): the vision tool runs "a second model on the same GPU".
- **What the vitals show** (1 s KV samples, during `ask_vlm` windows only): the agent's own SGLang
  server runs many requests at once. Outside the windows, more than one request runs in at most 0.4% of
  samples.

  | Configuration | Running requests (median / max) | Peak KV in use (share of pool) |
  | --- | --- | --- |
  | Thor gemma-26B | 18 / 45 | 20% |
  | Thor Qwen3.6 | 10 / 12 | 1% |
  | Orin 64 gemma-26B | 8 / 20 | 99.5% |
  | Orin 32 gemma-E4B | 23 / 24 | 73% |

- **On Orin 64 gemma the burst evicts the paused agent's context.**
  - All 62 calls that follow an `ask_vlm` miss their cached prefix: 90% of the expected prefix is
    recomputed, which is 0.6% of LLM time.
  - After any other tool, 0 of 498 calls miss.
  - Orin 32 E4B: 12 of 50 miss. Thor: none.
- **This also qualifies "batch size is one" (§2).** Traffic runs are one agent at a time, but not one
  request at a time.
- Code: `analysis/p1_opportunity.py` (`ask_vlm_bursts`, `after_tool_cache`). Figure:
  `figures/vlm_burst.png`.

## 2. The loop rule misses long-period loops

- **The rule** (`insights_why.py`): calls of at least 2,000 tokens whose last 6,000 characters compress
  below 10%. On drone Thor Reflexion it flags 94 of 122 capped calls (77%).
- **What it misses.** 27 of the 28 calls it misses compress to 0.10–0.18 over that window. They are loops
  with a longer period.
- **An online detector** catches them. It compresses the last 4,000 and 16,000 characters every 1,000
  characters and fires after 3 checks below 10%.
  - It flags 121 of 122 Reflexion capped calls, and 127 of 127 Thor tool-calling calls capped at 32,768
    (our copy of that sweep).
  - It flags none of the 173 long calls that finished on their own.
- **Consequences.**
  - "38.7% of capped calls loop" understates the drone case.
  - Stopping each call where the detector fires would save 43.5% of the Reflexion cell's board energy
    (upper bound) and stop no call that finished on its own. The first-cap rule saves 50.2% but loses 22
    passing runs.
- Code: `analysis/p1_caps.py` (`p1_rule_missed_ratios`), `analysis/p1_loops.py`.

## 3. The drone Orin 32 "capped calls" are evaluator calls at 1,024 tokens

- 88 of the 93 capped calls in the gemma-E4B drone cell are thinking-off evaluator calls that hit a
  1,024-token cap while echoing JSON state. Their zlib ratio is about 0.35, so they are not repetitive.
  They are the first capped call in 47 of 49 runs.
- **So two numbers measure evaluator truncation, not runaway reasoning:**
  - its 17% "capped share of LLM time";
  - its 41.9% stop-at-first-cap saving.
- Only its 5 capped generator calls are loops (ratio 0.008–0.010).
- Code: `analysis/p1_caps.py` (`caps` by cap value).

## 4. Orin 64's context guard truncates calls the 8,000-token rule does not count

- Traffic traces have no finish reason. `tidy.py` counts a call as capped when it reaches 99% of 8,000
  tokens.
- **The context guard lowers the granted budget** when the window is nearly full (`token_budget.granted_max_tokens`).
  Calls that end at the lowered budget are not counted:
  - all 66 capped calls on Orin 64 gemma (13% of its LLM time; P1 reports 0);
  - 22 more on Orin 64 granite;
  - 18 on Orin 32 granite;
  - 12 on Orin 32 E4B.
- These are capacity cut-offs, not runaway decoding.
- Code: `analysis/p1_repo.py` (capped = output ≥ 99% of the granted budget).

## 5. Devstral's prefix cache is off, and Orin 32's cache hits are not reported

- **Devstral** (drone, Orin 64): 0 cached tokens on every call, and the server's own hit rate is 0
  throughout. Yet 57% of each prompt's text repeats an earlier prompt in the same run.
  - Devstral does not think (median 112 output tokens per call), so prefill is 20% of its LLM time.
  - A working cache would save about 8.7% of its LLM time.
  - This bears on open question Q-D7 and on the paper's Devstral prefill figure (22.7%).
- **gemma-E4B** (drone, Orin 32): the server's hit rate reaches 0.999, so its cache works. Only the
  per-call `cached_tokens` field is missing.
- Code: `analysis/p1_opportunity.py` (`drone_prefix_reuse`).

## Smaller data notes

- **Traffic text gaps.** When the 8K cap hits inside a tool call, the parser drops the partial call
  (arguments `"{}"`), so about 7,400 tokens of text are lost.
  - This applies to most capped gemma calls: 137 of 158 on Thor, 75 of 76 on Orin 32 E4B.
  - 9 Thor gemma traces have no assistant turns.
  - Loop shares on traffic are therefore lower bounds.
- **Repeated caps.** On traffic gemma the waste is a cap inside a tool call followed by a retry that caps
  again: 121 of Thor gemma's 158 capped calls follow a capped call, and 64 of Orin 32 E4B's 76.
  - Stopping a run at its second consecutive cap would save 27% and 25% of those cells' energy.
  - It would lose 1 and 7 completed runs, against 4 and 10 for the first-cap rule.
- **The 144th Reflexion run** (D2, instance 3, run 3) ends partial after a 32,768-token generator loop
  and 90,387 evicted tokens.

Full report: `reports/2026-10-05-p1-repo/README.md` in P5's repository.

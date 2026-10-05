# FailFast-RestartSmart — 0.6B monitor predicts failing SWE-agent trajectories, then restarts the same policy with an optional diff overlay

- **Source:** Fail-Fast, Restart-Smart: Early Failure Prediction and Restart for SWE Agentic Tasks; Chenyu Wang, Yunbo Lyu, ..., David Lo; arXiv preprint 2608.03222v1 (4 Aug 2026), SMU; https://arxiv.org/abs/2608.03222
- **Review depth:** partial. Abstract, introduction, Section 3 method and Table 1 / energy paragraph read from PDF text extraction; Tables 2-5 and appendix only keyword-checked. No code link found in what I read.
- **Category:** agent-level early termination plus retry (inference-time; not serving-layer)
- **Code/artifacts:** not confirmed.

## 1. Summary
- Two stages for a single active trajectory: FailFast (Qwen3-0.6B monitor with probing heads, reads observable text only, trained with terminal and dense fail-to-pass supervision) raises an alarm; RestartSmart launches a fresh same-policy rollout without prior history and offers the interrupted repo diff as an optional overlay. [paper, abstract]
- On SWE-bench Verified: saves 14.6%-20.4% of execution tokens at a 5% false-positive target across four policies; for Qwen3.6-27B, 20.4% versus 12.5% for their AgentStop adaptation. At a 25% FPR target, RestartSmart lifts Qwen3.6-27B resolution from 66.6% to 71.8%, whereas cold restart gives 66.8%. [paper, abstract]

## 2. Problem and key insight
- Failed runs are longer and loop or explore redundantly, but early termination can abort would-be successes, and failed runs may hold useful partial edits. The question is what, if anything, should cross the restart boundary. [paper, Sec. 1]

## 3. Workloads
- SWE-bench Verified, 500 instances split 350/50/100 train/val/test; policies Qwen3.5-9B, Qwen3.6-27B, Gemma4-31B and a closed-API model (resolving 48%, 66%, 62%, 67%). Monitor trained only on Qwen3.6-27B trajectories. [paper, Sec. 4]
- Token-level (execution tokens) accounting; datacenter-class GPUs; no Jetson.

## 4. Assumptions
- Step-boundary monitoring; labelled trajectories; restart is allowed (task is idempotent apart from the repo).

## 5. Controller / mechanism
- Per-step monitor + threshold calibrated to an FPR budget; restart with fresh context; diff overlay optional. Monitor <2 GB VRAM, 15x-52x cheaper per token than the 9-31B policies, ~0.1% compute overhead (their estimate). [paper]
- Table 1 (FPR 5/10/15%): FailFast recall 22.7/31.9/36.8, saved 16.0/23.3/29.5 (units as in table; policy not stated in my excerpt). [paper, Table 1]

## 6. Evaluation and reported results
- "Estimated" inference-energy and carbon savings of 14.5%-20.3% for open-weight policies, computed as saved tokens scaled by model FLOPs and minus monitor overhead; hardware-agnostic estimate, **not measured energy**. [paper, energy paragraph near Table 1]

## 7. What JouleServe-WS can take
- The framing "stop + same-policy retry" with an explicit FPR budget and the comparison of cold restart vs restart-with-carry-over; use it to design the retry policy arms for a stopped runaway call (restart, truncate-and-close, resample with sampling on).
- A baseline: step-level monitors (their AgentStop adaptation).

## 8. What JouleServe must add beyond it
- Within-call runaway handling; measured Jetson energy; engine-side implementation; retry cost accounting in energy, not tokens.

## 9. Workstation -> edge
- A 0.6B monitor costs real share on a 32-64 GB Jetson alongside a 26B model (memory and GPU contention); would need to be CPU or a non-learned signal (inferred).

## 10. Relevance to our current findings
- Supports "retry after early stop can beat both no-stop and cold restart" for agents. Our retry problem is different in kind: the loop is a decoding pathology under greedy/temperature 0, so a same-policy restart with identical sampling will likely loop again (in traffic, 121 of 158 capped calls follow a capped call). Their restart presumably changes the trajectory through context; ours needs a change of decoding settings. [inferred]

## 11. Open questions / uncertainty
- Which of their Table 1 columns correspond to which policy; code availability.

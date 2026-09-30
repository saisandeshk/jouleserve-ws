# Adaptive KV Retention — GPU-opportunity-cost tiered retention for human-approval-length pauses

- **Source:** Adaptive KV Retention for LLM Agents at Human-Approval Timescales; Minseo Choi, Ananya Joshi; arXiv preprint (cs.OS), 2608.30830v1, 2026; https://arxiv.org/abs/2608.30830
- **Review depth:** full text (arXiv HTML v1 via fetch-and-summarize extraction; formulas/numbers quoted from that, not re-verified against PDF). ID resolves and matches title. Supersedes the abstract-only prior card.
- **Category:** agentic KV retention
- **Code/artifacts:** no repository URL in the paper; experiments use internal vLLM ports. Traces: 2,161 tau2-bench trajectories (public benchmark), wait times synthetic.

## 1. Summary
- Targets agents suspended for *human approval* (minutes to hours). Retaining suspended KV in GPU costs active capacity (41% goodput drop at 72 suspended contexts); discarding costs ~10x resume TTFT. Proposes a linear three-tier cost model (HBM / host DRAM / discard) with break-evens, and a load-indexed host-TTL (`cpu_ttl(lambda)`) chosen by pre-serving calibration.
- Headline: +23-51% active-request goodput vs vLLM baselines, +22-29% vs MORI, +41-52% vs Continuum (Fig. 4, at 2x lambda_crit) [paper].

## 2. Problem and key insight
- At human timescales GPU residency is never worth it for long; the real question is host DRAM: keep everything (host-retain) until DRAM saturates, then expire host copies. Needs no per-request wait prediction, only offered load lambda and calibration.

## 3. Workloads
- Wait distributions (mean 30 min, W_ref = 1,800 s): lognormal (sigma=1); exponential; mixture 50% exp (mean 60 s) + 50% lognormal (sigma 0.7, mean 3,540 s). **Synthetic** [paper; limitation stated].
- Traces: 2,161 approval-gated trajectories from tau2-bench retail/airline (WRITE tool calls); median context 8.4K tokens (5.4K shared prefix + 3.0K private suffix); approval rate 93-96%. Context accumulates (suffix retained per session).
- Model Llama-3.1-70B bf16, TP=4, 4x H100 NVL (94 GB), 1.5 TiB DRAM, PCIe Gen5 57.5 GB/s measured; KV pool 680,768 tokens; 327,680 B/token. Validated on A100 SXM (26.2 GB/s) and L40S (27.0 GB/s). No hybrid/MoE.
- Arrival: offered load sweeps around lambda_crit ~0.236 req/s.

## 4. Assumptions
- Pauses >> seconds (tens of minutes); PCIe host tier with large DRAM (375-380 GB budget); no SSD tier modelled.
- Linear costs, calibrated coefficients; lambda is given, not estimated online; approval outcomes simulated.

## 5. Controller / mechanism
- Cost per tier j (Eq. 1): `C_j(l) = alpha_j*l + beta_j`; j = 1 HBM, 2 host, 3 discard; alpha holding rate, beta resume cost, l residence time.
- Break-evens: `t1 = beta2/alpha1` (HBM vs DRAM; H100: ~1.13 s), `t* = beta3/alpha1` (HBM vs discard; ~109 s). Calibrated: alpha1 = 0.0176 GPU-s/s, beta2 = 0.02 GPU-s (sync overhead; DMA overlaps), beta3 = 1.91 GPU-s (suffix re-prefill 0.479 s/rank x 4).
- Consequence: keep in HBM only ~1 s, then move to host; with waits ~1800 s, discard-vs-host matters.
- Expiration under host congestion: `alpha2(lambda) = max(0, lambda - lambda_crit) * beta3/C2`; `t2(lambda) = inf if lambda <= lambda_crit else (beta3 - beta2)/alpha2(lambda)`; `lambda_crit = C2/W_ref` (Little's law; ~425 host-resident contexts). Host copies discarded after t2.
- Calibration: replay held-out traces under host-retain vs cpu_ttl(lambda), pick lower-cost; cpu_ttl favored when P(W <= t*) > 0.39 (Fig. 4d), claimed distribution-shape independent.
- Engine: vLLM 0.27.1 (main), victim-exclusion patch to BlockPool (O(1) pin/unpin) used in Fig. 2 residency enforcement.

## 6. Evaluation and reported results
- Fig. 2: enforced residency at N=72 suspended contexts: goodput 2.42 -> 1.44 req/s (-41%); resume TTFT 66-75 ms resident vs 687-705 ms evicted (~10x).
- Fig. 4 (2x lambda_crit), goodput req/s ours / MORI / Continuum / vLLM+offload: lognormal 0.95/0.78/0.63/0.70; exponential 0.96/0.77/0.63/0.73; mixture 1.07/0.83/0.76/0.87. Retention: ours 38.1% (lognormal), 17.6% (mixture); MORI 24.1/21.9; Continuum 0.4/0.1.
- Baselines: unmodified vLLM (retains ~0.3%), vLLM+host offload (0.6%), MORI (policy port), Continuum (fork with *fixed 2 s TTL*, without its pause estimator, so the Continuum comparison is weak).

## 7. What JouleServe-WS can take
- The **opportunity-cost/break-even template** `t* = beta3/alpha1` as a baseline and as a way to express our own thresholds (in GPU-s or joules). Reimplement on SGLang 0.5.20: measure alpha (share of KV pool per session x time), beta3 = recompute prefill time of the reusable suffix; policy = keep radix path locked for at most t*, else release; host tier via HiCache with an expiry timer (cpu_ttl analogue) [inferred]. Effort: ~3-5 days (calibration script + timer wrapper); depends on HiCache demotion hooks.
- Calibration-by-replay methodology needing no per-request prediction.
- Goodput-under-suspended-residency experiment design (Fig. 2) is directly reusable to measure "active capacity lost to retention".

## 8. What JouleServe must add beyond it
- Energy per task (they count GPU-seconds only), real tool timescales (13-115 s sits between t1=1.1 s and t*=109 s: exactly the ambiguous zone), hybrid states, unified memory, decode-dominated agents, concurrency of active decodes.

## 9. Workstation -> edge
- Tier 2 (host DRAM) does not exist as separate capacity on Jetson: beta2 tier vanishes, alpha2 congestion analysis (C2 = 375 GB) collapses into the same pool as HBM; only tiers 1 and 3 remain, so the policy reduces to `t*` (hold vs discard). Recompute coefficient beta3 must be recalibrated per power mode. KV pool of 25K tokens (A5000) or a few tens of thousands (Orin) makes alpha1 per session huge (3K suffix ~ 10%+ of pool), moving t* down.

## 10. Relevance to our current findings
- Using their numbers scaled to us: alpha1 relative to pool is far larger on a 25K-token pool, beta3 small (prefill 1-8% of time), so t* is short: **discard** for 13-115 s waits. That agrees with our measured bound (0.3-1.7%). Their finding that retention hurts *active* capacity (41%) matches our hypothesis that pressure comes from active decodes, not paused state. Human-approval waits are 10-100x longer than our tool waits, so their host-tier machinery is out of regime.

## 11. Open questions / uncertainty
- Synthetic wait distributions; single model family; lambda not estimated online; no code.
- The 41% and 10x numbers are for a 70B/TP4 pool with 3K suffixes; not transferable numerically.
- Extraction via summarizer; verify Eq. 1 and t2(lambda) in PDF.

# Festina — energy-aware scheduling of multi-model serverless LLM serving with GPU frequency and SM partitioning

- **Source:** Energy-Aware Scheduling for Serverless LLM Serving on Shared GPUs; authors not captured in my extraction (verify on arXiv page); arXiv preprint, 2026; arXiv 2606.30391
- **Review depth:** partial — arXiv HTML read via a summarizing fetch (methods, evaluation, ablation, headline numbers); no PDF text, appendix or code read. Details below are from that extraction; verify section numbers before citing.
- **Category:** energy-aware serving
- **Code/artifacts:** no repo link found in the paper. About 2,800 lines Python/CUDA/C++ on vLLM; asyncio, pyNVML, FlashAttention, PagedAttention **[paper]**. Workloads are synthetic (ShareGPT), so no trace release needed.

## 1. Summary
- Festina co-schedules many small LLMs on shared H100s using MPS SM partitioning and DVFS, then consolidates GPUs to save idle energy. Up to 56% cluster energy reduction with SLO attainment within 2% of baselines (Abstract, Fig. 10).
- Ablations: frequency-aware dispatching 12%, runtime management 25% (Fig. 13). Overheads: profiling under 40 minutes per H100 (§3.2.1), dispatch under 1 ms at 10K GPUs (§3.3), frequency sweep 0.1 ms (§3.4).
- Relevant to us mostly as a source of the idea "SM share + clock + placement as a joint knob space" and a "slack consumption ratio". Not agent-aware.

## 2. Problem and key insight
- Serverless serving hosts many models (4 to 32) with bursty traffic; static co-location wastes energy at max clock. Insight: use per-request SLO slack to pick the (frequency, SM%) point per batch, and consolidate lightly used models so GPUs can power down.
- Unifies heterogeneous prefill and decode work through a "slack consumption ratio" (urgency).

## 3. Workloads
- ShareGPT, plus ShareGPT-ix2 (2x input length) and ShareGPT-ox2 (2x output). Scaled Poisson arrivals across 4 to 32 models and varying RPS. Single-turn chat; no agent behavior, no tool pauses, no growing context.
- SLOs borrowed from DynamoLLM: 250/100 ms TTFT/TBT (short), 400/100 (medium), 2000/100 (long).
- Models: Qwen, Llama, Yi, Mistral, 3B to 14B; 70B Llama2 in Appendix B. Hardware: 8x H100 NVLink with MPS.

## 4. Assumptions
- Output length predictable (under 5% error for 98% of cases, from prior work); offline profiling reusable per (GPU SKU, model); 5% safety margins.
- Power cubic in frequency (P ~ f^3). Device-wide clock shared by co-residents. Requires MPS and clock control (root/admin).
- Multi-model, memory not the constraint (models are small; weight swap handled via serverless keep-alive, 5-min windows).

## 5. Controller / mechanism
- **Knobs:** clock 795 to 1635 MHz (90 MHz stride); SM allocation 10 to 100% (10% stride) via MPS; prefill/decode interleaving; model-to-GPU placement/consolidation.
- **Predictors:** output-length predictor; LUT from (frequency, SM%, input length 256 to 8192) to latency and power, polynomial-interpolated from offline profiling.
- **Cadence:** global scheduler per request O(1); local scheduler per batch epoch; consolidation on keep-alive expiry.
- Energy measured with pyNVML over first arrival to last completion **[paper]**; sampling rate not stated in extraction.

## 6. Evaluation and reported results
- Baselines: ServerlessLLM, MuxServe, Dilu, Aegaeon, AegVoltana (Aegaeon + VoltanaLLM DVFS), and Festina+ (simulated HBM frequency scaling).
- Results above. Metrics: cluster energy, TTFT/TBT attainment. No task-level metrics.

## 7. What JouleServe-WS can take
- Measurement: pyNVML power integration; we should use cumulative NVML energy instead. Also the "energy from first arrival to last completion" including idle within the window is a fair accounting we can copy, reporting active and idle separately.
- Concept for offline profile: LUT of (concurrency, context length) to latency/power measured on A5000; reproducible without root using batch and context as the only knobs.
- Not reproducible: MPS SM partitioning is available without root for a process group only if MPS daemon allowed (often needs admin); clock control needs root. Baseline priority optional.

## 8. What JouleServe must add beyond it
- Multi-turn state: Festina has no notion of retained context, sessions, or tool waits.
- Task-level objective and success accounting.
- Idle attribution during tool waits (GPU idle but KV resident); Festina's consolidation timescale (5 minute keep-alive) is far longer than tool waits of seconds.

## 9. Workstation -> edge
- Jetson has no MPS-like SM partition; single small model, so multi-model consolidation is moot. Clock is exposed as coarse nvpmodel/devfreq, root-only, slow. Unified memory removes HBM-vs-host asymmetry. Porting Festina's controller is not meaningful; only its profiling methodology is.

## 10. Relevance to our current findings
- Its per-batch frequency selection targets prefill/decode SLO slack; our workloads are decode-dominated with 1 to 8% prefill, so prefill-oriented slack scheduling gives little. Long tool waits make GPU idle states more important than clock during decode.

## 11. Open questions / uncertainty
- Authors, exact section numbers, code status, and MPS granularity are unverified. HBM frequency scaling result is simulated, so do not cite it as measured.

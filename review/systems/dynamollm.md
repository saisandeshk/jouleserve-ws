# DynamoLLM — hierarchical reconfiguration of LLM inference clusters (pools, tensor parallelism, GPU frequency) for energy

- **Source:** DynamoLLM: Designing LLM Inference Clusters for Performance and Energy Efficiency; Jovan Stojkovic, Chaojie Zhang, Inigo Goiri, Josep Torrellas, Esha Choukse; HPCA 2025 (arXiv abs page lists DOI 10.1109/HPCA61900.2025.00102; confirmed); arXiv 2408.00741 (v1 2024-08-01)
- **Review depth:** partial — arXiv HTML via a summarizing fetch plus abstract page; no PDF or appendix text.
- **Category:** energy-aware serving
- **Code/artifacts:** no code link. Built on vLLM, PuLP MILP, SciPy. Uses public Azure LLM traces (Coding and Conversation; one-week and one-hour).

## 1. Summary
- Cluster manager, pool manager and instance manager reconfigure instance count, TP degree and GPU frequency per request-class pool. Headline: 53% energy, 38% operational carbon, 61% customer cost reduction with SLOs met (Abstract). Week-long simulation: 47% energy (Conversation), 56% (Coding) vs SinglePool.

## 2. Problem and key insight
- Load is diurnal (peak-to-valley 2.8x to 34.6x); best (TP, frequency) differs by request length class; static max-performance provisioning wastes energy. Reconfigure at multiple timescales while hiding reconfiguration overhead.

## 3. Workloads
- Azure Coding and Conversation traces; single-turn requests classified into 9 pools by input x output length (S/M/L each). No agent tool pauses or context growth.
- Models: Llama2-13B/70B, Llama3-70B, Mixtral-8x7B/8x22B, Falcon-180B, BLOOM. Hardware: DGX H100 (8 GPUs, NVLink 300 GB/s).

## 4. Assumptions
- SLO: P99 within 5x single-request time. Output length predictable (BERT proxy; 40% misclassification raises energy 13%). Weekly load templates predict load. Prefill compute-bound, decode memory-bound. Root access for clocks.

## 5. Controller / mechanism
- Pools: 9 length classes. TP2/4/8, clocks 800 to 1980 MHz in 200 MHz steps (profiled).
- Cadence: cluster ~30 min (scale out/in); pool ~5 min (re-shard); instance ~5 s (frequency). MILP solved with profiled energy/latency tables. Re-sharding about 50 to 100 ms over NVLink; weights cached, VMs provisioned in background.
- Energy: measured in Wh; profiled via load sweeps at each TP and clock on DGX H100; simulator for week-long runs **[paper]**. Details on node vs GPU-only power not captured.

## 6. Evaluation and reported results
- Baselines: SinglePool (TP8 max clock), MultiPool, ScaleInst, ScaleShard, ScaleFreq. Numbers above. Large gains come from combining knobs.

## 7. What JouleServe-WS can take
- Methodology: offline profiling tables of energy vs (load, config), an instance-level fast loop and slower structural loop. The "SinglePool at max clock" as state-of-practice baseline.
- Reproducible: only the load-class-aware pooling idea (route long-decode vs short sessions to different GPU; we have 2 A5000s). TP and clock are not usable (single GPU model at 7B; no root). Baseline priority: optional.

## 8. What JouleServe must add beyond it
- Agent sessions and retained state; pool by session phase, not request length; task-level SLO; edge (single device, no re-sharding).

## 9. Workstation -> edge
- No TP, no cluster scaling, no diurnal pools. Frequency loop at 5 s needs modes switching costs Jetson lacks tolerance for. Only "config table + profiled energy" survives.

## 10. Relevance to our current findings
- Its length-class pools presume request lengths and output predictability; our decode lengths (long thinking) vary widely, and per-role prompts might be a better classifier (role predicts length).

## 11. Open questions / uncertainty
- Power meter granularity, code status, and exact simulator fidelity unverified. Confirmed the HPCA 2025 venue only from the arXiv abs page.

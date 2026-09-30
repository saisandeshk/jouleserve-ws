# TAWS — thermal-aware (V/f-aware) job placement and batch sizing for LLM inference in cooling-regulated datacenters

- **Source:** A Thermal-Aware Workload Scheduler for High-Performance LLM Inference in Cooling-Regulated Datacenters; R. Lu and D. Wang (per search snippet); ACM SIGENERGY Energy Informatics Review 5(2), pp. 98-104, 2025; DOI 10.1145/3757892.3757906
- **Review depth:** abstract-only — the ACM page and the EIR page returned 403 or were not fetched, and my attempt to read the author-hosted PDF (wangdan.people.ust.hk) failed with a socket error. All content below comes from the search-result abstract; nothing about the method internals was read. A short 7-page EIR paper, so a retry of the PDF is worthwhile.
- **Category:** energy-aware serving (thermal)
- **Code/artifacts:** none known.

## 1. Summary
- Scheduler assigns LLM inference jobs to GPUs and sets execution batch sizes with awareness of GPU voltage and frequency, under datacenter cooling regulation.
- Claims (abstract): existing schedulers can raise thermal-throttling probability 10x with up to 34.2% performance degradation; TAWS gives up to 40.94% higher throughput at 41 C **[paper, abstract]**.

## 2. Problem and key insight
- Cooling standards ensure aggregate heat removal but may mismatch localized GPU heat generation under high-performance inference; heat-oblivious placement triggers throttling. Fix: model V/f and temperature when placing jobs and choosing batch size.

## 3. Workloads
- Not verified (abstract-only). Presumably simulated or profiled LLM inference jobs **[inferred]**; models, traces, hardware unknown.

## 4. Assumptions
- Datacenter with regulated inlet temperature (41 C scenario); GPUs subject to throttling; scheduler can control placement and batch size. No agents.

## 5. Controller / mechanism
- Knobs: job-to-GPU assignment and batch size, informed by voltage/frequency state. Predictors, cadence and overheads unknown.
- Energy measurement methodology: not verifiable here. Objective is throughput, not energy.

## 6. Evaluation and reported results
- Only the two abstract numbers above.

## 7. What JouleServe-WS can take
- Concept only: log GPU temperature, clock and throttle reason (`nvmlDeviceGetCurrentClocksThrottleReasons`, no root) during every run so thermal throttling is detectable on A5000. Batch size as thermal lever is available on both platforms. Baseline priority: optional (related work).

## 8. What JouleServe must add beyond it
- Edge thermal behaviour is chip- and enclosure-level with no CRAC; sessions with paused state; task-level energy objective.

## 9. Workstation -> edge
- Jetson throttles autonomously through DVFS and thermal governors; on-device this is the primary power cap (power budgets via nvpmodel, root). Sustained-throughput drift over long runs must be measured; use tegrastats temperatures alongside INA3221 rails.

## 10. Relevance to our current findings
- Our long real-time decode runs (thinking, minutes) can heat-soak Thor/Orin; throughput measured cold may not persist. Tool waits give cooling gaps, an interaction TAWS does not consider.

## 11. Open questions / uncertainty
- Everything about method depth. Re-read the PDF before citing beyond the abstract.

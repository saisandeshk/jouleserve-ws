# GreenServ — contextual-bandit router across a pool of LLMs for accuracy and energy

- **Source:** GreenServ: Energy-Efficient Context-Aware Dynamic Routing for Multi-Model LLM Inference; first author not captured (verify); arXiv preprint, 2026; arXiv 2601.17551
- **Review depth:** partial — arXiv HTML via a summarizing fetch (method, features, workloads, results, overhead, assumptions). No appendix read.
- **Category:** energy-aware serving (model routing)
- **Code/artifacts:** public: https://github.com/TZData1/llm-inference-router (Python 3.10, FastAPI, Redis, PostgreSQL, HF transformers, scikit-learn, PyTorch). License not checked.

## 1. Summary
- LinUCB router picks one of 16 LLMs (0.5B to 34B) per query from a 12-dim context (task type, semantic cluster, complexity). Reported vs random routing: +22% accuracy, -31% energy (Abstract, §6.3.1). RouterBench average accuracy 71.7%, peak 75.7% (Table 1, §6.3.6). Overhead 7.77 ms/query (§6.3.5), which is 3.9 to 21.6% of inference time depending on model. About 100 queries to adapt to a newly added model (Fig. 6).

## 2. Problem and key insight
- Multi-model serving wastes energy by sending easy queries to large models. Route by cheap query features and learn reward (accuracy minus energy) online.

## 3. Workloads
- 5 tasks x 500 samples: MMLU, HellaSwag, Winogrande, GSM8K (exact match), CNN/DailyMail (ROUGE). Single-turn, batch size 1; no agents, no tools. Pool: Qwen 2.5 (5 sizes), Mistral 7B v0.3, Gemma 3 (4), Llama 3.1/3.2, Phi, Yi-34B, bf16. Hardware: one A100 80 GB, EPYC 9354P.

## 4. Assumptions
- Stationary rewards; ground-truth quality metrics available; batch size 1; all models resident/available locally; latency estimated from max output tokens excluding queueing and model loading; linear reward in context (LinUCB).

## 5. Controller / mechanism
- Arms = models. Features: logistic-regression task classifier on embeddings, online K-Means (K=3), Flesch Reading Ease bins. Decision per request, no other knobs (no DVFS, no batching).
- Energy: **GPU-only, zeus library, integrating P(t) over inference duration (Eq. 1)**; excludes CPU/system power **[paper]**. Sampling rate not stated.

## 6. Evaluation and reported results
- Baselines: random, largest, smallest, highest-accuracy (Gemma-3-27B), epsilon-greedy and Thompson sampling. Numbers above.

## 7. What JouleServe-WS can take
- Code: reusable for a "model routing" ablation but it is off-scope for retained-state. Take the measurement of per-request energy with Zeus/NVML, and the online-learning pattern for a per-session retention decision (a bandit over {keep, offload, evict} using wait-duration bucket as context is a plausible cheap policy).
- Baseline priority: optional.

## 8. What JouleServe must add beyond it
- Multi-turn sessions with state; routing affects KV locality (moving a session loses cache); no model swap cost is modeled; quality is task success not exact match.

## 9. Workstation -> edge
- Edge devices cannot hold 16 models (unified memory is shared with KV); model loading/swap latency dominates and is excluded from their analysis. A 2 to 3 model pool (e.g. small + large) is the realistic edge analogue. Router overhead 7.8 ms is negligible vs 10 s tool waits but the embedding classifier competes for GPU.

## 10. Relevance to our current findings
- Our agents use fixed role models and long thinking decode; routing per role (e.g. small model for evaluator) is a legitimate energy lever but orthogonal. Not relevant to retained state.

## 11. Open questions / uncertainty
- First author and license unverified; energy per query at batch 1 says nothing about batched or concurrent serving.

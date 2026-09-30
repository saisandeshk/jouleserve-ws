# Parrot — Semantic Variables expose LLM-app dataflow for DAG-aware scheduling and prefix sharing

- **Source:** Parrot: Efficient Serving of LLM-based Applications with Semantic Variable; Chaofan Lin et al. (SJTU / Microsoft Research); OSDI 2024; arXiv 2405.19888 (verified); code https://github.com/microsoft/ParrotServe
- **Review depth:** full text — arXiv HTML (Sec 4–5, 7, 8). Code repo not inspected (found via search only; described as a research prototype, not maintained).
- **Category:** agent-aware scheduling
- **Code/artifacts:** microsoft/ParrotServe (research prototype, not actively maintained). ~14k lines Python total: frontend 1.6k, manager 3.2k, engine 5.4k Python + 1.6k CUDA; built on vLLM kernels/xFormers, PyTorch + Transformers. No traces.

## 1. Summary
- Semantic Variables (named placeholders for instruction/example/input/output regions) are kept unrendered in the service API, so the service builds a request DAG, deduces latency vs throughput objectives, groups requests, and detects shared prefixes [paper].
- Up to an order of magnitude gains; e.g. 11.7× on MetaGPT, 12× on Bing-Copilot-like multi-user load [paper, Sec 8].

## 2. Problem and key insight
- Request-level APIs hide dependencies, causing extra network round trips, blind per-request objectives, and lost prefix sharing.
- Insight: conventional dataflow analysis over Semantic Variables recovers producer/consumer edges; "over 94% of tokens in requests are repeated across users" in Bing Chat motivates prefix sharing.

## 3. Workloads
- Data analytics on long documents (Arxiv, >20k tokens; chain and map-reduce summarization) (Sec 8.2).
- Bing-Copilot-style (6k-token system prompt, 64 requests) and GPTs multi-user with Poisson arrivals (Sec 8.3).
- MetaGPT multi-agent software engineering: Architect -> Coders -> Reviewers, 3 revision cycles, 1–16 files (Sec 8.4).
- Mixed: chat at 1 req/s (latency) + map-reduce (throughput) (Sec 8.5).
- Static DAGs, no tools/pauses; synthetic 200–300 ms network latency per request. Models LLaMA 7B/13B (MHA); A100 80GB and 4× A6000 48GB.

## 4. Assumptions
- Static acyclic request structure; conditionals and function calls stay client-side; stable Semantic Variable positions; same tokenizer; deterministic output lengths (validated with GPT-4 for equivalence).
- Datacenter multi-tenant, many requests, all in GPU memory.

## 5. Controller / mechanism
- Per-session DAG of requests and variables; primitives GetProducer/GetConsumers/GetPerfObj/PrefixHash (Sec 4.2).
- Objective deduction (Sec 5.2): throughput annotation propagates to all producers; latency annotation propagates in reverse topological order; parallel same-stage requests form "task groups".
- App-centric scheduling (Alg. 1, Sec 5.4): topological order; prefer same task group, else co-locate with queued requests sharing a prefix, else reuse an existing context with shared prefix, else independent.
- Prefix sharing (Sec 5.3): context fork, multi-position prefix hashes, and a combined FlashAttention+PagedAttention kernel loading shared prefix tiles once.
- Engine API: Fill/Generate/FreeContext with parent contexts.
- **Preemption/admission:** no preemption; per-engine token-capacity threshold (baseline ~4k–6k; default 6144 tokens) with FIFO queueing above it [paper]. Capacity threshold is effectively its admission control.

## 6. Evaluation and reported results
- Baselines: FastChat with vLLM/HuggingFace; vLLM paged attention for prefix; latency-centric (2k cap) and throughput-centric baselines.
- Chain summary 1.38–1.88× (2.38× under background load); map-reduce 2.37×; Bing Copilot 12× request rate on 4 GPUs; MetaGPT 11.7× vs latency-centric, 2.45× vs throughput-centric; mixed 5.5× (chat), 3.7× (map-reduce).

## 7. What JouleServe-WS can take
- Ideas, not code (vLLM-era prototype, unmaintained). On SGLang 0.5.20: RadixAttention already gives prefix sharing; the useful piece is DAG-aware objective deduction, reimplementable as a gateway that marks priority/"latency-critical" per request. Effort: ~2–3 days as a gateway with fixed known graph, but modest value over Autellix/KVFlow baselines. Optional baseline.
- Token-capacity admission cap is an easy knob to include in a sweep (`--max-running-requests` / `--max-total-tokens`).

## 8. What JouleServe must add beyond it
- Anything about long decodes, pauses, tool waits, preemption, energy, or dynamic control flow (ReAct/Reflexion loops are excluded by its static-DAG assumption).

## 9. Workstation → edge
- Ideas port (metadata + gateway). Its kernel and multi-engine machinery are irrelevant on a single Orin with small batches. Unified memory changes nothing for it since it never tiers KV. Effort low but benefit small.

## 10. Relevance to our current findings
- Weakest match: static DAGs, no tool waits, outputs sized for summarization, gains from prefix sharing (94% repetition) versus our 10–66% and prefill 1–8% of time. Its conceptual contribution (expose structure to the server) is what P1 already has for free because we control the LangGraph client.

## 11. Open questions / uncertainty
- Repo not inspected; verify default capacity and scheduling constants if we ever port it. Multi-turn Reflexion is a dynamic loop it can't express without the client submitting each iteration as a new DAG.

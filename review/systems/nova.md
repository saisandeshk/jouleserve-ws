# Nova — real-time agentic VLM serving with SM partitioning and vision-encoder weight offloading to protect KV space

- **Source:** Nova: Real-Time Agentic Vision-Language Model Serving with Adaptive Cross-Stage Parallelization; Yuhang Xu, Shengzhong Liu, Dong Zhang, Bingheng Yan, Fan Wu, Guihai Chen (SJTU, Inspur); arXiv preprint 2509.21301 (v1, 25 Sep 2025, cs.OS); https://arxiv.org/abs/2509.21301
- **Review depth:** full text via pdftotext (abstract, §I-§II, mechanism sections, §V setup, weight-offloading result paragraph). Tables/figures with numbers not all read.
- **Category:** agent-aware scheduling (VLM GUI agents) / edge-style single-GPU serving
- **Code/artifacts:** none found. Workloads: AndroidLab instruction data (public) plus a **private** real-world trace on RTX 4090 **[paper §V]**.

## 1. Summary
Single-GPU serving of GUI-agent VLMs (CogAgent-9B) with three stages: vision encode, LLM prefill, LLM decode. Nova co-runs stages on disjoint SM subsets (libsmctrl), adapts the SM split from queue load with a Pareto/M-G-1 analysis, and offloads the vision encoder's weights layer-wise to CPU so the encoder's memory does not squeeze the KV cache. **[paper abstract, §I, §III-§IV]**

## 2. Problem and key insight
- Agentic VLMs use big encoders (CogAgent: 4B-parameter ViT, 1120x1120 images) whose forward pass (806.8 ms) exceeds prefill (324.1 ms) and a decode step (28.9 ms) **[paper Table I, II; RTX A6000]**.
- "the GPU memory optimization space in vision encoder inference in agentic VLMs, which compete with the pre-allocated KV cache of LLM decode. This contention can lead to cache eviction or recomputation" **[paper §I]**.
- Important correction to a first-pass reading: Nova's *elastic* part is **SM (compute) partitioning**; the memory remedy is **static-in-time weight offloading of the encoder** (keep K physical layers, 2 <= K << L, stream the rest), not a resizable KV pool **[paper §IV]**.

## 3. Workloads
- GUI agents: screenshot + instruction -> action command (30-80 output tokens). Dataset: AndroidLab Android Instruction (138 tasks, 9 apps). Arrivals Poisson up to 0.8 req/s (limit because vision+prefill take ~1.1 s) **[paper §V-A]**.
- The VLM is the agent's own model; there is no tool that calls a second model, and no multi-turn KV retention across tool pauses (single request per step) **[inferred]**.
- Hardware: RTX A6000 (48 GB), RTX 4090 (24 GB), 256 GB host. bf16: ~9 GB encoder + 18 GB LLM; KV about 70 MB per request **[paper §V-A]**.

## 4. Assumptions
- Discrete GPU with PCIe (encoder weight swap needs at most 16 GB/s vs 32 GB/s of PCIe 4.0 x16 **[paper §IV]**).
- Offered load is the only dynamic input; memory use of encoder vs KV is a design-time split.
- Agent steps arrive as independent requests; no session state kept across steps.

## 5. Controller / mechanism
- Stage workers (vision, prefill, decode) on separate CUDA streams with SM masks; SM_op = 24 for decode-vision, 30 for decode-prefill; SM_min = 12; decode SMs drop to SM_min when pending requests reach alpha (4 and 6) **[paper §V-A5]**.
- Queueing model M/G/1 to calibrate; Table V compares measured vs predicted delay.
- Encoder weight offload: "only 2 physical layers in GPU memory are sufficient to hide the latency of weight swapping, enabling over 90% memory reduction for the vision encoder, with negligible overhead" **[paper §V-D, Table VI]**.

## 6. Evaluation and reported results
- "improving the maximum latency by up to 23.3%, while keeping competitive throughput"; average latency up to 14.6% **[paper abstract, §I]**.
- Baselines: PF-Limit (prefill-first with threshold), Chunked prefill (budget 128), Multi-Stream.
- No energy or power metric.

## 7. What JouleServe-WS can take
- The **observation and Table I-style numbers**: vision encode is the bottleneck stage, and its memory competes with KV. Useful to motivate that a vision tool is not a free burst.
- The **weight offload for the vision component** as an Option D knob: shrink the tool's memory footprint rather than the KV's. On the WS (discrete memory) this is emulable; for P1's `ask_vlm` the "encoder" is inside the agent's own server, so it only applies if the VLM is a separate process **[inferred; depends on P1's answer on ask_vlm]**.
- Method for characterising bursty multi-stage requests (M/G/1 calibration).

## 8. What JouleServe must add beyond it
- Paused-session KV (Nova has none), memory budgets that move, task-level energy, unified memory, hybrid models.

## 9. Workstation -> edge
- Single-GPU, privacy-motivated edge framing, but tested on A6000/4090, not Jetson. libsmctrl SM masking depends on a specific GPU/driver stack; its availability on Orin/Thor is unknown **[inferred]**.
- On unified memory, offloading encoder weights to "CPU memory" frees no capacity; only quantising or dropping them does.

## 10. Relevance to our current findings
- P1's `ask_vlm` burst (8-45 image requests; 99.5% of the 12.4K pool on Orin 64) is the same encoder-vs-KV contention Nova names, but through the engine's own pool, and Nova does not address a paused agent whose context is in the pool.

## 11. Open questions / uncertainty
- Venue: arXiv only. Real-world 4090 trace is private. Tables IV-VI not fully read.

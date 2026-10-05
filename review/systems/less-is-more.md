# Less-is-More — fine-tuning-free dynamic tool selection for function calling on edge (Jetson AGX Orin)

- **Source:** Less is More: Optimizing Function Calling for LLM Execution on Edge Devices; Varatheepan Paramanayakam, Andreas Karatzas, Iraklis Anagnostopoulos, Dimitrios Stamoulis; DATE 2025 (accepted; dblp conf/date/ParamanayakamKA25); arXiv:2411.15399 (cs.PF), 23 Nov 2024
- **Review depth:** full text of the arXiv PDF (text extracted locally): Tables I-II, method (Sec. III), results (Sec. IV). Figures not inspected. Code: no repository link seen.
- **Category:** edge/on-device; tool-definition reduction (agent prompt)
- **Code/artifacts:** none found in the paper. Benchmarks BFCL and GeoEngine are public.

## 1. Summary
- Shows on a Jetson AGX Orin that giving the model fewer, more relevant tool definitions raises success and cuts time and power. Method: an LLM "Recommender" first writes descriptions of the ideal tools without seeing any tools; a Controller matches them by embedding (MPNet + FAISS) at three levels: single tools (L1), tool clusters (L2), or all tools (L3). [paper]

## 2. Problem and key insight
- Motivating example (Table II, Llama3.1-8B q4_K_M on Orin): 16K context, 46 tools: fail, 30 s, 27 W; 16K, 19 tools: success, 20 s, 26 W; 8K, 19 tools: success, 17 s, 22 W. "Max drop" 43% time, 19% power. A single query, so illustrative only. [paper, Table II]
- Table I: quantization hurts function calling: Llama3.1-8B full precision BFCL 63.04%, q4_0 20.43%, q4_K_M 39.57%, q8_0 44.35%; GeoEngine 63.91 / 43.04 / 56.96 / 53.04. [paper, Table I] (relevant to "weights" quantization, not KV).

## 3. Workloads
- BFCL (single function calls per sub-question) and GeoEngine (46 tools, multi-step dependent calls); models Hermes2-Pro-8B, Llama3.1-8B, Mistral-8B, Phi3, Qwen2-7B, Qwen2-1.5B in Ollama variants (q4_0 etc). Default context 16K. Not a closed-loop multi-turn agent; no thinking models. [paper]

## 4. Assumptions
- A one-time offline step builds the tool embedding spaces. Tool set is static and known. The Recommender LLM call adds latency but runs without tools in the prompt (cheap). Ollama (llama.cpp), not SGLang/vLLM.

## 5. Controller / mechanism
- Recommender -> Controller (kNN over L1 and L2, choose level, fall back to L3 on failure) -> LLM sees only the selected tools. Search level is chosen from the retrieval result, not from memory pressure. [paper]

## 6. Evaluation and reported results
- Metrics: success rate, tool accuracy, normalized time, normalized power. Per-model highlights in the text: Hermes2-Pro-8B BFCL success about 71% with time down up to 80% and power down up to 45% at best; on GeoEngine Llama3.1-8B success 56%, time -40%, power -12%; best GeoEngine: success to 68%, time -70%, power -27%. Abstract: time up to -70%, power up to -40%. Baseline Gorilla-style retrieval gave smaller gains. [paper, Sec. IV]
- Power is device-average power, not energy per task; energy per task falls roughly as time x power. [inferred]

## 7. What JouleServe-WS can take
- A baseline "tool retrieval/on-demand loading" lever: a retrieval step that selects k of N tools per call or per task phase. On SGLang, changing the tool list per call breaks prefix-cache sharing for the tool block; a hierarchical scheme (stable core tools + retrieved extras) keeps the common prefix. [inferred]
- Their Table II style experiment (tools x context window on a device) is an easy template for ours.

## 8. What JouleServe must add beyond it
- It measures per-query execution, not 8 concurrent agents sharing a KV pool; it has no KV precision lever; the decision is not made from memory pressure; no thinking-model decode; no energy per successful long task. P1's 7 tool definitions are already few, so the benefit at 7 tools is small (Their gains arrive at 19 to 46 tools). Key issue for us: with only 7 tools, tool retrieval can save at most a fraction of the 3.9-5.1K fixed prompt (the system text is also in it). [inferred]

## 9. Workstation -> edge
- Already on Orin; Ollama not SGLang. Porting is the retrieval front end only.

## 10. Relevance to our current findings
- Direct support that prompt size on an Orin costs time and power and can change correctness. Does not address window overflow (11-21% of Orin runs).

## 11. Open questions / uncertainty
- Table II is one query; the numbers are normalized; no confidence intervals; unclear tool-accuracy definition. Verify the Recommender overhead accounting.

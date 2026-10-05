# WordSaladChopper (WSC) — on-the-fly linear-probe detector of repetition chunks in reasoning traces, then chop and regenerate

- **Source:** Word Salad Chopper: Reasoning Models Waste A Ton Of Decoding Budget On Useless Repetitions, Self-Knowingly; Wenya Xie, Shaochen Zhong, ..., Zirui Liu; EMNLP 2025 main (aclanthology 2025.emnlp-main.1705), arXiv 2511.00536; code https://github.com/wenyaxie023/WordSaladChopper
- **Review depth:** partial. Abstract, Sections 1-4 and Table 1/2/6/7 skimmed from PDF text extraction; appendices (overhead details, Appendix I) and the code not read.
- **Category:** inference-time loop detection (decode-side), not a serving system
- **Code/artifacts:** public repo; experiments on 4xA100 80GB (Appendix, "We conduct all generation experiments..."). [paper]

## 1. Summary
- Defines "word salad" as chunks (split on "\n\n") that are near-duplicates of an earlier chunk (embedding similarity threshold, 0.99 for labelling). [paper, Sec. 2.1, 3.1]
- Shows that 55%+ of tokens of DeepSeek-R1-Distill models on GPQA-Diamond are word salad (Table 1: e.g. 63.37% for the 1.5B model). [paper]
- Detector: a single-layer linear classifier on the hidden state of the "\n\n" token trailing each chunk; chop after two consecutive salad chunks; append a "rescue regeneration" prompt with a fixed small budget so the model concludes. [paper, Sec. 3]

## 2. Problem and key insight
- The model "knows" it is looping (hidden states separate salad from benign chunks), so a cheap probe suffices; detection and chopping avoid the token cap being exhausted. Under temperature 0 and 0.6 salad chunks are measured separately (Table 2). [paper]

## 3. Workloads
- GSM8K, MATH-500, AIME25, GPQA-Diamond; DeepSeek-R1-Distill-Qwen-1.5B/7B, -Llama-8B and others. Single-turn reasoning, no agents, no tools, no energy or edge measurement. [paper]

## 4. Assumptions
- Hidden-state access; a trained probe per model (1,000 seed traces for data curation per Sec. 3.2); the task answer can be produced after a short regeneration.

## 5. Controller / mechanism
- Chunk-level streaming detector; chop point = start of the first of two consecutive salad chunks; regeneration with constant budget (Table 9, Appendix). Optional repeated chop-and-regenerate described in the discussion. [paper]
- Overhead claimed negligible: one hidden state per chunk, "hidden from an LRM inference perspective" (Sec. 4 discussion; details in Appendix I, not read). [paper]

## 6. Evaluation and reported results
- Table 6 (Qwen-7B, tau=0.6): accuracy original / chopped / regenerated, e.g. MATH-500 90.8 / 83.2 / 89.60, AIME25 37.92 / 29.17 / 37.92, GSM8K 89.76 / 78.24 / 89.69: the regeneration prompt recovers accuracy lost by chopping. [paper]
- Table 7 (tau=0, rows I could parse): length reductions of 31.00% to 57.34% with accuracy changes of roughly +0.4 to -2.5 points. Numbers are from text extraction of a multi-column table; verify against the PDF before quoting. [paper]
- Limitation noted in Sec. 5-ish discussion: some generations still lapse into loops after rescue regeneration. [paper]

## 7. What JouleServe-WS can take
- The detect -> chop -> short regeneration recipe is the closest published "retry after stop" policy for loops. Reimplement as a retry arm: on our detector firing, truncate the thinking and force a close-thinking token plus a bounded answer, versus restart, versus fall back to sampling.
- Their label definition (near-duplicate chunk) can score our zlib detector's precision/recall.

## 8. What JouleServe must add beyond it
- Serving-layer (engine) integration with request-state handling (KV of the chopped call, batch slot release).
- Agent tasks: a chopped tool-call body is a parse failure, not a short answer; recovery has to preserve the tool-call format.
- Energy per successful task on Jetson, and cheap text-only detection.

## 9. Workstation -> edge
- Probe cost negligible; hidden-state export is an engineering issue. Regeneration reuses the KV, which on unified memory costs no transfer (inferred).

## 10. Relevance to our current findings
- Direct precedent that repetition loops are detectable on the fly and that stopping them preserves accuracy in math QA. Their 55% salad share echoes our 67-69% energy in capped calls. They do not frame it as energy, do not use greedy-only agent settings, and do not test Gemma-4 or tool calling.
- Their data (temp 0 vs 0.6 in Table 2) bears on our greedy-decoding hypothesis; exact values not extracted here.

## 11. Open questions / uncertainty
- Accuracy recovery in agent loops (tool-call formatting). Whether detection by embeddings/hidden states beats compression ratio on earliness.

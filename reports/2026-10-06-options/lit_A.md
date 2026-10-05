# Literature review for P5 option A (decode-side energy): what is covered and what is open

Task A-E3. Written 2026-10-05. Review depth is stated per work: **F** = substantial full-text reading (PDF text extraction), **P** = partial, **A** = abstract / search snippet only, **S** = secondary summary (fetch-and-summarise pass), not re-verified. Per-system notes for the six closest works are in `review/systems/` (agentstop.md, word-salad-chopper.md, circular-reasoning-loop-prediction.md, dynasor-certaindex.md, fail-fast-restart-smart.md, edgereasoning.md). Setting: TT = training-time, IT = inference-time (decode hook, outside engine), SL = serving layer (inside a serving system), AG = agent-level (acts between LLM calls).

## 1. Table of works found

| Work | Venue / year | Link | What it does | Setting | Energy measured? | Edge? | Closeness to A |
|---|---|---|---|---|---|---|---|
| AgentStop (P) | ACM CAIS '26; arXiv 2605.15206 | arxiv.org/abs/2605.15206 | GBDT on logprobs and step features predicts failing agent runs, kills them; 15-20% less wasted energy, <5% utility drop (abstract) | AG | Yes, laptop powermetrics, replayed | Consumer laptop (M1 Max), non-reasoning mode | High (energy + agents + stop), but step-level, no intra-call, no retry |
| Fail-Fast, Restart-Smart (P) | arXiv 2608.03222 (Aug 2026) | arxiv.org/abs/2608.03222 | 0.6B monitor stops failing SWE-agent runs and restarts same policy; 14.6-20.4% tokens saved; resolution 66.6 -> 71.8% at 25% FPR | AG | Estimated from FLOPs only | No | High for retry-after-stop; step-level |
| Word Salad Chopper (P) | EMNLP 2025; arXiv 2511.00536 | arxiv.org/abs/2511.00536 | Linear probe on hidden state detects repeated chunks on the fly; chop plus rescue regeneration; 55%+ tokens are word salad on GPQA for R1-distills | IT | No | No | High for loop detect + stop + retry; math QA, hidden states |
| Circular Reasoning / LoopBench (P+S) | arXiv 2601.05693 (Jan 2026) | arxiv.org/abs/2601.05693 | Loop taxonomy; CUSUM on hidden states predicts statement loops ~1,500 tokens early | IT | No | No | Medium-high (detector, no system) |
| Wait, Wait, Wait... Why Do Reasoning Models Loop? (S) | arXiv 2512.12895 v2 | arxiv.org/abs/2512.12895 ; code github.com/microsoft/llm-looping | Theory + synthetic study: at T=0 R1-distill-Qwen-1.5B loops 76%, 32B 37%; temperature reduces looping (secondary summary) | TT diagnosis | No | No | Medium (supports greedy-causes-loops) |
| Solving LLM Repetition Problem in Production (F) | arXiv 2512.04419 (Dec 2025) | arxiv.org/abs/2512.04419 | Production batch job where repetition runs to max_tokens; greedy 77.3% repetition vs 0% with beam search early_stopping=True (+18.6% time); presence_penalty, DPO | IT / TT | Time, not energy | No | Medium-high (serving, max_tokens runaway, greedy cause); non-reasoning, vLLM |
| Dynasor / Certaindex (P) | arXiv 2412.20993 | arxiv.org/abs/2412.20993 ; github.com/hao-ai-lab/Dynasor | Probe-in-the-middle answer stability; early exit, budget reallocation, gang scheduling in SGLang; up to 50% compute, 3.3x throughput | SL | No | No | Medium-high (serving-layer early exit in SGLang) |
| DEER dynamic early exit (A+P) | arXiv 2504.15895 (v3 Sep 2025) | arxiv.org/abs/2504.15895 ; github.com/iie-ycx/DEER | Stops thinking when trial-answer confidence is high; CoT shortened 19.1% on average (intro text) | IT | No | No | Medium |
| SART (P) | arXiv 2505.13326 | arxiv.org/abs/2505.13326 | Serving framework: redundant sampling with early stopping, prune low-quality branches; up to 28.2x efficiency | SL | No | No | Medium (kills branches in a serving system) |
| Doomed from the Start (P) | arXiv 2607.06503 | arxiv.org/abs/2607.06503 | Hidden-state probe cascade aborts doomed agent episodes with recall guarantee; 60.2% fewer tokens on TextCraft at 90% recall | AG | No | No | Medium |
| Runaway is Ashamed, But Helpful (A) | arXiv 2505.17616 | arxiv.org/abs/2505.17616 | Early-exit for embodied agents trapped in loops; intrinsic EXIT instruction vs extrinsic verifier | AG | No | No | Low-medium |
| Babbling Suppression (A) | arXiv 2604.06755 (Apr 2026) | arxiv.org/abs/2604.06755 | Stops code generation once tests pass; up to 65% less energy (Python), 3-7B models | IT | Yes (GPU energy) | Small models, desktop GPU | Medium (energy + stop; code gen) |
| EdgeReasoning (P) | arXiv 2511.01866 (Oct 2025) | arxiv.org/abs/2511.01866 | Jetson AGX Orin 64GB characterisation of reasoning models, token budgets, parallel scaling; decode >99.5% of time | Characterisation | Yes (Orin) | Yes | Medium-high (edge energy + budgets; no loops, no agents) |
| The Energy Cost of Reasoning (P) | arXiv 2505.14733 | arxiv.org/abs/2505.14733 | A100 energy of test-time compute; TTC can amplify energy up to 113.48x; output length tracks comprehension | Characterisation | Yes | No | Medium |
| Where Does the Energy Go? (P) | arXiv 2609.29707 (Aug 2026) | arxiv.org/abs/2609.29707 | Full-stack energy of agents on Blackwell GPUs; thinking adds 21-75% tokens, per-token energy within 1% | Characterisation | Yes | No (datacenter GPUs) | Medium |
| Characterization of Request and Token Energy Costs (A) | arXiv 2608.28044 | arxiv.org/abs/2608.28044 | Per-request vs per-token GPU energy, long-output regimes | Characterisation | Yes | No | Low-medium |
| LoopLLM (A) | AAAI 2026; arXiv 2511.07876 | arxiv.org/abs/2511.07876 | Attack that triggers repetition loops to hit the output limit (energy-latency attack) | Attack | No (length) | No | Low-medium (shows loops are an availability and energy problem) |
| s1 budget forcing (A) | arXiv 2501.19393 | arxiv.org/abs/2501.19393 | Forcibly end or extend thinking with "Wait" / end-of-thinking token | IT | No | No | Medium (budget knob) |
| L1 / LCPO (A) | COLM 2025; arXiv 2503.04697 | arxiv.org/abs/2503.04697 | RL for prompt-specified length control | TT | No | No | Low-medium |
| ThinkPrune (A) | arXiv 2504.01296 | arxiv.org/abs/2504.01296 | RL with a token limit, iteratively tightened; halves length of R1-1.5B on AIME24 for 2% drop (search snippet) | TT | No | No | Low |
| Qwen3 thinking budget (A) | arXiv 2505.09388 | arxiv.org/abs/2505.09388 | Thinking halted at a user token threshold, stop-thinking instruction inserted | IT | No | No | Medium (knob exists in model family; we use Gemma) |
| Overthinking of o1-like LLMs (A) | arXiv 2412.21187 | arxiv.org/abs/2412.21187 | Defines overthinking, efficiency metrics, self-training fix | TT | No | No | Low |
| Stop Overthinking survey (A) | TMLR 2025; arXiv 2503.16419 | arxiv.org/abs/2503.16419 | Taxonomy of efficient reasoning | Survey | No | No | Background |
| Neural text degeneration (Holtzman et al.) | ICLR 2020; arXiv 1904.09751 | arxiv.org/abs/1904.09751 | Greedy/beam repetition, nucleus sampling | IT | No | No | Background; cited by the loop papers, **not fetched by me** |

Unread leads that appeared in search results (not verified, not reviewed): TrimR 2505.17155, Answer Convergence 2506.02536, Mid-Think 2601.07036, "Increasing the Thinking Budget is Not All You Need" 2512.19585, ePACT 2610.01784.

Drop list: nothing named in the brief failed to resolve; "certaindex/Dynasor" has the arXiv title "Efficiently Scaling LLM Reasoning with Certaindex" (the "serving reasoning programs" title in the lead is an earlier version name, not confirmed).

## 2. What is covered by prior work

- **Loops are real, frequent, and linked to greedy/low-temperature decoding** (Circular Reasoning, Wait-Wait-Wait, Production repetition paper, Word Salad Chopper). Expected escape time under greedy decoding is infinite in the production paper's Markov model [paper]; temperature lowers looping but does not remove it.
- **Online loop detection and stop with a recovery prompt** exists for math QA (Word Salad Chopper) and as early prediction (Circular Reasoning CUSUM), using hidden-state probes.
- **Early exit of reasoning** by confidence/answer stability (DEER, Dynasor), including integration into SGLang (Dynasor).
- **Early termination of agents, judged by energy** (AgentStop) and **stop + restart** (Fail-Fast Restart-Smart), both at step granularity.
- **Budgets for thinking length**: s1, L1, ThinkPrune, Qwen3 budget; EdgeReasoning evaluates them on Jetson Orin with energy.
- **Reasoning energy characterisation**, including on Jetson (EdgeReasoning: decode >99.5% of time) and for agents (Where Does the Energy Go).
- **Repetition as an energy-latency attack** (LoopLLM).

## 3. What is still open for P5 (as far as I found)

1. **A serving-layer, text-only online stop for repetition loops inside thinking calls, with energy measured on Jetson-class boards.** Closest are Word Salad Chopper (hidden-state probe, math QA, A100, no energy) and AgentStop (step level, laptop). I found no work combining engine-level hook + Jetson power rails + agents.
2. **Retry policy after a decoding runaway for agents with tool calls**, where the capped output is a tool-call body the parser drops and retry repeats the loop (our 121 of 158). Fail-Fast studies restart but for trajectory-level failure; WSC regenerates a conclusion for answers.
3. **Energy per successful task as the objective** for stop/retry/budget choices, including cost of false positives (P1's offline bound lost 22 passing runs).
4. **Measured evidence that loops dominate agent energy on edge boards** (our 33-69% shares) and that sampling settings (Gemma-4 defaults) avoid them. Wait-Wait-Wait and Circular Reasoning give the mechanism; nobody I found measures board energy.
5. **Admission/batching of long decodes on edge**: I did not find edge-specific work; SART and Dynasor are datacenter. The search was shallow here (see caveats).

## 4. Novelty paragraph for option A

Option A is partly covered. The idea of stopping reasoning that repeats itself, and of recovering with a short forced conclusion, is published (Word Salad Chopper, EMNLP 2025; Circular Reasoning, 2026), as are energy-motivated early termination of local agents (AgentStop, CAIS 2026), stop-and-restart for agents (Fail-Fast Restart-Smart, 2026), and early exit inside SGLang (Dynasor). The causal story that greedy decoding drives loops is also established. What I did not find is the combination P5 would contribute: an engine-side, training-free text detector validated against thinking-on agent traces on Jetson Orin/Thor with board-level energy, a retry policy that handles capped tool-call bodies, and energy per successful task as the headline metric, including the cost of wrongly stopping. A reviewer will ask why not simply change sampling, so P5 must report that baseline honestly. If sampling removes most loops, the contribution shrinks to a measurement paper. Novelty is moderate, mostly in the edge-energy and agent-retry evidence rather than in the detector.

## 5. Caveats

- My search was wide but not exhaustive; claims of "not found" mean not found in about 15 searches and the six deep reads. Several recent (mid-2026) preprints could be missing.
- AgentStop's 19%/3% SWE-Bench figures and Circular Reasoning's Table 1 numbers, and Wait-Wait-Wait's loop rates, come from search/fetch summaries, not my own reading of those tables.
- A power cut deleted my scratch PDFs mid-task; I re-extracted only Word Salad Chopper, Fail-Fast and EdgeReasoning afterwards. Rows for DEER, SART, s1, L1, ThinkPrune, Qwen3 and Overthinking rest on abstracts, first pages or search snippets, as marked A.

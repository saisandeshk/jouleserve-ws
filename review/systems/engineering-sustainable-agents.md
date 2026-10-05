# Engineering Sustainable Agents — energy/latency/accuracy of non-agentic vs single-, dual-, multi-agent LLM workflows

- **Source:** Engineering Sustainable Agents: A Systematic Comparison of Agentic LLMs for Developer Workflows; Merve Astekin, Yan Naing Tun, Arda Goknil, Erik J. Husom, Lwin Khin Shar, Hasan Sozer, Ratnadira Widyasari, Hui Song; arXiv preprint 2610.03010, 2 Oct 2026; https://arxiv.org/abs/2610.03010
- **Review depth:** partial. HTML read through a summarising fetch tool (two passes: setup/RQs and framework details). Not read line by line; no code read.
- **Category:** workload/benchmark (energy of agent designs)
- **Code/artifacts:** https://github.com/merveast/agent-green (replication package: code, prompts, configs, raw measurements) **[paper]**.

## 1. Summary
Factorial study of agent complexity on five software-engineering tasks: six open-weight models, two prompt strategies, three hardware platforms, four configurations (non-agentic NA, single-agent SA, dual-agent DA, multi-agent MA). Energy and latency rise with agent complexity; accuracy does not.

## 2. Problem and key insight
Does adding agents pay for itself? Finding: usually not; report energy next to accuracy.

## 3. Workloads
HumanEval (164), technical-debt detection (MLCQ, 385), vulnerability detection (PrimeVul, 386), log parsing and log analysis (HDFS, 385 each), §3.2. Models up to 7B plus gpt-oss:20b (Server-SMU only), §3.5. Hardware (Table 5): 8x H100 server, workstation with RTX A2000 12 GB, 2x RTX 6000 Ada. AG2 (AutoGen) framework. Temperature 0. Roles per task (e.g. Programmer + Refiner for code generation; Actor-Critic for debt/log tasks). Tool use beyond LLM calls not specified in what I read.

## 4. Assumptions
Process-level energy via CodeCarbon (RAPL for CPU, NVML at 1 s for GPU); idle infrastructure excluded; cold-start model load not production-like (§6).

## 5. Controller / mechanism
None. Reusable: factorial design and Pareto analysis of accuracy vs energy vs latency.

## 6. Evaluation and reported results (**[paper]**)
- Multi-agent uses on average 6.36x the energy and 6.07x the time of NA; worst case 160x (§4.2); SA 1.20x and DA 3.06x on average (abstract-level search snippet, section not verified).
- NA has highest average accuracy on 4 of 5 tasks; MA best only for vulnerability detection (§4.1).
- Of 66 Pareto-optimal configurations only one is multi-agent; 36 (55%) are non-agentic (§4.4). Energy and latency correlate at r=0.987 in log-log (§4.3.5).
- No table with per-configuration kWh and no energy-per-correct metric in what I read.

## 7. What JouleServe-WS can take
Pareto-front reporting and the practice of publishing raw measurements; a baseline narrative that "simpler designs dominate".

## 8. What JouleServe must add beyond it
Agents that act in an environment with tool results and real waits; strict success; edge boards; per-success normalisation.

## 9. Workstation -> edge
Includes an RTX A2000 workstation but no Jetson. Software-engineering tasks use short single-shot inputs; thermal/power mode effects absent.

## 10. Relevance to our current findings
- Agrees with P5 that more orchestration (Reflexion, multi-agent) costs far more energy. But its axis is the number of cooperating LLM roles, not code-as-action vs step-wise tool calls; models are small non-reasoning ones. It does not undercut P5's step-wise claim; it is a "lower-bound" precedent for the general direction **[inferred]**.

## 11. Open questions / uncertainty
Whether non-agentic baseline fits embodied closed-loop tasks at all (it cannot observe tool results). Section numbers beyond those quoted not verified.

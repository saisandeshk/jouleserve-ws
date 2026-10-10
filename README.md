# jouleserve-ws

JouleServe (P5) asks how an edge LLM serving system should manage the state agent sessions hold while they wait
for tools, to minimise energy per successful task on Jetson Orin and Thor. This repository holds its
workstation platform (2× RTX A5000), the analyses of P1's (EdgeAgentBench) drone and traffic runs, and the reports
behind the direction decision. It is research code for an independent study project at IISc.

Where to start:
- [`HANDOFF.md`](HANDOFF.md): the current state, results and open questions.
- [`AGENTS.md`](AGENTS.md): how the project works, the machines, the rules and the recipes.
- [`reports/2026-10-06-options/README.md`](reports/2026-10-06-options/README.md): the newest report, the options
  compared side by side, with P1's submitted paper and final data in its §12; the shared summary of all reports is
  [`reports/2026-10-02-p5-evidence/README.md`](reports/2026-10-02-p5-evidence/README.md).
- [`planning/`](planning/): the plans and the tracker.

Layout: `jsw/` (gateway, policies, workloads, runner, telemetry, costs), `analysis/` (one module per analysis),
`env/` (launchers and WS queues), `tests/`, `review/` (prior work), `reports/` (dated reports with their figures and
JSON results). Raw traces and run outputs live in the git-ignored `data/`.

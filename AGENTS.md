# AGENTS.md — operating guide for jouleserve-ws

Read this first, then [`HANDOFF.md`](HANDOFF.md), which records the current state and open
questions. This file changes rarely. `HANDOFF.md` changes every working session.

## 1. The project

- **JouleServe (P5)** is one of Prof. Yogesh's edge-LLM projects (P1–P10) at IISc. It is run as
  an independent study project (ISP) by Sandesh, who is the only person working on P5 for now.
  The professor makes the direction calls; our job is to bring evidence.
- **Research question:** how should an edge LLM serving system manage the *retained state* of
  agent sessions (KV cache, and for hybrid models the sliding-window or recurrent state) while
  those agents wait for tools, so as to minimize **energy per successful task** on Jetson
  Orin/Thor-class devices?
- **P5 depends on P1 (EdgeAgentBench).**
  - P1 is a closed-loop agentic benchmark for edge devices: drone and traffic workloads,
    targeting SIGMETRICS.
  - P5 uses P1's devices and workloads, and possibly P1's online trajectory predictor (if P1
    builds it).
  - P1's plan is in the deck at `~/Study/ISP/JouleServe/EdgeAgentBench_paper_plan.pptx`. The
    P1 team's current plan differs somewhat, but the idea is the same.
- **This repo is a fresh restart.** It builds **JouleServe-WS**, a reusable research platform
  on the 2×A5000 workstation, and the Track A/B evidence. The goal is to be ready when the
  edge devices come back from P1.

## 2. Read order

1. `HANDOFF.md`: state as of the last session, audit findings, open questions, next steps.
2. `planning/OPTIONS_PLAN.md` and `planning/TRACKER.md` (since 2026-10-05): **the current work plan**,
   which puts master-plan M3–M5 on hold until the direction decision (D12). G1 builds an even-handed case for
   options A–D; G2 builds their WS versions. Decisions D13–D17. The tracker holds task status.
3. `planning/JOULESERVE_WS_PLAN.md`: **master plan**. It covers architecture, milestones M0–M6,
   edge plan, risks and decisions D6–D11.
4. `planning/PLAN.md`: Track A working notes and measurements. It holds P1 trace analysis, WS
   environment facts, decisions D1–D5, and the P1 code map (Appendix A).
5. `review/systems/README.md`: Track B, with one doc per system in `review/systems/`. It has
   findings F1–F10, prioritized baselines and hypotheses H1–H5.
6. `review/*.csv` and `review/paper_cards.md`: evidence carried over from the legacy repo. Its
   "N1→N5 ladder" framing is historical.
7. The newest report named in `HANDOFF.md` (as of 2026-10-05, `reports/2026-10-05-p1-repo/`, which covers
   P1's repository, drone and traffic). The shared summary of all reports is
   `reports/2026-10-02-p5-evidence/README.md` (repo copy of the evidence Claude Doc).

## 3. Machines

| Machine | How to reach it | Role |
|---|---|---|
| Local checkout | `~/Study/ISP/jouleserve-ws` | docs, analysis, git |
| WS `resiliente-2053` | `ssh saisandeshk@10.24.32.174` | all P5 compute. 2× RTX A5000 24 GB, no NVLink, no root. Clone at `~/jouleserve-ws` |
| P1 Thor `dream-thor-1` | `ssh yash@10.24.24.79` | P1's live sweep device; source of the drone code and traces. **Read-only** |
| P1's repository clone | `data/edge-agent-bench` (local, git-ignored) | P1's raw drone and traffic runs, pipeline and paper (`dream-lab/edge-agent-bench`, cloned by Sandesh 2026-10-05). **Read-only**; rules in §4 |
| Orin 32/64, other Thors | — | allocated to P1 until their deadline |

- **Code flow:** edit locally, push to `git@github.com:saisandeshk/jouleserve-ws.git`, then
  run `git pull` in `~/jouleserve-ws` on the WS.
- `data/` and `runs/` are git-ignored, so raw traces and run outputs never go through git.
  Copy them with `rsync`/`scp`.

## 4. Hard rules

### P1 Thor: someone else's live experiment

- **Look only.** Use `ls`, `cat`, `tail`, `ps` and copies *out*.
  - Never write, install, launch, kill or restart anything there.
  - Never send requests to P1's SGLang server (port 30000), MCP server (8001) or Docker.
- **P1's busy check.** P1's harness refuses to start a run, and its sweep halts after 2
  failures, if *any* process command line on the Thor contains one of these strings:
  - `run_one.py`
  - `sweep.py`
  - `clgsce_subagents_mcp.py`
  - `gazebo_aeroeval_subagents.py`
  - `run_16_reflexion`
  - `gz_farm_test`

  That includes the remote shell of your own `ssh` command, and the argv of the `cat`, `grep`,
  `sha256sum` or `scp` you run there.
- **How to work within the busy check:**
  - Never put those strings in a remote command.
  - Filter `ps` locally: `ssh yash@10.24.24.79 'ps -eo pid,etime,args' | grep ...`.
  - Copy **directories**, never named files. For example:
    `ssh yash@10.24.24.79 'tar -C /home/yash/final_sweep -cf - _harness' | tar -xf -`.
  - To read or hash specific files, glob inside Python (`glob.glob("*.py")`) so no filename
    appears in argv.
  - **No shell globs** in Thor folders that hold those files. For example,
    `ls agent/*` in `aeroeval_gazebo_subagents` puts `gazebo_aeroeval_subagents.py` in argv.
    The check runs only when a run starts, so a stray millisecond `ls` is unlikely to hit it,
    but don't rely on that.
- **Where P1's code is on the Thor** (AeroEval agent, task sets, harness, aerogen): see
  `reports/2026-10-01-p1-task-overview/README.md` §2.
- **Timing.** Make big copies only while no sweep is running (check
  `tail /home/yash/final_sweep/<model>/sweep.log`).
- **Ownership.** Ask Sandesh before vendoring P1 code, or the `aerogen_mcp` agent by
  mayankarya (Mayank Arya, P1's analysis lead), into this repo. Keep attribution in `vendor/*/README`.
- **Credentials.** Never use credentials stored on the Thor (SSH keys, `gh` tokens, git
  credential helpers) to reach GitHub or anything else. For example, never clone P1's private
  repository through them; ask for access instead.
- **P1's checkouts.** Never run git commands inside P1's checkouts: even `git status` can rewrite
  `.git/index`. Copy a directory with `tar` instead.

### P1's repository clone (`data/edge-agent-bench`)

- **Read only.** Never edit, create or delete files in it, and never run its `make` targets or scripts in
  place: they write `analysis/outputs/` and a telemetry cache inside the clone. To run P1's code, copy it
  to a scratch directory first. Our own loader (`analysis/p1_repo.py`) reads the raw files directly.
- **Never push** (its remote is P1's GitHub) and never commit in it. `git log`/`show` are fine; `git pull`
  only when Sandesh asks.
- **Nothing from it goes into our git:** it sits under the git-ignored `data/`. Our analyses commit only
  derived numbers and our own figures. P1's own figures (from the repository or P1's decks) go only into
  `reports/*/p1_figures/` (git-ignored) and P5's private artifacts.
- **Who is who:** P1's analysis and paper are written by Mayank Arya (`mayankarya`, also the author of
  aerogen); drone runs by Aayushi, traffic runs by Priyanshu. The paper is double-blind until Sat
  2026-10-10.

### WS

- **No root or sudo.** Install only into user venvs (`uv` is at `~/.local/bin`).
- **Before launching:** check `nvidia-smi` and `tmux ls`. Run long jobs inside `tmux`.
- **Teardown:** stop every server you start, and confirm GPU memory drops back to idle
  (≈15–50 MiB).
- **NUMA pinning.** Pin each server, and its harness, to its GPU's NUMA node:
  - GPU0 ↔ cores 0–9, 20–29
  - GPU1 ↔ cores 10–19, 30–39
- **Manifests.** Record versions and flags in every run manifest. We run SGLang 0.5.20; P1
  runs 0.5.16.
- **Legacy tree.** Don't modify or delete `~/legacy/`: it holds reusable assets (§6). Copy
  out of it.
- **Sim concurrency.** P1's `reset_airsim()` runs `pkill -x thor_headless`, which would kill
  **every** concurrent sim. Any multi-session driver must reset only the sim process group it
  owns (the legacy `sim_handle.py` does this).

### Legacy JouleServe

- `~/Study/ISP/JouleServe` (local) and `~/legacy/jouleserve-ws` (WS) are the earlier P5
  attempt. Their plans are **not followed**:
  - `JOULESERVE_MASTER_RESEARCH_PLAN.md`
  - the N1→N5 ladder
  - the gate/sealed-evidence process
  - the legacy `AGENTS.md`/`HANDOFF.md`
- Open legacy files only when Sandesh points at them, or to reuse a specific asset listed in §6.

## 5. WS serving recipe (verified 2026-09-30)

```bash
L=~/legacy/jouleserve-ws
export LD_LIBRARY_PATH=$L/.venv/lib/python3.11/site-packages/nvidia/cu13/lib:$LD_LIBRARY_PATH
CUDA_VISIBLE_DEVICES=1 taskset -c 10-19 $L/.venv/bin/python -m sglang.launch_server \
  --model-path IFM/K2-Horizon-7B --tp-size 1 --context-length 65536 \
  --mem-fraction-static 0.88 --cuda-graph-max-bs-decode 16 --disable-prefill-cuda-graph \
  --reasoning-parser k2_horizon --tool-call-parser k2_horizon \
  --enable-metrics --enable-cache-report --port 30000
```

- Always launch with `python -m ...`. The venv was moved, so its `bin/` shebangs are stale.
- **Why this venv:** SGLang ≥ 0.5.11 needs CUDA 13, but the WS driver is 560 (CUDA 12.6). The
  legacy venv (SGLang 0.5.20, torch 2.13+cu126) works.
- **HiCache:** use `--hicache-io-backend direct`. The `kernel` backend fails with
  `cudaErrorInsufficientDriver`.
- **K2 Horizon tp1 numbers:**
  - The auto mem fraction (0.70) leaves no room for KV.
  - 0.90 hits OOM during CUDA graph capture.
  - At 0.88, the pool is **25,427 tokens** and decode runs at **36.5 tok/s**.
- Torchcodec/FFmpeg import errors at startup are harmless.

## 6. Reusable legacy assets (WS, under `~/legacy/jouleserve-ws/`)

| Asset | Path | State |
|---|---|---|
| Serving venv (SGLang 0.5.20) | `.venv` | works; see §5 |
| Workflow venv (LangGraph, MCP, OpenAI SDK, AirSim client) | `.venv-workflow` | versions differ from P1's: langgraph 1.2.12 vs 1.2.11, mcp 2.2.0 vs 1.29.1 |
| x86 headless AirSim sim | `build/airsim-x86/headless-x86` (+ `BUILD_PROVENANCE.md`, `CMakeLists.txt`, `sim_handle.py`, `LIFECYCLE.md`) | built 2026-09-22 with g++ 11 (needs a `-include mutex/thread/atomic` shim). Its source `thor_headless.cpp` (sha `95368d1e…`) is **identical to P1's current source** (checked 2026-09-30). RPC port is **hard-coded to 41451**, so N sessions need a small patch and rebuild |
| P1 CLGSCE code snapshot | `sources/p1-clgsce/20260922/` | **partly stale**: `clgsce_mcp_server.py` and `clgsce_subagents.py` changed on the Thor on 2026-09-23; `task_sets/advanced.txt` and P1's `final_sweep/_harness` are missing. The other files match |
| AirSim source snapshot | `sources/airsim/20260922/` | fork `d109f0d` |
| B5 Reflexion runner, NVML/collector code | `JouleServe/runner/` | absolute paths are stale (they point at `~/jouleserve-ws/...`). Produced one natural B5 PASS with Qwen3.5-9B at 8K `max_tokens` (`runs/b5-20260922T124700Z-g5n`) |
| KV-primitive benchmarks | `benchmarker/k3-primitives`, `k4-crossover`, `k5-pressure` | Qwen3.5-9B results; headlines in `HANDOFF.md` §4 |
| Qwen3.5-9B weights | `cache/hf/models--Qwen--Qwen3.5-9B` | hybrid, same family as P1's Qwen3.8 |
| Orin SGLang image | `jouleserve/sglang:0.5.16-orin-cu126-sm87` | built on Orin-2 (legacy); for M6 |

## 6b. WS working directories and gotchas (set up 2026-10-01)

| What | Where (WS) | Notes |
|---|---|---|
| Dev copy of this repo's code | `~/jsw-dev/` | `rsync -a jsw env <ws>:~/jsw-dev/` from the local checkout. `~/jouleserve-ws` stays a clean git clone |
| aerogen private copy | `~/work/aeroeval/` (own local git) | mayankarya's code from the Thor. **Not vendored into this repo** until the owner agrees. The only edit is the pacing hook (commit `0acef8c`) |
| aerogen venv | `~/work/venv-aerogen` | openai 3.22, **mcp 1.29.1** (the agent's client needs mcp 1.x: 2.x renamed `Tool.inputSchema`), nvidia-ml-py |
| Run outputs | `~/work/runs/<run>/` | Copy back to local `data/ws_runs/` (git-ignored) for analysis |
| Logs | `~/work/logs/` | Server and queue logs |

- **K2-Horizon-7B has no thinking-off mode.** `chat_template_kwargs.reasoning_effort` is
  one of high, medium or low (default high).
  - The template **raises** unless every assistant message in the history carries a
    thinking field. SGLang 0.5.20 forwards only `reasoning_content`, so send that (`""`
    when empty).
  - Past reasoning stays in the history. At high effort, one aerogen session outgrows a
    one-GPU pool (25.4K tokens) within about 7 turns (`finish_reason=length`).
- **Streaming TTFT is not prefill time for tool calls.** The `k2_horizon` tool parser
  emits a tool call only once it is complete. Model prefill from the calibrated rate
  instead (`jsw/costs/calibrate.py`).
- **Pin model revisions and run offline.** On 2026-10-02 Hugging Face served a re-upload of
  K2 (revision `85d46bb`, re-sharded) and SGLang fetched it silently. `env/launch_k2_tp1.sh` now
  pins `f846b1e` (the revision of every earlier run) with `HF_HUB_OFFLINE=1`.
- **Qwen3.5-9B** (`env/launch_qwen35_tp1.sh`): hybrid, with 8 of 32 layers full attention.
  - Use `--reasoning-parser qwen3 --tool-call-parser qwen3_coder`, and turn thinking on or off
    with `chat_template_kwargs.enable_thinking`.
  - At 0.85 the KV pool is 35.5K tokens, and the mamba state slots cap concurrency at 3.
  - The unified radix cache reuses both state kinds across tool steps.
- **`pkill -f <pattern>` over ssh kills the ssh shell itself** when the pattern is in the
  command line. Select PIDs with `ps | grep "[x]yz"` instead.
- **Foreground `sleep` is blocked for the agent.** Wait on WS jobs with a background
  `until …; do sleep N; done` over ssh.

## 7. Conventions

- **Keep it lean.** The legacy attempt accumulated heavy process and got bloated. Prefer the
  smallest experiment or code that answers the current question.
- **Keep docs consolidated.** Update `HANDOFF.md`, the two plans and the review index instead
  of adding new dated notes. Update `HANDOFF.md` at the end of every working session.
- **Decisions** go into the tables: D1–D5 in `PLAN.md` §6, D6–D11 in
  `JOULESERVE_WS_PLAN.md` §8, D13–D17 in `OPTIONS_PLAN.md` §6. D12 is the professor's direction
  decision (open). The next free ID is **D18**.
- **Dates and numbers.**
  - Use absolute dates.
  - Label every number with its source: a Thor trace, a WS measurement or a paper.
  - Track B numbers mostly came from a fetch-and-summarize read. Re-check them against the
    PDF before citing.
- **Trace schema** stays a superset of P1's (`run_meta.json`, `iterations.jsonl`,
  `llm_calls.jsonl`, `mcp_calls.jsonl`, `server_kv.jsonl`, `device_samples.jsonl`), so WS
  runs line up with Thor runs.
- **Code layout** follows `JOULESERVE_WS_PLAN.md` §4 (`jsw/`, `configs/`, `analysis/`,
  `vendor/`, `tests/`, `env/`). Create directories as needed.
- **Results.** Negative results count. If an opportunity is absent, report it with numbers
  and hand the choice to the professor.
- **This repository is public.**
  - Keep P1's unpublished material, such as deck figures and slides, out of git:
    `reports/*/p1_figures/` is git-ignored.
  - Check the visibility before pushing:
    `gh repo view saisandeshk/jouleserve-ws --json visibility`.

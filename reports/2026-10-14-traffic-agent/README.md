# P1's traffic agent: what it needs to run (TRF-2a)

**14 Oct 2026.** Code-only copy taken from Thor-2 (look-and-copy):
- **Source:** `mayankarya@10.24.24.80:/media/ssd/Deepstream-Yolo-upstream/camera_query_agent/`.
- **Destination:** the WS, `~/work/p1/traffic_agent/camera_query_agent/`, 131 files, 4 MB.
- **Checksums:** SHA-256 in `../SHA256SUMS`.
- **Not copied:**
  - `fixtures/` (60 GB);
  - `hf_cache/` (226 GB);
  - `traces_sweep/` (7.9 GB);
  - `.venv/`.

The code is P1's (Mayank Arya). It is not vendored into this repo. This note summarises a read-only code study (a Sonnet
agent, file:line citations in its report, kept in the session log).

## What it is

- **Loop.** A LangChain/LangGraph tool-calling agent (`agent.py`, edited 6 Oct). It has a Reflexion variant
  (`agent_reflect.py`). The campaign allows 20 steps per question.
- **Tools.** Seven tools from three MCP servers, five for text-only models:
  - `camera_mcp.py`: `resolve_location`, `get_traffic_series` and `get_camera_frames` read a SQLite store; `ask_vlm`
    sends frames to the **same SGLang server** as the agent, up to 24 requests at once.
  - `sandbox_mcp.py`: `run_python` runs in the docker image `camera-agent-sandbox:1` with no network.
  - `web_mcp.py`: `geocode` and `web_search` need the internet.
- **P1's settings** (`deploy/campaigns/thor_campaign_v4.sh`):
  - temperature 0, seed 42;
  - `max_tokens` 8,000 (unbounded for Devstral and Ministral);
  - LLM at `CAMERA_AGENT_LLM_URL`;
  - the radix cache flushed between runs.
- **System prompt.** It starts with the wall-clock time. `CAMERA_AGENT_NOW` can pin it to replay a run.
- **Context guard.** On a context-overflow error the agent retries once with a lower `max_tokens`. If the prompt alone
  no longer fits, it records `input_ceiling` (the overflow failure in the waterfall).
- **Grading.** P1's deterministic grader `traffic/grading/grade.py` in P1's repository, not the agent folder:
  - any `failure_class` is a fail;
  - numbers have tolerances;
  - vision tasks must call the vision tools;
  - chart tasks need a non-blank PNG.

## What a live run needs

| Need | Status |
| --- | --- |
| Camera data | Kamath: the full one-week store (2025-06-12 to 2025-06-18), because some tasks need the week. Silk: its own store for 2025-07-30. Images only for the vision tasks (never for granite). Sizes unknown until copied. Image paths in the DB are absolute and must be rewritten for a new location (P1's `relocate_fixtures.py` does not cover these stores) |
| Python packages | langchain, langgraph, langchain-openai, langchain-mcp-adapters, openai, mcp: **versions unknown** (`deploy/requirements.txt` is incomplete). Ask P1 for a `pip freeze` of the agent's `.venv` |
| Sandbox | `camera-agent-sandbox:1` (on Thor-2; on Thor-1 too, per 12 Oct notes). **The WS has no docker**, so `run_python` cannot run there without changing P1's sandbox code (for example a bwrap runner); that change needs Sandesh's OK. The Orin 32 docker disks are full, so the image cannot be loaded there either |
| Internet | `web_search` and `geocode` hit the public internet; P1's results cannot be replayed exactly |
| Energy | P1's sampler integrates only Jetson power fields; on the WS use our NVML counter |

**Where to run it:**
- **Thor-1 is the easiest host.** It has docker, P1's SGLang image and probably the sandbox image. It is busy with the
  mentor's drone runs, so it needs a slot agreed with her.
- **Orin-64-1 is the other candidate.** It is idle, and its docker root is not the full Orin 32 SSD. Load the sandbox
  image only with Sandesh's OK.

## A correction to our notes

**P1's final traffic traces keep the tool outputs.** Each `turns[]` entry of role `tool` holds `tool`, `args`, `result`
and `result_truncated`. HANDOFF §5 said traffic tool results were empty and the tool definitions absent; that held for
the data of 5 Oct.
- **What it enables:** traffic episodes can be replayed **as text**, step by step, with the real prompts and tool
  outputs, without the camera data.
- **What that is enough for:** single-step counterfactuals, for example:
  - resample a capped call;
  - shrink an oversized tool output, then check the next step against the window.
- **What still needs the live agent:** continuing an episode beyond the recorded tool outputs needs the agent and its
  data.

## Update, 14 Oct night: P1's code map, checked against the machines

P1 shared a code map of the traffic agent (a copy, not in git: `data/p1_traffic/AGENT_CODE_MAP_2026-10-14.md`). Checked
read-only against our copy, Thor-2 and the WS:

- **Our copy is the version P1 ran.** All 11 files the map lists have the same line counts in our copy
  (`agent.py` 1,359, `agent_reflect.py` 600, `run_traces.py` 679, and so on). `CAMERA_AGENT_IMPL=agent|reflect`
  selects tool calling or Reflexion. P1's traffic campaigns ran on other boxes than P5's units (Orin 32: .54, .55;
  Orin 64: .74, .75; Thor: .80).
- **Package versions are now known.** From the agent's `.venv` on Thor-2 (its `dist-info` folders):
  - Python 3.12;
  - langchain 1.4.0, langchain-core 1.6.1, langchain-openai 1.6.0, langchain-mcp-adapters 0.3.2;
  - langgraph 1.2.11;
  - mcp 1.29.1 (with mcp-types 2.1.0);
  - openai 3.8.0;
  - pydantic 2.13.5, httpx 0.28.1, tiktoken 0.14.0, tokenizers 0.23.2.
- **Data on Thor-2** (`fixtures/`, 60 GB):

  | What | Size | Needed for |
  | --- | --- | --- |
  | `fixtures.db` (Kamath store, instances A and B) | 20.8 GB | every model |
  | `stores/Silk_Brd_JN_HD_2_2025-07-30_6d` (instance C) | 10 GB | every model |
  | `meta.json`, `ground_truth.json` | small | every model |
  | `_real_kamath/` images | 21 GB | vision tasks only |
  | `_real_silk6/` images | 8.4 GB | vision tasks only |

  So a text-only model (granite) needs about 31 GB, and a vision model about 60 GB. The map's `frames/` (574 MB) does
  not exist on Thor-2, where images live in `_real_*`. Ask which layout the Orin boxes use.
- **Sandbox: run it on the WS with P1's x86 variant.**
  - Our copy (the Thor version) runs `run_python` only in docker; its header says bwrap is blocked on the Jetsons by
    AppArmor.
  - `deploy/CANONICAL.json` lists an x86 variant ("bwrap backend + rlimits", plus `SmiReader` for NVIDIA power),
    used on P1's RTX and cloud boxes.
  - The WS has bwrap 0.6.1, unprivileged user namespaces are allowed, and a test sandbox ran.
  - So the WS can run the agent with P1's x86 variant, which is a request to P1 rather than a change to their code.
- **Serving:** no traffic campaign set `--kv-cache-dtype`, so every traffic arm ran with **bf16 KV**, including the
  FP8-weight models. That agrees with the waterfall's pools.
- **Devstral counting differs.**
  - P1's submitted selection rule (`analysis/edgebench/selection.py`, `TEXT_ONLY`) treats Devstral as text-only and
    drops its 7 vision tasks; our waterfall follows that rule (189 runs per Devstral cell).
  - The code map says Devstral has a vision config, so all 28 tasks count, and both Devstral sweeps did run all 7
    vision tasks (9 runs each).
  - If P1 adopts the map's reading, the three Devstral cells of the waterfall change.
- **A data trap behind some wrong answers:** `detections.ts` has one-second resolution over about 15 fps video, so raw
  row counts overcount 2–4× (the map's note on `store.py`).

**Updated asks for P1:**
1. The x86 variant of the agent folder (bwrap sandbox, `SmiReader`), for example from the RTX box.
2. `deploy/campaigns/orin_campaign_v6.sh`.
3. Permission to copy the data: 31 GB for text-only models, 60 GB with images.
4. Whether Devstral counts as text-only.

## TRF-3: P1's agent live on Thor-2, against P1's runs (15 Oct)

**Setup:**
- P1's agent, unchanged, with P1's run settings (greedy, seed 42, 8,000-token cap, 20 steps; `env/thor2/traffic_run.sh`).
- P1's gemma-26B traffic server flags, in a P5 container.
- Graded by P1's grader (from a copy; it reproduces 336 of 336 of P1's Thor gemma grades).
- Compared with P1's 4 recorded Thor runs of each task (instance A; `analysis/traffic_validate.py compare`).

**Result on the 7 of 9 tasks that finished before Thor-2 crashed:**

| Task | Ours | P1 passes | Calls, ours / P1 median | kJ, ours | kJ, P1 min–max (median) |
| --- | --- | --- | --- | --- | --- |
| day-summary | pass | 1/4 | 2 / 4.5 | 9.9 | 6.2–532 (62.8) |
| peak-count | pass | 4/4 | 3 / 2 | 5.3 | 2.3–3.5 (3.0) |
| class-mix | pass | 4/4 | 3 / 4 | 7.3 | 5.0–14.3 (8.4) |
| busiest-hour | pass | 4/4 | 2 / 2 | 7.1 | 4.2–7.6 (5.8) |
| avg-per-minute | pass | 3/4 | 9 / 10 | 38.5 | 20.5–66.5 (50.9) |
| compare-periods | pass | 4/4 | 6 / 4 | 18.4 | 7.0–12.2 (8.6) |
| heavy-vehicle | pass | 2/4 | 12 / 6 | 21.3 | 6.8–34.4 (11.7) |

- **Passes:** we passed 7 of 7, where P1 passed 22 of 28 on the same tasks.
- **Energy:** ours lies within P1's own min–max on 5 of 7 tasks. Our total is 107.7 kJ, against 151.0 kJ for P1's
  medians.
- **Where we differ, the path differs.** In peak-count and compare-periods our agent made more calls.
- **Per generated token,** the board's energy (ours over P1's median) is within 3–7% of P1's on 5 of 7 tasks. The
  other two are busiest-hour (1.3×) and day-summary (1.7×), where our short runs carry tool time over few tokens.
- **Reading:** the platform reproduces P1's outcomes and per-token cost. Greedy runs still take different paths from
  P1's, as P1's own repeats do (day-summary ranges from 6.2 to 532 kJ).

**The crash.** Thor-2 reset at 01:24, during the 8th task (peak-start-end). The cause was memory exhaustion:
- the kernel's out-of-memory killer fired from 01:10:02 and killed desktop processes in a loop;
- swap was full, the page cache had dropped to almost nothing, and P1's sampler stalled at 01:15:39;
- the kernel log stops at 01:23:33.

At the first kill, process memory was only about 12 GB. Most of the rest was GPU memory reserved by the server at
P1's `--mem-fraction-static 0.80`, which had left about 5 GB for P1's agent, its SQLite and Python tools over a 20 GB
database, Docker and the desktop. The fixes:
- P5's servers now run at 0.70, which leaves about 28 GB free;
- a memory guard (`env/thor2/memguard.sh`) stops P5's own server if free memory stays under 4 GB;
- the last 2 TRF-3 tasks rerun at the end of the CAND chain.

## Questions for P1 (through Sandesh)

1. A `pip freeze` of `camera_query_agent/.venv`, and which `agent.py` the final sweeps used. The copy's `agent.py` differs
   from the hash pinned in `deploy/CANONICAL.json`.
2. The Orin campaign and serve scripts (`orin_campaign_v5.sh`/`v6.sh`), which are not in the folder.
3. May we copy the Kamath one-week store and the Silk store (and the images for the vision tasks), and run the agent on
   P5's units?

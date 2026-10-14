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

## Questions for P1 (through Sandesh)

1. A `pip freeze` of `camera_query_agent/.venv`, and which `agent.py` the final sweeps used. The copy's `agent.py` differs
   from the hash pinned in `deploy/CANONICAL.json`.
2. The Orin campaign and serve scripts (`orin_campaign_v5.sh`/`v6.sh`), which are not in the folder.
3. May we copy the Kamath one-week store and the Silk store (and the images for the vision tasks), and run the agent on
   P5's units?

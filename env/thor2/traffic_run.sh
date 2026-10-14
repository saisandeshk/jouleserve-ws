#!/bin/bash
# P5 on Thor-2: one cell of P1's traffic agent, unchanged, with P1's run settings (P1's thor_campaign_v4.sh, run_one),
# writing only under /media/hdd/p5 (traces, sandbox artifacts and log, temporary files; no bytecode in P1's folder).
# Differences from P1, recorded in p5_run.txt: no sudo (the OS page cache is not dropped, CAMERA_AGENT_CACHE_FLUSHED=0);
# the server on port 30101.
#   traffic_run.sh <label> <comma,separated,task,ids> [instance A|B|C] [run number]
# GW_K=<k> (optional): route the agent's calls through the P5 gateway (/media/hdd/p5/jsw-dev) in first-of-k mode with
# Gemma's model-card sampling (temperature 1.0, top_p 0.95, top_k 64); k = 1 is plain sampling. The vision tool's
# calls still go straight to the server. Unset: P1's protocol (greedy) straight to the server.
set -u
B=/media/ssd/Deepstream-Yolo-upstream/camera_query_agent; P=/media/hdd/p5
LABEL=$1; IDS=$2; INST=${3:-A}; N=${4:-1}; PORT=30101; SERVED=gemma4-it
D=$P/runs/${LABEL}-$(date +%Y%m%dT%H%M); mkdir -p "$D" $P/tmp
cd $B || exit 1
. ./instances.sh && "instance_$INST"
if [ "$INST" = C ]; then S=$B/fixtures/stores/Silk_Brd_JN_HD_2_2025-07-30_6d; O=$P/fixtures_overlay/silk
else S=$B/fixtures; O=$P/fixtures_overlay/kamath; fi
mkdir -p $O/artifacts $O/frames
export CAMERA_AGENT_FIXTURES_DIR=$O CAMERA_AGENT_DB=$S/fixtures.db CAMERA_AGENT_META=$S/meta.json \
  CAMERA_AGENT_GROUND_TRUTH=$S/ground_truth.json CAMERA_AGENT_FRAMES_DIR=$O/frames CAMERA_AGENT_ARTIFACTS_DIR=$O/artifacts \
  TMPDIR=$P/tmp SQLITE_TMPDIR=$P/tmp PYTHONDONTWRITEBYTECODE=1
AGENT_URL=http://127.0.0.1:$PORT/v1; GP=
if [ -n "${GW_K:-}" ]; then
  mkdir -p "$D/gw"
  (cd $P/jsw-dev && PYTHONDONTWRITEBYTECODE=1 exec $P/venv-gw/bin/python -m jsw.gateway.server \
     --upstream http://127.0.0.1:$PORT --port 31101 --log-dir "$D/gw" --first-of-k "$GW_K" \
     --sampling '{"temperature": 1.0, "top_p": 0.95, "top_k": 64}' > "$D/gw/gateway.log" 2>&1) &
  GP=$!
  for i in $(seq 1 30); do sleep 1; curl -sf -m 2 http://127.0.0.1:31101/v1/models >/dev/null && break; done
  AGENT_URL=http://127.0.0.1:31101/v1
fi
KV=$(curl -s -o /dev/null -w "%{http_code}" -m 10 -X POST http://127.0.0.1:$PORT/flush_cache); [ "$KV" = 200 ] && KV=1 || KV=0
{ echo "label=$LABEL ids=$IDS instance=$INST run=$N kv_flushed=$KV page_cache_dropped=0 port=$PORT served=$SERVED"
  echo "fixtures_db=$CAMERA_AGENT_DB overlay=$O agent_url=$AGENT_URL gw_k=${GW_K:-none} started=$(date -Iseconds)"; } > "$D/p5_run.txt"
.venv/bin/python sweep_vitals.py "$D/vitals.jsonl" --interval 0.2 --label "$LABEL" --llm-url http://127.0.0.1:$PORT/v1 \
  > "$D/_vitals.log" 2>&1 &
VP=$!; sleep 6
env CAMERA_AGENT_TEMPERATURE=0 CAMERA_AGENT_SEED=42 CAMERA_AGENT_TOP_P=1.0 CAMERA_AGENT_TOKEN_BREAKDOWN=1 \
  CAMERA_AGENT_TOKENIZER=google/gemma-4-26B-A4B-it HF_HUB_OFFLINE=1 CAMERA_AGENT_PRECISION=BF16 \
  CAMERA_AGENT_RUN_NUMBER="$N" CAMERA_AGENT_CACHE_FLUSHED=0 CAMERA_AGENT_KV_FLUSHED=$KV CAMERA_AGENT_MAX_STEPS=20 \
  CAMERA_AGENT_MAX_TOKENS=8000 CAMERA_AGENT_TOOL_TIMEOUT=600 CAMERA_AGENT_SANDBOX_TIMEOUT=180 \
  CAMERA_AGENT_LLM_TIMEOUT=3600 LANGCHAIN_OPENAI_STREAM_CHUNK_TIMEOUT_S=0 \
  CAMERA_AGENT_LLM_URL=$AGENT_URL CAMERA_AGENT_LLM_MODEL=$SERVED \
  CAMERA_AGENT_SERVER_INFO_URL=http://127.0.0.1:$PORT/v1 CAMERA_AGENT_NO_STREAM= CAMERA_AGENT_IMPL=agent \
  CAMERA_AGENT_VLM_URL=http://127.0.0.1:$PORT/v1 CAMERA_AGENT_VLM_MODEL=$SERVED CAMERA_AGENT_WORKLOAD_TIMEOUT=3600 \
  CAMERA_AGENT_TRACE_DIR="$D" CAMERA_AGENT_PROGRESS="$D/progress.jsonl" \
  .venv/bin/python run_traces.py --ids "$IDS" >> "$D/run.log" 2>&1
rc=$?; sleep 3; kill $VP 2>/dev/null; [ -n "$GP" ] && kill $GP 2>/dev/null
echo "rc=$rc ended=$(date -Iseconds)" >> "$D/p5_run.txt"
(cd "$D" && sha256sum $(ls | grep -v SHA256SUMS) > SHA256SUMS 2>/dev/null)
echo "$D rc=$rc"

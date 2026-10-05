#!/bin/bash
# One A-E1 job on one GPU: gemma-4-E4B server (if not up), a gateway with the decode guard ("truncate": a call
# stops where the loop detector fires), and jsw/workloads/loop_replay.py for the given selection and arms.
# Usage: env/queue_a_e1_one.sh <gpu> <port> <gwport> <select: pilot|full|o32> <arms> <name> [concurrency]
set -u
GPU=$1; PORT=$2; GW=$3; SEL=$4; ARMS=$5; NAME=$6; CONC=${7:-4}
PY=~/legacy/jouleserve-ws/.venv/bin/python
cd ~/jsw-dev
log() { echo "=== $(date +%T) $*"; }
if ! curl -s -m 3 http://127.0.0.1:$PORT/v1/models | grep -q gemma-4-E4B; then
  tmux kill-session -t g$GPU-e4b 2>/dev/null; sleep 5
  tmux new-session -d -s g$GPU-e4b "cd ~/jsw-dev && env/launch_model.sh gemma-e4b $GPU $PORT 2>&1 | tee ~/work/logs/a_e1_server_g$GPU.log"
  for i in $(seq 1 120); do curl -s -m 3 http://127.0.0.1:$PORT/v1/models | grep -q gemma && break; sleep 5; done
fi
mkdir -p ~/work/runs/$NAME
tmux kill-session -t gw-a-e1-g$GPU 2>/dev/null
tmux new-session -d -s gw-a-e1-g$GPU "cd ~/jsw-dev && $PY -m jsw.gateway.server --upstream http://127.0.0.1:$PORT --port $GW \
  --log-dir ~/work/runs/$NAME/gw --policy jsw.policies.decode_guard:DecodeGuard --policy-args '{\"action\": \"truncate\"}' \
  2>&1 | tee ~/work/logs/gw_$NAME.log"
sleep 4
log "$NAME arms=$ARMS select=$SEL"
$PY -m jsw.workloads.loop_replay --prompts data/a_e1/prompts.jsonl --select $SEL --arms $ARMS \
  --gateway http://127.0.0.1:$GW --server http://127.0.0.1:$PORT --gpu $GPU --model gemma-4-E4B-it \
  --concurrency $CONC --name $NAME > ~/work/logs/$NAME.log 2>&1
log "$NAME done rc=$?"
tmux kill-session -t gw-a-e1-g$GPU 2>/dev/null

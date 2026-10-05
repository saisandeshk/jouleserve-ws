#!/bin/bash
# D-E2b (2026-10-06): the first D-E2 policies never engaged. Admission read pool usage from /metrics (~2 Hz) and the
# 24-request burst arrived before usage rose (0 requests held); pinning cannot protect a paused context when the
# burst alone exceeds the free pool. Here the burst is capped unconditionally (usage_threshold 0) at k = 2 requests,
# so k * ~2K tokens fits beside a ~7K paused context in the 12,415-token pool; with and without pinning; N = 1, 4.
set -u
GPU=${1:-1}; PORT=${2:-30001}; GW=${3:-31002}; H=${4:-720}
cd ~/jsw-dev
PY=~/legacy/jouleserve-ws/.venv/bin/python
log() { echo "=== $(date +%T) $*"; }
SESS=data/replay/t_o32_e4b_bursts.jsonl
tmux kill-session -t g$GPU-e4b 2>/dev/null; sleep 8
tmux new-session -d -s g$GPU-e4b "cd ~/jsw-dev && env/launch_model.sh gemma-e4b $GPU $PORT --enable-priority-scheduling \
  --schedule-policy fcfs --radix-eviction-policy priority --max-total-tokens 12415 2>&1 | tee ~/work/logs/d_e2b_server.log"
for i in $(seq 1 120); do curl -s -m 3 http://127.0.0.1:$PORT/v1/models | grep -q gemma && break; sleep 5; done
run() {
  local name=$1 n=$2 pargs=$3
  rm -rf ~/work/runs/$name; mkdir -p ~/work/runs/$name
  tmux kill-session -t gw-d-e2 2>/dev/null
  tmux new-session -d -s gw-d-e2 "cd ~/jsw-dev && $PY -m jsw.gateway.server --upstream http://127.0.0.1:$PORT --port $GW \
    --log-dir ~/work/runs/$name/gw --policy jsw.policies.burst_memory:BurstMemory --policy-args '$pargs' 2>&1 | tee ~/work/logs/gw_$name.log"
  sleep 3; curl -s -X POST http://127.0.0.1:$PORT/flush_cache > /dev/null
  log "$name"
  $PY -m jsw.workloads.replay --sessions $SESS --gateway http://127.0.0.1:$GW --server http://127.0.0.1:$PORT \
    --gpu $GPU --n $n --horizon $H --grace 180 --ctx 32768 --bursts --seed 7 --name $name > ~/work/logs/$name.log 2>&1
  log "$name done rc=$?"
}
run d-e2-p12k-n4-admit2 4 '{"admit_k": 2, "usage_threshold": 0.0}'
run d-e2-p12k-n4-both2  4 '{"pin": true, "admit_k": 2, "usage_threshold": 0.0}'
run d-e2-p12k-n1-both2  1 '{"pin": true, "admit_k": 2, "usage_threshold": 0.0}'
tmux kill-session -t gw-d-e2 2>/dev/null; tmux kill-session -t g$GPU-e4b 2>/dev/null
log "D-E2b done"

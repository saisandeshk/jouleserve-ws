#!/bin/bash
# Wave 2 on the WS (OPTIONS_PLAN.md §4): when B-E1 (GPU1) and the granite calibration (GPU0) are done, serve the
# 26B stand-in over both GPUs, smoke-test it, and run the A-E1 pilot. Runs unattended in tmux ("wave2").
set -u
cd ~/jsw-dev
PY=~/legacy/jouleserve-ws/.venv/bin/python
log() { echo "=== $(date +%T) $*"; }
wait_session() { while tmux has-session -t "$1" 2>/dev/null; do sleep 20; done; }
log "waiting for g1-be1 and g0-calib"
wait_session g1-be1; wait_session g0-calib
for s in g0-granite g1-e4b g1-gw g0-gw; do tmux kill-session -t $s 2>/dev/null; done
sleep 15
log "launching gemma26b-fp8-text TP=2"
tmux new-session -d -s g01-gemma26b "cd ~/jsw-dev && TP=2 env/launch_model.sh gemma26b-fp8-text 0,1 30000 2>&1 | tee ~/work/logs/s1_gemma26b_fp8_derived.log"
for i in $(seq 1 240); do
  curl -s -m 3 http://127.0.0.1:30000/v1/models | grep -q gemma && break
  tmux has-session -t g01-gemma26b 2>/dev/null || { log "26B server died"; exit 1; }
  sleep 10
done
log "26B up; smoke test"
timeout 900 $PY env/smoke_model.py 30000 --tools --out ~/work/logs/smoke_gemma26b_fp8.json > ~/work/logs/smoke_gemma26b_fp8.log 2>&1 \
  || { log "smoke failed (rc=$?)"; exit 1; }
grep -q '"finish": "stop"' ~/work/logs/smoke_gemma26b_fp8.json || { log "smoke: no normal chat reply"; exit 1; }
log "smoke ok; A-E1 pilot"
env/queue_a_e1.sh pilot gemma-4-26B-A4B-it-fp8 0,1 12
log "wave2 done"

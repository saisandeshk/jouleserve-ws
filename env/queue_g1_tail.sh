#!/bin/bash
# GPU1 tail (2026-10-06): E4B cost calibration (A-E5; the WS price ratio r for C-E1), then C-E1's best case for
# option C: tau2 airline with the agent's thinking off (short outputs), 20 tasks.
set -u
cd ~/jsw-dev
log() { echo "=== $(date +%T) $*"; }
tmux kill-session -t g1-e4b 2>/dev/null; sleep 6
tmux new-session -d -s g1-e4b "cd ~/jsw-dev && env/launch_model.sh gemma-e4b 1 30001 2>&1 | tee ~/work/logs/g1_tail_server.log"
for i in $(seq 1 120); do curl -s -m 3 http://127.0.0.1:30001/v1/models | grep -q gemma && break; sleep 5; done
log "calibrate E4B"
~/work/venv-aerogen/bin/python -m jsw.costs.calibrate2 --server http://127.0.0.1:30001 --gpu 1 \
  --out ~/work/runs/calib/gemma-e4b_tp1_gpu1.json --ctx-lens 1000,4000,16000 > ~/work/logs/calib_e4b.log 2>&1
log "calibrate done rc=$?"
THINK=false DOMAINS=airline env/queue_c_e1.sh 1 30001 31003 20
log "GPU1 tail done"

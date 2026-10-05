#!/bin/bash
# Wave 3 on the WS (OPTIONS_PLAN.md §4): after wave 2 (A-E1 pilot on the 26B over both GPUs), stop the 26B and run
# the single-GPU experiments in parallel: GPU0 RET-E1 (granite), GPU1 D-E2 then C-E1 (gemma-4-E4B).
set -u
cd ~/jsw-dev
log() { echo "=== $(date +%T) $*"; }
log "waiting for wave2"
while tmux has-session -t wave2 2>/dev/null; do sleep 30; done
for s in g01-gemma26b gw-a-e1; do tmux kill-session -t $s 2>/dev/null; done
sleep 20
log "starting GPU0 RET-E1 and GPU1 D-E2 -> C-E1"
tmux new-session -d -s q-g0 "cd ~/jsw-dev && env/queue_ret_e1.sh 0 30000 31000 2400 2>&1 | tee ~/work/logs/queue_ret_e1.log"
tmux new-session -d -s q-g1 "cd ~/jsw-dev && env/queue_d_e2.sh 1 30001 31002 720 2>&1 | tee ~/work/logs/queue_d_e2.log; \
  tmux kill-session -t g1-e4b 2>/dev/null; sleep 8; env/queue_c_e1.sh 1 30001 31003 2 smoke 2>&1 | tee ~/work/logs/queue_c_e1_smoke.log; \
  env/queue_c_e1.sh 1 30001 31003 20 2>&1 | tee ~/work/logs/queue_c_e1.log"
log "wave3 launched"

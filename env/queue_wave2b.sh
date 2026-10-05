#!/bin/bash
# Wave 2b (2026-10-06): the 26B stand-in cannot run on Ampere in SGLang 0.5.20 (D13), so A-E1 runs on gemma-4-E4B
# (P1's weights): the pilot with greedy on GPU0 and Gemma's default sampling on GPU1 in parallel, then E4B's own
# Orin 32 prompts, then wave 3 (RET-E1 on GPU0; D-E2 and C-E1 on GPU1).
set -u
cd ~/jsw-dev
log() { echo "=== $(date +%T) $*"; }
wait_both() { while tmux has-session -t a-g0 2>/dev/null || tmux has-session -t a-g1 2>/dev/null; do sleep 20; done; }
tmux new-session -d -s a-g0 "cd ~/jsw-dev && env/queue_a_e1_one.sh 0 30000 31000 pilot greedy a-e1-pilot-e4b-greedy 4 2>&1 | tee -a ~/work/logs/queue_a_e1.log"
tmux new-session -d -s a-g1 "cd ~/jsw-dev && env/queue_a_e1_one.sh 1 30001 31001 pilot sampled:0 a-e1-pilot-e4b-sampled 4 2>&1 | tee -a ~/work/logs/queue_a_e1.log"
wait_both; log "pilot done"
tmux new-session -d -s a-g0 "cd ~/jsw-dev && env/queue_a_e1_one.sh 0 30000 31000 o32 greedy a-e1-o32-e4b-greedy 4 2>&1 | tee -a ~/work/logs/queue_a_e1.log"
tmux new-session -d -s a-g1 "cd ~/jsw-dev && env/queue_a_e1_one.sh 1 30001 31001 o32 sampled:0,sampled:1 a-e1-o32-e4b-sampled 4 2>&1 | tee -a ~/work/logs/queue_a_e1.log"
wait_both; log "o32 done"
for s in g0-e4b g1-e4b; do tmux kill-session -t $s 2>/dev/null; done
sleep 10
log "wave 3"
tmux new-session -d -s q-g0 "cd ~/jsw-dev && env/queue_ret_e1.sh 0 30000 31000 2400 2>&1 | tee ~/work/logs/queue_ret_e1.log"
tmux new-session -d -s q-g1 "cd ~/jsw-dev && env/queue_d_e2.sh 1 30001 31002 720 2>&1 | tee ~/work/logs/queue_d_e2.log; \
  tmux kill-session -t g1-e4b 2>/dev/null; sleep 8; env/queue_c_e1.sh 1 30001 31003 2 smoke 2>&1 | tee ~/work/logs/queue_c_e1_smoke.log; \
  env/queue_c_e1.sh 1 30001 31003 20 2>&1 | tee ~/work/logs/queue_c_e1.log"
log "wave2b done; wave 3 running"

#!/bin/bash
# GPU0 chain (2026-10-06, after the grammar/NCCL crash): A-E1 pilot greedy, then sampled, then E4B's own Orin 32
# prompts (greedy; sampled seeds 0, 1), all on gemma-4-E4B; then RET-E1 on granite.
set -u
cd ~/jsw-dev
log() { echo "=== $(date +%T) $*"; }
tmux kill-session -t g0-e4b 2>/dev/null; sleep 5
env/queue_a_e1_one.sh 0 30000 31000 pilot greedy a-e1-pilot-e4b-greedy 4
env/queue_a_e1_one.sh 0 30000 31000 pilot sampled:0 a-e1-pilot-e4b-sampled 4
env/queue_a_e1_one.sh 0 30000 31000 o32 greedy,sampled:0,sampled:1 a-e1-o32-e4b 4
tmux kill-session -t g0-e4b 2>/dev/null; sleep 8
env/queue_ret_e1.sh 0 30000 31000 2400
log "GPU0 chain done"

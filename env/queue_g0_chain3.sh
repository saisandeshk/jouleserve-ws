#!/bin/bash
# GPU0 chain 3 (2026-10-06): after the 26B A-E1 arms, A-E2 on the same 26B (llama.cpp) right away, then RET-E1.
set -u
cd ~/jsw-dev
log() { echo "=== $(date +%T) $*"; }
for s in g0-granite gw-ret gw-a-e1-g0; do tmux kill-session -t $s 2>/dev/null; done
if ! curl -s -m 3 http://127.0.0.1:30002/v1/models | grep -q gemma; then
  tmux kill-session -t g0-llama 2>/dev/null; sleep 5
  tmux new-session -d -s g0-llama "cd ~/jsw-dev && env/launch_llamacpp.sh 0 30002 2 40960 2>&1 | tee ~/work/logs/llama_server_g0b.log"
  for i in $(seq 1 120); do curl -s -m 3 http://127.0.0.1:30002/v1/models | grep -q gemma && break; sleep 5; done
fi
env/queue_a_e2.sh http://127.0.0.1:30002 0 31006 gemma-4-26B-A4B-it-gguf ~/work/runs/a-e1-rfx-g26b-gguf a-e2-g26b-gguf
tmux kill-session -t g0-llama 2>/dev/null; sleep 8
env/queue_ret_e1.sh 0 30000 31000 2400
log "GPU0 chain 3 done"

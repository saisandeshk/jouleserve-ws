#!/bin/bash
# GPU0 chain, revised 2026-10-06 01:35: gemma-4-E4B does not loop on the 26B's prompts, so its sampled pilot is
# dropped; P1's 26B itself runs through llama.cpp (4-bit GGUF) on the Reflexion prompts instead. Then RET-E1.
set -u
cd ~/jsw-dev
PY=~/legacy/jouleserve-ws/.venv/bin/python
log() { echo "=== $(date +%T) $*"; }
env/queue_a_e1_one.sh 0 30000 31000 pilot greedy a-e1-pilot-e4b-greedy 4
env/queue_a_e1_one.sh 0 30000 31000 o32 greedy,sampled:0,sampled:1 a-e1-o32-e4b 4
tmux kill-session -t g0-e4b 2>/dev/null; sleep 8
log "waiting for llama.cpp and the GGUF"
for i in $(seq 1 240); do grep -q "BUILD-RC=0" ~/work/logs/llama_build.log 2>/dev/null && grep -q DL-DONE ~/work/logs/dl_gguf.log 2>/dev/null && break; sleep 15; done
if grep -q "BUILD-RC=0" ~/work/logs/llama_build.log && grep -q DL-DONE ~/work/logs/dl_gguf.log; then
  tmux new-session -d -s g0-llama "cd ~/jsw-dev && env/launch_llamacpp.sh 0 30002 2 40960 2>&1 | tee ~/work/logs/llama_server_g0.log"
  for i in $(seq 1 120); do curl -s -m 3 http://127.0.0.1:30002/v1/models | grep -q gemma && break; sleep 5; done
  NAME=a-e1-rfx-g26b-gguf
  mkdir -p ~/work/runs/$NAME
  tmux kill-session -t gw-a-e1-g0 2>/dev/null
  tmux new-session -d -s gw-a-e1-g0 "cd ~/jsw-dev && $PY -m jsw.gateway.server --upstream http://127.0.0.1:30002 --port 31005 \
    --log-dir ~/work/runs/$NAME/gw --policy jsw.policies.decode_guard:DecodeGuard --policy-args '{\"action\": \"truncate\"}' 2>&1 | tee ~/work/logs/gw_$NAME.log"
  sleep 4
  log "$NAME"
  $PY -m jsw.workloads.loop_replay --prompts data/a_e1/prompts.jsonl --select rfx --arms greedy,sampled:0 \
    --gateway http://127.0.0.1:31005 --server http://127.0.0.1:30002 --gpu 0 --model gemma-4-26B-A4B-it-gguf \
    --concurrency 2 --name $NAME > ~/work/logs/$NAME.log 2>&1
  log "$NAME done rc=$?"
  tmux kill-session -t gw-a-e1-g0 2>/dev/null; tmux kill-session -t g0-llama 2>/dev/null; sleep 8
else
  log "llama.cpp or GGUF not ready; skipping the 26B arm"
fi
env/queue_ret_e1.sh 0 30000 31000 2400
log "GPU0 chain 2 done"

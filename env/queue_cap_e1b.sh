#!/bin/bash
# CAP-E1b (2026-10-06): gemma-4-E4B with an FP8 KV cache failed in SGLang 0.5.20 on Ampere with the default (triton)
# attention backend ("Unsupported rhs dtype fp8e5"). Try the flashinfer backend; if it serves, run the quality pairs
# (A-E1 pilot prompts, greedy; B-E1 D1 missions, greedy). Records the outcome either way.
set -u
GPU=${1:-1}; PORT=${2:-30001}; GW=${3:-31004}
PY=~/legacy/jouleserve-ws/.venv/bin/python
cd ~/jsw-dev
log() { echo "=== $(date +%T) $*"; }
tmux kill-session -t g$GPU-cap 2>/dev/null; tmux kill-session -t g$GPU-e4b 2>/dev/null; sleep 6
tmux new-session -d -s g$GPU-cap "cd ~/jsw-dev && env/launch_model.sh gemma-e4b $GPU $PORT --kv-cache-dtype fp8_e5m2 --attention-backend flashinfer 2>&1 | tee ~/work/logs/cap_e1b_server.log"
up=0
for i in $(seq 1 100); do curl -s -m 3 http://127.0.0.1:$PORT/v1/models | grep -q gemma && { up=1; break; }; tmux has-session -t g$GPU-cap 2>/dev/null || break; sleep 5; done
if [ $up = 1 ]; then
  # one real request: does generation work with FP8 KV + flashinfer?
  if timeout 300 $PY env/smoke_model.py $PORT --out ~/work/logs/smoke_e4b_fp8kv.json > ~/work/logs/smoke_e4b_fp8kv.log 2>&1; then
    log "E4B FP8 KV (flashinfer) serves; quality runs"
    rm -rf ~/work/runs/cap-e1-e4b-fp8kv-controls ~/work/runs/cap-e1-e4b-fp8kv-think-greedy-d1
    NAME=cap-e1-e4b-fp8kv-controls; mkdir -p ~/work/runs/$NAME
    tmux new-session -d -s gw-cap "cd ~/jsw-dev && $PY -m jsw.gateway.server --upstream http://127.0.0.1:$PORT --port $GW --log-dir ~/work/runs/$NAME/gw --policy jsw.policies.decode_guard:DecodeGuard --policy-args '{\"action\": \"truncate\"}' 2>&1 | tee ~/work/logs/gw_$NAME.log"
    sleep 3
    $PY -m jsw.workloads.loop_replay --prompts data/a_e1/prompts.jsonl --select pilot --arms greedy --gateway http://127.0.0.1:$GW \
      --server http://127.0.0.1:$PORT --gpu $GPU --model gemma-4-E4B-it --concurrency 4 --name $NAME > ~/work/logs/$NAME.log 2>&1
    log "$NAME done rc=$?"
    tmux kill-session -t gw-cap 2>/dev/null
    mkdir -p ~/work/runs/cap-e1-gw2
    tmux new-session -d -s gw-cap "cd ~/jsw-dev && $PY -m jsw.gateway.server --upstream http://127.0.0.1:$PORT --port $GW --log-dir ~/work/runs/cap-e1-gw2 --pythonic-fallback first 2>&1 | tee ~/work/logs/gw_cap_b2.log"
    sleep 3
    A=~/work/aeroeval/orig/system_prompts
    ~/work/venv-aerogen/bin/python -m jsw.workloads.aerogen_driver --out ~/work/runs/cap-e1-e4b-fp8kv-think-greedy-d1 \
      --task-file ~/work/tasks/p1_d1.txt --world-prompt $A/world_information/common_world_delivery.txt \
      --runtime-prompt $A/modularized_new/navigation/runtime_information.txt --pace-speedup 50 --seed 42 \
      --mission-timeout-s 3600 --max-tokens 32768 --gpu $GPU --base-url http://127.0.0.1:$GW/s/cap-b/v1 \
      --model gemma-4-E4B-it --effort think --temperature 0 --top-p 1 --top-k 1 --runs 2 --concurrency 1 --flush-each \
      > ~/work/logs/cap-e1-e4b-fp8kv-d1.log 2>&1
    log "D1 done rc=$?"
    tmux kill-session -t gw-cap 2>/dev/null
  else
    log "E4B FP8 KV (flashinfer) loads but a request fails: see ~/work/logs/smoke_e4b_fp8kv.log"
  fi
else
  log "E4B FP8 KV (flashinfer) does not start: see ~/work/logs/cap_e1b_server.log"
fi
tmux kill-session -t g$GPU-cap 2>/dev/null
log "CAP-E1b done"

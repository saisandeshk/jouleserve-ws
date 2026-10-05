#!/bin/bash
# CAP-E1 (OPTIONS_PLAN.md §2.4): does an FP8 KV cache cost quality on these agents, and does the capacity it buys
# cut energy live? On Ampere only fp8_e5m2 is available (fp8e4nv needs sm89+).
# 1. Capacity, live: granite-4.2-8b with an FP8 KV cache, P1's Orin 32 granite traffic replayed by 8 agents for
#    40 min (compare with RET-E1's bf16 run at 8 agents: same sessions, seed and window).
# 2. Quality: gemma-4-E4B with an FP8 KV cache on A-E1's controls (greedy; finish rate, valid programs, loops) and
#    on B-E1's D1 missions (greedy; strict pass, step sizes), against the bf16 runs.
# Usage: env/queue_cap_e1.sh <gpu> <port> <gwport>
set -u
GPU=${1:-0}; PORT=${2:-30000}; GW=${3:-31000}
PY=~/legacy/jouleserve-ws/.venv/bin/python
cd ~/jsw-dev
log() { echo "=== $(date +%T) $*"; }
serve() {  # model session-suffix extra...
  local m=$1; shift
  tmux kill-session -t g$GPU-cap 2>/dev/null; sleep 6
  tmux new-session -d -s g$GPU-cap "cd ~/jsw-dev && env/launch_model.sh $m $GPU $PORT --kv-cache-dtype fp8_e5m2 $* 2>&1 | tee ~/work/logs/cap_e1_server_$m.log"
  for i in $(seq 1 120); do curl -s -m 3 http://127.0.0.1:$PORT/v1/models | grep -q -E "granite|gemma" && return 0; sleep 5; done
  log "server $m failed"; return 1
}
# 1. granite, FP8 KV, 8 agents
if serve granite8b; then
  curl -s http://127.0.0.1:$PORT/get_server_info | python3 -c "import json,sys; d=json.load(sys.stdin); print('pool', d.get('max_total_num_tokens'), 'kv', d.get('kv_cache_dtype'))"
  NAME=cap-e1-o32granite-n8-fp8kv
  rm -rf ~/work/runs/$NAME; mkdir -p ~/work/runs/$NAME
  tmux kill-session -t gw-cap 2>/dev/null
  tmux new-session -d -s gw-cap "cd ~/jsw-dev && $PY -m jsw.gateway.server --upstream http://127.0.0.1:$PORT --port $GW --log-dir ~/work/runs/$NAME/gw 2>&1 | tee ~/work/logs/gw_$NAME.log"
  sleep 3; curl -s -X POST http://127.0.0.1:$PORT/flush_cache > /dev/null
  log "$NAME"
  $PY -m jsw.workloads.replay --sessions data/replay/t_o32_granite.jsonl --gateway http://127.0.0.1:$GW \
    --server http://127.0.0.1:$PORT --gpu $GPU --n 8 --horizon 2400 --grace 300 --ctx 26624 --seed 11 \
    --name $NAME > ~/work/logs/$NAME.log 2>&1
  log "$NAME done rc=$?"
  tmux kill-session -t gw-cap 2>/dev/null
fi
# 2. E4B, FP8 KV: A-E1 controls (greedy) and B-E1 D1 (greedy)
if serve gemma-e4b; then
  NAME=cap-e1-e4b-fp8kv-controls
  mkdir -p ~/work/runs/$NAME
  tmux new-session -d -s gw-cap "cd ~/jsw-dev && $PY -m jsw.gateway.server --upstream http://127.0.0.1:$PORT --port $GW --log-dir ~/work/runs/$NAME/gw --policy jsw.policies.decode_guard:DecodeGuard --policy-args '{\"action\": \"truncate\"}' 2>&1 | tee ~/work/logs/gw_$NAME.log"
  sleep 3
  log "$NAME"
  $PY -m jsw.workloads.loop_replay --prompts data/a_e1/prompts.jsonl --select pilot --arms greedy \
    --gateway http://127.0.0.1:$GW --server http://127.0.0.1:$PORT --gpu $GPU --model gemma-4-E4B-it \
    --concurrency 4 --name $NAME > ~/work/logs/$NAME.log 2>&1
  log "$NAME done rc=$?"
  tmux kill-session -t gw-cap 2>/dev/null
  mkdir -p ~/work/runs/cap-e1-gw
  tmux new-session -d -s gw-cap "cd ~/jsw-dev && $PY -m jsw.gateway.server --upstream http://127.0.0.1:$PORT --port $GW --log-dir ~/work/runs/cap-e1-gw --pythonic-fallback first 2>&1 | tee ~/work/logs/gw_cap_b.log"
  sleep 3
  A=~/work/aeroeval/orig/system_prompts
  log "cap-e1-e4b-fp8kv-think-greedy-d1"
  ~/work/venv-aerogen/bin/python -m jsw.workloads.aerogen_driver --out ~/work/runs/cap-e1-e4b-fp8kv-think-greedy-d1 \
    --task-file ~/work/tasks/p1_d1.txt --world-prompt $A/world_information/common_world_delivery.txt \
    --runtime-prompt $A/modularized_new/navigation/runtime_information.txt --pace-speedup 50 --seed 42 \
    --mission-timeout-s 3600 --max-tokens 32768 --gpu $GPU --base-url http://127.0.0.1:$GW/s/cap-b/v1 \
    --model gemma-4-E4B-it --effort think --temperature 0 --top-p 1 --top-k 1 --runs 2 --concurrency 1 --flush-each \
    > ~/work/logs/cap-e1-e4b-fp8kv-d1.log 2>&1
  log "cap-e1 D1 done rc=$?"
  tmux kill-session -t gw-cap 2>/dev/null
fi
tmux kill-session -t g$GPU-cap 2>/dev/null
log "CAP-E1 done"

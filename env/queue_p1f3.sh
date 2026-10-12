#!/bin/bash
# P1F-3 (planning/OPTIONS_PLAN.md §5.1): RET-E1 and CAP-E1 redone on P1's clean Orin 32 granite sessions
# (data/replay/t_o32_granite.jsonl, P1F-2) at P1's re-run pool, so the WS numbers line up with CAP-J1's:
# bf16 at 25,358 tokens (N = 1, 4, 8; GPU0) and FP8 KV at the same bytes, 50,716 tokens (N = 4, 8; GPU1).
# Each point: server restarted with the pool set exactly, cache flushed, replay with a 10-minute warm-up and a
# 60-minute measured window (--warm 600 --horizon 4200), the agent's window held at the bf16 pool (--ctx 25358),
# seed 11; the server stops at the end. traffic_sim on the same sessions runs in the analysis (analysis/p1f3.py).
# Usage: env/queue_p1f3.sh <gpu> <port> <gwport> <points...>   points: bf16n1 bf16n4 bf16n8 fp8n4 fp8n8
set -u
GPU=$1; PORT=$2; GW=$3; shift 3
PY=~/legacy/jouleserve-ws/.venv/bin/python
STAMP=$(date +%Y%m%dT%H%M)
if [ "$GPU" = 0 ]; then CORES=0-9,20-29; else CORES=10-19,30-39; fi   # the harness on its GPU's NUMA node
cd ~/jsw-dev
log() { echo "=== $(date +%T) $*"; }
serve() {  # kv pool
  tmux kill-session -t g$GPU-p1f3 2>/dev/null; sleep 8
  local kvf=""; [ "$1" = fp8 ] && kvf="--kv-cache-dtype fp8_e5m2"
  tmux new-session -d -s g$GPU-p1f3 "cd ~/jsw-dev && env/launch_model.sh granite8b $GPU $PORT --max-total-tokens $2 $kvf \
    2>&1 | tee ~/work/logs/p1f3_server_g$GPU.log"
  for i in $(seq 1 120); do curl -s -m 3 http://127.0.0.1:$PORT/v1/models | grep -q granite && return 0; sleep 5; done
  return 1
}
for p in "$@"; do
  case $p in
    bf16n1) kv=bf16; pool=25358; n=1 ;;
    bf16n4) kv=bf16; pool=25358; n=4 ;;
    bf16n8) kv=bf16; pool=25358; n=8 ;;
    fp8n4)  kv=fp8;  pool=50716; n=4 ;;
    fp8n8)  kv=fp8;  pool=50716; n=8 ;;
    *) log "unknown point $p"; continue ;;
  esac
  name=p1f3-ws-$p-$STAMP
  serve $kv $pool || { log "$name SERVER_FAILED"; continue; }
  got=$(curl -s http://127.0.0.1:$PORT/get_server_info | python3 -c "import json,sys; print(json.load(sys.stdin).get('max_total_num_tokens'))")
  [ "$got" = "$pool" ] || { log "$name POOL_MISMATCH got $got want $pool"; continue; }
  mkdir -p ~/work/runs/$name
  tmux kill-session -t gw-p1f3-g$GPU 2>/dev/null
  tmux new-session -d -s gw-p1f3-g$GPU "cd ~/jsw-dev && taskset -c $CORES $PY -m jsw.gateway.server --upstream http://127.0.0.1:$PORT --port $GW \
    --log-dir ~/work/runs/$name/gw > ~/work/logs/gw_$name.log 2>&1"
  sleep 3
  curl -s -X POST http://127.0.0.1:$PORT/flush_cache > /dev/null
  log "$name start (kv $kv pool $pool n $n)"
  taskset -c $CORES $PY -m jsw.workloads.replay --sessions data/replay/t_o32_granite.jsonl --gateway http://127.0.0.1:$GW \
    --server http://127.0.0.1:$PORT --gpu $GPU --n $n --warm 600 --horizon 4200 --grace 300 --ctx 25358 --seed 11 \
    --name $name --note "P1F-3 $p (clean sessions, P1F-2)" > ~/work/logs/$name.log 2>&1
  log "$name done rc=$?"
  tmux kill-session -t gw-p1f3-g$GPU 2>/dev/null
done
tmux kill-session -t g$GPU-p1f3 2>/dev/null
sleep 10
log "P1F-3 queue on GPU$GPU done; GPU memory $(nvidia-smi --query-gpu=memory.used --format=csv,noheader -i $GPU)"

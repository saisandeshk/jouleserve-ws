#!/bin/bash
# RET-E1 (OPTIONS_PLAN.md §2.4): does the simulator's "default within 2.4%" and capacity knee hold on a live engine?
# P1's Orin 32 granite traffic runs (data/replay/t_o32_granite.jsonl) replayed on granite-4.2-8b on one A5000 at
# 26,467 tokens (P1's Orin 32 granite pool: 26-27K), window 26,624 (P1's). N = 1, 4, 8 agents with SGLang's default;
# N = 8 with no reuse (drop state at every wait). Each point: --horizon s + grace; the cache flushed at the start.
# Usage: env/queue_ret_e1.sh <gpu> <port> <gwport> [horizon_s] [order: n1 n4 n8 n8nr]
# Several GPUs can share the list: a run is skipped when it is finished or another GPU holds its lock file.
set -u
GPU=${1:-0}; PORT=${2:-30000}; GW=${3:-31000}; H=${4:-2400}; ORDER=${5:-n1 n4 n8 n8nr}
PY=~/legacy/jouleserve-ws/.venv/bin/python
cd ~/jsw-dev
log() { echo "=== $(date +%T) $*"; }
if ! curl -s -m 3 http://127.0.0.1:$PORT/v1/models | grep -q granite; then
  tmux kill-session -t g$GPU-granite 2>/dev/null; sleep 5
  tmux new-session -d -s g$GPU-granite "cd ~/jsw-dev && env/launch_model.sh granite8b $GPU $PORT 2>&1 | tee ~/work/logs/ret_e1_server.log"
  for i in $(seq 1 120); do curl -s -m 3 http://127.0.0.1:$PORT/v1/models | grep -q granite && break; sleep 5; done
fi
run() {  # name n extra-args
  local name=$1 n=$2; shift 2
  [ -f ~/work/runs/$name/manifest.json ] && grep -q t_end_mono ~/work/runs/$name/manifest.json && { log "skip $name (done)"; return; }
  [ -f ~/work/runs/$name.lock ] && { log "skip $name (locked by $(cat ~/work/runs/$name.lock))"; return; }
  echo "gpu$GPU $(date +%T)" > ~/work/runs/$name.lock
  rm -rf ~/work/runs/$name; mkdir -p ~/work/runs/$name
  tmux kill-session -t gw-ret$GPU 2>/dev/null
  tmux new-session -d -s gw-ret$GPU "cd ~/jsw-dev && $PY -m jsw.gateway.server --upstream http://127.0.0.1:$PORT --port $GW \
    --log-dir ~/work/runs/$name/gw 2>&1 | tee ~/work/logs/gw_$name.log"
  sleep 3
  curl -s -X POST http://127.0.0.1:$PORT/flush_cache > /dev/null
  log "$name"
  $PY -m jsw.workloads.replay --sessions data/replay/t_o32_granite.jsonl --gateway http://127.0.0.1:$GW \
    --server http://127.0.0.1:$PORT --gpu $GPU --n $n --horizon $H --grace 300 --ctx 26624 --seed 11 \
    --name $name "$@" > ~/work/logs/$name.log 2>&1
  log "$name done rc=$?"
}
for p in $ORDER; do
  case $p in
    n1) run ret-e1-o32granite-n1-default 1 ;;
    n4) run ret-e1-o32granite-n4-default 4 ;;
    n8) run ret-e1-o32granite-n8-default 8 ;;
    n8nr) run ret-e1-o32granite-n8-noreuse 8 --no-reuse ;;
  esac
done
tmux kill-session -t gw-ret$GPU 2>/dev/null
log "RET-E1 done"

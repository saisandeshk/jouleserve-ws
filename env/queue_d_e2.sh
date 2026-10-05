#!/bin/bash
# D-E2 (OPTIONS_PLAN.md §2.4): is the vision burst worth more than 0.6% with several agents? P1's Orin 32
# gemma-E4B traffic sessions that contain an ask_vlm burst (data/replay/t_o32_e4b.jsonl), replayed on gemma-4-E4B
# (P1's weights) with the bursts sent as concurrent tool-tagged requests, under 4 gateway policies (D-P1):
# default (equal priority = LRU), pin (agent > burst priority), admit4 (<= 4 burst requests at a time while the
# pool is >= 50% used), both. Pools: 12,415 tokens (Orin 64 gemma's) and the full WS pool (~63.5K; Orin 32: 71K).
# Usage: env/queue_d_e2.sh <gpu> <port> <gwport> [horizon_s]
set -u
GPU=${1:-1}; PORT=${2:-30001}; GW=${3:-31002}; H=${4:-720}
PY=~/legacy/jouleserve-ws/.venv/bin/python
cd ~/jsw-dev
log() { echo "=== $(date +%T) $*"; }
SESS=data/replay/t_o32_e4b_bursts.jsonl
$PY -c "
import json
rows=[json.loads(l) for l in open('data/replay/t_o32_e4b.jsonl')]
keep=[r for r in rows if any(s.get('burst') for s in r['steps'])]
open('$SESS','w').write(''.join(json.dumps(r)+'\n' for r in keep)); print(len(keep), 'sessions with bursts')"
serve() {  # pool
  tmux kill-session -t g$GPU-e4b 2>/dev/null; sleep 8
  local extra=""; [ "$1" != full ] && extra="--max-total-tokens $1"
  tmux new-session -d -s g$GPU-e4b "cd ~/jsw-dev && env/launch_model.sh gemma-e4b $GPU $PORT --enable-priority-scheduling \
    --schedule-policy fcfs --radix-eviction-policy priority $extra 2>&1 | tee ~/work/logs/d_e2_server_$1.log"
  for i in $(seq 1 120); do curl -s -m 3 http://127.0.0.1:$PORT/v1/models | grep -q gemma && return 0; sleep 5; done
  log "server failed ($1)"; exit 1
}
run() {  # name pool n policy-args
  local name=$1 pool=$2 n=$3 pargs=$4
  [ -f ~/work/runs/$name/manifest.json ] && grep -q t_end_mono ~/work/runs/$name/manifest.json && { log "skip $name"; return; }
  rm -rf ~/work/runs/$name; mkdir -p ~/work/runs/$name
  tmux kill-session -t gw-d-e2 2>/dev/null
  tmux new-session -d -s gw-d-e2 "cd ~/jsw-dev && $PY -m jsw.gateway.server --upstream http://127.0.0.1:$PORT --port $GW \
    --log-dir ~/work/runs/$name/gw --policy jsw.policies.burst_memory:BurstMemory --policy-args '$pargs' 2>&1 | tee ~/work/logs/gw_$name.log"
  sleep 3
  curl -s -X POST http://127.0.0.1:$PORT/flush_cache > /dev/null
  log "$name"
  $PY -m jsw.workloads.replay --sessions $SESS --gateway http://127.0.0.1:$GW --server http://127.0.0.1:$PORT \
    --gpu $GPU --n $n --horizon $H --grace 180 --ctx 32768 --bursts --seed 7 --name $name > ~/work/logs/$name.log 2>&1
  log "$name done rc=$?"
}
DEF='{}'; PIN='{"pin": true}'; ADM='{"admit_k": 4, "usage_threshold": 0.5}'; BOTH='{"pin": true, "admit_k": 4, "usage_threshold": 0.5}'
serve 12415
for n in 1 4; do
  run d-e2-p12k-n$n-default 12415 $n "$DEF"
  run d-e2-p12k-n$n-pin     12415 $n "$PIN"
  run d-e2-p12k-n$n-admit4  12415 $n "$ADM"
  run d-e2-p12k-n$n-both    12415 $n "$BOTH"
done
serve full
run d-e2-pfull-n4-default full 4 "$DEF"
run d-e2-pfull-n4-both    full 4 "$BOTH"
tmux kill-session -t gw-d-e2 2>/dev/null
log "D-E2 done"

#!/bin/bash
# CAP-J1, its anchor and RET-J1 on one Orin 32 (planning/OPTIONS_PLAN.md §5.2, §5.4), driven from the WS in tmux.
# Each point restarts granite with P1's flags (env/launch_jetson.py), changing only the KV dtype, the pool
# (--max-total-tokens) and the running-request limit, then runs env/jetson_replay_point.sh with plan §5.2's settings:
# P1's clean Orin 32 granite sessions (P1F-2), seed 11, --warm 600 --horizon 7800 --grace 300, the agent's window held
# at the bf16 pool (--ctx 25358), 5-minute idle baselines before and after, preflight before and after.
# Points: bf16n4 bf16n8 fp8n4 fp8n8 (replicates), anchor (bf16, N = 1, one request at a time, SGLang's default),
#         retj1 (as anchor, with --no-reuse: fresh IDs for every prompt, nothing kept between tool waits).
# Usage: env/queue_capj1.sh <unit> <tag e.g. o32a> <points...>
set -u
UNIT=$1; TAG=$2; shift 2
PY=~/work/venv-analysis/bin/python
SESS=~/jsw-dev/data/replay/t_o32_granite.jsonl
cd ~/jsw-dev
log() { echo "=== $(date +%T) $*"; }
stop_ours() { ssh -o BatchMode=yes $UNIT 'ids=$(docker ps -q -f name=p5-); [ -n "$ids" ] && docker stop $ids >/dev/null; true'; }
for p in "$@"; do
  extra=""
  case $p in
    bf16n4) kv=bf16; pool=25358; n=4 ;;
    bf16n8) kv=bf16; pool=25358; n=8 ;;
    fp8n4)  kv=fp8_e5m2; pool=50716; n=4 ;;
    fp8n8)  kv=fp8_e5m2; pool=50716; n=8 ;;
    anchor) kv=bf16; pool=25358; n=1 ;;
    retj1)  kv=bf16; pool=25358; n=1; extra="--no-reuse" ;;
    *) log "unknown point $p"; continue ;;
  esac
  STAMP=$(date +%Y%m%dT%H%M)
  case $p in
    retj1) name=retj1-$TAG-noreuse-$STAMP ;;
    *)     name=capj1-$TAG-$p-$STAMP ;;
  esac
  stop_ours
  log "$name server (kv $kv pool $pool max-running $n)"
  if ! $PY env/launch_jetson.py $UNIT $p --model granite --kv $kv --pool $pool --max-running $n \
       --out ~/work/runs/$name/server.json > ~/work/logs/${name}_server.log 2>&1; then
    log "$name SERVER_FAILED $(tail -c 300 ~/work/logs/${name}_server.log)"; continue
  fi
  got=$(python3 -c "import json; print(json.load(open('$HOME/work/runs/$name/server.json')).get('pool'))")
  [ "$got" = "$pool" ] || { log "$name POOL_MISMATCH got $got want $pool"; stop_ours; continue; }
  env/jetson_replay_point.sh $UNIT $name $SESS $n 600 7800 300 25358 300 $pool $extra
  log "$name point rc=$?"
  stop_ours
done
log "queue $TAG done"

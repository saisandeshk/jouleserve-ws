#!/bin/bash
# One replay point on a Jetson, driven from the WS (planning/OPTIONS_PLAN.md §4.1-§4.2, §5.2). The server must already
# run on the unit (env/launch_jetson.py). Steps: preflight before (quiet, clocks, disk, time, temperature, server; one
# discarded warm-up; idle baseline; P1's verified flush), a gateway in tmux on the WS, the replayer with board
# telemetry (--device), preflight after (temperature exempt; idle baseline), SHA-256 sums of the run directory.
# Usage: env/jetson_replay_point.sh <unit> <run> <sessions.jsonl> <n> <warm_s> <horizon_s> <grace_s> <ctx> <idle_s> \
#        <pool> [extra replay args]
# Prints one line per step; "PREFLIGHT_BEFORE_FAILED" or "rc=<non-zero>" marks a failed point.
set -u
UNIT=$1; NAME=$2; SESS=$3; N=$4; WARM=$5; H=$6; GRACE=$7; CTX=$8; IDLE=$9; POOL=${10}; shift 10
PY=~/legacy/jouleserve-ws/.venv/bin/python
cd ~/jsw-dev
cfg() { python3 -c "import json; print(json.load(open('configs/jetsons.json'))['$UNIT']['$1'])"; }
IP=$(cfg ip); P5=$(cfg p5); GW=$((31000 + ${IP##*.})); URL=http://$IP:30000
R=~/work/runs/$NAME
mkdir -p $R
log() { echo "=== $(date +%T) $*"; }
log "$NAME preflight before"
$PY env/jetson_preflight.py $UNIT --server $URL --pool $POOL --warmup --wait-cool 900 --idle $IDLE \
  --out $R/preflight_before > $R/preflight_before.log 2>&1 || { log "$NAME PREFLIGHT_BEFORE_FAILED $(tail -1 $R/preflight_before.log)"; exit 2; }
$PY env/jetson_preflight.py $UNIT --server $URL --flush --wait-cool 600 > $R/preflight_flush.log 2>&1 \
  || { log "$NAME PREFLIGHT_BEFORE_FAILED (flush) $(tail -1 $R/preflight_flush.log)"; exit 2; }
tmux kill-session -t gw-$UNIT 2>/dev/null
tmux new-session -d -s gw-$UNIT "cd ~/jsw-dev && $PY -m jsw.gateway.server --upstream $URL --port $GW --log-dir $R/gw \
  --generate-stream > ~/work/logs/gw_$NAME.log 2>&1"
sleep 3
log "$NAME replay n=$N warm=$WARM horizon=$H ctx=$CTX"
$PY -m jsw.workloads.replay --sessions $SESS --gateway http://127.0.0.1:$GW --server $URL --n $N --warm $WARM \
  --horizon $H --grace $GRACE --ctx $CTX --seed 11 --device $UNIT:$P5 --name $NAME "$@" > ~/work/logs/$NAME.log 2>&1
rc=$?
tmux kill-session -t gw-$UNIT 2>/dev/null
log "$NAME replay rc=$rc"
$PY env/jetson_preflight.py $UNIT --server $URL --no-temp --idle $IDLE --out $R/preflight_after \
  > $R/preflight_after.log 2>&1; prc=$?
(cd $R && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
log "$NAME done rc=$rc preflight_after=$prc"
[ $rc -eq 0 ] && [ $prc -eq 0 ]

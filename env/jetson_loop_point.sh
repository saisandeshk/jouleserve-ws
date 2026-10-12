#!/bin/bash
# P1's recorded drone requests on a Jetson under decoding arms (DEV-4 check (c); A-J1, planning/OPTIONS_PLAN.md §5.3),
# driven from the WS. The server must already run on the unit (env/launch_jetson.py --model gemma26b). Steps:
# preflight before (warm-up, idle baseline, verified flush), a gateway with the decode guard in "truncate" mode (a
# call stops where the loop detector fires, as in A-E1), jsw/workloads/loop_replay.py with board telemetry,
# preflight after (temperature exempt), SHA-256 sums.
# Usage: env/jetson_loop_point.sh <unit> <run> <select: pilot|full|rfx> <arms> <idle_s> [extra loop_replay args]
set -u
UNIT=$1; NAME=$2; SEL=$3; ARMS=$4; IDLE=$5; shift 5
PY=~/legacy/jouleserve-ws/.venv/bin/python
cd ~/jsw-dev
cfg() { python3 -c "import json; print(json.load(open('configs/jetsons.json'))['$UNIT']['$1'])"; }
IP=$(cfg ip); P5=$(cfg p5); GW=$((31000 + ${IP##*.})); URL=http://$IP:30000
R=~/work/runs/$NAME
mkdir -p $R
log() { echo "=== $(date +%T) $*"; }
log "$NAME preflight before"
$PY env/jetson_preflight.py $UNIT --server $URL --warmup --flush --wait-cool 900 --idle $IDLE --out $R/preflight_before \
  > $R/preflight_before.log 2>&1 || { log "$NAME PREFLIGHT_BEFORE_FAILED $(tail -1 $R/preflight_before.log)"; exit 2; }
tmux kill-session -t gw-$UNIT 2>/dev/null
tmux new-session -d -s gw-$UNIT "cd ~/jsw-dev && $PY -m jsw.gateway.server --upstream $URL --port $GW --log-dir $R/gw \
  --policy jsw.policies.decode_guard:DecodeGuard --policy-args '{\"action\": \"truncate\"}' > ~/work/logs/gw_$NAME.log 2>&1"
sleep 3
log "$NAME loop_replay select=$SEL arms=$ARMS"
$PY -m jsw.workloads.loop_replay --prompts data/a_e1/prompts.jsonl --select $SEL --arms $ARMS --gateway http://127.0.0.1:$GW \
  --server $URL --gpu '' --model google/gemma-4-26B-A4B-it --concurrency 1 --device $UNIT:$P5 --name $NAME "$@" \
  > ~/work/logs/$NAME.log 2>&1
rc=$?
tmux kill-session -t gw-$UNIT 2>/dev/null
log "$NAME loop_replay rc=$rc"
$PY env/jetson_preflight.py $UNIT --server $URL --no-temp --idle $IDLE --out $R/preflight_after \
  > $R/preflight_after.log 2>&1; prc=$?
(cd $R && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
log "$NAME done rc=$rc preflight_after=$prc"
[ $rc -eq 0 ] && [ $prc -eq 0 ]

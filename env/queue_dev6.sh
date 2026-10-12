#!/bin/bash
# DEV-6 (planning/OPTIONS_PLAN.md §4.1): are the three Orin 32s interchangeable? On one unit: granite bf16 with P1's
# flags (pool 25,358; running requests up to 8 so batch 8 can run), preflight with a 10-minute idle reading, then
# calibrate2 on the board: decode J/token and tokens/s at batch 1 and 8 (contexts 1,000 and 8,000; 256 tokens), plus
# two prefill lengths. Rule: interchangeable if idle power and decode J/token agree within +-3% across units.
# Usage: env/queue_dev6.sh <unit> <tag e.g. o32c>
set -u
UNIT=$1; TAG=$2
PY=~/work/venv-analysis/bin/python
cd ~/jsw-dev
cfg() { python3 -c "import json; print(json.load(open('configs/jetsons.json'))['$UNIT']['$1'])"; }
IP=$(cfg ip); P5=$(cfg p5); URL=http://$IP:30000
name=dev6-$TAG-$(date +%Y%m%dT%H%M); R=~/work/runs/$name; mkdir -p $R
log() { echo "=== $(date +%T) $*"; }
ssh -o BatchMode=yes $UNIT 'ids=$(docker ps -q -f name=p5-); [ -n "$ids" ] && docker stop $ids >/dev/null; true'
log "$name server"
$PY env/launch_jetson.py $UNIT dev6 --model granite --kv bf16 --pool 25358 --max-running 8 --out $R/server.json \
  > ~/work/logs/${name}_server.log 2>&1 || { log "$name SERVER_FAILED"; exit 1; }
log "$name preflight + 10-minute idle"
$PY env/jetson_preflight.py $UNIT --server $URL --pool 25358 --warmup --flush --wait-cool 1800 --idle 600 \
  --out $R/preflight_before > $R/preflight_before.log 2>&1 || { log "$name PREFLIGHT_BEFORE_FAILED $(tail -1 $R/preflight_before.log)"; }
log "$name calibrate2"
$PY -m jsw.costs.calibrate2 --server $URL --device $UNIT:$P5 --batches 1,8 --ctx-lens 1000,8000 --prefill-lens 2000,8000 \
  --gen 256 --reps 2 --out $R/calib.json > ~/work/logs/$name.log 2>&1
log "$name calibrate2 rc=$?"
$PY env/jetson_preflight.py $UNIT --server $URL --no-temp --out $R/preflight_after > $R/preflight_after.log 2>&1
ssh -o BatchMode=yes $UNIT 'ids=$(docker ps -q -f name=p5-); [ -n "$ids" ] && docker stop $ids >/dev/null; true'
(cd $R && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
log "$name done"

#!/bin/bash
# DEV-7a (planning/OPTIONS_PLAN.md §5.5): P1's 26B on Orin-64-1 with the flags of P1's server found there on 12 Oct
# (env/launch_jetson.py: context 65,536, mem 0.95, SWA ratio 0.2, CUDA graphs up to batch 1, pool 60,000 requested),
# FP8 KV (P1's) then bf16 KV. Per KV dtype: the pool SGLang actually builds, a 10-minute idle reading, then calibrate2
# on the board (prefill time and energy against length; decode J/token and tokens/s against batch and context; points
# that do not fit the pool are skipped). Running requests up to 8 so batch 8 can run. Report only.
# Usage: env/queue_dev7.sh [kv ...]    (default: fp8_e5m2 bf16)
set -u
UNIT=Orin-64-1
PY=~/work/venv-analysis/bin/python
cd ~/jsw-dev
cfg() { python3 -c "import json; print(json.load(open('configs/jetsons.json'))['$UNIT']['$1'])"; }
IP=$(cfg ip); P5=$(cfg p5); URL=http://$IP:30000
log() { echo "=== $(date +%T) $*"; }
stop_ours() { ssh -o BatchMode=yes $UNIT 'ids=$(docker ps -q -f name=p5-); [ -n "$ids" ] && docker stop $ids >/dev/null; true'; }
KVS=${*:-fp8_e5m2 bf16}
for kv in $KVS; do
  name=dev7a-o64-${kv%%_*}-$(date +%Y%m%dT%H%M); R=~/work/runs/$name; mkdir -p $R
  stop_ours
  log "$name server (gemma26b, kv $kv)"
  if ! $PY env/launch_jetson.py $UNIT dev7 --model gemma26b --kv $kv --max-running 8 --out $R/server.json \
       > ~/work/logs/${name}_server.log 2>&1; then
    log "$name SERVER_FAILED $(tail -c 300 ~/work/logs/${name}_server.log)"; stop_ours; continue
  fi
  pool=$(python3 -c "import json; print(json.load(open('$R/server.json')).get('pool'))")
  log "$name pool $pool"
  $PY env/jetson_preflight.py $UNIT --server $URL --pool $pool --warmup --flush --wait-cool 1800 --idle 600 \
    --out $R/preflight_before > $R/preflight_before.log 2>&1 \
    || { log "$name PREFLIGHT_BEFORE_FAILED $(tail -1 $R/preflight_before.log)"; stop_ours; continue; }
  log "$name calibrate2"
  $PY -m jsw.costs.calibrate2 --server $URL --device $UNIT:$P5 --batches 1,4,8 --ctx-lens 1000,8000,32000 \
    --prefill-lens 2000,8000,16000 --gen 256 --reps 2 --out $R/calib.json > ~/work/logs/$name.log 2>&1
  log "$name calibrate2 rc=$?"
  $PY env/jetson_preflight.py $UNIT --server $URL --no-temp --out $R/preflight_after > $R/preflight_after.log 2>&1
  log "$name preflight_after=$?"
  stop_ours
  (cd $R && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
  log "$name done"
done
log "queue dev7a done"

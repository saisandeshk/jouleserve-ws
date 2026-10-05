#!/bin/bash
# A-E2 (OPTIONS_PLAN.md §2.4): after an online stop, does a retry finish usefully, and at what cost?
# The prompts that looped under greedy decoding in an A-E1 run, replayed greedy (P1's protocol) through the gateway
# with the decode guard: stop where the loop detector fires, then retry once with action R1 resample (Gemma's
# defaults), R2 nudge (a note that the attempt repeated itself), R3 budget (max_tokens 8,192). The client sees the
# retry's result; the gateway logs both attempts.
# Usage: env/queue_a_e2.sh <server-url> <gpu> <gwport> <model> <from-run-dir> <name-prefix>
set -u
SRV=$1; GPU=$2; GW=$3; MODEL=$4; FROM=$5; PFX=$6
PY=~/legacy/jouleserve-ws/.venv/bin/python
cd ~/jsw-dev
log() { echo "=== $(date +%T) $*"; }
for act in resample nudge budget; do
  NAME=$PFX-$act
  [ -f ~/work/runs/$NAME/manifest.json ] && grep -q t_end_mono ~/work/runs/$NAME/manifest.json && { log "skip $NAME"; continue; }
  mkdir -p ~/work/runs/$NAME
  tmux kill-session -t gw-a-e2 2>/dev/null
  tmux new-session -d -s gw-a-e2 "cd ~/jsw-dev && $PY -m jsw.gateway.server --upstream $SRV --port $GW --log-dir ~/work/runs/$NAME/gw \
    --policy jsw.policies.decode_guard:DecodeGuard --policy-args '{\"action\": \"$act\", \"max_retries\": 1, \"budget_tokens\": 8192}' \
    2>&1 | tee ~/work/logs/gw_$NAME.log"
  sleep 4
  log "$NAME"
  $PY -m jsw.workloads.loop_replay --prompts data/a_e1/prompts.jsonl --select full --from-run $FROM --arms greedy \
    --gateway http://127.0.0.1:$GW --server $SRV --gpu $GPU --model $MODEL --concurrency 2 --name $NAME \
    > ~/work/logs/$NAME.log 2>&1
  log "$NAME done rc=$?"
done
tmux kill-session -t gw-a-e2 2>/dev/null
log "A-E2 done"

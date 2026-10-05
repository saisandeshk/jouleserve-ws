#!/bin/bash
# A-E1 (OPTIONS_PLAN.md §2.4): do Gemma-4's loops survive sampling? P1's recorded capped Thor prompts and finished
# controls, replayed exactly, under P1's greedy protocol and Gemma's default sampling, through the gateway with
# the decode guard in "truncate" mode (a call stops where the loop detector fires).
# Needs: the model on :30000 (gemma26b-fp8-text, TP=2 on GPUs 0,1; or gemma-e4b), data/a_e1/prompts.jsonl
# (python -m analysis.loop_prompts). Usage: env/queue_a_e1.sh <stage: pilot|full|o32> <model> <gpus> [concurrency]
set -u
STAGE=${1:?pilot|full|o32}; MODEL=${2:?served model name}; GPUS=${3:?gpus}; CONC=${4:-12}
NAME=a-e1-$STAGE-$(echo $MODEL | tr 'A-Z' 'a-z' | tr -c 'a-z0-9\n' '-' | sed 's/-*$//')
PY=~/legacy/jouleserve-ws/.venv/bin/python
cd ~/jsw-dev
mkdir -p ~/work/runs/$NAME
tmux kill-session -t gw-a-e1 2>/dev/null
tmux new-session -d -s gw-a-e1 "$PY -m jsw.gateway.server --upstream http://127.0.0.1:30000 --port 31000 \
  --log-dir ~/work/runs/$NAME/gw --policy jsw.policies.decode_guard:DecodeGuard --policy-args '{\"action\": \"truncate\"}' \
  2>&1 | tee ~/work/logs/gw_$NAME.log"
sleep 4
case "$STAGE" in
  pilot) ARMS=greedy,sampled:0 ;;
  full)  ARMS=greedy,sampled:0 ;;
  o32)   ARMS=greedy,sampled:0,sampled:1 ;;
esac
echo "=== $(date +%T) $NAME arms=$ARMS conc=$CONC"
$PY -m jsw.workloads.loop_replay --prompts data/a_e1/prompts.jsonl --select $STAGE --arms $ARMS \
  --gateway http://127.0.0.1:31000 --server http://127.0.0.1:30000 --gpu $GPUS --model $MODEL \
  --concurrency $CONC --name $NAME > ~/work/logs/$NAME.log 2>&1
echo "=== $(date +%T) $NAME done rc=$?"
tmux kill-session -t gw-a-e1 2>/dev/null

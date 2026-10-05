#!/bin/bash
# GPU0 chain 4 (2026-10-06 05:20): A-E2's resample retry runs on all 29 looping prompts; the nudge retry (does a
# stop plus a note work when decoding must stay greedy?) on 12 of them; the budget retry is dropped (under greedy
# decoding it is expected to loop again; time goes to RET-E1). Then RET-E1.
set -u
cd ~/jsw-dev
PY=~/legacy/jouleserve-ws/.venv/bin/python
log() { echo "=== $(date +%T) $*"; }
tmux kill-session -t gw-a-e2 2>/dev/null
if ! curl -s -m 3 http://127.0.0.1:30002/v1/models | grep -q gemma; then
  tmux kill-session -t g0-llama 2>/dev/null; sleep 5
  tmux new-session -d -s g0-llama "cd ~/jsw-dev && env/launch_llamacpp.sh 0 30002 2 40960 2>&1 | tee ~/work/logs/llama_server_g0c.log"
  for i in $(seq 1 120); do curl -s -m 3 http://127.0.0.1:30002/v1/models | grep -q gemma && break; sleep 5; done
fi
NAME=a-e2-g26b-gguf-nudge
rm -rf ~/work/runs/$NAME; mkdir -p ~/work/runs/$NAME
tmux new-session -d -s gw-a-e2 "cd ~/jsw-dev && $PY -m jsw.gateway.server --upstream http://127.0.0.1:30002 --port 31006 --log-dir ~/work/runs/$NAME/gw \
  --policy jsw.policies.decode_guard:DecodeGuard --policy-args '{\"action\": \"nudge\", \"max_retries\": 1}' 2>&1 | tee ~/work/logs/gw_$NAME.log"
sleep 4
log "$NAME (12 prompts)"
$PY -m jsw.workloads.loop_replay --prompts data/a_e1/prompts.jsonl --select full --from-run ~/work/runs/a-e1-rfx-g26b-gguf \
  --arms greedy --gateway http://127.0.0.1:31006 --server http://127.0.0.1:30002 --gpu 0 --model gemma-4-26B-A4B-it-gguf \
  --concurrency 2 --limit 12 --name $NAME > ~/work/logs/$NAME.log 2>&1
log "$NAME done rc=$?"
tmux kill-session -t gw-a-e2 2>/dev/null; tmux kill-session -t g0-llama 2>/dev/null; sleep 8
env/queue_ret_e1.sh 0 30000 31000 2400
log "GPU0 chain 4 done"

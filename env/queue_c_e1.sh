#!/bin/bash
# C-E1 (OPTIONS_PLAN.md §2.4): does tau2-bench give a retained-state opportunity? P1's gemma-4-E4B as the agent
# (thinking on, Gemma's default sampling) and as the user simulator (thinking off), one conversation at a time,
# through the gateway (agent calls: session tau-agent-<domain>; user: tau-user-<domain>). Per agent call the
# gateway logs prompt, cached and output tokens: the ceiling P/(P + r*O) follows (analysis/c_e1.py).
# Usage: env/queue_c_e1.sh <gpu> <port> <gwport> [num_tasks] [smoke]
set -u
GPU=${1:-1}; PORT=${2:-30001}; GW=${3:-31003}; NT=${4:-20}; SMOKE=${5:-}
PY=~/legacy/jouleserve-ws/.venv/bin/python
TAU=~/work/venv-tau2/bin/tau2
cd ~/jsw-dev
log() { echo "=== $(date +%T) $*"; }
if ! curl -s -m 3 http://127.0.0.1:$PORT/v1/models | grep -q gemma-4-E4B; then
  tmux kill-session -t g$GPU-e4b 2>/dev/null; sleep 5
  tmux new-session -d -s g$GPU-e4b "cd ~/jsw-dev && env/launch_model.sh gemma-e4b $GPU $PORT 2>&1 | tee ~/work/logs/c_e1_server.log"
  for i in $(seq 1 120); do curl -s -m 3 http://127.0.0.1:$PORT/v1/models | grep -q gemma && break; sleep 5; done
fi
THINK=${THINK:-true}
DOMAINS=${DOMAINS:-airline retail}
NAME=c-e1${SMOKE:+-smoke}$([ "$THINK" = false ] && echo -nothink)
mkdir -p ~/work/runs/$NAME
tmux kill-session -t gw-c-e1 2>/dev/null
tmux new-session -d -s gw-c-e1 "cd ~/jsw-dev && $PY -m jsw.gateway.server --upstream http://127.0.0.1:$PORT --port $GW \
  --log-dir ~/work/runs/$NAME/gw --pythonic-fallback first 2>&1 | tee ~/work/logs/gw_$NAME.log"
sleep 3
for D in $DOMAINS; do
  [ -n "$SMOKE" ] && [ "$D" = retail ] && break
  A="{\"api_base\": \"http://127.0.0.1:$GW/s/tau-agent-$D/v1\", \"api_key\": \"EMPTY\", \"temperature\": 1.0, \"top_p\": 0.95, \"max_tokens\": 8000, \"extra_body\": {\"top_k\": 64, \"chat_template_kwargs\": {\"enable_thinking\": $THINK}}}"
  U="{\"api_base\": \"http://127.0.0.1:$GW/s/tau-user-$D/v1\", \"api_key\": \"EMPTY\", \"temperature\": 0.0, \"max_tokens\": 2000, \"extra_body\": {\"chat_template_kwargs\": {\"enable_thinking\": false}}}"
  log "$NAME $D"
  ( cd ~/work/tau2-bench && $TAU run --domain $D --agent llm_agent --agent-llm openai/gemma-4-E4B-it --agent-llm-args "$A" \
      --user user_simulator --user-llm openai/gemma-4-E4B-it --user-llm-args "$U" --num-tasks $([ -n "$SMOKE" ] && echo 2 || echo $NT) \
      --max-concurrency 1 --seed 300 --save-to ~/work/runs/$NAME/$D.json > ~/work/logs/${NAME}_$D.log 2>&1 )
  log "$NAME $D done rc=$?"
done
tmux kill-session -t gw-c-e1 2>/dev/null
log "C-E1 done"

#!/bin/bash
# B-E1 (OPTIONS_PLAN.md §2.4): P1's own model family as a step-wise agent on P1's delivery tasks D1-D3,
# the same protocol as the 2026-10-02 step-wise test (env/queue_stepwise_d.sh): aerogen's agent loop, P1's task
# texts and delivery world, flights paced 50x, thinking on (P1's setting), greedy (P1's protocol) vs the model's
# default sampling (Gemma-4 generation_config: temperature 1.0, top_p 0.95, top_k 64).
# Usage: env/queue_b_e1.sh <e4b|g26b> <port> <gpu> [smoke]
set -u
WHICH=${1:?e4b|g26b}; PORT=${2:?port}; GPU=${3:?gpu}; SMOKE=${4:-}
A=~/work/aeroeval/orig/system_prompts
COMMON=(--world-prompt $A/world_information/common_world_delivery.txt
        --runtime-prompt $A/modularized_new/navigation/runtime_information.txt
        --pace-speedup 50 --seed 42 --mission-timeout-s 3600 --max-tokens 32768 --gpu $GPU)
case "$WHICH" in
  e4b)  M=(--base-url http://127.0.0.1:$PORT/v1 --model gemma-4-E4B-it); P=e4b ;;
  g26b) M=(--base-url http://127.0.0.1:$PORT/v1 --model gemma-4-26B-A4B-it-fp8); P=g26b ;;
esac
GREEDY=(--temperature 0 --top-p 1 --top-k 1)
SAMPLED=(--temperature 1.0 --top-p 0.95 --top-k 64)
cd ~/jsw-dev
run() {  # name taskfile args...
  local name=$1 tf=$2; shift 2
  [ -f ~/work/runs/$name/manifest.json ] && grep -q t_end_wall ~/work/runs/$name/manifest.json && { echo "skip $name"; return; }
  echo "=== $(date +%T) $name"
  ~/work/venv-aerogen/bin/python -m jsw.workloads.aerogen_driver --out ~/work/runs/$name \
    --task-file $tf "${COMMON[@]}" "${M[@]}" "$@" > ~/work/logs/$name.log 2>&1
  echo "=== $(date +%T) $name done rc=$?"
}
D1=~/work/tasks/p1_d1.txt; D23=~/work/tasks/p1_d23.txt
if [ -n "$SMOKE" ]; then
  run b-e1-${P}-smoke $D1 --effort think "${SAMPLED[@]}" --tasks 0 --runs 1 --concurrency 1 --flush-start
  exit 0
fi
run b-e1-${P}-think-greedy-d1    $D1  --effort think "${GREEDY[@]}"  --runs 2 --concurrency 1 --flush-each
run b-e1-${P}-think-sampled-d1   $D1  --effort think "${SAMPLED[@]}" --runs 3 --concurrency 2 --flush-start
run b-e1-${P}-think-greedy-d23   $D23 --effort think "${GREEDY[@]}"  --runs 1 --concurrency 1 --flush-each
run b-e1-${P}-think-sampled-d23  $D23 --effort think "${SAMPLED[@]}" --runs 2 --concurrency 2 --flush-start
echo "QUEUE B-E1 $WHICH DONE $(date +%T)"

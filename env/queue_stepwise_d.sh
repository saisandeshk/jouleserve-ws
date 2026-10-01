#!/bin/bash
# Step-wise (aerogen-style) agent on P1's delivery tasks in P1's delivery world (2026-10-02).
# Usage: env/queue_stepwise_d.sh qwen   (GPU0, Qwen3.5-9B on :30010)
#        env/queue_stepwise_d.sh k2     (GPU1, K2-Horizon-7B on :30011)
# D1 first for every arm (the agreed test), then D2/D3. Flights are paced 50x faster than
# real time; tool logs record the simulated clock (`sim_t`).
set -u
WHICH=${1:?qwen|k2}
A=~/work/aeroeval/orig/system_prompts
COMMON=(--world-prompt $A/world_information/common_world_delivery.txt
        --runtime-prompt $A/modularized_new/navigation/runtime_information.txt
        --pace-speedup 50 --seed 42 --mission-timeout-s 3600)
cd ~/jsw-dev
run() {  # name taskfile args...
  local name=$1 tf=$2; shift 2
  [ -f ~/work/runs/$name/manifest.json ] && grep -q t_end_wall ~/work/runs/$name/manifest.json && { echo "skip $name"; return; }
  echo "=== $(date +%T) $name"
  ~/work/venv-aerogen/bin/python -m jsw.workloads.aerogen_driver --out ~/work/runs/$name \
    --task-file $tf "${COMMON[@]}" "$@" > ~/work/logs/$name.log 2>&1
  echo "=== $(date +%T) $name done rc=$?"
}
D1=~/work/tasks/p1_d1.txt; D23=~/work/tasks/p1_d23.txt
if [ "$WHICH" = qwen ]; then
  Q=(--base-url http://127.0.0.1:30010/v1 --model Qwen/Qwen3.5-9B --gpu 0 --max-tokens 32768)
  GREEDY=(--temperature 0 --top-p 1 --top-k 1)              # P1's protocol
  T_SAMP=(--temperature 0.6 --top-p 0.95 --top-k 20)         # Qwen model card, thinking
  N_SAMP=(--temperature 0.7 --top-p 0.8 --top-k 20)          # Qwen model card, non-thinking
  run q_think_greedy_d1    $D1  "${Q[@]}" --effort think   "${GREEDY[@]}" --runs 2 --concurrency 1 --flush-each
  run q_nothink_greedy_d1  $D1  "${Q[@]}" --effort nothink "${GREEDY[@]}" --runs 2 --concurrency 1 --flush-each
  run q_think_sampled_d1   $D1  "${Q[@]}" --effort think   "${T_SAMP[@]}" --runs 3 --concurrency 2 --flush-start
  run q_nothink_sampled_d1 $D1  "${Q[@]}" --effort nothink "${N_SAMP[@]}" --runs 3 --concurrency 2 --flush-start
  run q_think_greedy_d23    $D23 "${Q[@]}" --effort think   "${GREEDY[@]}" --runs 1 --concurrency 1 --flush-each
  run q_nothink_greedy_d23  $D23 "${Q[@]}" --effort nothink "${GREEDY[@]}" --runs 1 --concurrency 1 --flush-each
  run q_think_sampled_d23   $D23 "${Q[@]}" --effort think   "${T_SAMP[@]}" --runs 2 --concurrency 2 --flush-start
  run q_nothink_sampled_d23 $D23 "${Q[@]}" --effort nothink "${N_SAMP[@]}" --runs 2 --concurrency 2 --flush-start
else
  K=(--base-url http://127.0.0.1:30011/v1 --model IFM/K2-Horizon-7B --gpu 1 --max-tokens 16384
     --temperature 1.0 --top-p 0.95)                         # K2 model card; as in E1/E2
  run k2_low_d1    $D1  "${K[@]}" --effort low  --runs 3 --concurrency 2 --flush-start
  run k2_high_d1   $D1  "${K[@]}" --effort high --runs 3 --concurrency 2 --flush-start
  run k2_low_d23   $D23 "${K[@]}" --effort low  --runs 2 --concurrency 2 --flush-start
  run k2_high_d23  $D23 "${K[@]}" --effort high --runs 2 --concurrency 2 --flush-start
fi
echo "QUEUE $WHICH DONE $(date +%T)"

#!/usr/bin/env bash
# GPU0 follow-up queue: stop E1-high after one pass over the 5 tasks, then high-effort
# concurrency N=2 and N=4 (reasoning stays in the history, so private state grows fast).
set -u
R=~/work/runs
until [ "$(ls $R/e1_high_n1/sessions/*/summary.json 2>/dev/null | wc -l)" -ge 5 ]; do sleep 15; done
tmux kill-session -t q0 2>/dev/null
sleep 5
cd ~/jsw-dev
PY=~/work/venv-aerogen/bin/python
COMMON="--base-url http://127.0.0.1:30001/v1 --gpu 0 --pace-speedup 1.0 --effort high --max-tokens 16384"
$PY -m jsw.workloads.aerogen_driver $COMMON --out $R/e2_high_n2 --runs 2 --concurrency 2 --stagger-s 30 --flush-start
$PY -m jsw.workloads.aerogen_driver $COMMON --out $R/e2_high_n4 --runs 2 --concurrency 4 --stagger-s 20 --flush-start
echo QUEUE2_GPU0_DONE

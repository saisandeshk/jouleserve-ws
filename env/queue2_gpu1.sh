#!/usr/bin/env bash
# GPU1 follow-up queue (replaces the tail of queue_aerogen_gpu1.sh after the shared-prefix
# finding): wait for the running E1-low driver, then low-effort concurrency N=4, N=8, N=2.
set -u
WAIT_PID=${1:?pid of the running e1_low driver}
while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 15; done
cd ~/jsw-dev
PY=~/work/venv-aerogen/bin/python
R=~/work/runs
COMMON="--base-url http://127.0.0.1:30000/v1 --gpu 1 --pace-speedup 1.0 --effort low"
$PY -m jsw.workloads.aerogen_driver $COMMON --out $R/e2_low_n4 --runs 3 --concurrency 4 --stagger-s 20 --flush-start
$PY -m jsw.workloads.aerogen_driver $COMMON --out $R/e2_low_n8 --runs 3 --concurrency 8 --stagger-s 15 --flush-start
$PY -m jsw.workloads.aerogen_driver $COMMON --out $R/e2_low_n2 --runs 2 --concurrency 2 --stagger-s 30 --flush-start
echo QUEUE2_GPU1_DONE

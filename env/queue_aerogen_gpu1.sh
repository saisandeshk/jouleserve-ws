#!/usr/bin/env bash
# Overnight aerogen queue on GPU1 (K2 tp1, port 30000, KV pool ~25.4K tokens).
#   E1: single session, cold cache per mission, low effort, 5 tasks x 3 seeds
#   E2: closed-loop concurrency N=2 and N=4 on the same pool, low effort
set -u
cd ~/jsw-dev
PY=~/work/venv-aerogen/bin/python
R=~/work/runs
COMMON="--base-url http://127.0.0.1:30000/v1 --gpu 1 --pace-speedup 1.0 --effort low"
$PY -m jsw.workloads.aerogen_driver $COMMON --out $R/e1_low_n1 --runs 3 --concurrency 1 --flush-each --flush-start
$PY -m jsw.workloads.aerogen_driver $COMMON --out $R/e2_low_n2 --runs 2 --concurrency 2 --stagger-s 30 --flush-start
$PY -m jsw.workloads.aerogen_driver $COMMON --out $R/e2_low_n4 --runs 3 --concurrency 4 --stagger-s 20 --flush-start
echo QUEUE_GPU1_DONE

#!/usr/bin/env bash
# Overnight queue on GPU0 (K2 tp1, port 30001): cost calibration, then high-effort E1,
# then high-effort concurrency N=2.
set -u
cd ~/jsw-dev
PY=~/work/venv-aerogen/bin/python
R=~/work/runs
$PY -m jsw.costs.calibrate --base-url http://127.0.0.1:30001/v1 --gpu 0 --out $R/calib_k2_tp1_gpu0.json
COMMON="--base-url http://127.0.0.1:30001/v1 --gpu 0 --pace-speedup 1.0 --effort high --max-tokens 16384"
$PY -m jsw.workloads.aerogen_driver $COMMON --out $R/e1_high_n1 --runs 2 --concurrency 1 --flush-each --flush-start
$PY -m jsw.workloads.aerogen_driver $COMMON --out $R/e2_high_n2 --runs 2 --concurrency 2 --stagger-s 30 --flush-start
echo QUEUE_GPU0_DONE

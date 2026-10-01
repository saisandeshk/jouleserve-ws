#!/usr/bin/env bash
# Rebalanced tail of the overnight queue (2026-10-01 ~03:20).
#   GPU1: wait for E1-low (pid $1), then low-effort N=4 and N=2 on the 25.4K pool.
#   GPU0: wait for queue3 (budget sweep + medium effort) to finish, then low-effort N=8
#         on its default 25.4K pool (same server config as GPU1).
set -u
which=${1:?gpu1|gpu0}
cd ~/jsw-dev
PY=~/work/venv-aerogen/bin/python
R=~/work/runs
if [ "$which" = gpu1 ]; then
  WAIT_PID=${2:?pid}
  while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 15; done
  C="--base-url http://127.0.0.1:30000/v1 --gpu 1 --pace-speedup 1.0 --effort low"
  $PY -m jsw.workloads.aerogen_driver $C --out $R/e2_low_n4 --runs 3 --concurrency 4 --stagger-s 20 --flush-start
  $PY -m jsw.workloads.aerogen_driver $C --out $R/e2_low_n2 --runs 2 --concurrency 2 --stagger-s 30 --flush-start
else
  while tmux has-session -t q0c 2>/dev/null; do sleep 30; done
  C="--base-url http://127.0.0.1:30001/v1 --gpu 0 --pace-speedup 1.0 --effort low"
  $PY -m jsw.workloads.aerogen_driver $C --out $R/e2_low_n8 --runs 3 --concurrency 8 --stagger-s 15 --flush-start
fi
echo QUEUE4_${which}_DONE

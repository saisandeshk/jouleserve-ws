#!/usr/bin/env bash
# GPU0 queue v3. High effort outgrows the one-GPU KV pool (prompt+output hits 25.4K within
# ~7 turns), so high-effort concurrency on tp1 is replaced by a low-effort KV-budget sweep:
# N=4 at --max-total-tokens 16384 and 13312, then medium effort single-session.
set -u
R=~/work/runs
until [ "$(ls $R/e1_high_n1/sessions/*/summary.json 2>/dev/null | wc -l)" -ge 5 ]; do sleep 15; done
tmux kill-session -t q0 2>/dev/null
sleep 5
cd ~/jsw-dev
PY=~/work/venv-aerogen/bin/python

restart() {  # restart the GPU0 server with extra flags; wait until it serves
  tmux kill-session -t k2g0 2>/dev/null
  while nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 0 | awk '{exit !($1>1000)}'; do sleep 3; done
  tmux new-session -d -s k2g0 "~/jsw-dev/env/launch_k2_tp1.sh 0 30001 $* 2>&1 | tee -a ~/work/logs/k2_gpu0_30001.log"
  until curl -sf http://127.0.0.1:30001/v1/models >/dev/null; do sleep 5; done
  curl -s http://127.0.0.1:30001/get_server_info | $PY -c "import json,sys; d=json.load(sys.stdin); print('max_total_num_tokens', d.get('max_total_num_tokens'), d.get('max_total_tokens'))"
}

COMMON="--base-url http://127.0.0.1:30001/v1 --gpu 0 --pace-speedup 1.0 --effort low"
restart --max-total-tokens 16384
$PY -m jsw.workloads.aerogen_driver $COMMON --out $R/e2_low_n4_kv16k --runs 3 --concurrency 4 --stagger-s 20 --flush-start
restart --max-total-tokens 13312
$PY -m jsw.workloads.aerogen_driver $COMMON --out $R/e2_low_n4_kv13k --runs 3 --concurrency 4 --stagger-s 20 --flush-start
restart
$PY -m jsw.workloads.aerogen_driver --base-url http://127.0.0.1:30001/v1 --gpu 0 --pace-speedup 1.0 --effort medium --out $R/e1_medium_n1 --runs 1 --concurrency 1 --flush-each --flush-start
echo QUEUE3_GPU0_DONE

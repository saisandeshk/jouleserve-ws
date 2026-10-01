#!/usr/bin/env bash
# Launch IFM/K2-Horizon-7B (bf16, tp1) on one A5000 with SGLang 0.5.20 from the legacy venv.
# Usage: env/launch_k2_tp1.sh <gpu 0|1> <port> [extra sglang flags...]
# GPU0 <-> cores 0-9,20-29; GPU1 <-> cores 10-19,30-39 (NUMA). KV pool at 0.88 ~= 25,427 tokens.
set -euo pipefail
GPU=${1:?gpu}; PORT=${2:?port}; shift 2
L=~/legacy/jouleserve-ws
export LD_LIBRARY_PATH=$L/.venv/lib/python3.11/site-packages/nvidia/cu13/lib:${LD_LIBRARY_PATH:-}
# Pinned: the revision every run since 2026-10-01 used (HF re-uploaded K2 as 85d46bb on 2026-10-02).
export HF_HUB_OFFLINE=1
K2_REV=${K2_REV:-f846b1e64076a5eff23f7e3539d2740cc76de8b4}
if [ "$GPU" = 0 ]; then CORES=0-9,20-29; else CORES=10-19,30-39; fi
exec env CUDA_VISIBLE_DEVICES=$GPU taskset -c $CORES $L/.venv/bin/python -m sglang.launch_server \
  --model-path IFM/K2-Horizon-7B --revision "$K2_REV" --tp-size 1 --context-length 65536 \
  --mem-fraction-static 0.88 --cuda-graph-max-bs-decode 16 --disable-prefill-cuda-graph \
  --reasoning-parser k2_horizon --tool-call-parser k2_horizon \
  --enable-metrics --enable-cache-report --host 127.0.0.1 --port "$PORT" "$@"

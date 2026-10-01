#!/bin/bash
# Qwen3.5-9B (hybrid: 8 full-attention + 24 linear-attention layers), bf16, tp1, SGLang 0.5.20.
# Usage: env/launch_qwen35_tp1.sh <gpu> <port> [extra sglang args]
GPU=${1:?gpu}; PORT=${2:?port}; shift 2
L=~/legacy/jouleserve-ws
export LD_LIBRARY_PATH=$L/.venv/lib/python3.11/site-packages/nvidia/cu13/lib:${LD_LIBRARY_PATH:-}
export HF_HUB_OFFLINE=1
if [ "$GPU" = 0 ]; then CORES=0-9,20-29; else CORES=10-19,30-39; fi
M=$L/cache/hf/models--Qwen--Qwen3.5-9B/snapshots/c202236235762e1c871ad0ccb60c8ee5ba337b9a
exec env CUDA_VISIBLE_DEVICES=$GPU taskset -c $CORES $L/.venv/bin/python -m sglang.launch_server \
  --model-path "$M" --served-model-name Qwen/Qwen3.5-9B --tp-size 1 --context-length 65536 \
  --mem-fraction-static 0.85 --dtype bfloat16 --trust-remote-code --attention-backend flashinfer \
  --reasoning-parser qwen3 --tool-call-parser qwen3_coder \
  --enable-metrics --enable-cache-report --host 127.0.0.1 --port "$PORT" "$@"

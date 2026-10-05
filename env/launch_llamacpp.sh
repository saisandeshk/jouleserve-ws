#!/bin/bash
# gemma-4-26B-A4B (P1's model) on one A5000 through llama.cpp (2026-10-06): SGLang 0.5.20 cannot run any quantized
# 26B on Ampere (D13). unsloth's UD-Q4_K_XL GGUF (17.0 GB), OpenAI-compatible server, thinking via the model's
# jinja template (chat_template_kwargs.enable_thinking), reasoning returned as reasoning_content.
# Usage: env/launch_llamacpp.sh <gpu> <port> [parallel] [ctx per slot]
set -euo pipefail
GPU=${1:?gpu}; PORT=${2:?port}; PAR=${3:-2}; CTX=${4:-40960}
M=$(ls ~/.cache/huggingface/hub/models--unsloth--gemma-4-26B-A4B-it-GGUF/snapshots/*/gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf | head -1)
if [ "$GPU" = 0 ]; then CORES=0-9,20-29; else CORES=10-19,30-39; fi
exec env CUDA_VISIBLE_DEVICES=$GPU taskset -c $CORES ~/work/llama.cpp/build/bin/llama-server -m "$M" \
  --alias gemma-4-26B-A4B-it-gguf -ngl 99 -c $((PAR * CTX)) --parallel $PAR --jinja --reasoning-format deepseek \
  -fa on --host 127.0.0.1 --port "$PORT" --metrics --no-webui

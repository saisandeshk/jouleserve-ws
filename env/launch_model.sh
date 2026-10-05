#!/usr/bin/env bash
# Launch a WS stand-in for one of P1's models on one A5000, SGLang 0.5.20 from the legacy venv (OPTIONS_PLAN.md S1).
# Usage: env/launch_model.sh <gemma26b-awq|gemma-e4b|granite8b> <gpu 0|1> <port> [extra sglang flags...]
# Weights come from env/fetch_models.py (pinned revisions); served offline so nothing is re-fetched.
# GPU0 <-> cores 0-9,20-29; GPU1 <-> cores 10-19,30-39 (NUMA).
# MEM (mem fraction) and CTX (context length) can be overridden from the environment.
set -euo pipefail
NAME=${1:?model}; GPU=${2:?gpu}; PORT=${3:?port}; shift 3
L=~/legacy/jouleserve-ws
H=~/.cache/huggingface/hub
export LD_LIBRARY_PATH=$L/.venv/lib/python3.11/site-packages/nvidia/cu13/lib:${LD_LIBRARY_PATH:-}
export HF_HUB_OFFLINE=1
# TP>1: the venv's NCCL 2.29.7 is a CUDA-13 build that the WS driver (CUDA 12.6) cannot run; preload a CUDA-12 build
# installed with: uv pip install --python $L/.venv/bin/python --target ~/work/nccl-cu12 nvidia-nccl-cu12==2.32.3
if [ "${TP:-1}" -gt 1 ]; then
  export LD_PRELOAD=~/work/nccl-cu12/nvidia/nccl/lib/libnccl.so.2 SGLANG_NCCL_SO_PATH=~/work/nccl-cu12/nvidia/nccl/lib/libnccl.so.2
fi
case "$NAME" in
  gemma26b-awq)  # stand-in for P1's google/gemma-4-26B-A4B-it (bf16 on Thor/Orin 64); 4-bit weights (D13).
    # Fails as published: its 4-bit vision tower has a 4,304-wide MLP that SGLang's Marlin repack rejects.
    M=$H/models--cyankiwi--gemma-4-26B-A4B-it-AWQ-4bit/snapshots/180b2d35e35e4e48f6245367f3b41036f7cdabd6
    SERVED=gemma-4-26B-A4B-it-awq; PARSE="--reasoning-parser gemma4 --tool-call-parser gemma4" ;;
  gemma26b-awq-text)  # the same weights, text only: ~/work/models/gemma26b-awq-text holds symlinks to the snapshot
    # and a config.json made of its text_config with architectures=Gemma4ForCausalLM (the vision tower is not loaded)
    M=~/work/models/gemma26b-awq-text
    SERVED=gemma-4-26B-A4B-it-awq; PARSE="--reasoning-parser gemma4 --tool-call-parser gemma4" ;;
  gemma-e4b)     # P1's exact weights (Orin 32 drone and traffic)
    M=$H/models--google--gemma-4-E4B-it/snapshots/ee0ef6023621cff504d758262d4e04895a5af4a2
    SERVED=gemma-4-E4B-it; PARSE="--reasoning-parser gemma4 --tool-call-parser gemma4" ;;
  gemma26b-fp8-text)  # FP8-dynamic weights (RedHatAI, ed35d7a), text only, like gemma26b-awq-text; needs TP=2 on A5000s
    M=~/work/models/gemma26b-fp8-text
    SERVED=gemma-4-26B-A4B-it-fp8; PARSE="--reasoning-parser gemma4 --tool-call-parser gemma4" ;;
  granite8b)     # P1's exact weights (traffic on Thor, Orin 64, Orin 32)
    M=$H/models--ibm-granite--granite-4.2-8b/snapshots/f8de16cdcdbc6c779ca517604e050d82cc119e44
    SERVED=granite-4.2-8b; PARSE="" ;;
  *) echo "unknown model $NAME" >&2; exit 2 ;;
esac
# TP>1: the venv's NCCL 2.29.7 is a CUDA-13 build that fails on driver 560 ("CUDA driver version is insufficient");
# preload a CUDA-12 NCCL (pip nvidia-nccl-cu12 2.32.3 in ~/work/nccl-cu12, 2026-10-06). The GPUs share no NVLink and
# sit on different sockets, so SGLang's custom all-reduce (P2P) is off too.
TPX=()
if [ "${TP:-1}" -gt 1 ]; then
  export LD_PRELOAD=~/work/nccl-cu12/nvidia/nccl/lib/libnccl.so.2 SGLANG_NCCL_SO_PATH=~/work/nccl-cu12/nvidia/nccl/lib/libnccl.so.2
  TPX=(--disable-custom-all-reduce)
fi
if [ "$GPU" = 0 ]; then CORES=0-9,20-29; elif [ "$GPU" = 1 ]; then CORES=10-19,30-39; else CORES=0-39; fi  # GPU=0,1 for TP=2
exec env CUDA_VISIBLE_DEVICES=$GPU taskset -c $CORES $L/.venv/bin/python -m sglang.launch_server \
  --model-path "$M" --served-model-name "$SERVED" --tp-size "${TP:-1}" --context-length "${CTX:-65536}" \
  --mem-fraction-static "${MEM:-0.88}" --cuda-graph-max-bs-decode 16 --disable-prefill-cuda-graph \
  $PARSE "${TPX[@]}" --enable-metrics --enable-cache-report --host 127.0.0.1 --port "$PORT" "$@"

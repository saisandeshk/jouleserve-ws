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
  granite8b)     # P1's exact weights (traffic on Thor, Orin 64, Orin 32)
    M=$H/models--ibm-granite--granite-4.2-8b/snapshots/f8de16cdcdbc6c779ca517604e050d82cc119e44
    SERVED=granite-4.2-8b; PARSE="" ;;
  *) echo "unknown model $NAME" >&2; exit 2 ;;
esac
if [ "$GPU" = 0 ]; then CORES=0-9,20-29; else CORES=10-19,30-39; fi
exec env CUDA_VISIBLE_DEVICES=$GPU taskset -c $CORES $L/.venv/bin/python -m sglang.launch_server \
  --model-path "$M" --served-model-name "$SERVED" --tp-size 1 --context-length "${CTX:-65536}" \
  --mem-fraction-static "${MEM:-0.88}" --cuda-graph-max-bs-decode 16 --disable-prefill-cuda-graph \
  $PARSE --enable-metrics --enable-cache-report --host 127.0.0.1 --port "$PORT" "$@"

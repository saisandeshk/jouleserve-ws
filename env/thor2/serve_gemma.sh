#!/bin/bash
# P5 on Thor-2 (dream-thor-2, mayankarya@10.24.24.80): P1's gemma-26B traffic server settings
# (P1's deploy/campaigns/serve_model.sh, key gemma4) in a P5 container. Root filesystem read-only; caches and log in
# /media/hdd/p5; the model mounted read-only from P1's hf_cache.
# HF_HUB_CACHE points at the mounted cache: HOME and XDG_CACHE_HOME are moved to /p5cache, which would otherwise
# move the hub cache too. Needs P1's idle sweep-llm stopped first (it holds ~98 GB):  docker stop sweep-llm   (restore: docker start sweep-llm;
# its full configuration is saved in /media/hdd/p5/state/2026-10-15/).
set -eu
P=/media/hdd/p5; B=/media/ssd/Deepstream-Yolo-upstream/camera_query_agent
mkdir -p $P/cache $P/logs $P/state/2026-10-15
docker run -d --rm --read-only --tmpfs /tmp --log-driver none --name p5-traffic-gemma --runtime nvidia --shm-size 2g \
  -p 30101:30000 -v $B/hf_cache:/root/.cache/huggingface/hub:ro -v $P/cache:/p5cache -v $P/logs:/p5logs \
  -e HF_HUB_OFFLINE=1 -e HF_HUB_CACHE=/root/.cache/huggingface/hub -e HOME=/p5cache -e XDG_CACHE_HOME=/p5cache/xdg -e TRITON_CACHE_DIR=/p5cache/triton \
  -e TORCHINDUCTOR_CACHE_DIR=/p5cache/inductor -e FLASHINFER_WORKSPACE_BASE=/p5cache \
  lmsysorg/sglang:latest-cu130-runtime sh -c "python3 -m sglang.launch_server --model-path google/gemma-4-26B-A4B-it \
  --served-model-name gemma4-it --mem-fraction-static 0.80 --context-length 110000 --attention-backend triton \
  --tool-call-parser gemma4 --reasoning-parser gemma4 --default-chat-template-kwargs '{\"enable_thinking\":true}' \
  --host 0.0.0.0 --port 30000 --enable-metrics --disable-cuda-graph --enable-cache-report --random-seed 42 \
  > /p5logs/p5-traffic-gemma.log 2>&1"
echo "launched p5-traffic-gemma $(date -Iseconds)" >> $P/state/2026-10-15/actions.log
for i in $(seq 1 120); do
  sleep 5
  curl -sf -m 3 http://127.0.0.1:30101/v1/models >/dev/null && { echo "ready after $((i * 5)) s"; exit 0; }
  docker ps --format "{{.Names}}" | grep -qx p5-traffic-gemma || { echo "container exited"; tail -20 $P/logs/p5-traffic-gemma.log; exit 1; }
done
echo "not ready after 10 min"; tail -20 $P/logs/p5-traffic-gemma.log; exit 1

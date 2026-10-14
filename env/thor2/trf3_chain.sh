#!/bin/bash
# TRF-3 on Thor-2: stop P1's idle sweep-llm server (its configuration is saved in /media/hdd/p5/state/2026-10-15),
# start the P5 gemma-26B server with P1's traffic settings, then run P1's agent on 9 instance-A tasks.
# Run inside tmux:  tmux new-session -d -s p5-trf3 "bash /media/hdd/p5/bin/trf3_chain.sh"
P=/media/hdd/p5; L=$P/logs/trf3_chain.log
say() { echo "[$(date -Iseconds)] $*" >> $L; }
say "chain start"
if docker ps --format "{{.Names}}" | grep -qx sweep-llm; then
  docker stop sweep-llm >/dev/null && say "sweep-llm stopped (restore: docker start sweep-llm)" &&
    echo "sweep-llm stopped $(date -Iseconds)" >> $P/state/2026-10-15/actions.log
fi
bash $P/bin/serve_gemma.sh >> $L 2>&1 || { say "SERVE FAILED"; exit 1; }
curl -s http://127.0.0.1:30101/get_server_info > $P/logs/p5-traffic-gemma.server_info.json
say "server up; validation start"
bash $P/bin/traffic_run.sh trf3-gemma-A \
  peak-count,class-mix,busiest-hour,compare-periods,heavy-vehicle,avg-per-minute,peak-start-end,day-summary,first-last-sighting \
  A 1 >> $L 2>&1
say "CHAIN DONE"

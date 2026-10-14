#!/bin/bash
# CAND-T1 (amended 15 Oct, before data) and CAND-T2 on Thor-2 (reports/2026-10-15-candidates/PLAN.md):
#  1. after TRF-3: gemma-26B, S1 (k = 1) then F4 (k = 4), one repeat each, 12 instance-A tasks;
#  2. swap to granite-4.2-8b (P1's flags), its cost curve (k = 1-16, 4K and 16K contexts);
#  3. granite: S1 then F4, one repeat each, 10 instance-A tasks.
# Run inside tmux:  tmux new-session -d -s p5-cand "bash /media/hdd/p5/bin/cand_chain2.sh"
P=/media/hdd/p5; L=$P/logs/cand_chain.log
say() { echo "[$(date -Iseconds)] $*" >> $L; }
GEMMA_TASKS=peak-count,class-mix,busiest-hour,avg-per-minute,special-vehicle,heavy-vehicle,viz-class-vs-dwell,peak-start-end,viz-stacked-area,day-summary,first-last-sighting,unusual-vs-median
GRANITE_TASKS=busiest-hour,avg-per-minute,stalled-vehicle,peak-count,class-mix,viz-class-vs-dwell,unusual-vs-median,peak-start-end,compare-periods,day-summary
say "cand chain 2 start; waiting for TRF-3"
until grep -q "CHAIN DONE" $P/logs/trf3_chain.log 2>/dev/null; do sleep 60; done
curl -sf -m 5 http://127.0.0.1:30101/v1/models >/dev/null || { say "gemma server not up; stopping"; exit 1; }
for spec in "s1 1" "f4 4"; do
  set -- $spec
  say "gemma arm $1 (k=$2) start"
  MODEL=gemma GW_K=$2 bash $P/bin/traffic_run.sh "cand-gemma-$1-r1" "$GEMMA_TASKS" A 1 >> $L 2>&1
  say "gemma arm $1 done"
done
say "swap to granite"
docker stop p5-traffic-gemma >/dev/null 2>&1; sleep 10
bash $P/bin/serve_granite.sh >> $L 2>&1 || { say "GRANITE SERVE FAILED"; exit 1; }
curl -s http://127.0.0.1:30101/get_server_info > $P/logs/p5-traffic-granite.server_info.json
say "granite cost curve start"
python3 $P/bin/costcurve.py --server http://127.0.0.1:30101 --model granite \
  --out $P/runs/costcurve-granite-$(date +%Y%m%dT%H%M) >> $L 2>&1
say "granite cost curve done"
for spec in "s1 1" "f4 4"; do
  set -- $spec
  say "granite arm $1 (k=$2) start"
  MODEL=granite GW_K=$2 bash $P/bin/traffic_run.sh "cand-granite-$1-r1" "$GRANITE_TASKS" A 1 >> $L 2>&1
  say "granite arm $1 done"
done
say "CAND CHAIN DONE"

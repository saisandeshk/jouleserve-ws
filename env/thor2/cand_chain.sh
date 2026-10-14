#!/bin/bash
# CAND-T1 on Thor-2 (reports/2026-10-15-candidates/PLAN.md): after TRF-3 ends, S1 (k = 1) and F4 (k = 4) on 12
# instance-A tasks, 2 repeats, interleaved S1 r1, F4 r1, S1 r2, F4 r2. Run inside tmux:
#   tmux new-session -d -s p5-cand "bash /media/hdd/p5/bin/cand_chain.sh"
P=/media/hdd/p5; L=$P/logs/cand_chain.log
say() { echo "[$(date -Iseconds)] $*" >> $L; }
TASKS=peak-count,class-mix,busiest-hour,avg-per-minute,special-vehicle,heavy-vehicle,viz-class-vs-dwell,peak-start-end,viz-stacked-area,day-summary,first-last-sighting,unusual-vs-median
say "cand chain start; waiting for TRF-3"
until grep -q "CHAIN DONE" $P/logs/trf3_chain.log 2>/dev/null; do sleep 60; done
curl -sf -m 5 http://127.0.0.1:30101/v1/models >/dev/null || { say "server not up; stopping"; exit 1; }
for spec in "s1 1 1" "f4 4 1" "s1 1 2" "f4 4 2"; do
  set -- $spec
  say "arm $1 (k=$2) repeat $3 start"
  GW_K=$2 bash $P/bin/traffic_run.sh "cand-$1-r$3" "$TASKS" A "$3" >> $L 2>&1
  say "arm $1 repeat $3 done"
done
say "CAND CHAIN DONE"

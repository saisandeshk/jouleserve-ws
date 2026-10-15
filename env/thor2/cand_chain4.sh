#!/bin/bash
# Resume after Thor-2's unclean reboot (15 Oct 01:24, mid TRF-3; the USB disk had to be remounted):
#  0. close the cut TRF-3 run (rc=cut, SHA256SUMS), and log free memory every 30 s to logs/mem.log (cause unknown);
#  1. CAND-T2: granite-4.2-8b (P1's flags), its cost curve, then S1 (k = 1) and F4 (k = 4), 10 tasks;
#  2. CAND-T1: gemma-26B (P1's flags), S1 and F4, 12 tasks;
#  3. TRF-3's tasks the crash cut off, on the same gemma server.
# Arms, tasks and rules as in cand_chain3.sh and reports/2026-10-15-candidates/PLAN.md.
# Run inside tmux:  tmux new-session -d -s p5-cand "bash /media/hdd/p5/bin/cand_chain4.sh"
P=/media/hdd/p5; L=$P/logs/cand_chain.log
[ -d $P/bin ] || { echo "$P missing: is the USB disk mounted on /media/hdd?" >&2; exit 1; }
say() { echo "[$(date -Iseconds)] $*" >> $L; }
GEMMA_TASKS=peak-count,class-mix,busiest-hour,avg-per-minute,special-vehicle,heavy-vehicle,viz-class-vs-dwell,peak-start-end,viz-stacked-area,day-summary,first-last-sighting,unusual-vs-median
GRANITE_TASKS=busiest-hour,avg-per-minute,stalled-vehicle,peak-count,class-mix,viz-class-vs-dwell,unusual-vs-median,peak-start-end,compare-periods,day-summary
TRF3_TASKS=peak-count,class-mix,busiest-hour,compare-periods,heavy-vehicle,avg-per-minute,peak-start-end,day-summary,first-last-sighting
say "--- Thor-2 rebooted uncleanly at 01:24 (chain 3 and TRF-3 cut); chain 4 (resume) start, MemAvailable $(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo) MB"
(while true; do echo "$(date -Iseconds) $(awk '/MemAvailable|SwapFree/{printf "%s %d MB  ", $1, $2/1024}' /proc/meminfo)"; sleep 30; done) >> $P/logs/mem.log 2>&1 &
MP=$!
T3=$(ls -d $P/runs/trf3-gemma-A-2026* | head -1)
if [ -n "$T3" ] && ! grep -q "rc=" "$T3/p5_run.txt"; then
  echo "rc=cut ended=2026-10-15T01:24 (Thor-2 unclean reboot; closed by cand_chain4.sh $(date -Iseconds))" >> "$T3/p5_run.txt"
  (cd "$T3" && sha256sum $(ls | grep -v SHA256SUMS) > SHA256SUMS 2>/dev/null)
fi
REST3=$(python3 - "$T3/runs.jsonl" "$TRF3_TASKS" <<'EOF'
import json, sys
done = set()
for l in open(sys.argv[1]):
    try:
        done.add(json.loads(l)["task_id"])
    except (ValueError, KeyError):
        pass                                   # a line cut by the crash
print(",".join(t for t in sys.argv[2].split(",") if t not in done))
EOF
)
say "TRF-3 left for the end of this chain: ${REST3:-none}"
say "swap to granite"
docker stop p5-traffic-gemma >/dev/null 2>&1; sleep 5
bash $P/bin/serve_granite.sh >> $L 2>&1 || { say "GRANITE SERVE FAILED"; kill $MP; exit 1; }
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
say "swap to gemma"
docker stop p5-traffic-granite >/dev/null 2>&1; sleep 10
bash $P/bin/serve_gemma.sh >> $L 2>&1 || { say "GEMMA SERVE FAILED"; kill $MP; exit 1; }
curl -s http://127.0.0.1:30101/get_server_info > $P/logs/p5-traffic-gemma.server_info.json
for spec in "s1 1" "f4 4"; do
  set -- $spec
  say "gemma arm $1 (k=$2) start"
  MODEL=gemma GW_K=$2 bash $P/bin/traffic_run.sh "cand-gemma-$1-r1" "$GEMMA_TASKS" A 1 >> $L 2>&1
  say "gemma arm $1 done"
done
if [ -n "$REST3" ]; then
  say "TRF-3 rest ($REST3) start"
  bash $P/bin/traffic_run.sh trf3-gemma-A-rest "$REST3" A 1 >> $L 2>&1
  say "TRF-3 rest done"
fi
kill $MP 2>/dev/null
say "CAND CHAIN DONE"

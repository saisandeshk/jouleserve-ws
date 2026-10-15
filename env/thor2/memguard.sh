#!/bin/bash
# Memory guard for P5's runs on Thor-2. If MemAvailable stays under 4 GB for 3 checks (30 s), stop P5's own server
# (p5-traffic-*), so that the board never again runs out of memory (the crash of 15 Oct 01:24). The run in progress
# then fails, which its log shows. Logs to logs/memguard.log.
# Run inside tmux:  tmux new-session -d -s p5-memguard "bash /media/hdd/p5/bin/memguard.sh"
L=/media/hdd/p5/logs/memguard.log; low=0
echo "[$(date -Iseconds)] memguard start (threshold 4096 MB, 3 checks 10 s apart)" >> $L
while true; do
  m=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
  if [ "$m" -lt 4096 ]; then low=$((low + 1)); echo "[$(date -Iseconds)] low memory: $m MB ($low)" >> $L; else low=0; fi
  if [ "$low" -ge 3 ]; then
    for c in $(docker ps --format '{{.Names}}' | grep '^p5-traffic-'); do
      docker stop "$c" >/dev/null && echo "[$(date -Iseconds)] MEMORY GUARD stopped $c at $m MB" >> $L
    done
    low=0
  fi
  sleep 10
done

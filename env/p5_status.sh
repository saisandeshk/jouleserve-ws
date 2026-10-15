#!/bin/sh
# One look at everything P5 has running, e.g. after a laptop restart (run from the repo root):
# Thor-2's chains and runs, the WS (tmux, GPUs, the follower's STATUS.txt), the five units' containers (look only;
# the mentor's p5_osdi runs are hers), then one relay of Thor-2's finished runs to the WS (env/p5_relay_thor2.sh).
#   env/p5_status.sh            status + relay
#   NORELAY=1 env/p5_status.sh  status only
O="-o BatchMode=yes -o ConnectTimeout=8"
echo "== Thor-2 (P5's traffic runs) =="
ssh $O mayankarya@10.24.24.80 '[ -d /media/hdd/p5 ] || echo "!! /media/hdd/p5 missing: the USB disk is not mounted (Thor-2 rebooted?); see HANDOFF"; uptime -s | sed "s/^/booted /";
  tmux ls 2>&1 | grep p5- ; docker ps --format "{{.Names}}  {{.Status}}" | grep p5-;
  for f in trf3_chain.log cand_chain.log; do echo "-- $f"; tail -3 /media/hdd/p5/logs/$f 2>/dev/null; done
  echo "-- runs (tasks done, finished?)"; cd /media/hdd/p5/runs && for d in */; do d=${d%/};
  n=$(cat $d/runs.jsonl 2>/dev/null | wc -l); f=$(grep -o "rc=[0-9]*" $d/p5_run.txt 2>/dev/null || { [ -f $d/costcurve.jsonl ] && echo done; } || echo running);
  echo "  $d  tasks=$n  $f"; done' || echo "Thor-2 unreachable"
echo; echo "== WS =="
ssh $O saisandeshk@10.24.32.174 'tmux ls 2>&1; nvidia-smi --query-gpu=index,memory.used --format=csv,noheader;
  cat ~/work/runs/thor2/STATUS.txt 2>/dev/null || echo "(no follower status yet)"' || echo "WS unreachable"
echo; echo "== Units (containers; look only) =="
for u in Thor-1 Orin-64-1 Orin-32-1 Orin-32-2 Orin-32-3; do
  printf "%-10s " $u; ssh $O $u 'echo "$(docker ps --format "{{.Names}}" | tr "\n" " ")| $(uptime -p)"' 2>/dev/null || echo unreachable
done
[ -n "${NORELAY:-}" ] || { echo; echo "== Relay Thor-2 -> WS =="; sh "$(dirname "$0")/p5_relay_thor2.sh"; }

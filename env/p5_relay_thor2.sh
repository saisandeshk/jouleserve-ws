#!/bin/sh
# Copy Thor-2's finished P5 runs (and P5's logs there) to the WS, ~/work/runs/thor2/ and ~/work/runs/thor2_logs/.
# A run is finished when its p5_run.txt has "rc=" and SHA256SUMS exists (traffic_run.sh), or costcurve.jsonl exists
# (costcurve.py). Each finished run is copied once, through a staging folder, so a cut copy is never taken as complete.
#   env/p5_relay_thor2.sh            from the laptop: Thor-2 -> laptop -> WS (the WS's key is not on Thor-2)
#   ON_WS=1 sh env/p5_relay_thor2.sh  on the WS itself, if it can reach Thor-2 (ws_follow.py tries this first)
T=mayankarya@10.24.24.80; WS=saisandeshk@10.24.32.174; O="-o BatchMode=yes -o ConnectTimeout=10"
dst() { if [ -n "${ON_WS:-}" ]; then sh -c "$1"; else ssh $O $WS "$1"; fi; }
DONE=$(ssh $O $T 'cd /media/hdd/p5/runs 2>/dev/null && for d in */; do d=${d%/};
  { grep -q "rc=" "$d/p5_run.txt" 2>/dev/null && [ -f "$d/SHA256SUMS" ]; } || [ -f "$d/costcurve.jsonl" ] && echo "$d"; done; true') \
  || { echo "relay: Thor-2 unreachable"; exit 1; }
HAVE=$(dst 'mkdir -p ~/work/runs/thor2/.incoming && ls ~/work/runs/thor2') || { echo "relay: WS unreachable"; exit 1; }
n=0
for d in $DONE; do
  echo "$HAVE" | grep -qx "$d" && continue
  ssh $O $T "tar -C /media/hdd/p5/runs -cf - '$d'" | dst "rm -rf ~/work/runs/thor2/.incoming/'$d' && tar -C ~/work/runs/thor2/.incoming -xf - && mv ~/work/runs/thor2/.incoming/'$d' ~/work/runs/thor2/" \
    && { n=$((n + 1)); echo "relay: copied $d"; }
done
ssh $O $T 'tar -C /media/hdd/p5 -cf - logs' | dst 'mkdir -p ~/work/runs/thor2_logs && tar -C ~/work/runs/thor2_logs -xf -'
echo "relay: $n new run(s); $(echo "$DONE" | grep -c .) finished on Thor-2"

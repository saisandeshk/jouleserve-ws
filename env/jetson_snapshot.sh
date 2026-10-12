#!/usr/bin/env bash
# DEV-1 (planning/OPTIONS_PLAN.md §4.1): look-only snapshot of a Jetson before P5 stops anything, so P1's stack can be
# restarted exactly. It reads only: it never stops, deletes or changes anything on the unit.
#
#   ssh <unit> 'bash -s' -- <p5-dir> <tag> [tegrastats-seconds] < env/jetson_snapshot.sh
#
# Writes <p5-dir>/state/<tag>/ with SHA256SUMS. `docker inspect` holds the containers' environment: keep the snapshot
# on the unit and the WS, never in git.
set -u
P5=${1:?p5 dir}; TAG=${2:?tag}; SECS=${3:-60}
D=$P5/state/$TAG
mkdir -p "$D" && cd "$D" || exit 1

{ date -Is; hostname; whoami; uptime; } > taken_at.txt
uname -a > uname.txt
cat /etc/nv_tegra_release > l4t.txt 2>&1
docker ps -a > docker_ps_a.txt 2>&1
docker ps -a --no-trunc --format '{{json .}}' > docker_ps_a.jsonl 2>&1
docker inspect $(docker ps -aq) > docker_inspect_all.json 2>&1      # stopped containers too (Thor-1's gemma ones)
docker images --digests --no-trunc > docker_images.txt 2>&1
ps -eo pid,ppid,user,lstart,etime,pcpu,rss,args --sort=pid > ps_full.txt
for pid in $(ps -eo pid,args | grep -E '[c]lgsce_mcp|[t]hor_headless|[s]glang|[o]llama|[e]nsure_infra|[a]irsim' |
             awk '{print $1}'); do
  {
    echo "== pid $pid ppid $(ps -o ppid= -p "$pid") user $(ps -o user= -p "$pid")"
    echo "cmdline: $(tr '\0' ' ' < /proc/$pid/cmdline)"
    echo "cwd: $(readlink /proc/$pid/cwd)"
  } >> p1_procs.txt 2>&1
done
ss -ltnp > listening.txt 2>&1
df -h > df.txt 2>&1
free -m > free.txt
nvpmodel -q > nvpmodel.txt 2>&1
for d in /sys/class/devfreq/*; do
  echo "$(basename "$d") $(cat "$d"/min_freq "$d"/max_freq "$d"/cur_freq 2>/dev/null | tr '\n' ' ')"
done > devfreq.txt
tmux ls > tmux_ls.txt 2>&1
crontab -l > crontab.txt 2>&1
systemctl list-units --type=service --state=running --no-pager > services_running.txt 2>&1
timeout "$SECS" tegrastats --interval 200 > tegrastats_${SECS}s.log 2>&1
sha256sum -- * > SHA256SUMS
echo "snapshot $D: $(ls | wc -l) files"

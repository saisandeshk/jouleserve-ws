"""Preflight and teardown checks for a device run (DEV-5, planning/OPTIONS_PLAN.md §4.1). Run on the WS; stdlib only.

    python env/jetson_preflight.py <unit> [--server http://<ip>:30000 --model granite --pool 25358 --flush --warmup]
        [--idle 300 --out <run_dir>/preflight_before] [--wait-cool 900] [--json <file>]

Checks (a failed check exits 1 and stops the run):
1. quiet: no container but ours (p5-*), no foreign process above 5% CPU (our containers' processes, our sampler,
   this probe and kernel threads excluded); on Thor also no GPU process outside our containers (nvidia-smi);
2. clocks: GPU devfreq min = max = cur = the locked frequency found on 12 Oct (configs/jetsons.json); nvpmodel MAXN;
3. disk: >= 5 GB free in <p5>, docker root free >= its DEV-2 value - 10 MB (Thor-1: - 5 GB, since its docker root
   shares `/` with <p5>, whose caches and logs grow);
4. time: NTP synchronised; the unit-WS clock offset recorded;
5. temperature: GPU below 50 C (--wait-cool S waits up to S seconds for it);
6. server (with --server): model and pool as specified; with --warmup one discarded short request; with --flush P1's
   verified flush (wait for idle, /flush_cache, num_used_tokens and swa_used_tokens 0, and still 0 a second later);
7. idle baseline (with --idle S): S seconds of board power on the unit, saved under --out, mean reported.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jsw.telemetry.jetson import board_energy, clock_offset, interval_ms, load, ssh  # noqa: E402

UNITS = json.loads((Path(__file__).resolve().parents[1] / "configs/jetsons.json").read_text())

PROBE = r'''
import json, os, subprocess, shutil, glob
def sh(c):
    return subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()
out = {"containers": sh("docker ps --format '{{.Names}}'").split()}
ours = set()
for c in out["containers"]:
    if c.startswith("p5-"):
        ours |= set(sh("docker top %s -eo pid | tail -n +2" % c).split())
me = str(os.getpid())
top = sh("top -b -n 2 -d 1 -w 512 | awk '/^top -/{f++} f==2' | tail -n +8")
busy = []
for l in top.splitlines():
    p = l.split(None, 11)
    if len(p) < 12:
        continue
    pid, cpu, cmd = p[0], float(p[8].replace(",", ".")), p[11]
    kernel = cmd.startswith(("kworker", "ksoftirqd", "irq/", "rcu_", "migration/", "kswapd"))   # kernel threads
    if cpu > 5 and pid not in ours and pid != me and not kernel and \
            not any(x in cmd for x in ("tegrastats", "jetson.py", "top", "python3 -")):
        busy.append((pid, cpu, cmd[:80]))
out["busy"] = busy
if shutil.which("nvidia-smi"):
    gp = sh("nvidia-smi --query-compute-apps=pid --format=csv,noheader").split()
    out["gpu_foreign"] = [p for p in gp if p.isdigit() and p not in ours]
dev = "/sys/class/devfreq/" + os.environ["GPUDEV"]
out["gpu_hz"] = [int(open(dev + "/" + k + "_freq").read()) for k in ("min", "max", "cur")]
out["nvpmodel"] = sh("nvpmodel -q 2>/dev/null | head -1")
st = os.statvfs(os.environ["P5"]); out["p5_free"] = st.f_bavail * st.f_frsize
out["droot_free"] = int(sh("df -B1 --output=avail %s | tail -1" % os.environ["DROOT"]) or 0)
out["ntp"] = sh("timedatectl show -p NTPSynchronized --value")
temps = {}
for z in glob.glob("/sys/class/thermal/thermal_zone*"):
    try:
        temps[open(z + "/type").read().strip()] = int(open(z + "/temp").read()) / 1000.0
    except Exception:
        pass
out["gpu_temp"] = max((v for k, v in temps.items() if "gpu" in k.lower()), default=None)
print(json.dumps(out))
'''


def probe(unit):
    u = UNITS[unit]
    cmd = (f"GPUDEV={u['gpu_devfreq']} P5={u['p5']} DROOT={u['docker_root']} python3 - <<'PYEOF'\n{PROBE}\nPYEOF")
    return json.loads(ssh(unit, cmd, timeout=60))


def http(url, data=None, timeout=30):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if isinstance(data, dict) else data,
                                 headers={"Content-Type": "application/json"} if isinstance(data, dict) else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode()


def metrics(server):
    vals = {}
    for line in http(server + "/metrics")[1].splitlines():
        for k in ("num_running_reqs", "num_queue_reqs", "num_used_tokens", "swa_used_tokens"):
            if line.startswith(f"sglang:{k}"):
                vals[k] = float(line.rsplit(" ", 1)[1])
    return vals


def flush_verified(server, max_wait=300):
    """P1's flush_cache_verified (P1's harness run_one.py): idle, flush, used tokens 0 and still 0 a second later."""
    t_end = time.monotonic() + max_wait
    time.sleep(3)
    while time.monotonic() < t_end:
        m = metrics(server)
        if m.get("num_running_reqs", 1) == 0 and m.get("num_queue_reqs", 1) == 0:
            st, body = http(server + "/flush_cache", data=b"")
            if st == 200 and body.startswith("Cache flushed"):
                time.sleep(1)
                a = metrics(server)
                if a.get("num_used_tokens", 1) == 0 and a.get("swa_used_tokens", 0) == 0:
                    time.sleep(1)
                    b = metrics(server)
                    if b.get("num_used_tokens", 1) == 0 and b.get("swa_used_tokens", 0) == 0:
                        return True
        time.sleep(2)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("unit", choices=[k for k in UNITS if not k.startswith("_")])
    ap.add_argument("--server")
    ap.add_argument("--model", help="substring the served model path must contain")
    ap.add_argument("--pool", type=int, help="max_total_num_tokens the server must report")
    ap.add_argument("--flush", action="store_true")
    ap.add_argument("--warmup", action="store_true")
    ap.add_argument("--idle", type=float, default=0, help="seconds of idle board power to record")
    ap.add_argument("--out", help="directory for the idle samples and the result")
    ap.add_argument("--wait-cool", type=float, default=0)
    ap.add_argument("--no-temp", action="store_true", help="after a run: the temperature check is reported, not required")
    ap.add_argument("--json")
    a = ap.parse_args()
    u, res = UNITS[a.unit], {"unit": a.unit, "t_wall": time.time(), "checks": {}}
    chk = res["checks"]

    p = probe(a.unit)
    t_cool = time.monotonic() + a.wait_cool
    while p["gpu_temp"] is not None and p["gpu_temp"] >= 50 and time.monotonic() < t_cool:
        time.sleep(30)
        p = probe(a.unit)
    res["probe"] = p
    foreign = [c for c in p["containers"] if not c.startswith("p5-")]
    chk["1_quiet"] = {"ok": not foreign and not p["busy"] and not p.get("gpu_foreign"),
                      "foreign_containers": foreign, "busy": p["busy"], "gpu_foreign": p.get("gpu_foreign")}
    chk["2_clocks"] = {"ok": all(f == u["gpu_locked_hz"] for f in p["gpu_hz"]) and "MAXN" in p["nvpmodel"],
                       "gpu_hz": p["gpu_hz"], "nvpmodel": p["nvpmodel"]}
    floor = u["docker_root_free_dev2"] - u.get("docker_root_tolerance", 10_000_000)
    chk["3_disk"] = {"ok": p["p5_free"] >= 5e9 and p["droot_free"] >= floor,
                     "p5_free_gb": round(p["p5_free"] / 1e9, 1), "docker_root_free": p["droot_free"],
                     "docker_root_floor": floor}
    off = clock_offset(a.unit)
    chk["4_time"] = {"ok": p["ntp"] == "yes", "ntp": p["ntp"], **off}
    chk["5_temp"] = {"ok": a.no_temp or (p["gpu_temp"] is not None and p["gpu_temp"] < 50), "gpu_temp_C": p["gpu_temp"]}
    if a.server:
        s = a.server.rstrip("/")
        info = json.loads(http(s + "/get_server_info")[1])
        c6 = {"model_path": info.get("model_path"), "pool": info.get("max_total_num_tokens"),
              "kv_cache_dtype": info.get("kv_cache_dtype"), "max_running_requests": info.get("max_running_requests"),
              "version": info.get("version")}
        ok = (not a.model or a.model in str(info.get("model_path"))) and (not a.pool or info.get("max_total_num_tokens") == a.pool)
        if a.warmup:
            st, _ = http(s + "/generate", {"input_ids": list(range(1000, 1064)),
                                           "sampling_params": {"max_new_tokens": 8, "ignore_eos": True}}, timeout=600)
            c6["warmup"] = st
            ok = ok and st == 200
        if a.flush:
            c6["flush_verified"] = flush_verified(s)
            ok = ok and c6["flush_verified"]
        chk["6_server"] = {"ok": ok, **c6}
    if a.idle:
        name = f"idle-{int(time.time())}"
        rdir = f"{u['p5']}/runs/{name}"
        ssh(a.unit, f"mkdir -p {rdir} && python3 {u['p5']}/bin/jetson.py sample --out {rdir}/device_samples.jsonl "
                    f"--interval {interval_ms(a.unit)} --duration {a.idle}", timeout=a.idle + 120)
        out = Path(a.out or ".")
        out.mkdir(parents=True, exist_ok=True)
        local = out / "idle_device_samples.jsonl"
        import subprocess
        subprocess.run(["rsync", "-a", f"{a.unit}:{rdir}/device_samples.jsonl", str(local)], check=True)
        e = board_energy(load(str(local)))
        chk["7_idle"] = {"ok": not e.get("flag"), "seconds": a.idle, "mean_W": e.get("mean_W"),
                         "median_interval_s": e.get("median_interval_s"), "gaps": e.get("gaps"), "file": str(local)}
    res["ok"] = all(c["ok"] for c in chk.values())
    txt = json.dumps(res, indent=1, default=str)
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(txt)
    if a.out:
        Path(a.out).mkdir(parents=True, exist_ok=True)
        (Path(a.out) / "preflight.json").write_text(txt)
    print(json.dumps({"unit": a.unit, "ok": res["ok"],
                      "failed": [k for k, c in chk.items() if not c["ok"]],
                      **{k: {x: y for x, y in c.items() if x != "ok"} for k, c in chk.items() if not c["ok"]}},
                     default=str))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

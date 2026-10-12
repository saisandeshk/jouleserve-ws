"""Jetson board telemetry in P1's schema (DEV-3, planning/OPTIONS_PLAN.md §4.1). Stdlib only, Python >= 3.8.

On the unit (copied to <p5>/bin/jetson.py; nothing installed):
    python3 jetson.py sample --out <run>/device_samples.jsonl [--interval 200] [--duration S] [--pidfile F]
    python3 jetson.py energy <device_samples.jsonl> [--t0 WALL] [--t1 WALL]

On the WS (driver side), `Telemetry(unit, p5, run_dir)` starts the sampler over ssh, stops it, copies the samples
back and records the WS-unit clock offset at start and end; `board_energy()` integrates a window.

Each tegrastats line becomes one record, stamped on receipt with t_mono and t_wall (the unit's clocks). Kept:
- every power rail verbatim, as P1's drone sampler names them (`power_VDD_GPU_SOC_mW`, `power_VIN_mW`, ...);
- the board total as P1's traffic vitals define it (`power_total_mw`, `power_total_source`): on the Orins the sum
  VDD_GPU_SOC + VDD_CPU_CV + VIN_SYS_5V0 (P1's vitals: 4,796 + 2,797 + 4,939 = 12,532 mW), on Thor the VIN rail;
- RAM, CPU, GR3D/EMC load and temperatures from tegrastats; GPU clocks (cur, min, max) and thermal zones from sysfs.
tegrastats runs as root through the password-free sudo rule where one exists (it adds EMC load), as P1's sampler does;
a root tegrastats cannot be signalled by us, so it is stopped by closing its pipe (it exits on its next write).
Energy is the trapezoid rule over power_total_mw against t_wall; a gap over 1 s between samples is flagged.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import signal
import statistics
import subprocess
import sys
import time

ORIN_TOTAL = ("VDD_GPU_SOC", "VDD_CPU_CV", "VIN_SYS_5V0")
GAP_S = 1.0


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:          # some Orin thermal zones fail inside the decoder (TypeError), not with OSError
        return None


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def parse(line: str) -> dict:
    """One tegrastats line -> fields (rails verbatim, P1's total, load, temperatures)."""
    d = {}
    m = re.search(r"RAM (\d+)/(\d+)MB", line)
    if m:
        d["ram_used_mb"], d["ram_total_mb"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"SWAP (\d+)/(\d+)MB", line)
    if m:
        d["swap_used_mb"] = int(m.group(1))
    m = re.search(r"CPU \[([^\]]*)\]", line)
    if m:
        util = [_num(c.split("@")[0].rstrip("%")) for c in m.group(1).split(",")]
        util = [u for u in util if u is not None]
        d["cpu_util_pct_mean"] = sum(util) / len(util) if util else None
    for k, v in re.findall(r"(\w+)@(-?[\d.]+)C", line):
        d["temp_" + k + "_C"] = float(v)
    rails = {k: int(v) for k, v in re.findall(r"\b(VDD\w*|VIN\w*) (\d+)mW/", line)}
    for k, v in rails.items():
        d["power_" + k + "_mW"] = v
    if all(k in rails for k in ORIN_TOTAL):
        d["power_total_mw"] = sum(rails[k] for k in ORIN_TOTAL)
        d["power_total_source"] = "sum(VDD_GPU_SOC+VDD_CPU_CV+VIN_SYS_5V0)"
    elif "VIN" in rails:
        d["power_total_mw"] = rails["VIN"]
        d["power_total_source"] = "VIN"
    m = re.search(r"GR3D_FREQ (\d+)%(?:@\[?(\d+))?", line)
    if m:
        d["gpu_util_pct"] = int(m.group(1))
        if m.group(2):
            d["gpu_freq_mhz"] = int(m.group(2))
    m = re.search(r"EMC_FREQ (\d+)%(?:@(\d+))?", line)
    if m:
        d["emc_util_pct"] = int(m.group(1))
    return d


class _Sysfs:
    """GPU clocks (devfreq) and thermal zones, read once per sample."""

    def __init__(self):
        names = {os.path.basename(p): p for p in glob.glob("/sys/class/devfreq/*")}
        self.gpu = next((names[n] for n in sorted(names) if n.endswith(".gpu") or "ga10b" in n or n.startswith("gpu-gpc")), None)
        self.zones = {_read(z + "/type"): z + "/temp" for z in sorted(glob.glob("/sys/class/thermal/thermal_zone*"))}

    def read(self) -> dict:
        d = {}
        if self.gpu:
            for k in ("cur", "min", "max"):
                d[f"gpu_{k}_freq_hz"] = _num(_read(f"{self.gpu}/{k}_freq"))
        d["zone_temp_C"] = {n: (_num(_read(p)) or 0) / 1000.0 for n, p in self.zones.items()}
        return d


def sample(out: str, interval_ms: int = 200, duration: float | None = None, pidfile: str | None = None):
    rooted = subprocess.call(["sudo", "-n", "/usr/bin/tegrastats", "--help"], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL) == 0
    cmd = (["sudo", "-n"] if rooted else []) + ["/usr/bin/tegrastats", "--interval", str(interval_ms)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, bufsize=1)
    if pidfile:
        with open(pidfile, "w") as f:
            f.write(str(os.getpid()))
    stop = {"now": False}

    def _stop(*_):
        stop["now"] = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    sysfs, t_end = _Sysfs(), (time.monotonic() + duration) if duration else None
    with open(out, "a", buffering=1) as f:
        for line in proc.stdout:
            rec = {"t_mono": time.monotonic(), "t_wall": time.time(), "tegrastats_root": rooted}
            rec.update(parse(line))
            try:
                rec.update(sysfs.read())
            except Exception as e:     # sysfs extras must never stop the power samples
                rec["sysfs_error"] = repr(e)[:120]
            f.write(json.dumps(rec) + "\n")
            if stop["now"] or (t_end and rec["t_mono"] >= t_end):
                break
    try:
        proc.stdout.close()
        proc.terminate()
    except OSError:
        pass
    if pidfile and os.path.exists(pidfile):
        os.remove(pidfile)


def load(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def board_energy(rows: list[dict], t0: float | None = None, t1: float | None = None, key: str = "power_total_mw",
                 clock: str = "t_wall") -> dict:
    """Energy (J) over [t0, t1] on `clock` by the trapezoid rule, the edges interpolated linearly. Returns the energy,
    the mean power, the sample count, the median interval and every gap over 1 s (flagged: a run with a gap is
    incomplete by plan §6)."""
    pts = [(r[clock], r[key] / 1000.0) for r in rows if r.get(key) is not None]
    pts.sort()
    if len(pts) < 2:
        return {"energy_J": None, "n": len(pts), "flag": "too few samples"}
    lo, hi = pts[0][0] if t0 is None else t0, pts[-1][0] if t1 is None else t1

    def at(t):
        for (ta, pa), (tb, pb) in zip(pts, pts[1:]):
            if ta <= t <= tb:
                return pa + (pb - pa) * (t - ta) / (tb - ta) if tb > ta else pa
        return None

    inner = [(t, p) for t, p in pts if lo < t < hi]
    edge = [(lo, at(lo)), *inner, (hi, at(hi))]
    if edge[0][1] is None or edge[-1][1] is None:
        return {"energy_J": None, "n": len(inner), "flag": "window outside the samples"}
    e = sum((tb - ta) * (pa + pb) / 2 for (ta, pa), (tb, pb) in zip(edge, edge[1:]))
    gaps = [(round(ta, 3), round(tb - ta, 3)) for (ta, _), (tb, _) in zip(edge, edge[1:]) if tb - ta > GAP_S]
    dts = [tb - ta for (ta, _), (tb, _) in zip(pts, pts[1:])]
    return {"energy_J": e, "mean_W": e / (hi - lo) if hi > lo else None, "t0": lo, "t1": hi, "n": len(inner),
            "median_interval_s": statistics.median(dts), "gaps": gaps, "flag": "gap" if gaps else ""}


# ----------------------------------------------------------------------------- WS side (driver)

def ssh(unit: str, cmd: str, timeout: float = 60) -> str:
    return subprocess.run(["ssh", "-o", "BatchMode=yes", unit, cmd], capture_output=True, text=True,
                          timeout=timeout).stdout.strip()


def clock_offset(unit: str, n: int = 9) -> dict:
    """Unit clock minus WS clock (s) over one open ssh session (so a probe costs one LAN round trip, not a new
    connection): the probe with the smallest round trip wins; the error bound is half of it."""
    p = subprocess.Popen(["ssh", "-o", "BatchMode=yes", unit,
                          "python3 -u -c 'import sys,time\nfor l in sys.stdin: print(repr(time.time()), flush=True)'"],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    best = None
    try:
        for _ in range(n):
            a = time.time()
            p.stdin.write("t\n")
            p.stdin.flush()
            u = float(p.stdout.readline())
            b = time.time()
            if best is None or b - a < best[1]:
                best = (u - (a + b) / 2, b - a)
    finally:
        p.stdin.close()
        p.wait(timeout=10)
    return {"offset_s": best[0], "rtt_s": best[1], "t_ws": time.time()}


def interval_ms(unit: str) -> int:
    """tegrastats interval to request on a unit (WS side): configs/jetsons.json "tegrastats_interval_ms", else 200.
    Root tegrastats on Thor-1 adds ~35 ms per sample (237 ms at 200; 202 ms at 180; 20 s tests, 12 Oct)."""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../configs/jetsons.json")) as f:
            return int(json.load(f).get(unit, {}).get("tegrastats_interval_ms", 200))
    except OSError:
        return 200


class Telemetry:
    """Start/stop the unit's sampler for one run: samples land in <p5>/runs/<run>/device_samples.jsonl on the unit
    and are copied to <run_dir>/device_samples.jsonl on the WS by stop()."""

    def __init__(self, unit: str, p5: str, run_name: str, run_dir: str):
        self.unit, self.p5, self.run, self.run_dir = unit, p5, run_name, run_dir
        self.remote = f"{p5}/runs/{run_name}"
        self.offsets = {}

    def start(self):
        self.offsets["start"] = clock_offset(self.unit)
        # ssh -n -f with an exec'd, fully redirected command: a background job inside the remote shell would hold the
        # ssh session open until the sampler ends
        subprocess.run(["ssh", "-n", "-f", "-o", "BatchMode=yes", self.unit,
                        f"mkdir -p {self.remote} && cd {self.remote} && exec setsid python3 {self.p5}/bin/jetson.py "
                        f"sample --out device_samples.jsonl --interval {interval_ms(self.unit)} --pidfile sampler.pid "
                        f"> sampler.log 2>&1 < /dev/null"],
                       timeout=60, check=True)
        for _ in range(50):
            if ssh(self.unit, f"test -s {self.remote}/device_samples.jsonl && echo ok") == "ok":
                return self
            time.sleep(0.2)
        raise RuntimeError(f"{self.unit}: sampler did not start ({self.remote}/sampler.log)")

    def stop(self):
        ssh(self.unit, f"cd {self.remote} && test -f sampler.pid && kill $(cat sampler.pid); "
                       f"for i in 1 2 3 4 5 6 7 8 9 10; do test -f sampler.pid || break; sleep 0.3; done")
        self.offsets["end"] = clock_offset(self.unit)
        os.makedirs(self.run_dir, exist_ok=True)
        subprocess.run(["rsync", "-a", f"{self.unit}:{self.remote}/", f"{self.run_dir}/device/"], check=True)
        with open(os.path.join(self.run_dir, "device", "clock_offsets.json"), "w") as f:
            json.dump(self.offsets, f, indent=1)
        return os.path.join(self.run_dir, "device", "device_samples.jsonl")


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("--out", required=True)
    s.add_argument("--interval", type=int, default=200)
    s.add_argument("--duration", type=float)
    s.add_argument("--pidfile")
    e = sub.add_parser("energy")
    e.add_argument("path")
    e.add_argument("--t0", type=float)
    e.add_argument("--t1", type=float)
    a = ap.parse_args(argv)
    if a.cmd == "sample":
        sample(a.out, a.interval, a.duration, a.pidfile)
    else:
        print(json.dumps(board_energy(load(a.path), a.t0, a.t1)))


if __name__ == "__main__":
    sys.exit(main())

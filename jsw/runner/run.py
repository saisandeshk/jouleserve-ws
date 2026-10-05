"""One run directory format for every WS experiment (OPTIONS_PLAN.md S5).

    with Run("a-e1-pilot", args=vars(a), gpu=0, server="http://127.0.0.1:30000") as run:
        run.event("start", n=len(prompts))
        ...  # write per-call records with run.call(...)
    # manifest.json, events.jsonl, calls.jsonl, nvml.jsonl, sglang_metrics.jsonl in ~/work/runs/<name>/

Every record carries t_mono and t_wall (the samplers' clock), so calls, server metrics and GPU energy line up.
GPU energy over any window comes from NVML's cumulative counter: `gpu_energy_j(run.dir, t0, t1)`.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[2]          # the repo checkout or ~/jsw-dev
RUNS_ROOT = Path(os.environ.get("JSW_RUNS", Path.home() / "work/runs"))


def _get(url, timeout=5):
    try:
        return json.loads(urllib.request.urlopen(url, timeout=timeout).read().decode())
    except Exception as e:
        return {"error": repr(e)}


def _sh(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception as e:
        return repr(e)


def code_revision() -> dict:
    """Git HEAD when run from a checkout; else the REVISION stamp written by env/sync_ws.sh. Plus a hash
    of the Python sources actually present, so a dev copy's edits show up."""
    rev = _sh(["git", "-C", str(CODE_ROOT), "describe", "--always", "--dirty"]) if (CODE_ROOT / ".git").exists() \
        else (CODE_ROOT / "REVISION").read_text().strip() if (CODE_ROOT / "REVISION").exists() else None
    h = hashlib.sha256()
    for p in sorted(CODE_ROOT.glob("jsw/**/*.py")) + sorted(CODE_ROOT.glob("analysis/*.py")):
        h.update(p.read_bytes())
    return {"revision": rev, "sources_sha": h.hexdigest()[:16], "root": str(CODE_ROOT)}


def package_versions(*names) -> dict:
    from importlib import metadata
    out = {}
    for n in names:
        try:
            out[n] = metadata.version(n)
        except Exception:
            out[n] = None
    return out


class Run:
    def __init__(self, name: str, args: dict | None = None, gpu: int | str | list | None = None, server: str | None = None,
                 root: Path | None = None, metrics_hz: float = 2.0, nvml_hz: float = 10.0, extra: dict | None = None):
        self.name, self.server = name, server.rstrip("/") if server else None
        if isinstance(gpu, str):
            gpu = [int(x) for x in gpu.split(",") if x != ""]
        self.gpus = [] if gpu is None else [gpu] if isinstance(gpu, int) else list(gpu)
        self.gpu = self.gpus[0] if self.gpus else None
        self.dir = Path(root or RUNS_ROOT) / name
        self.dir.mkdir(parents=True, exist_ok=True)
        self.args, self.extra = args or {}, extra or {}
        self.metrics_hz, self.nvml_hz = metrics_hz, nvml_hz
        self._lock = threading.Lock()
        self._events = self._calls = None
        self.samplers = []

    # ------------------------------------------------------------------ lifecycle
    def __enter__(self):
        self.manifest = {
            "name": self.name, "args": self.args, "host": socket.gethostname(), "argv": sys.argv,
            "t_start_wall": time.time(), "t_start_mono": time.monotonic(), "code": code_revision(),
            "python": sys.version.split()[0],
            "packages": package_versions("sglang", "torch", "transformers", "flashinfer-python", "openai", "aiohttp"),
            "nvidia_smi": _sh(["nvidia-smi", "--query-gpu=index,name,driver_version,memory.used,temperature.gpu,"
                               "power.draw,clocks.sm", "--format=csv,noheader"]),
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "hf_hub_offline": os.environ.get("HF_HUB_OFFLINE"),
            **self.extra,
        }
        if self.server:
            self.manifest["server_info"] = _get(self.server + "/get_server_info")
            self.manifest["models"] = _get(self.server + "/v1/models")
        self._write_manifest()
        self._events = open(self.dir / "events.jsonl", "a")
        self._calls = open(self.dir / "calls.jsonl", "a")
        from jsw.telemetry.samplers import NvmlSampler, SglangMetricsSampler
        for i, g in enumerate(self.gpus):          # one file per GPU: nvml.jsonl, nvml_g<k>.jsonl (TP>1)
            self.samplers.append(NvmlSampler(str(self.dir / ("nvml.jsonl" if i == 0 else f"nvml_g{g}.jsonl")), g,
                                             hz=self.nvml_hz))
        if self.server:
            self.samplers.append(SglangMetricsSampler(str(self.dir / "sglang_metrics.jsonl"), self.server,
                                                      hz=self.metrics_hz))
        for s in self.samplers:
            s.start()
        self.event("run_start")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.event("run_end", error=repr(exc) if exc else None)
        for s in self.samplers:
            s.stop()
        self.manifest.update(t_end_wall=time.time(), t_end_mono=time.monotonic(),
                             status="error" if exc else "done", error=repr(exc) if exc else None)
        self._write_manifest()
        for f in (self._events, self._calls):
            f.close()
        return False

    def _write_manifest(self):
        (self.dir / "manifest.json").write_text(json.dumps(self.manifest, indent=1, default=str))

    # ------------------------------------------------------------------ records
    def _rec(self, f, kw):
        kw.setdefault("t_mono", time.monotonic())
        kw.setdefault("t_wall", time.time())
        with self._lock:
            f.write(json.dumps(kw, default=str) + "\n")
            f.flush()

    def event(self, kind: str, **kw):
        self._rec(self._events, {"kind": kind, **kw})

    def call(self, **kw):
        """One LLM call (any fields; see jsw/gateway for the gateway's own call log)."""
        self._rec(self._calls, kw)

    def note(self, **kw):
        """Add fields to the manifest (written immediately)."""
        self.manifest.update(kw)
        self._write_manifest()


# ---------------------------------------------------------------------- energy
def load_nvml(run_dir) -> list[dict]:
    return load_nvml_file(Path(run_dir) / "nvml.jsonl")


def load_nvml_file(p) -> list[dict]:
    p = Path(p)
    rows = []
    if p.exists():
        for line in open(p):
            r = json.loads(line)
            if "energy_mj" in r:
                rows.append(r)
    return rows


def gpu_energy_j(run_dir_or_rows, t0: float, t1: float) -> float | None:
    """GPU energy (J) between two t_mono instants, by linear interpolation of NVML's cumulative counter. A run
    directory sums every GPU it sampled (nvml.jsonl and nvml_g<k>.jsonl)."""
    if not isinstance(run_dir_or_rows, list):
        files = sorted(Path(run_dir_or_rows).glob("nvml*.jsonl"))
        parts = [gpu_energy_j(load_nvml_file(f), t0, t1) for f in files]
        return sum(p for p in parts if p is not None) if any(p is not None for p in parts) else None
    rows = run_dir_or_rows
    if len(rows) < 2 or t1 <= t0:
        return None

    def at(t):
        if t <= rows[0]["t_mono"]:
            return rows[0]["energy_mj"]
        lo, hi = 0, len(rows) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if rows[mid]["t_mono"] <= t:
                lo = mid
            else:
                hi = mid
        a, b = rows[lo], rows[hi]
        if t >= b["t_mono"]:
            return b["energy_mj"]
        f = (t - a["t_mono"]) / max(1e-9, b["t_mono"] - a["t_mono"])
        return a["energy_mj"] + f * (b["energy_mj"] - a["energy_mj"])

    return (at(t1) - at(t0)) / 1000.0


def gpu_idle(threshold_mib: float = 100.0) -> dict:
    """Teardown check: GPU memory per index, and whether all are back to idle (AGENTS.md §4)."""
    out = _sh(["nvidia-smi", "--query-gpu=index,memory.used", "--format=csv,noheader,nounits"])
    used = {}
    for line in out.splitlines():
        i, m = (x.strip() for x in line.split(","))
        used[int(i)] = float(m)
    return {"used_mib": used, "idle": all(v < threshold_mib for v in used.values())}

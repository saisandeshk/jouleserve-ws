"""Background samplers that write JSONL on a shared monotonic clock.

- NvmlSampler: GPU power, cumulative energy counter, clocks, memory, utilization,
  temperature and throttle reasons (no root needed).
- SglangMetricsSampler: SGLang's Prometheus /metrics (gauges and counters, no histogram
  buckets).

Every record carries `t_mono` (time.monotonic) and `t_wall` (time.time) so it lines up
with per-call logs written by other processes on the same host.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request


class _Sampler(threading.Thread):
    def __init__(self, path: str, hz: float):
        super().__init__(daemon=True)
        self.path, self.period = path, 1.0 / hz
        self._halt = threading.Event()

    def sample(self) -> dict:  # pragma: no cover - overridden
        raise NotImplementedError

    def run(self):
        with open(self.path, "a") as f:
            nxt = time.monotonic()
            while not self._halt.is_set():
                try:
                    rec = self.sample()
                except Exception as e:  # keep sampling through transient errors
                    rec = {"error": repr(e)}
                rec["t_mono"], rec["t_wall"] = time.monotonic(), time.time()
                f.write(json.dumps(rec) + "\n")
                f.flush()
                nxt += self.period
                self._halt.wait(max(0.0, nxt - time.monotonic()))

    def stop(self):
        self._halt.set()
        self.join(timeout=5)


class NvmlSampler(_Sampler):
    def __init__(self, path: str, gpu_index: int, hz: float = 10.0):
        super().__init__(path, hz)
        import pynvml
        pynvml.nvmlInit()
        self.nv = pynvml
        self.h = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
        self.gpu_index = gpu_index

    def sample(self) -> dict:
        nv, h = self.nv, self.h
        mem = nv.nvmlDeviceGetMemoryInfo(h)
        util = nv.nvmlDeviceGetUtilizationRates(h)
        return {
            "gpu": self.gpu_index,
            "power_w": nv.nvmlDeviceGetPowerUsage(h) / 1000.0,
            "energy_mj": nv.nvmlDeviceGetTotalEnergyConsumption(h),
            "sm_mhz": nv.nvmlDeviceGetClockInfo(h, nv.NVML_CLOCK_SM),
            "mem_mhz": nv.nvmlDeviceGetClockInfo(h, nv.NVML_CLOCK_MEM),
            "mem_used_mib": mem.used / 2**20,
            "util_gpu": util.gpu,
            "util_mem": util.memory,
            "temp_c": nv.nvmlDeviceGetTemperature(h, nv.NVML_TEMPERATURE_GPU),
            "throttle": int(nv.nvmlDeviceGetCurrentClocksThrottleReasons(h)),
        }


class SglangMetricsSampler(_Sampler):
    """Keeps every `sglang:` gauge/counter sample; drops histogram buckets."""

    def __init__(self, path: str, base: str, hz: float = 2.0):
        super().__init__(path, hz)
        self.url = base.rstrip("/") + "/metrics"

    def sample(self) -> dict:
        text = urllib.request.urlopen(self.url, timeout=2).read().decode()
        out = {}
        for line in text.splitlines():
            if not line.startswith("sglang:") or "_bucket{" in line:
                continue
            key, _, val = line.rpartition(" ")
            name, _, labels = key.partition("{")
            # Labels only differ by model/engine here; keep the metric name plus any
            # label that is not a constant identity label.
            extra = [kv for kv in labels.rstrip("}").split(",")
                     if kv and not kv.startswith(("model_name", "engine_type", "tp_rank",
                                                  "pp_rank", "dp_rank", "moe_ep_rank"))]
            k = name + ("{" + ",".join(extra) + "}" if extra else "")
            try:
                out[k] = float(val)
            except ValueError:
                pass
        return {"m": out}

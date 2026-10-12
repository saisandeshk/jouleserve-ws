"""Start or stop an SGLang server on one of P5's Jetsons with P1's image and flags (DEV-4, OPTIONS_PLAN.md §4.1, D20).

    python env/launch_jetson.py <unit> <name> --model granite|e4b|gemma26b [--kv bf16|fp8_e5m2] [--pool N]
        [--max-running N] [--extra "<more sglang flags>"] [--timeout 1800] [--out <file.json>]
    python env/launch_jetson.py <unit> <name> --stop

The container is `p5-<name>`, run per AGENTS.md §4: P1's image on that unit (configs/jetsons.json), `--rm --read-only
--tmpfs /tmp --log-driver none`, the model's Hugging Face folder mounted read-only where P1 keeps it, HF_HUB_OFFLINE=1,
every write in <p5> (HOME and the Triton/FlashInfer/torch caches in <p5>/cache, the server log in <p5>/logs/<name>.log).
Flags are P1's, per model and setting (sources below); only the KV dtype, the pool (--max-total-tokens) and the
running-request limit change per arm. The launcher waits for /get_server_info and prints the pool the server got.

Sources of P1's flags:
- granite, traffic on the Orin 32s: P1's run records (runs.jsonl of the clean Orin 32 granite rows, 12 Oct): SGLang
  0.5.16, triton attention, chunked prefill 2,048, CUDA graphs off, bf16, context 26,624, mem 0.80, pool 25,358 in
  every re-run, one request at a time, parsers qwen3_coder and deepseek-r1;
- e4b, traffic on Orin-32-1: the same records: context 32,768, mem 0.85, gemma4 parsers;
- gemma26b on Thor-1: P1's final drone server `p1-final-gemma-it` (30 Sep-6 Oct, docker inspect in DEV-1's snapshot):
  context 65,536, mem 0.65, pool 80,000, one request at a time, P1's chat template, gemma4 parsers;
- gemma26b on Orin-64-1: P1's server found running on 12 Oct (`sglang-benchmark`, DEV-1): context 65,536, pool
  60,000, mem 0.95, SWA ratio 0.2, CUDA graph batch 1, FP8 KV.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNITS = json.loads((ROOT / "configs/jetsons.json").read_text())

HUB_O32 = {"Orin-32-1": "/media/hdd/huggingface/hub",
           "Orin-32-2": "/media/ssd/final_sweep/orin57_10.24.24.57/hf_granite/hub",
           "Orin-32-3": "/media/ssd/huggingface/hub"}
PATCH = {"Orin-64-1": "/media/ssd/final_sweep/orin45_10.24.24.45/_patches/nccl_gloo_patch",
         "Orin-32-1": "/media/ssd/final_sweep/orin56_10.24.24.56/_patches/nccl_gloo_patch",
         "Orin-32-2": "/media/ssd/final_sweep/orin57_10.24.24.57/_patches/nccl_gloo_patch",
         "Orin-32-3": "/media/ssd/final_sweep/orin58_10.24.24.58/_patches/nccl_gloo_patch"}
GRANITE = "models--ibm-granite--granite-4.2-8b", "f8de16cdcdbc6c779ca517604e050d82cc119e44"
GEMMA26 = "models--google--gemma-4-26B-A4B-it", "4d7ae4984b7db7de8f8457170b3f1a419ee76d52"

COMMON = "--host 0.0.0.0 --port 30000 --enable-metrics --enable-cache-report"
TRAFFIC_O32 = "--attention-backend triton --chunked-prefill-size 2048 --disable-cuda-graph"


def model_spec(unit, model):
    """(hub dir to mount, snapshot path, served name, P1's flags, default pool, default kv)."""
    if model == "granite" and unit in HUB_O32:
        hub = HUB_O32[unit]
        return (f"{hub}/{GRANITE[0]}", f"{hub}/{GRANITE[0]}/snapshots/{GRANITE[1]}", "ibm-granite/granite-4.2-8b",
                f"{TRAFFIC_O32} --dtype bfloat16 --context-length 26624 --mem-fraction-static 0.8 "
                "--tool-call-parser qwen3_coder --reasoning-parser deepseek-r1", 25358, "bf16")
    if model == "gemma26b" and unit == "Thor-1":
        hub = "/home/yash/.cache/huggingface/hub"
        return (f"{hub}/{GEMMA26[0]}", f"{hub}/{GEMMA26[0]}/snapshots/{GEMMA26[1]}", "google/gemma-4-26B-A4B-it",
                "--tp-size 1 --context-length 65536 --mem-fraction-static 0.65 "
                "--chat-template /home/yash/llmbench/gemma4_chat_template/chat_template.jinja "
                "--reasoning-parser gemma4 --tool-call-parser gemma4", 80000, "bf16")
    if model == "gemma26b" and unit == "Orin-64-1":
        hub = "/media/hdd/huggingface/hub"
        return (f"{hub}/{GEMMA26[0]}", f"{hub}/{GEMMA26[0]}/snapshots/{GEMMA26[1]}", "google/gemma-4-26B-A4B-it",
                "--context-length 65536 --mem-fraction-static 0.95 --reasoning-parser gemma4 --tool-call-parser gemma4 "
                "--swa-full-tokens-ratio 0.2 --cuda-graph-max-bs 1", 60000, "fp8_e5m2")
    raise SystemExit(f"no spec for {model} on {unit} (e4b: add its path on Orin-32-1 before use)")


def ssh(unit, cmd, timeout=120):
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", unit, cmd], capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr).strip()


def get(url, timeout=5):
    try:
        return json.loads(urllib.request.urlopen(url, timeout=timeout).read().decode())
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("unit")
    ap.add_argument("name")
    ap.add_argument("--model", choices=("granite", "gemma26b", "e4b"))
    ap.add_argument("--kv", default=None, help="bf16 (auto) or fp8_e5m2; default: P1's for that unit")
    ap.add_argument("--pool", type=int, default=None, help="--max-total-tokens; default: P1's")
    ap.add_argument("--max-running", type=int, default=1)
    ap.add_argument("--extra", default="")
    ap.add_argument("--timeout", type=float, default=1800)
    ap.add_argument("--out")
    ap.add_argument("--stop", action="store_true")
    a = ap.parse_args()
    u = UNITS[a.unit]
    cname = f"p5-{a.name}"
    if a.stop:
        rc, out = ssh(a.unit, f"docker stop {cname}", timeout=180)
        print(json.dumps({"stopped": cname, "rc": rc, "out": out[-200:]}))
        return rc
    hub, snap, served, flags, pool0, kv0 = model_spec(a.unit, a.model)
    kv, pool = a.kv or kv0, a.pool or pool0
    p5 = u["p5"]
    sg = (f"python3 -m sglang.launch_server --model-path {snap} --served-model-name {served} {COMMON} {flags} "
          f"--max-total-tokens {pool} --max-running-requests {a.max_running}"
          + (f" --kv-cache-dtype {kv}" if kv != "bf16" else "") + (f" {a.extra}" if a.extra else ""))
    env = {"HOME": "/p5cache", "XDG_CACHE_HOME": "/p5cache/xdg", "TRITON_CACHE_DIR": "/p5cache/triton",
           "TORCHINDUCTOR_CACHE_DIR": "/p5cache/inductor", "FLASHINFER_WORKSPACE_BASE": "/p5cache",
           "HF_HUB_OFFLINE": "1", "SGLANG_WARMUP_TIMEOUT": "1800"}
    vols = [f"{hub}:{hub}:ro", f"{p5}/cache:/p5cache", f"{p5}/logs:/p5logs"]
    dock = ["--runtime nvidia", "--network host"]
    if a.unit == "Thor-1":
        dock += ["--gpus all", "--ipc host"]
        vols.append("/home/yash/llmbench/gemma4_chat_template:/home/yash/llmbench/gemma4_chat_template:ro")
    else:                          # P1's Orin environment: NCCL off, gloo patch on the path, 8 GB /dev/shm
        dock += ["--shm-size 8g"]
        vols.append(f"{PATCH[a.unit]}:/patches:ro")
        env.update(NCCL_SHM_DISABLE="1", NCCL_P2P_DISABLE="1", NCCL_IB_DISABLE="1", NCCL_IGNORE_DISABLED_P2P="1",
                   PYTHONPATH="/patches")
    cmd = (f"mkdir -p {p5}/cache {p5}/logs && docker run -d --rm --read-only --tmpfs /tmp --log-driver none "
           f"--name {cname} {' '.join(dock)} " + " ".join(f"-v {v}" for v in vols) + " "
           + " ".join(f"-e {k}={v}" for k, v in env.items())
           + f" {u['image']} sh -c {shlex.quote(f'exec {sg} >> /p5logs/{a.name}.log 2>&1')}")
    rc, out = ssh(a.unit, cmd)
    if rc:
        print(json.dumps({"error": "docker run failed", "out": out[-500:]}))
        return 1
    url, t0, info = f"http://{u['ip']}:30000", time.monotonic(), None
    while time.monotonic() - t0 < a.timeout:
        info = get(url + "/get_server_info")
        if info:
            break
        rc, alive = ssh(a.unit, f"docker ps -q -f name={cname}")
        if not alive:
            _, tail = ssh(a.unit, f"tail -20 {p5}/logs/{a.name}.log")
            print(json.dumps({"error": "container exited", "log_tail": tail[-1500:]}))
            return 1
        time.sleep(10)
    res = {"unit": a.unit, "container": cname, "url": url, "image": u["image"], "image_id": u["image_id"],
           "model": snap, "kv": kv, "pool_requested": pool, "load_s": round(time.monotonic() - t0, 1),
           "server_args": sg, "docker": cmd}
    if info:
        res.update(pool=info.get("max_total_num_tokens"), version=info.get("version"),
                   kv_cache_dtype=info.get("kv_cache_dtype"), context_length=info.get("context_length"),
                   max_running_requests=info.get("max_running_requests"),
                   mem_fraction_static=info.get("mem_fraction_static"))
    else:
        res["error"] = "timeout"
    txt = json.dumps(res, indent=1)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(txt)
    print(txt)
    return 0 if info else 1


if __name__ == "__main__":
    sys.exit(main())

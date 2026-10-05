"""Serving-cost calibration with token IDs (OPTIONS_PLAN.md A-E5; device model for live-vs-simulator checks).

    python -m jsw.costs.calibrate2 --server http://127.0.0.1:30000 --gpu 0 --out calib.json

Model-agnostic (SGLang's native /generate, synthetic token IDs, ignore_eos), measured on an otherwise idle server:
- idle power;
- cold prefill time and energy against prompt length (cache flushed before each request);
- decode time and energy per token against batch size AND context length: the b prompts of length L are first
  prefilled (1 output token), then decoded with G tokens each while fully cached, so the window is decode only.
  Points that would not fit the KV pool (b * (L + G) > 90% of max_total_num_tokens) are skipped.
GPU energy is NVML's cumulative counter, summed over --gpu (a list for TP=2).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import random
import time
import urllib.request

import pynvml


def post(url, body, timeout=1800):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True)
    ap.add_argument("--gpu", default="0")
    ap.add_argument("--out", required=True)
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--gen", type=int, default=256)
    ap.add_argument("--prefill-lens", default="1000,2000,4000,8000,16000")
    ap.add_argument("--ctx-lens", default="1000,4000,16000")
    ap.add_argument("--batches", default="1,2,4,8,16")
    a = ap.parse_args()
    pynvml.nvmlInit()
    hs = [pynvml.nvmlDeviceGetHandleByIndex(int(g)) for g in str(a.gpu).split(",")]
    S = a.server.rstrip("/")

    def energy():
        return sum(pynvml.nvmlDeviceGetTotalEnergyConsumption(h) for h in hs) / 1000.0

    def power():
        return sum(pynvml.nvmlDeviceGetPowerUsage(h) for h in hs) / 1000.0

    def flush():
        post(S + "/flush_cache", {}, timeout=60) if False else urllib.request.urlopen(
            urllib.request.Request(S + "/flush_cache", data=b"", method="POST"), timeout=60).read()
        time.sleep(1.0)

    def ids(n, seed):
        r = random.Random(seed)
        return [r.randrange(1000, 30000) for _ in range(n)]

    def gen(prompt, n_out):
        g = post(S + "/generate", {"input_ids": prompt, "sampling_params": {
            "max_new_tokens": n_out, "ignore_eos": True, "temperature": 0}})
        return (g[0] if isinstance(g, list) else g)["meta_info"]

    info = json.loads(urllib.request.urlopen(S + "/get_server_info", timeout=10).read())
    pool = info.get("max_total_num_tokens")
    res = {"server": S, "gpu": a.gpu, "model_path": info.get("model_path"), "pool_tokens": pool,
           "t_wall": time.time(), "gen": a.gen}
    time.sleep(5)
    p = []
    for _ in range(100):
        p.append(power())
        time.sleep(0.1)
    res["idle_w"] = sum(p) / len(p)
    print("idle_w", round(res["idle_w"], 1), "pool", pool, flush=True)
    gen(ids(500, 1), 8)                                   # warm up

    res["prefill"] = []
    for L in [int(x) for x in a.prefill_lens.split(",")]:
        if L + 8 > 0.9 * pool:
            continue
        for rep in range(a.reps):
            flush()
            t0, e0 = time.monotonic(), energy()
            mi = gen(ids(L, 10 * L + rep), 1)
            t1, e1 = time.monotonic(), energy()
            row = {"L": L, "rep": rep, "s": t1 - t0, "j": e1 - e0, "prompt_tokens": mi.get("prompt_tokens"),
                   "cached": mi.get("cached_tokens"), "tok_s": L / (t1 - t0)}
            res["prefill"].append(row)
            print("prefill", L, round(row["s"], 3), "s", round(row["j"], 1), "J", round(row["tok_s"]), "tok/s", flush=True)

    res["decode"] = []
    for L in [int(x) for x in a.ctx_lens.split(",")]:
        for b in [int(x) for x in a.batches.split(",")]:
            if b * (L + a.gen) > 0.9 * pool:
                continue
            flush()
            prompts = [ids(L, 7919 * L + 31 * b + i) for i in range(b)]
            with cf.ThreadPoolExecutor(b) as ex:          # prefill them (cached afterwards)
                list(ex.map(lambda q: gen(q, 1), prompts))
            t0, e0 = time.monotonic(), energy()
            with cf.ThreadPoolExecutor(b) as ex:
                outs = list(ex.map(lambda q: gen(q, a.gen), prompts))
            t1, e1 = time.monotonic(), energy()
            toks = sum(o.get("completion_tokens") or 0 for o in outs)
            row = {"L": L, "batch": b, "wall_s": t1 - t0, "energy_j": e1 - e0, "tokens": toks,
                   "tok_s": toks / (t1 - t0), "step_s": (t1 - t0) / a.gen, "j_per_tok": (e1 - e0) / toks,
                   "avg_power_w": (e1 - e0) / (t1 - t0),
                   "cached_min": min((o.get("cached_tokens") or 0) for o in outs)}
            res["decode"].append(row)
            print("decode L", L, "b", b, "step", round(row["step_s"] * 1000, 1), "ms", round(row["j_per_tok"], 3),
                  "J/tok", round(row["avg_power_w"]), "W", flush=True)
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()

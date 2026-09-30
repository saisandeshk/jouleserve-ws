"""Calibrate the basic serving costs of one SGLang server on one GPU (WS: NVML energy).

Measures, with nothing else running on that GPU:
  - idle power;
  - cold prefill time and energy vs prompt length (cache flushed before each request);
  - warm (fully cached) prefill for the same prompts;
  - decode time and energy per token vs batch size (concurrent requests, ignore_eos).

Usage: python -m jsw.costs.calibrate --base-url http://127.0.0.1:30001/v1 --gpu 0 --out <file.json>
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import random
import time
import urllib.request

import pynvml
from openai import OpenAI

WORDS = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november "
         "oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee zulu drone "
         "altitude waypoint battery sensor camera tower survey depot road node yaw pitch").split()


def energy_j(h):
    return pynvml.nvmlDeviceGetTotalEnergyConsumption(h) / 1000.0


def text(n_words, seed):
    rng = random.Random(seed)
    return " ".join(rng.choice(WORDS) for _ in range(n_words))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--gpu", type=int, required=True)
    ap.add_argument("--model", default="IFM/K2-Horizon-7B")
    ap.add_argument("--out", required=True)
    ap.add_argument("--reps", type=int, default=3)
    a = ap.parse_args()
    pynvml.nvmlInit()
    h = pynvml.nvmlDeviceGetHandleByIndex(a.gpu)
    c = OpenAI(base_url=a.base_url, api_key="EMPTY", timeout=600, max_retries=0)
    base = a.base_url.rsplit("/v1", 1)[0]

    def flush():
        urllib.request.urlopen(urllib.request.Request(base + "/flush_cache", data=b"", method="POST"),
                               timeout=30).read()
        time.sleep(1.0)

    def one(prompt, max_tokens=1, ignore_eos=False):
        t0, e0 = time.monotonic(), energy_j(h)
        r = c.chat.completions.create(
            model=a.model, messages=[{"role": "user", "content": prompt}], max_tokens=max_tokens,
            temperature=0.0, extra_body={"chat_template_kwargs": {"reasoning_effort": "low"},
                                         "ignore_eos": ignore_eos})
        t1, e1 = time.monotonic(), energy_j(h)
        d = r.usage.prompt_tokens_details
        return {"s": t1 - t0, "j": e1 - e0, "prompt_tokens": r.usage.prompt_tokens,
                "cached": d.cached_tokens if d else None, "completion": r.usage.completion_tokens}

    res = {"gpu": a.gpu, "base_url": a.base_url, "t_wall": time.time()}

    # Idle power (server loaded, no requests).
    time.sleep(5)
    p = []
    for _ in range(100):
        p.append(pynvml.nvmlDeviceGetPowerUsage(h) / 1000.0)
        time.sleep(0.1)
    res["idle_w"] = sum(p) / len(p)
    print("idle_w", res["idle_w"], flush=True)

    one("warm up the kernels " * 50)
    one(text(3000, 999))

    # Cold vs warm prefill.
    res["prefill"] = []
    for n_words in [800, 1600, 3200, 6400, 9600, 12800, 16000]:
        for rep in range(a.reps):
            prompt = text(n_words, 1000 * n_words + rep)
            flush()
            cold = one(prompt)
            warm = one(prompt)
            row = {"n_words": n_words, "rep": rep, "cold": cold, "warm": warm}
            res["prefill"].append(row)
            print("prefill", n_words, cold["prompt_tokens"], round(cold["s"], 3),
                  round(cold["j"], 1), "| warm", warm["cached"], round(warm["s"], 3), flush=True)

    # Decode vs batch size.
    res["decode"] = []
    gen = 512
    for b in [1, 2, 4, 8, 16]:
        flush()
        prompts = [text(80, 50000 + b * 100 + i) for i in range(b)]
        t0, e0 = time.monotonic(), energy_j(h)
        with cf.ThreadPoolExecutor(b) as ex:
            outs = list(ex.map(lambda q: one(q, max_tokens=gen, ignore_eos=True), prompts))
        t1, e1 = time.monotonic(), energy_j(h)
        toks = sum(o["completion"] for o in outs)
        row = {"batch": b, "wall_s": t1 - t0, "energy_j": e1 - e0, "tokens": toks,
               "tok_s": toks / (t1 - t0), "j_per_tok": (e1 - e0) / toks,
               "avg_power_w": (e1 - e0) / (t1 - t0)}
        res["decode"].append(row)
        print("decode", row, flush=True)

    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()

"""Decode cost against width on Thor-2 (CAND-T2's calibration), with the design of the mentor's T1/O1 cost curves.

For each context (4K, 16K tokens) and width k (1, 2, 4, 8, 16), twice: flush the cache, prefill one shared prompt,
then send k concurrent requests forced to 2,048 output tokens (ignore_eos). Board energy over each k-request window
comes from P5's sampler (jsw/telemetry/jetson.py, P1's power fields, Thor VIN). Stdlib only.

    python3 costcurve.py --server http://127.0.0.1:30101 --model granite --out /media/hdd/p5/runs/costcurve-granite
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
JETSON = "/media/hdd/p5/jsw-dev/jsw/telemetry/jetson.py"


def post(url, body, timeout=3600):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def prompt(ctx):
    base = "You are reviewing traffic counts from a roadside camera. Summarise the notes below in one line.\n\n"
    pad = "camera log entry: vehicles counted, lane clear, signal cycle normal, no incident reported.\n" * 4000
    return base + pad[: ctx * 4 - len(base)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ks", default="1,2,4,8,16")
    ap.add_argument("--ctx", default="4096,16384")
    ap.add_argument("--out-tokens", type=int, default=2048)
    ap.add_argument("--reps", type=int, default=2)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    samples = os.path.join(a.out, "device_samples.jsonl")
    pid = os.path.join(a.out, "sampler.pid")
    sp = subprocess.Popen([sys.executable, JETSON, "sample", "--out", samples, "--interval", "180", "--pidfile", pid])
    time.sleep(5)
    sys.path.insert(0, os.path.dirname(JETSON))
    import jetson  # noqa: E402
    windows = []
    for ctx in [int(x) for x in a.ctx.split(",")]:
        msgs = [{"role": "user", "content": prompt(ctx)}]
        for k in [int(x) for x in a.ks.split(",")]:
            for rep in range(a.reps):
                post(a.server + "/flush_cache", {})
                time.sleep(2)
                post(a.server + "/v1/chat/completions", {"model": a.model, "messages": msgs, "max_tokens": 1})
                res = [None] * k

                def one(i):
                    res[i] = post(a.server + "/v1/chat/completions", {
                        "model": a.model, "messages": msgs, "max_tokens": a.out_tokens, "ignore_eos": True,
                        "temperature": 1.0, "top_p": 0.95, "seed": 1000 + i})
                th = [threading.Thread(target=one, args=(i,)) for i in range(k)]
                t0 = time.time()
                for t in th:
                    t.start()
                for t in th:
                    t.join()
                t1 = time.time()
                gen = sum(((r or {}).get("usage") or {}).get("completion_tokens") or 0 for r in res)
                windows.append(dict(ctx=ctx, k=k, rep=rep, t0=t0, t1=t1, gen_tokens=gen,
                                    cached=[((r or {}).get("usage") or {}).get("prompt_tokens_details") for r in res][:1]))
                print(json.dumps(windows[-1]), flush=True)
    time.sleep(3)
    try:
        os.kill(int(open(pid).read()), 15)
    except Exception:
        sp.terminate()
    sp.wait(timeout=30)
    rows = jetson.load(samples)
    with open(os.path.join(a.out, "costcurve.jsonl"), "w") as f:
        for w in windows:
            e = jetson.board_energy(rows, w["t0"], w["t1"])
            ej = e.get("energy_J") if isinstance(e, dict) else e
            steps = w["gen_tokens"] / w["k"] if w["k"] else 0
            rec = dict(model=a.model, ctx=w["ctx"], k=w["k"], rep=w["rep"], wall_s=w["t1"] - w["t0"], energy_j=ej,
                       gen_tokens=w["gen_tokens"], j_per_token=(ej / w["gen_tokens"]) if ej and w["gen_tokens"] else None,
                       j_per_step=(ej / steps) if ej and steps else None,
                       s_per_step=((w["t1"] - w["t0"]) / steps) if steps else None, energy_detail=e)
            f.write(json.dumps(rec, default=str) + "\n")
    print("DONE", os.path.join(a.out, "costcurve.jsonl"))


if __name__ == "__main__":
    main()

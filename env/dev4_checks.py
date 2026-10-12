"""DEV-4's API checks of our stack against a Jetson's SGLang 0.5.16 server (planning/OPTIONS_PLAN.md §4.1). Stdlib only.

    python env/dev4_checks.py http://<ip>:30000 [--out <file.json>]

1. /generate with input_ids, ignore_eos and max_new_tokens returns exactly the requested output length;
2. a prompt that extends the previous one hits the cache (cached tokens = the shared prefix), fresh IDs do not;
3. the /metrics names our runner and analyses read exist;
4. /flush_cache works with P1's verified-empty check (env/jetson_preflight.flush_verified);
5. a client that disconnects mid-generation aborts its request (num_running_reqs back to 0).
"""
from __future__ import annotations

import argparse
import json
import random
import socket
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jetson_preflight import flush_verified, http, metrics  # noqa: E402

NAMES = ("num_running_reqs", "num_queue_reqs", "num_used_tokens", "token_usage", "max_total_num_tokens",
         "evicted_tokens_total", "num_retracted_reqs", "kv_used_tokens", "kv_evictable_tokens", "cache_hit_rate",
         "prompt_tokens_total", "generation_tokens_total")


def gen(s, ids, n):
    st, body = http(s + "/generate", {"input_ids": ids, "sampling_params": {"max_new_tokens": n, "ignore_eos": True,
                                                                           "temperature": 0}}, timeout=900)
    j = json.loads(body)
    m = j.get("meta_info", {})
    return {"status": st, "out": m.get("completion_tokens"), "prompt": m.get("prompt_tokens"),
            "cached": m.get("cached_tokens"), "ids": j.get("output_ids") or []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("server")
    ap.add_argument("--out")
    a = ap.parse_args()
    s, rng, res = a.server.rstrip("/"), random.Random(5), {}
    assert flush_verified(s), "initial flush failed"
    p1 = [rng.randrange(1000, 30000) for _ in range(1500)]
    r1 = gen(s, p1, 64)
    p2 = p1 + r1["ids"] + [rng.randrange(1000, 30000) for _ in range(300)]
    r2 = gen(s, p2, 32)
    r3 = gen(s, [rng.randrange(1000, 30000) for _ in range(1500)], 16)
    res["1_exact_lengths"] = {"ok": (r1["out"], r2["out"], r3["out"]) == (64, 32, 16),
                              "out": [r1["out"], r2["out"], r3["out"]], "prompt": [r1["prompt"], r2["prompt"], r3["prompt"]]}
    res["2_cache"] = {"ok": r1["cached"] == 0 and r2["cached"] >= len(p1) and r3["cached"] == 0,
                      "cached": [r1["cached"], r2["cached"], r3["cached"]], "shared_prefix": len(p1) + len(r1["ids"])}
    text = http(s + "/metrics")[1]
    present = {n: any(l.startswith(f"sglang:{n}") for l in text.splitlines()) for n in NAMES}
    res["3_metrics"] = {"ok": all(present[n] for n in ("num_running_reqs", "num_queue_reqs", "num_used_tokens")),
                        "present": present}
    res["4_flush"] = {"ok": flush_verified(s), "used_after": metrics(s).get("num_used_tokens")}
    # 5: raw HTTP request for a long generation, read the first bytes of the stream, then drop the socket
    u = urllib.parse.urlparse(s)
    body = json.dumps({"input_ids": [rng.randrange(1000, 30000) for _ in range(200)], "stream": True,
                       "sampling_params": {"max_new_tokens": 4000, "ignore_eos": True}}).encode()
    sock = socket.create_connection((u.hostname, u.port), timeout=60)
    sock.sendall(b"POST /generate HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\nContent-Length: "
                 + str(len(body)).encode() + b"\r\n\r\n" + body)
    sock.recv(4096)
    time.sleep(3)
    running_before = metrics(s).get("num_running_reqs")
    sock.close()
    t0, running_after = time.monotonic(), None
    while time.monotonic() - t0 < 30:
        time.sleep(1)
        running_after = metrics(s).get("num_running_reqs")
        if running_after == 0:
            break
    res["5_abort"] = {"ok": running_before == 1 and running_after == 0, "running_before": running_before,
                      "running_after": running_after, "seconds": round(time.monotonic() - t0, 1)}
    res["ok"] = all(v["ok"] for v in res.values() if isinstance(v, dict))
    txt = json.dumps(res, indent=1)
    if a.out:
        Path(a.out).write_text(txt)
    print(txt)
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

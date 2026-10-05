"""Smoke test for a model served by env/launch_model.sh (OPTIONS_PLAN.md S1), plus the S2/S3 engine checks.

Usage (WS, legacy venv): python env/smoke_model.py <port> [--image] [--tools] [--out smoke.json]
Checks: server info and pool sizes; chat with thinking on and off; a tool call; an image (multimodal models);
/generate with token IDs, ignore_eos and exact output length (does it return output IDs?); abort on client
disconnect and via /abort_request; the /metrics names for pools. Prints a JSON report.
"""
import argparse
import base64
import io
import json
import threading
import time
import uuid

import requests


def metrics(base):
    out = {}
    for line in requests.get(base + "/metrics", timeout=5).text.splitlines():
        if line.startswith("sglang:") and "_bucket{" not in line:
            k, _, v = line.rpartition(" ")
            try:
                out[k.split("{")[0]] = float(v)
            except ValueError:
                pass
    return out


def chat(base, model, messages, **kw):
    t = time.time()
    r = requests.post(base + "/v1/chat/completions", json=dict(model=model, messages=messages, **kw), timeout=600)
    r.raise_for_status()
    j = r.json()
    m = j["choices"][0]["message"]
    return dict(s=round(time.time() - t, 2), finish=j["choices"][0]["finish_reason"], usage=j.get("usage"),
                content=(m.get("content") or "")[:300], reasoning=(m.get("reasoning_content") or "")[:300],
                reasoning_len=len(m.get("reasoning_content") or ""), tool_calls=m.get("tool_calls"))


def image_b64():
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (640, 360), (40, 40, 40))
    d = ImageDraw.Draw(im)
    d.rectangle([60, 200, 260, 300], fill=(200, 30, 30))     # a red "car"
    d.rectangle([380, 220, 520, 290], fill=(30, 60, 200))    # a blue "car"
    d.line([0, 320, 640, 320], fill=(220, 220, 220), width=6)
    buf = io.BytesIO()
    im.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port", type=int)
    ap.add_argument("--image", action="store_true")
    ap.add_argument("--tools", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    base = f"http://127.0.0.1:{a.port}"
    rep = {}
    info = requests.get(base + "/get_server_info", timeout=10).json()
    model = requests.get(base + "/v1/models", timeout=10).json()["data"][0]["id"]
    keep = ("max_total_num_tokens", "context_length", "mem_fraction_static", "attention_backend", "kv_cache_dtype",
            "swa_full_tokens_ratio", "is_hybrid", "max_running_requests", "page_size", "quantization",
            "chunked_prefill_size", "model_path", "version")
    rep["server"] = {k: v for k, v in info.items() if k in keep}
    for k, v in info.items():
        if isinstance(v, (int, float)) and any(s in k for s in ("token", "swa", "pool")) and k not in rep["server"]:
            rep["server"][k] = v
    if "internal_states" in info:
        st = info["internal_states"][0] if isinstance(info["internal_states"], list) else info["internal_states"]
        rep["internal"] = {k: v for k, v in st.items() if isinstance(v, (int, float, str)) and len(str(v)) < 80}
    rep["model"] = model
    m0 = metrics(base)
    rep["metrics_names"] = sorted(k for k in m0 if any(s in k for s in ("token", "swa", "usage", "cache", "running")))

    q = [{"role": "user", "content": "A drone is at (0,0,0). It flies 5 m north then 3 m east. Where is it? Be brief."}]
    rep["chat_think"] = chat(base, model, q, max_tokens=1024, temperature=0,
                             chat_template_kwargs={"enable_thinking": True})
    rep["chat_nothink"] = chat(base, model, q, max_tokens=256, temperature=0,
                               chat_template_kwargs={"enable_thinking": False})
    if a.tools:
        tools = [{"type": "function", "function": {
            "name": "go_to_point", "description": "Fly the drone to a point (metres).",
            "parameters": {"type": "object", "properties": {"x": {"type": "number"}, "y": {"type": "number"},
                                                            "z": {"type": "number"}}, "required": ["x", "y", "z"]}}}]
        tq = [{"role": "user", "content": "Fly the drone to x=5, y=3 at 10 m altitude (z=10)."}]
        for think in (True, False):
            rep[f"tool_think={think}"] = chat(base, model, tq, tools=tools, max_tokens=1024, temperature=0,
                                              chat_template_kwargs={"enable_thinking": think})
    if a.image:
        iq = [{"role": "user", "content": [
            {"type": "text", "text": "How many coloured rectangles are in this image, and what colours? Be brief."},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_b64()}}]}]
        rep["image"] = chat(base, model, iq, max_tokens=256, temperature=0,
                            chat_template_kwargs={"enable_thinking": False})

    # /generate with token IDs: exact lengths, output IDs, prefix reuse
    ids = [int(x) for x in __import__("random").Random(0).sample(range(1000, 20000), 2000)]
    g = requests.post(base + "/generate", json={"input_ids": ids, "sampling_params": {
        "max_new_tokens": 300, "ignore_eos": True, "temperature": 0}}, timeout=300).json()
    g0 = g[0] if isinstance(g, list) else g
    mi = g0.get("meta_info", {})
    rep["generate"] = dict(keys=sorted(g0.keys()), meta=sorted(mi.keys()), prompt_tokens=mi.get("prompt_tokens"),
                           completion_tokens=mi.get("completion_tokens"), cached=mi.get("cached_tokens"),
                           has_output_ids="output_ids" in g0, n_output_ids=len(g0.get("output_ids") or []))
    if g0.get("output_ids"):
        g2 = requests.post(base + "/generate", json={"input_ids": ids + g0["output_ids"] + ids[:500],
                           "sampling_params": {"max_new_tokens": 50, "ignore_eos": True, "temperature": 0}},
                           timeout=300).json()
        g2 = g2[0] if isinstance(g2, list) else g2
        rep["generate_followup"] = dict(prompt_tokens=g2["meta_info"].get("prompt_tokens"),
                                        cached=g2["meta_info"].get("cached_tokens"),
                                        completion_tokens=g2["meta_info"].get("completion_tokens"))

    # abort on client disconnect (streaming)
    def running():
        return metrics(base).get("sglang:num_running_reqs", -1)

    body = {"model": model, "messages": q, "max_tokens": 8000, "stream": True, "temperature": 0,
            "chat_template_kwargs": {"enable_thinking": True}}
    r = requests.post(base + "/v1/chat/completions", json=body, stream=True, timeout=60)
    t0, n = time.time(), 0
    for _ in r.iter_lines():
        n += 1
        if time.time() - t0 > 2:
            break
    run_before = running()
    r.close()
    time.sleep(2)
    rep["abort_on_disconnect"] = dict(chunks=n, running_before_close=run_before, running_after_close=running())

    # abort by rid
    rid = "smoke-" + uuid.uuid4().hex[:8]
    th = threading.Thread(target=lambda: requests.post(base + "/generate", json={
        "input_ids": ids, "rid": rid, "sampling_params": {"max_new_tokens": 6000, "ignore_eos": True}}, timeout=600))
    th.start()
    time.sleep(2)
    before = running()
    ab = requests.post(base + "/abort_request", json={"rid": rid}, timeout=10)
    th.join(timeout=30)
    rep["abort_request"] = dict(status=ab.status_code, running_before=before, running_after=running(),
                                thread_done=not th.is_alive())
    rep["metrics_after"] = {k: v for k, v in metrics(base).items()
                            if any(s in k for s in ("token_usage", "swa", "num_used", "max_total", "cache_hit"))}
    s = json.dumps(rep, indent=1, default=str)
    print(s)
    if a.out:
        open(a.out, "w").write(s)


if __name__ == "__main__":
    main()

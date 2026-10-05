"""S2 tests: the gateway against a fake SGLang (OpenAI streaming + /generate + /metrics + /abort_request).

Run (WS, legacy venv has aiohttp): python -m tests.test_gateway
"""
import asyncio
import json
import tempfile
import time
from pathlib import Path

import aiohttp
from aiohttp import web

from jsw.gateway.server import Gateway, load_policy, make_app

LOOP = "the drone moves north and checks the corner. "


class FakeSGLang:
    """Streams reasoning, content and one tool call; a request whose last message contains LOOP streams a loop
    until the client disconnects (or 4,000 chunks) unless it is sampled (temperature > 0)."""

    def __init__(self):
        self.aborts, self.disconnects, self.requests = [], 0, []

    async def chat(self, request):
        body = await request.json()
        self.requests.append(body)
        resp = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await resp.prepare(request)

        async def send(delta=None, finish=None, usage=None):
            j = {"id": body.get("rid"), "object": "chat.completion.chunk", "model": body.get("model"),
                 "choices": [] if usage else [{"index": 0, "delta": delta or {}, "finish_reason": finish}]}
            if usage:
                j["usage"] = usage
            await resp.write(b"data: " + json.dumps(j).encode() + b"\n\n")

        looping = LOOP in json.dumps(body.get("messages")) and not body.get("temperature")
        try:
            if looping:
                for i in range(4000):
                    await send({"reasoning_content": LOOP})
                    await asyncio.sleep(0)
                await send(finish="length")
            else:
                for w in ["Let ", "me ", "think. "]:
                    await send({"reasoning_content": w})
                for w in ["Flying ", "now."]:
                    await send({"content": w})
                await send({"tool_calls": [{"index": 0, "id": "c1", "type": "function",
                                            "function": {"name": "go_to_point", "arguments": "{\"x\": "}}]})
                await send({"tool_calls": [{"index": 0, "function": {"arguments": "5}"}}]})
                await send(finish="tool_calls")
            await send(usage={"prompt_tokens": 11, "completion_tokens": 9,
                              "prompt_tokens_details": {"cached_tokens": 4}})
            await resp.write(b"data: [DONE]\n\n")
        except (ConnectionResetError, asyncio.CancelledError):
            self.disconnects += 1
            raise
        return resp

    async def generate(self, request):
        body = await request.json()
        n = body["sampling_params"]["max_new_tokens"]
        return web.json_response({"text": "x", "output_ids": list(range(n)), "meta_info": {
            "prompt_tokens": len(body["input_ids"]), "completion_tokens": n, "cached_tokens": 0,
            "finish_reason": {"type": "length"}}})

    async def metrics(self, request):
        return web.Response(text="sglang:num_running_reqs{model_name=\"m\"} 1.0\nsglang:token_usage 0.25\n")

    async def abort(self, request):
        self.aborts.append((await request.json()).get("rid"))
        return web.json_response({})

    def app(self):
        a = web.Application()
        a.router.add_post("/v1/chat/completions", self.chat)
        a.router.add_post("/generate", self.generate)
        a.router.add_get("/metrics", self.metrics)
        a.router.add_post("/abort_request", self.abort)
        return a


async def _serve(app, port):
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", port).start()
    return runner


async def main():
    fake = FakeSGLang()
    up = await _serve(fake.app(), 39001)
    log_dir = Path(tempfile.mkdtemp())
    pol = load_policy("jsw.policies.decode_guard:DecodeGuard", {"action": "resample", "max_consecutive_caps": 2})
    gw = Gateway("http://127.0.0.1:39001", log_dir, pol, tick_s=0.1)
    gwr = await _serve(make_app(gw), 39002)
    base = "http://127.0.0.1:39002"
    async with aiohttp.ClientSession() as s:
        # 1. non-streaming client: aggregated response
        async with s.post(base + "/s/a/v1/chat/completions",
                          json={"model": "m", "messages": [{"role": "user", "content": "go"}]}) as r:
            j = await r.json()
        m = j["choices"][0]["message"]
        assert m["reasoning_content"] == "Let me think. " and m["content"] == "Flying now.", m
        assert m["tool_calls"][0]["function"] == {"name": "go_to_point", "arguments": "{\"x\": 5}"}, m
        assert j["choices"][0]["finish_reason"] == "tool_calls" and j["usage"]["completion_tokens"] == 9
        # 2. streaming client: chunks pass through, [DONE] at the end
        async with s.post(base + "/s/a/v1/chat/completions",
                          json={"model": "m", "stream": True, "messages": [{"role": "user", "content": "go"}]}) as r:
            raw = (await r.read()).decode()
        assert raw.count("data: ") >= 8 and raw.rstrip().endswith("data: [DONE]"), raw[-200:]
        # 3. looping call: the guard stops it, aborts upstream and retries with sampling
        t0 = time.monotonic()
        async with s.post(base + "/s/b/v1/chat/completions",
                          json={"model": "m", "temperature": 0, "messages": [{"role": "user", "content": LOOP}]}) as r:
            j = await r.json()
        assert j["gateway"]["attempts"] == 2 and j["choices"][0]["message"]["content"] == "Flying now.", j
        assert fake.requests[-1]["temperature"] == 1.0 and fake.requests[-1]["top_k"] == 64
        await asyncio.sleep(0.2)
        assert len(fake.aborts) == 1, fake.aborts
        stop_s = time.monotonic() - t0
        # 4. consecutive caps: truncate-mode guard ends the session after 2 capped calls
        gw.policy = pol2 = load_policy("jsw.policies.decode_guard:DecodeGuard",
                                       {"action": "truncate", "max_consecutive_caps": 2})
        pol2.attach(gw)
        for i in range(2):
            async with s.post(base + "/s/c/v1/chat/completions",
                              json={"model": "m", "messages": [{"role": "user", "content": LOOP}]}) as r:
                j = await r.json()
            assert j["choices"][0]["finish_reason"] == "length", j
        async with s.post(base + "/s/c/v1/chat/completions",
                          json={"model": "m", "messages": [{"role": "user", "content": "go"}]}) as r:
            j = await r.json()
        assert j["error"]["type"] == "gateway_stop", j
        # 5. /generate passthrough and overhead
        async with s.post(base + "/s/d/generate", json={"input_ids": [1, 2, 3], "sampling_params": {
                "max_new_tokens": 5, "ignore_eos": True}}) as r:
            j = await r.json()
        assert j["meta_info"]["completion_tokens"] == 5 and len(j["output_ids"]) == 5

        async def timed(url, n=200):
            t = time.perf_counter()
            for _ in range(n):
                async with s.post(url, json={"input_ids": [1], "sampling_params": {"max_new_tokens": 1}}) as r:
                    await r.read()
            return (time.perf_counter() - t) / n

        direct, via = await timed("http://127.0.0.1:39001/generate"), await timed(base + "/s/d/generate")
        async with s.get(base + "/gateway/status") as r:
            st = await r.json()
    await gwr.cleanup()
    await up.cleanup()
    calls = [json.loads(x) for x in open(log_dir / "calls.jsonl")]
    stopped = [c for c in calls if c["stopped_by"] == "loop"]
    assert stopped and stopped[0]["meta"]["loop_fired_char"] and stopped[0]["chunks"] < 4000
    print(json.dumps({"ok": True, "calls_logged": len(calls), "loop_stop_s": round(stop_s, 3),
                      "loop_fired_char": stopped[0]["meta"]["loop_fired_char"],
                      "overhead_ms_per_call": round((via - direct) * 1000, 3), "direct_ms": round(direct * 1000, 3),
                      "metrics_seen": bool(gw.metrics), "sessions": list(st["sessions"])}, indent=1))


if __name__ == "__main__":
    asyncio.run(main())

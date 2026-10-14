"""First-of-k in the gateway (jsw/gateway/server.py) against a fake SGLang whose candidates either finish or loop.

Run (WS, legacy venv has aiohttp): python -m tests.test_first_of_k
"""
import asyncio
import json
import tempfile
from pathlib import Path

import aiohttp
from aiohttp import web

from jsw.gateway.server import Gateway, Policy, make_app
from tests.test_gateway import _serve


class FakeK:
    """A sampled request whose seed is even loops (2,000 chunks, then "length"); an odd seed finishes after a short
    pause with a tool call. A request with "all-loop" in it always loops."""

    def __init__(self):
        self.requests, self.aborts, self.disconnects = [], [], 0

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

        loops = body.get("seed", 0) % 2 == 0 or "all-loop" in json.dumps(body.get("messages"))
        try:
            if loops:
                for _ in range(2000):
                    await send({"reasoning_content": "again "})
                    await asyncio.sleep(0.001)
                await send(finish="length")
                await send(usage={"prompt_tokens": 5, "completion_tokens": 2000})
            else:
                await asyncio.sleep(0.05)
                await send({"reasoning_content": "ok. "})
                await send({"tool_calls": [{"index": 0, "id": "c1", "type": "function",
                                            "function": {"name": "get_traffic_series", "arguments": "{}"}}]})
                await send(finish="tool_calls")
                await send(usage={"prompt_tokens": 5, "completion_tokens": 3})
            await resp.write(b"data: [DONE]\n\n")
        except (ConnectionResetError, asyncio.CancelledError):
            self.disconnects += 1
            raise
        return resp

    async def abort(self, request):
        self.aborts.append((await request.json()).get("rid"))
        return web.json_response({})

    async def metrics(self, request):
        return web.Response(text="")

    def app(self):
        a = web.Application()
        a.router.add_post("/v1/chat/completions", self.chat)
        a.router.add_post("/abort_request", self.abort)
        a.router.add_get("/metrics", self.metrics)
        return a


async def main():
    fake = FakeK()
    up = await _serve(fake.app(), 39011)
    log_dir = Path(tempfile.mkdtemp())
    sampling = {"temperature": 1.0, "top_p": 0.95, "top_k": 64}
    gw = Gateway("http://127.0.0.1:39011", log_dir, Policy(), tick_s=0.1, first_of_k=4, sampling=sampling)
    gwr = await _serve(make_app(gw), 39012)
    base = "http://127.0.0.1:39012"
    async with aiohttp.ClientSession() as s:
        # 1. non-streaming: a finishing candidate wins; the sampling override and distinct seeds reach the server
        body = {"model": "m", "temperature": 0, "top_p": 1.0, "seed": 42, "messages": [{"role": "user", "content": "q"}]}
        async with s.post(base + "/s/a/v1/chat/completions", json=body) as r:
            j = await r.json()
        assert j["choices"][0]["finish_reason"] == "tool_calls", j
        assert j["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "get_traffic_series", j
        assert j["gateway"]["candidates"] == 4, j
        sent = fake.requests[-4:]
        assert all(x["temperature"] == 1.0 and x["top_k"] == 64 for x in sent), sent
        assert len({x["seed"] for x in sent}) == 4, [x["seed"] for x in sent]
        # 2. streaming client: the winner's own chunks, then [DONE]
        async with s.post(base + "/s/b/v1/chat/completions", json=dict(body, stream=True)) as r:
            raw = (await r.read()).decode()
        assert "get_traffic_series" in raw and raw.rstrip().endswith("data: [DONE]"), raw[-300:]
        assert "again" not in raw, "a looping candidate's text reached the client"
        # 3. every candidate loops: the first to end wins, capped
        async with s.post(base + "/s/c/v1/chat/completions",
                          json=dict(body, messages=[{"role": "user", "content": "all-loop"}])) as r:
            j = await r.json()
        assert j["choices"][0]["finish_reason"] == "length", j
    await asyncio.sleep(0.3)
    await gwr.cleanup()
    await up.cleanup()
    calls = [json.loads(x) for x in open(log_dir / "calls.jsonl")]
    by = {}
    for c in calls:
        by.setdefault((c["sid"], c["index"]), []).append(c)
    for key, cs in by.items():
        assert len(cs) == 4 and sum(c["meta"]["winner"] for c in cs) == 1, (key, cs)
    lost = [c for c in calls if c["stopped_by"] == "lost_race"]
    assert lost, "no candidate was cancelled"
    print(json.dumps({"ok": True, "calls_logged": len(calls), "cancelled": len(lost), "aborts_sent": len(fake.aborts),
                      "disconnects_seen": fake.disconnects}, indent=1))


if __name__ == "__main__":
    asyncio.run(main())

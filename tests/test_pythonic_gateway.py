"""Gateway "first" fallback end to end: a fake engine streams a Python-text call and then imagines the result."""
import asyncio
import json
import tempfile
from pathlib import Path

import aiohttp
from aiohttp import web

from jsw.gateway.server import Gateway, make_app
from jsw.policies.base import Policy

TOOLS = [{"type": "function", "function": {"name": n, "parameters": {"type": "object", "properties": p}}}
         for n, p in (("connect", {"namespace": {"type": "string"}}), ("arm", {}), ("takeoff", {"height": {}, "speed": {}}))]
SCRIPTS = {
    "mark": [{"reasoning_content": "plan "}, {"content": "connect(namespace=\"drone0\")\n"}, {"content": "<|channel>thought\nI have"}],
    "arrow": [{"reasoning_content": "plan "}, {"content": "connect(namespace=\"drone0\")"}, {"content": "\n"}, {"content": "-> {\"status\""}],
    "nameless": [{"reasoning_content": "plan "}, {"content": "connect(namespace=\"drone0\")\n"},
                 {"content": "<|channel>thought", "tool_calls": [{"index": 0, "function": {"arguments": ""}}]}],
    "split": [{"content": "connect(names"}, {"content": "pace=\"drone0\")\narm()\n"}, {"content": "takeoff(height=5, speed=1.0)\n-"}],
}


async def fake(request):
    body = await request.json()
    script = SCRIPTS[body["messages"][0]["content"]]
    resp = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
    await resp.prepare(request)
    try:
        for d in script:
            await resp.write(b"data: " + json.dumps({"choices": [{"index": 0, "delta": d}]}).encode() + b"\n\n")
            await asyncio.sleep(0.01)
        await resp.write(b"data: " + json.dumps({"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}).encode() + b"\n\n")
        await resp.write(b"data: [DONE]\n\n")
    except Exception:
        pass
    return resp


async def main():
    up = web.Application(); up.router.add_post("/v1/chat/completions", fake)
    async def m(r): return web.Response(text="")
    up.router.add_get("/metrics", m)
    async def ab(r): return web.json_response({})
    up.router.add_post("/abort_request", ab)
    r1 = web.AppRunner(up); await r1.setup(); await web.TCPSite(r1, "127.0.0.1", 39011).start()
    gw = Gateway("http://127.0.0.1:39011", Path(tempfile.mkdtemp()), Policy(), pythonic_fallback="first")
    r2 = web.AppRunner(make_app(gw)); await r2.setup(); await web.TCPSite(r2, "127.0.0.1", 39012).start()
    async with aiohttp.ClientSession() as s:
        for name in SCRIPTS:
            async with s.post("http://127.0.0.1:39012/s/x/v1/chat/completions",
                              json={"model": "m", "tools": TOOLS, "messages": [{"role": "user", "content": name}]}) as r:
                j = await r.json()
            msg = j["choices"][0]["message"]
            print(name, "->", j["choices"][0]["finish_reason"], [t["function"] for t in msg.get("tool_calls") or []],
                  repr(msg.get("content")), j["gateway"])
    await r2.cleanup(); await r1.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

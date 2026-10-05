"""JouleServe gateway v0: a session-aware OpenAI-compatible proxy in front of SGLang (OPTIONS_PLAN.md S2).

    python -m jsw.gateway.server --upstream http://127.0.0.1:30000 --port 31000 --log-dir ~/work/runs/<run>/gw \
        [--policy jsw.policies.decode_guard:DecodeGuard --policy-args '{"action": "truncate"}']

Routes (sid = any session id chosen by the client; agents only change their base URL):
  POST /s/<sid>/v1/chat/completions       agent calls (streaming or not)
  POST /s/<sid>/tool/v1/chat/completions  calls made by a tool on the agent's behalf (e.g. a vision burst); tagged
  POST /s/<sid>/generate                  SGLang's native API (used by the trace replayer)
  POST /s/<sid>/event                     driver events, e.g. {"kind": "tool_start", "tool": "ask_vlm"}
  POST /v1/chat/completions, /generate    as above, session "anon"
  GET  /v1/models, /metrics, /health, /get_server_info, ...   passed through; POST /flush_cache, /abort_request too
Chat calls are always streamed from SGLang, so a policy can watch every token (on_chunk) and stop a call; a client
that did not ask for a stream gets one aggregated response. Every call (and every retry) is logged to
<log-dir>/calls.jsonl with its timings and token counts; driver events go to <log-dir>/events.jsonl.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib
import itertools
import json
import time
import uuid
from pathlib import Path

import aiohttp
from aiohttp import web

from jsw.gateway import pythonic
from jsw.policies.base import STOP, Policy


class Session:
    def __init__(self, sid):
        self.sid, self.phase, self.tool = sid, "new", None
        self.n_calls, self.t_last_end, self.t_tool_start = 0, None, None
        self.open_calls = 0


class Call:
    _ids = itertools.count()

    def __init__(self, session, route, tag, body, client_stream):
        self.session, self.route, self.tag, self.body = session, route, tag, body
        self.client_stream = client_stream
        self.call_id = next(Call._ids)
        self.index = session.n_calls
        self.attempt = 0
        self.t_req = time.monotonic()
        self.held_s = 0.0
        self.reset()

    def reset(self):
        self.rid = f"gw-{self.session.sid}-{self.call_id}-{self.attempt}-{uuid.uuid4().hex[:6]}"
        self.t_sent = self.t_first = self.t_last = None
        self.reasoning, self.content, self.args = [], [], {}
        self.tool_calls = {}
        self.finish_reason, self.usage, self.status, self.error = None, None, None, None
        self.stopped_by, self.chunks, self.chars = None, 0, 0
        self.meta = None

    @property
    def text(self):
        return "".join(self.reasoning) + "".join(self.content) + "".join(
            (tc.get("function") or {}).get("arguments") or "" for tc in self.tool_calls.values())

    def record(self):
        u = self.usage or {}
        return dict(
            sid=self.session.sid, call_id=self.call_id, index=self.index, attempt=self.attempt, route=self.route,
            tag=self.tag, rid=self.rid, t_req=self.t_req, t_sent=self.t_sent, t_first=self.t_first, t_last=self.t_last,
            held_s=round(self.held_s, 4), status=self.status, error=self.error, finish_reason=self.finish_reason,
            stopped_by=self.stopped_by, prompt_tokens=u.get("prompt_tokens"),
            cached_tokens=(u.get("prompt_tokens_details") or {}).get("cached_tokens", u.get("cached_tokens")),
            completion_tokens=u.get("completion_tokens"), reasoning_tokens=u.get("reasoning_tokens"),
            chunks=self.chunks, chars=self.chars, reasoning_chars=sum(map(len, self.reasoning)),
            max_tokens=self.body.get("max_tokens") or (self.body.get("sampling_params") or {}).get("max_new_tokens"),
            temperature=self.body.get("temperature", (self.body.get("sampling_params") or {}).get("temperature")),
            priority=self.body.get("priority"), meta=self.meta,
        )


def _parse_metrics(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        if line.startswith("sglang:") and "_bucket{" not in line:
            k, _, v = line.rpartition(" ")
            try:
                out[k.split("{")[0]] = float(v)
            except ValueError:
                pass
    return out


class Gateway:
    def __init__(self, upstream: str, log_dir: Path, policy: Policy, tick_s: float = 0.5,
                 pythonic_fallback: str = "off"):
        self.upstream, self.policy, self.tick_s = upstream.rstrip("/"), policy, tick_s
        self.pythonic_fallback = pythonic_fallback     # off | all | first (see jsw/gateway/pythonic.py)
        self.log_dir = Path(log_dir).expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: dict[str, Session] = {}
        self.metrics: dict = {}
        self.metrics_t = None
        self._calls_f = open(self.log_dir / "calls.jsonl", "a")
        self._events_f = open(self.log_dir / "events.jsonl", "a")
        policy.attach(self)

    # ------------------------------------------------------------------ plumbing
    async def start(self, app):
        self.http = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=0),
                                          timeout=aiohttp.ClientTimeout(total=None, sock_read=1800))
        self._tick_task = asyncio.create_task(self._tick())
        self.log_event(None, "gateway_start", upstream=self.upstream, pythonic_fallback=self.pythonic_fallback,
                       **self.policy.describe())

    async def stop(self, app):
        self._tick_task.cancel()
        await self.http.close()
        self.log_event(None, "gateway_stop")
        self._calls_f.close()
        self._events_f.close()

    def session(self, sid) -> Session:
        if sid not in self.sessions:
            self.sessions[sid] = Session(sid)
        return self.sessions[sid]

    def log_call(self, call: Call):
        self._calls_f.write(json.dumps(call.record(), default=str) + "\n")
        self._calls_f.flush()

    def log_event(self, sid, kind, **kw):
        self._events_f.write(json.dumps(dict(t_mono=time.monotonic(), t_wall=time.time(), sid=sid, kind=kind, **kw),
                                        default=str) + "\n")
        self._events_f.flush()

    async def _tick(self):
        while True:
            try:
                async with self.http.get(self.upstream + "/metrics") as r:
                    self.metrics = _parse_metrics(await r.text())
                    self.metrics_t = time.monotonic()
                self.policy.on_tick(self.metrics)
            except asyncio.CancelledError:
                raise
            except Exception:
                pass
            await asyncio.sleep(self.tick_s)

    async def abort_upstream(self, rid):
        try:
            async with self.http.post(self.upstream + "/abort_request", json={"rid": rid}) as r:
                await r.read()
        except Exception:
            pass

    # ------------------------------------------------------------------ chat completions
    async def chat(self, request: web.Request):
        sid = request.match_info.get("sid", "anon")
        tag = "tool" if request.match_info.get("tool") else "agent"
        body = await request.json()
        sess = self.session(sid)
        call = Call(sess, "chat", tag, body, bool(body.get("stream")))
        sess.n_calls += 1
        sess.open_calls += 1
        if tag == "agent":
            sess.phase = "llm"
        try:
            t0 = time.monotonic()
            early = await self.policy.on_request(call)
            call.held_s = time.monotonic() - t0
            if isinstance(early, dict):
                call.status, call.stopped_by = "rejected", "policy"
                self.log_call(call)
                return web.json_response(early)
            resp = None
            while True:
                if call.client_stream and resp is None:
                    resp = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
                    await resp.prepare(request)
                await self._chat_upstream(call, resp if call.client_stream else None)
                if self.pythonic_fallback != "off" and not call.client_stream and not call.tool_calls:
                    text = "".join(call.content)
                    tc = pythonic.leading_calls(text, call.body.get("tools"))[0] \
                        if self.pythonic_fallback == "first" else pythonic.parse(text, call.body.get("tools"))
                    if tc:
                        call.tool_calls = dict(enumerate(tc))
                        call.content, call.finish_reason = [], "tool_calls"
                        call.meta = dict(call.meta or {}, pythonic_fallback=len(tc))
                self.log_call(call)
                retry = await self.policy.on_complete(call)
                if not isinstance(retry, dict) or call.client_stream:
                    break
                call.body = retry
                call.attempt += 1
                call.reset()
            if call.client_stream:
                await resp.write(b"data: [DONE]\n\n")
                await resp.write_eof()
                return resp
            if call.status != 200 and call.error:
                return web.json_response({"error": call.error}, status=call.status or 502)
            return web.json_response(self._aggregate(call))
        finally:
            sess.open_calls -= 1
            sess.t_last_end = time.monotonic()
            if tag == "agent" and sess.open_calls == 0:
                sess.phase = "idle"

    async def _chat_upstream(self, call: Call, client):
        body = dict(call.body, stream=True, stream_options={"include_usage": True}, rid=call.rid)
        call.t_sent = time.monotonic()
        try:
            async with self.http.post(self.upstream + "/v1/chat/completions", json=body) as r:
                call.status = r.status
                if r.status != 200:
                    call.error = (await r.text())[:2000]
                    return
                async for raw in r.content:
                    line = raw.strip()
                    if not line.startswith(b"data:"):
                        continue
                    data = line[5:].strip()
                    if data == b"[DONE]":
                        break
                    try:
                        j = json.loads(data)
                    except ValueError:
                        continue
                    if j.get("usage"):
                        call.usage = j["usage"]
                    stop = False
                    for ch in j.get("choices") or []:
                        d = ch.get("delta") or {}
                        pieces = []
                        if d.get("reasoning_content"):
                            call.reasoning.append(d["reasoning_content"])
                            pieces.append(d["reasoning_content"])
                        if d.get("content"):
                            call.content.append(d["content"])
                            pieces.append(d["content"])
                            if self.pythonic_fallback == "first" and not call.tool_calls:
                                _, moved = pythonic.leading_calls("".join(call.content), call.body.get("tools"))
                                if moved:                    # calls written, now imagining their results
                                    stop = True
                                    call.stopped_by = "pythonic_first"
                        for tc in d.get("tool_calls") or []:
                            slot = call.tool_calls.setdefault(tc.get("index", 0), {"type": "function", "function": {}})
                            if tc.get("id"):
                                slot["id"] = tc["id"]
                            f = tc.get("function") or {}
                            if f.get("name"):
                                slot["function"]["name"] = f["name"]
                            if f.get("arguments"):
                                slot["function"]["arguments"] = slot["function"].get("arguments", "") + f["arguments"]
                                pieces.append(f["arguments"])
                        if ch.get("finish_reason"):
                            call.finish_reason = ch["finish_reason"]
                        for p in pieces:
                            call.chunks += 1
                            call.chars += len(p)
                            if call.t_first is None:
                                call.t_first = time.monotonic()
                            if self.policy.on_chunk(call, p) == STOP:
                                stop = True
                    call.t_last = time.monotonic()
                    if client is not None and not stop:
                        await client.write(raw if raw.endswith(b"\n\n") else raw.rstrip(b"\n") + b"\n\n")
                    if stop:
                        call.stopped_by = call.stopped_by or "policy"
                        call.finish_reason = "stop" if call.stopped_by == "pythonic_first" else "length"
                        asyncio.create_task(self.abort_upstream(call.rid))
                        if client is not None:
                            fin = {"id": j.get("id"), "object": "chat.completion.chunk", "model": j.get("model"),
                                   "choices": [{"index": 0, "delta": {}, "finish_reason": "length"}]}
                            await client.write(b"data: " + json.dumps(fin).encode() + b"\n\n")
                        break
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            call.status, call.error = call.status or 502, repr(e)
        if call.usage is None and call.chunks:
            call.usage = {"completion_tokens": None, "estimated_completion_tokens": call.chunks}

    def _aggregate(self, call: Call) -> dict:
        msg = {"role": "assistant", "content": "".join(call.content) or None}
        if call.reasoning:
            msg["reasoning_content"] = "".join(call.reasoning)
        if call.tool_calls:
            msg["tool_calls"] = [dict(v, index=k) for k, v in sorted(call.tool_calls.items())]
        return {"id": call.rid, "object": "chat.completion", "created": int(time.time()),
                "model": call.body.get("model"), "choices": [{"index": 0, "message": msg,
                                                              "finish_reason": call.finish_reason}],
                "usage": call.usage, "gateway": {"attempts": call.attempt + 1, "stopped_by": call.stopped_by}}

    # ------------------------------------------------------------------ native /generate
    async def generate(self, request: web.Request):
        sid = request.match_info.get("sid", "anon")
        tag = "tool" if request.match_info.get("tool") else "agent"
        body = await request.json()
        sess = self.session(sid)
        call = Call(sess, "generate", tag, body, bool(body.get("stream")))
        sess.n_calls += 1
        sess.open_calls += 1
        if tag == "agent":
            sess.phase = "llm"
        try:
            t0 = time.monotonic()
            early = await self.policy.on_request(call)
            call.held_s = time.monotonic() - t0
            if isinstance(early, dict):
                call.status, call.stopped_by = "rejected", "policy"
                self.log_call(call)
                return web.json_response(early)
            body = dict(call.body)
            body.setdefault("rid", call.rid)
            call.rid = body["rid"]
            call.t_sent = time.monotonic()
            async with self.http.post(self.upstream + "/generate", json=body) as r:
                call.status = r.status
                out = await r.read()
            call.t_last = time.monotonic()
            try:
                j = json.loads(out)
                mi = (j[0] if isinstance(j, list) else j).get("meta_info", {})
                call.usage = {k: mi.get(k) for k in ("prompt_tokens", "completion_tokens", "cached_tokens")}
                call.finish_reason = (mi.get("finish_reason") or {}).get("type") if isinstance(
                    mi.get("finish_reason"), dict) else mi.get("finish_reason")
                call.meta = {k: mi.get(k) for k in ("e2e_latency", "queue_time", "num_retractions")}
            except Exception as e:
                call.error = repr(e)
            self.log_call(call)
            await self.policy.on_complete(call)
            return web.Response(body=out, status=r.status, content_type="application/json")
        finally:
            sess.open_calls -= 1
            sess.t_last_end = time.monotonic()
            if tag == "agent" and sess.open_calls == 0:
                sess.phase = "idle"

    # ------------------------------------------------------------------ events and passthrough
    async def event(self, request: web.Request):
        sid = request.match_info["sid"]
        data = await request.json()
        sess = self.session(sid)
        kind = data.get("kind")
        if kind == "tool_start":
            sess.phase, sess.tool, sess.t_tool_start = "tool", data.get("tool"), time.monotonic()
        elif kind == "tool_end":
            sess.phase, sess.tool = "idle", None
        elif kind == "session_end":
            sess.phase = "done"
        self.log_event(sid, kind, **{k: v for k, v in data.items() if k != "kind"})
        self.policy.on_event(sess, kind, data)
        return web.json_response({"ok": True})

    async def passthrough(self, request: web.Request):
        path = request.path_qs
        if path.startswith("/s/"):                      # /s/<sid>/flush_cache etc.: drop the session prefix
            path = "/" + path.split("/", 3)[3]
        url = self.upstream + path
        data = await request.read() if request.can_read_body else None
        async with self.http.request(request.method, url, data=data,
                                     headers={"Content-Type": request.headers.get("Content-Type", "application/json")}) as r:
            body = await r.read()
            return web.Response(body=body, status=r.status, content_type=r.content_type)

    async def status(self, request):
        return web.json_response({
            "policy": self.policy.describe(), "metrics_age_s": None if self.metrics_t is None else
            round(time.monotonic() - self.metrics_t, 2),
            "sessions": {s.sid: dict(phase=s.phase, tool=s.tool, n_calls=s.n_calls, open=s.open_calls)
                         for s in self.sessions.values()}})


def load_policy(spec: str | None, args: dict) -> Policy:
    if not spec:
        return Policy()
    mod, _, cls = spec.partition(":")
    return getattr(importlib.import_module(mod), cls)(**args)


def make_app(gw: Gateway) -> web.Application:
    app = web.Application(client_max_size=256 * 2**20)
    r = app.router
    for prefix in ("/s/{sid}", ""):
        r.add_post(prefix + "/v1/chat/completions", gw.chat)
        r.add_post(prefix + "/generate", gw.generate)
    r.add_post("/s/{sid}/{tool:tool}/v1/chat/completions", gw.chat)
    r.add_post("/s/{sid}/{tool:tool}/generate", gw.generate)
    r.add_post("/s/{sid}/event", gw.event)
    r.add_get("/gateway/status", gw.status)
    for prefix in ("", "/s/{sid}"):
        for path in ("/v1/models", "/metrics", "/health", "/get_server_info", "/server_info", "/get_model_info"):
            r.add_get(prefix + path, gw.passthrough)
        for path in ("/flush_cache", "/abort_request", "/open_session", "/close_session"):
            r.add_post(prefix + path, gw.passthrough)
    app.on_startup.append(gw.start)
    app.on_cleanup.append(gw.stop)
    return app


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", default="http://127.0.0.1:30000")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=31000)
    ap.add_argument("--log-dir", required=True)
    ap.add_argument("--policy", default=None, help="module:Class (default: no policy)")
    ap.add_argument("--policy-args", default="{}")
    ap.add_argument("--pythonic-fallback", default="off", choices=("off", "all", "first"),
                    help="turn content that is only Python-style calls to the request's tools into tool calls; "
                         "'first' also stops a reply when it opens a new thought after its calls")
    a = ap.parse_args()
    gw = Gateway(a.upstream, Path(a.log_dir), load_policy(a.policy, json.loads(a.policy_args)),
                 pythonic_fallback=a.pythonic_fallback)
    web.run_app(make_app(gw), host=a.host, port=a.port, access_log=None, print=None)


if __name__ == "__main__":
    main()

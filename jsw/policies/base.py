"""Policy interface for the JouleServe gateway (OPTIONS_PLAN.md S2, §3.6 of the master plan).

A policy sees every LLM call of every session and may act at four points:
- on_request(call): before the call goes upstream. It may change call.body (sampling, priority, budget), hold
  the call (await something: admission), or reject it by returning a dict (sent to the client as the response).
- on_chunk(call, text): for each streamed piece of generated text (reasoning, content, tool-call arguments, in
  order). Return STOP to abort the call upstream.
- on_complete(call): after the call ends (finished, stopped or failed). Return a new request body to retry the
  call upstream (the client then sees the retry's result), or None to deliver it.
- on_tick(metrics) and on_event(session, kind, data): server metrics (~2 Hz) and driver events (tool start/end).
The default policy does nothing, which is SGLang's own behaviour.
"""
from __future__ import annotations

STOP = "stop"


class Policy:
    name = "default"

    def attach(self, gateway):
        self.gw = gateway

    async def on_request(self, call):
        return None

    def on_chunk(self, call, text: str):
        return None

    async def on_complete(self, call):
        return None

    def on_tick(self, metrics: dict):
        pass

    def on_event(self, session, kind: str, data: dict):
        pass

    def describe(self) -> dict:
        return {"policy": self.name}

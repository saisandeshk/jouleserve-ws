"""Decode guard: option A's WS version (OPTIONS_PLAN.md A-P1).

Watches every streamed call with the online loop detector (jsw/policies/loop_detector.py) and, when it fires,
stops the call upstream and then does one of:
- "truncate": return what was generated with finish_reason "length", as if the call had hit its cap early, so the
  agent's own retry logic runs (P1's agents then evaluate, reflect and retry);
- "resample": retry the same request inside the gateway with the model's default sampling (Gemma-4: temperature
  1.0, top_k 64, top_p 0.95), so the agent sees one call;
- "nudge": retry with a short user message appended that says the attempt repeated itself;
- "budget": retry with max_tokens cut to `budget_tokens`.
Optionally ends a session after `max_consecutive_caps` capped calls in a row (traffic's repeated tool-call caps):
the next request gets an error instead of going upstream.
Each decision is logged on the call (stopped_by="loop", attempt number) and as a gateway event.
"""
from __future__ import annotations

from jsw.policies.base import STOP, Policy
from jsw.policies.loop_detector import LoopDetector

DEFAULT_SAMPLING = {"temperature": 1.0, "top_p": 0.95, "top_k": 64}
NUDGE = ("Your previous attempt at this reply started repeating itself and was stopped. Do not repeat earlier "
         "text; give your final answer now, concisely.")


class DecodeGuard(Policy):
    name = "decode_guard"

    def __init__(self, action: str = "truncate", max_retries: int = 1, budget_tokens: int = 8192,
                 sampling: dict | None = None, max_consecutive_caps: int | None = None, detect: bool = True):
        assert action in ("truncate", "resample", "nudge", "budget")
        self.action, self.max_retries, self.budget_tokens = action, max_retries, budget_tokens
        self.sampling = sampling or DEFAULT_SAMPLING
        self.max_consecutive_caps, self.detect = max_consecutive_caps, detect
        self.detectors: dict[tuple, LoopDetector] = {}
        self.consec: dict[str, int] = {}

    def describe(self):
        return {"policy": self.name, "action": self.action, "max_retries": self.max_retries,
                "budget_tokens": self.budget_tokens, "sampling": self.sampling,
                "max_consecutive_caps": self.max_consecutive_caps, "detect": self.detect}

    async def on_request(self, call):
        k = self.max_consecutive_caps
        if k and call.tag == "agent" and self.consec.get(call.session.sid, 0) >= k:
            self.gw.log_event(call.session.sid, "guard_session_stop", consecutive_caps=self.consec[call.session.sid])
            return {"error": {"message": f"stopped by gateway after {k} consecutive capped calls",
                              "type": "gateway_stop"}}
        return None

    def on_chunk(self, call, text):
        if not self.detect or call.route != "chat":
            return None
        key = (call.call_id, call.attempt)
        d = self.detectors.get(key)
        if d is None:
            d = self.detectors[key] = LoopDetector()
        if d.feed(text) is not None:
            call.stopped_by = "loop"
            call.meta = dict(call.meta or {}, loop_fired_char=d.fired_at)
            return STOP
        return None

    async def on_complete(self, call):
        self.detectors.pop((call.call_id, call.attempt), None)
        capped = call.finish_reason == "length"
        if call.tag == "agent" and call.route == "chat":
            sid = call.session.sid
            self.consec[sid] = self.consec.get(sid, 0) + 1 if capped else 0
        if call.stopped_by != "loop" or self.action == "truncate" or call.attempt >= self.max_retries:
            return None
        body = dict(call.body)
        if self.action == "resample":
            body.update(self.sampling)
            body.pop("seed", None)
        elif self.action == "nudge":
            body["messages"] = list(body.get("messages") or []) + [{"role": "user", "content": NUDGE}]
        elif self.action == "budget":
            body["max_tokens"] = min(int(body.get("max_tokens") or self.budget_tokens), self.budget_tokens)
        self.gw.log_event(call.session.sid, "guard_retry", call_id=call.call_id, attempt=call.attempt + 1,
                          action=self.action, fired_char=(call.meta or {}).get("loop_fired_char"))
        return body

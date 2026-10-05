"""Burst-aware memory: option D's WS version (OPTIONS_PLAN.md D-P1).

A tool that runs a model on the agent's own server (P1's vision tool sends 8-45 requests at once) takes memory
while the agent's context sits paused, and on a small pool evicts it. The gateway knows which requests come from
a tool (route /s/<sid>/tool/...), so it can act on two levers SGLang 0.5.20 has:
- pin: agent requests carry a high request priority and tool requests a low one. With the server started with
  --enable-priority-scheduling --radix-eviction-policy priority, the tree evicts low-priority (burst) KV before the
  paused agent's context (a node keeps the highest priority of the requests that touched it).
- admit_k: while the pool is above `usage_threshold` (sglang:token_usage, polled ~2 Hz), at most k tool requests
  run at once; the rest wait in the gateway.
With both off the policy only sets equal priorities, which is LRU: SGLang's default.
"""
from __future__ import annotations

import asyncio

from jsw.policies.base import Policy


class BurstMemory(Policy):
    name = "burst_memory"

    def __init__(self, pin: bool = False, admit_k: int | None = None, usage_threshold: float = 0.0,
                 prio_agent: int = 10, prio_tool: int = 0):
        self.pin, self.admit_k, self.usage_threshold = pin, admit_k, usage_threshold
        self.prio_agent, self.prio_tool = prio_agent, prio_tool
        self.running_tool = 0
        self.cond = None
        self.held = 0

    def describe(self):
        return {"policy": self.name, "pin": self.pin, "admit_k": self.admit_k, "usage_threshold": self.usage_threshold,
                "prio_agent": self.prio_agent, "prio_tool": self.prio_tool}

    def _usage(self):
        m = self.gw.metrics or {}
        return m.get("sglang:token_usage", m.get("sglang:full_token_usage", 0.0)) or 0.0

    async def on_request(self, call):
        if self.cond is None:
            self.cond = asyncio.Condition()
        tool = call.tag == "tool"
        call.body = dict(call.body, priority=(self.prio_tool if tool and self.pin else
                                              self.prio_agent if self.pin else self.prio_agent))
        if tool and self.admit_k:
            async with self.cond:
                waited = False
                while self.running_tool >= self.admit_k and self._usage() >= self.usage_threshold:
                    waited = True
                    try:
                        await asyncio.wait_for(self.cond.wait(), timeout=0.5)   # re-check usage as it changes
                    except asyncio.TimeoutError:
                        pass
                self.held += waited
                self.running_tool += 1
            call.meta = dict(call.meta or {}, admitted_after_wait=waited)
        return None

    async def on_complete(self, call):
        if call.tag == "tool" and self.admit_k:
            async with self.cond:
                self.running_tool -= 1
                self.cond.notify_all()
        return None

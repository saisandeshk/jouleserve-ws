"""Fallback tool-call parser for replies that write calls as Python text (OPTIONS_PLAN.md B-E1).

Modes (gateway --pythonic-fallback): "all" converts a reply that is only calls; "first" also stops a reply as
soon as it opens a new thought after its calls (gemma-4-E4B with aerogen's prompt writes a call, imagines the
result in a thought block, writes the next call, ... to the end of the mission) and keeps the calls before it,
like a stop sequence at the first tool call. Tokens generated before the stop are real and logged.

Some models copy a prompt's examples and write `connect(namespace="drone0")` as plain content instead of using
their native tool-call format; gemma-4-E4B does this with aerogen's prompts, whose examples are written that
way. When a reply has no native tool call and every non-empty line of its content (code fences allowed) is a
call to one of the request's own tools with literal arguments, the gateway turns those lines into OpenAI tool
calls. Anything else is left untouched. It is a serving-side parser fix (like SGLang's "pythonic" detector),
not an agent change, and every conversion is counted in the call log.
"""
from __future__ import annotations

import ast
import json
import uuid

# Gemma-4 opens a thought block with this marker. In mode "first" the gateway stops a reply at the first marker
# that follows content (the model has started to imagine the tool's result) and keeps the calls before it.
MARK = "<|channel>"


def _tool_params(tools):
    out = {}
    for t in tools or []:
        f = t.get("function") or {}
        if f.get("name"):
            out[f["name"]] = list(((f.get("parameters") or {}).get("properties") or {}).keys())
    return out


def parse(content: str | None, tools) -> list[dict] | None:
    """Tool calls for `content`, or None when it is not purely calls to known tools."""
    if not content or not tools:
        return None
    params = _tool_params(tools)
    lines = [ln.strip() for ln in content.strip().splitlines()]
    lines = [ln for ln in lines if ln and not ln.startswith("```")]
    if not lines:
        return None
    calls = []
    for ln in lines:
        ln = ln.split(" -> ")[0].rstrip(";").strip()        # examples show "call(...) -> {result}"
        try:
            node = ast.parse(ln, mode="eval").body
        except SyntaxError:
            return None
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in params):
            return None
        try:
            args = {kw.arg: ast.literal_eval(kw.value) for kw in node.keywords if kw.arg}
            names = params[node.func.id]
            for i, a in enumerate(node.args):
                if i >= len(names):
                    return None
                args[names[i]] = ast.literal_eval(a)
        except (ValueError, SyntaxError):
            return None
        calls.append({"id": "call_" + uuid.uuid4().hex[:24], "type": "function",
                      "function": {"name": node.func.id, "arguments": json.dumps(args)}})
    return calls or None


def leading_calls(content: str | None, tools) -> tuple[list[dict] | None, bool]:
    """Mode "first": the calls on the reply's leading lines, and whether the reply has moved past them, i.e. a
    line after at least one call has begun that is not a call (an imagined result "-> {...}", a comment, a new
    thought block). Only complete lines are parsed as calls; a started line counts as "moved past" as soon as
    its beginning cannot start a call."""
    if not content or not tools:
        return None, False
    params = _tool_params(tools)
    text = content.split(MARK)[0] if MARK in content else content
    passed_mark = MARK in content
    parts = text.split("\n")
    complete, partial = parts[:-1], parts[-1]
    calls_src = []
    for ln in complete:
        s = ln.strip()
        if not s or s.startswith("```"):
            continue
        c = parse(s, tools)
        if c and not calls_src or (c and calls_src):
            calls_src.append(s)
            continue
        # a complete non-call line
        return (parse("\n".join(calls_src), tools) if calls_src else None), bool(calls_src)
    if not calls_src:
        return None, False
    p = partial.strip()
    moved = passed_mark or (p != "" and not any(p.startswith(n) or n.startswith(p) for n in params))
    return parse("\n".join(calls_src), tools), moved

"""LLM tool-calling loop for multi-tool agent orchestration."""

from __future__ import annotations

import json
from typing import Any

from django.conf import settings

try:
    from langchain_core.messages import ToolMessage
except ImportError:  # pragma: no cover
    ToolMessage = None  # type: ignore[misc, assignment]


def dispatch_tool_call(tool_name: str, tool_args: dict[str, Any] | str, tool_by_name: dict[str, Any]) -> str:
    tool = tool_by_name.get(tool_name)
    if not tool:
        return f'未知工具：{tool_name}'

    args = tool_args
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {}

    try:
        if hasattr(tool, 'invoke'):
            return str(tool.invoke(args))
        return str(tool.run(args))
    except Exception as exc:
        return f'工具 {tool_name} 执行失败：{exc}'


def run_tool_orchestration(
    llm,
    messages: list,
    tools: list,
    max_rounds: int | None = None,
) -> tuple[list | None, str | None]:
    """
    Execute a tool-calling loop (ReAct-style) before the final streamed reply.

    Returns:
        (updated_messages, early_reply):
            - updated_messages: conversation with tool call/result trail appended
            - early_reply: when the model answers without needing a stream pass
        (None, None): bind/invoke failed — caller should fall back to keyword tools
    """
    if not tools or ToolMessage is None:
        return None, None

    rounds = max_rounds if max_rounds is not None else int(getattr(settings, 'AGENT_TOOL_MAX_ROUNDS', 3))
    tool_by_name = {getattr(t, 'name', ''): t for t in tools if getattr(t, 'name', '')}

    try:
        bound = llm.bind_tools(tools)
    except Exception:
        return None, None

    working = list(messages)
    for _ in range(rounds):
        try:
            ai = bound.invoke(working)
        except Exception:
            return None, None

        tool_calls = getattr(ai, 'tool_calls', None) or []
        if not tool_calls:
            if ai.content:
                working.append(ai)
                return working, str(ai.content)
            return working, None

        working.append(ai)
        for tc in tool_calls:
            tc_id = tc.get('id') or ''
            name = tc.get('name') or ''
            args = tc.get('args') or {}
            result = dispatch_tool_call(name, args, tool_by_name)
            working.append(ToolMessage(content=result, tool_call_id=tc_id))

    return working, None

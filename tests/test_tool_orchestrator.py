"""Tests for multi-tool agent orchestration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.services.tool_orchestrator import dispatch_tool_call, run_tool_orchestration


class _FakeTool:
    name = 'demo_tool'

    def invoke(self, args):
        city = (args or {}).get('city', '')
        return f'weather:{city}'


class _FakeAIMessage:
    def __init__(self, content: str = '', tool_calls: list | None = None):
        self.content = content
        self.tool_calls = tool_calls or []


class _FakeLLM:
    def __init__(self, responses: list[_FakeAIMessage]):
        self._responses = list(responses)
        self.bound_tools: list | None = None

    def bind_tools(self, tools):
        self.bound_tools = tools
        return self

    def invoke(self, messages):
        if not self._responses:
            raise RuntimeError('no more fake responses')
        return self._responses.pop(0)


def test_dispatch_tool_call_invokes_registered_tool() -> None:
    result = dispatch_tool_call('demo_tool', {'city': '上海'}, {'demo_tool': _FakeTool()})
    assert result == 'weather:上海'


def test_dispatch_tool_call_unknown_tool() -> None:
    assert '未知工具' in dispatch_tool_call('missing', {}, {})


def test_run_tool_orchestration_executes_tool_then_returns_for_stream() -> None:
    llm = _FakeLLM(
        [
            _FakeAIMessage(
                tool_calls=[{'id': 'tc1', 'name': 'demo_tool', 'args': {'city': '北京'}}],
            ),
            _FakeAIMessage(content=''),
        ]
    )
    messages = [{'role': 'user', 'content': '北京天气'}]
    updated, early = run_tool_orchestration(llm, messages, [_FakeTool()], max_rounds=3)
    assert early is None
    assert updated is not None
    assert len(updated) == 4  # user + ai tool call + tool result + empty ai
    assert llm.bound_tools == [_FakeTool()]


def test_run_tool_orchestration_early_reply_without_stream() -> None:
    llm = _FakeLLM([_FakeAIMessage(content='你好，我是助手。')])
    updated, early = run_tool_orchestration(llm, [], [_FakeTool()], max_rounds=2)
    assert early == '你好，我是助手。'
    assert updated is not None
    assert updated[-1].content == '你好，我是助手。'


def test_run_tool_orchestration_bind_failure_returns_none() -> None:
    llm = MagicMock()
    llm.bind_tools.side_effect = RuntimeError('tools unsupported')
    updated, early = run_tool_orchestration(llm, [], [_FakeTool()])
    assert updated is None
    assert early is None


@patch('core.services.llm_service.run_tool_orchestration', return_value=(None, None))
def test_stream_chat_falls_back_to_keyword_tools(mock_orchestrate) -> None:
    from core.services.llm_service import stream_chat

    class _Char:
        name = '测试'
        system_prompt = '你是测试角色'
        opening_message = ''
        personality = []

    tokens = list(
        stream_chat(
            _Char(),
            'sess-1',
            '北京天气怎么样',
            chain_dict={'llm': None, 'system': 'sys'},
        )
    )
    assert tokens == ['（未能连接本地 Ollama，请检查 OPENAI_BASE_URL）']
    mock_orchestrate.assert_not_called()

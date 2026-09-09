"""SubAgent 白名单工具的直通拦截切面。"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator, Callable
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from ..tool_result_cleaners import clean_tool_result, truncate_tool_result

logger = logging.getLogger(__name__)

DEFAULT_SUBAGENT_BYPASS_TOOLS = (
    "fetch",
    "web_search_tavily",
    "read_text_file",
    "astr_kb_search",
    "list_directory",
    "angel_note_read",
    "browse_threads",
    "search_threads",
    "read_thread",
    "get_sub_replies",
)

_subagent_active: ContextVar[bool] = ContextVar(
    "astrbot_tweaks_subagent_active", default=False
)


@contextmanager
def with_subagent_context():
    """标记当前异步任务处于 HandoffTool 子 Agent 调用链。"""
    token = _subagent_active.set(True)
    try:
        yield
    finally:
        _subagent_active.reset(token)


def _bypass_tools(config: dict[str, Any]) -> set[str]:
    configured = config.get("subagent_bypass_tools")
    if not isinstance(configured, list):
        configured = list(DEFAULT_SUBAGENT_BYPASS_TOOLS)
    return {
        str(tool_name).strip()
        for tool_name in configured
        if str(tool_name).strip()
    }


def _json_payload(response: Any) -> dict[str, Any] | None:
    data = getattr(response, "data", None)
    chain = data.get("chain") if isinstance(data, dict) else getattr(data, "chain", None)
    components = getattr(chain, "chain", None)
    if not isinstance(components, list):
        return None
    for component in components:
        payload = getattr(component, "data", None)
        if isinstance(payload, dict):
            return payload
    return None


def _finalize_direct_return(runner: Any, result: str) -> None:
    from astrbot.core.agent.runners.base import AgentState
    from astrbot.core.provider.entities import LLMResponse

    runner.final_llm_resp = LLMResponse(role="assistant", completion_text=result)
    if getattr(runner, "stats", None) is not None:
        runner.stats.end_time = time.time()
    if hasattr(runner, "_transition_state"):
        runner._transition_state(AgentState.DONE)
    if hasattr(runner, "_resolve_unconsumed_follow_ups"):
        runner._resolve_unconsumed_follow_ups()


def make_patched_step(
    original: Callable[..., AsyncGenerator[Any, None]],
    config: dict[str, Any],
) -> Callable[..., AsyncGenerator[Any, None]]:
    """包装 Agent 循环 step，命中直通条件时终止下一轮 LLM 推理。"""
    tools = _bypass_tools(config)

    async def patched(self: Any, *args: Any, **kwargs: Any) -> AsyncGenerator[Any, None]:
        if not _subagent_active.get():
            async for response in original(self, *args, **kwargs):
                yield response
            return

        tool_calls: list[dict[str, Any]] = []
        direct_result: str | None = None
        async for response in original(self, *args, **kwargs):
            yield response
            payload = _json_payload(response)
            if payload is None:
                continue

            if response.type == "tool_call":
                tool_calls.append(payload)
            elif response.type == "tool_call_result" and tool_calls:
                if len(tool_calls) != 1:
                    continue
                call = tool_calls[0]
                tool_name = str(payload.get("name") or call.get("name") or "")
                if tool_name not in tools:
                    continue
                result = str(payload.get("result") or "")
                try:
                    direct_result = clean_tool_result(tool_name, result, config)
                except Exception:
                    logger.exception(
                        "Astrbot Tweaks failed to clean direct tool result: %s",
                        tool_name,
                    )
                    max_chars = int(
                        config.get("subagent_direct_max_chars", 30000)
                    )
                    direct_result = truncate_tool_result(result, max_chars)

        if direct_result is not None and len(tool_calls) == 1:
            _finalize_direct_return(self, direct_result)

    return patched


def make_wrapped_execute_handoff(
    original: Callable[..., AsyncGenerator[Any, None]],
) -> Callable[..., AsyncGenerator[Any, None]]:
    """进入 HandoffTool 执行链时设置 ContextVar，退出时恢复。"""

    async def wrapped(
        cls: type,
        *args: Any,
        **kwargs: Any,
    ) -> AsyncGenerator[Any, None]:
        token = _subagent_active.set(True)
        try:
            async for response in original(cls, *args, **kwargs):
                yield response
        finally:
            _subagent_active.reset(token)

    return wrapped


def _unwrap_descriptor(method: Any) -> Any:
    return getattr(method, "__func__", method)


class SubAgentDirectReturnPatch:
    """注册并恢复 SubAgent 直通相关的两个内部切面。"""

    def __init__(self) -> None:
        self.applied = False
        self._config: dict[str, Any] = {}
        self._original_execute_handoff: Any = None
        self._original_step: Any = None

    def install(self, config: dict[str, Any] | None = None) -> None:
        if self.applied:
            return

        from astrbot.core.agent.runners.tool_loop_agent_runner import (
            ToolLoopAgentRunner,
        )
        from astrbot.core.astr_agent_tool_exec import FunctionToolExecutor

        original_execute_handoff = FunctionToolExecutor.__dict__.get(
            "_execute_handoff"
        )
        original_step = ToolLoopAgentRunner.__dict__.get("step")
        if original_execute_handoff is None or original_step is None:
            raise RuntimeError("AstrBot SubAgent runtime methods are unavailable")

        self._config = dict(config or {})
        self._original_execute_handoff = original_execute_handoff
        self._original_step = original_step
        FunctionToolExecutor._execute_handoff = classmethod(
            make_wrapped_execute_handoff(
                _unwrap_descriptor(original_execute_handoff)
            )
        )
        ToolLoopAgentRunner.step = make_patched_step(original_step, self._config)
        self.applied = True

    def restore(self) -> None:
        if not self.applied:
            return

        from astrbot.core.agent.runners.tool_loop_agent_runner import (
            ToolLoopAgentRunner,
        )
        from astrbot.core.astr_agent_tool_exec import FunctionToolExecutor

        if self._original_execute_handoff is not None:
            FunctionToolExecutor._execute_handoff = self._original_execute_handoff
        if self._original_step is not None:
            ToolLoopAgentRunner.step = self._original_step
        self._original_execute_handoff = None
        self._original_step = None
        self._config = {}
        self.applied = False

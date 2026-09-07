"""ContextManager 压缩策略补丁。"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

ContextProcess = Callable[..., Awaitable[Any]]


async def call_original(
    original: ContextProcess,
    manager: Any,
    messages: Any,
    trusted_token_usage: int = 0,
) -> Any:
    """兼容旧方法签名，尽量回退到 AstrBot 官方实现。"""
    try:
        return await original(manager, messages, trusted_token_usage)
    except TypeError:
        try:
            return await original(manager, messages)
        except Exception:
            return messages


def _uses_llm_summary_compressor(manager: Any) -> bool:
    try:
        from astrbot.core.agent.context.compressor import LLMSummaryCompressor
    except Exception:
        return False
    return isinstance(getattr(manager, "compressor", None), LLMSummaryCompressor)


def make_patched_context_process(
    original: ContextProcess,
) -> ContextProcess:
    """生成带回退的 ContextManager.process 包装函数。"""

    async def patched_context_process(
        manager: Any,
        messages: Any,
        trusted_token_usage: int = 0,
    ) -> Any:
        try:
            if not hasattr(manager, "truncator") or not hasattr(
                manager.truncator,
                "_split_system_rest",
            ):
                return await call_original(
                    original,
                    manager,
                    messages,
                    trusted_token_usage,
                )

            config = manager.config
            truncator = manager.truncator
            token_counter = manager.token_counter
            compressor = manager.compressor

            result = messages
            if config.enforce_max_turns != -1 and not _uses_llm_summary_compressor(
                manager
            ):
                result = truncator.truncate_by_turns(
                    result,
                    keep_most_recent_turns=config.enforce_max_turns,
                    drop_turns=config.truncate_turns,
                )

            if config.max_context_tokens > 0:
                total_tokens = token_counter.count_tokens(
                    result,
                    trusted_token_usage,
                )
                should_compress = compressor.should_compress(
                    result,
                    total_tokens,
                    config.max_context_tokens,
                )
                if (
                    _uses_llm_summary_compressor(manager)
                    and config.enforce_max_turns != -1
                ):
                    _, non_system = truncator._split_system_rest(result)
                    if len(non_system) // 2 > config.enforce_max_turns:
                        should_compress = True

                if should_compress:
                    result = await manager._run_compression(result, total_tokens)

            return result
        except Exception as exc:
            logger.exception("Astrbot Tweaks context patch failed: %s", exc)
            return await call_original(
                original,
                manager,
                messages,
                trusted_token_usage,
            )

    return patched_context_process


class ContextCompressionPatch:
    """包装 ContextManager.process，并在恢复时还原原方法。"""

    _original: ContextProcess | None = None

    @property
    def applied(self) -> bool:
        return self._original is not None

    def install(self) -> None:
        """安装补丁；重复调用不产生双重包装。"""
        if self.applied:
            return

        from astrbot.core.agent.context.manager import ContextManager

        original = getattr(ContextManager, "process", None)
        if not callable(original):
            raise RuntimeError("ContextManager.process is missing or not callable")

        ContextManager.process = make_patched_context_process(original)
        self._original = original
        logger.info("Astrbot Tweaks: context compression patch installed.")

    def restore(self) -> None:
        """恢复原始方法；未安装时 no-op。"""
        if not self.applied:
            return

        try:
            from astrbot.core.agent.context.manager import ContextManager

            ContextManager.process = self._original
        finally:
            self._original = None

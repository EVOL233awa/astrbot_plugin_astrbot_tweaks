"""拦截只有 reasoning、没有最终正文的 OpenAI-compatible 响应。"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

ParseCompletion = Callable[..., Awaitable[Any]]
ErrorFactory = Callable[[str], BaseException]


def _default_error_factory(message: str) -> BaseException:
    from astrbot.core.exceptions import EmptyModelOutputError

    return EmptyModelOutputError(message)


def make_patched_parse_openai_completion(
    original: ParseCompletion,
    error_factory: ErrorFactory | None = None,
) -> ParseCompletion:
    """包装解析方法，把 reasoning-only 响应判定为空输出。"""

    make_error = error_factory or _default_error_factory

    async def patched(
        provider: Any,
        completion: Any,
        tools: Any,
    ) -> Any:
        response = await original(provider, completion, tools)
        text = str(getattr(response, "completion_text", None) or "").strip()
        tool_call_args = getattr(response, "tools_call_args", None) or []
        if text or tool_call_args:
            return response

        reasoning = str(getattr(response, "reasoning_content", None) or "")
        choices = getattr(completion, "choices", None) or []
        finish_reason = (
            getattr(choices[0], "finish_reason", "unknown") if choices else "unknown"
        )
        response_id = str(getattr(completion, "id", "") or "unknown")
        message = (
            "OpenAI completion returned reasoning without final content. "
            f"response_id={response_id}, finish_reason={finish_reason}, "
            f"reasoning_chars={len(reasoning)}"
        )
        logger.warning(
            "Rejecting reasoning-only completion: response_id=%s "
            "finish_reason=%s reasoning_chars=%s",
            response_id,
            finish_reason,
            len(reasoning),
        )
        raise make_error(message)

    return patched


class ReasoningOnlyGuardPatch:
    """包装 ProviderOpenAIOfficial._parse_openai_completion。"""

    def __init__(self, target_class: type | None = None) -> None:
        self.applied = False
        self._target_class = target_class
        self._original_parse: ParseCompletion | None = None

    def _resolve_target(self) -> type:
        if self._target_class is not None:
            return self._target_class
        from astrbot.core.provider.sources.openai_source import (
            ProviderOpenAIOfficial,
        )

        return ProviderOpenAIOfficial

    def install(self, config: dict[str, Any] | None = None) -> None:
        """安装补丁；重复调用不产生双重包装。"""

        _ = config
        if self.applied:
            return

        target = self._resolve_target()
        original = target.__dict__.get("_parse_openai_completion")
        if not callable(original):
            raise RuntimeError(
                "AstrBot OpenAI provider _parse_openai_completion is unavailable"
            )

        target._parse_openai_completion = make_patched_parse_openai_completion(  # noqa: SLF001
            original,
        )
        self._target_class = target
        self._original_parse = original
        self.applied = True
        logger.info("Astrbot Tweaks: reasoning-only guard patch installed.")

    def restore(self) -> None:
        """恢复原始解析方法。"""

        if not self.applied or self._target_class is None:
            return

        target = self._target_class
        if self._original_parse is not None:
            target._parse_openai_completion = self._original_parse  # noqa: SLF001
        self._original_parse = None
        self.applied = False

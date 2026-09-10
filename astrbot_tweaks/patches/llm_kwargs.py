"""让 AstrBot OpenAI Provider 透传插件显式指定的生成参数。"""

from __future__ import annotations

import re
from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

DEFAULT_LLM_KWARGS_ALLOWLIST = ("temperature", "max_tokens")
BLOCKED_LLM_KWARGS = frozenset(
    {
        "messages",
        "model",
        "stream",
        "stream_options",
        "tools",
        "tool_choice",
        "functions",
        "function_call",
    }
)
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_llm_kwargs: ContextVar[dict[str, Any]] = ContextVar(
    "astrbot_tweaks_llm_kwargs", default={}
)


def normalize_llm_kwargs_allowlist(values: Any) -> tuple[str, ...]:
    """Normalize user-provided LLM kwargs names."""

    if not isinstance(values, (list, tuple)):
        return DEFAULT_LLM_KWARGS_ALLOWLIST
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        key = value.strip()
        if (
            not key
            or key in seen
            or key in BLOCKED_LLM_KWARGS
            or not _IDENTIFIER_RE.fullmatch(key)
        ):
            continue
        seen.add(key)
        result.append(key)
    return tuple(result)


def extract_llm_kwargs(
    kwargs: dict[str, Any],
    allowed_keys: tuple[str, ...] | frozenset[str] | None = None,
) -> dict[str, Any]:
    """只提取显式传入且允许透传的生成参数。"""
    allowed = (
        frozenset(allowed_keys)
        if allowed_keys is not None
        else frozenset(DEFAULT_LLM_KWARGS_ALLOWLIST)
    )
    return {
        key: value
        for key, value in kwargs.items()
        if key in allowed and value is not None
    }


@contextmanager
def with_llm_kwargs(kwargs: dict[str, Any]):
    """在当前异步任务中标记一次 LLM 请求的显式参数覆盖。"""
    token = _llm_kwargs.set(dict(kwargs))
    try:
        yield
    finally:
        _llm_kwargs.reset(token)


def make_patched_prepare(
    original: Callable[..., object],
    allowed_keys: tuple[str, ...] | frozenset[str] | None = None,
) -> Callable[..., object]:
    """包装 payload 准备方法，保留原始结果并记录显式 kwargs。"""
    allowed = (
        frozenset(allowed_keys)
        if allowed_keys is not None
        else frozenset(DEFAULT_LLM_KWARGS_ALLOWLIST)
    )

    async def patched(self, *args: Any, **kwargs: Any):
        overrides = extract_llm_kwargs(kwargs, allowed)
        _llm_kwargs.set(overrides)
        return await original(self, *args, **kwargs)

    return patched


def make_patched_apply_overrides(
    original: Callable[..., None],
    allowed_keys: tuple[str, ...] | frozenset[str] | None = None,
) -> Callable[..., None]:
    """在 provider 覆盖之后应用显式 kwargs，避免被 extra_body 反向覆盖。"""
    allowed = (
        frozenset(allowed_keys)
        if allowed_keys is not None
        else frozenset(DEFAULT_LLM_KWARGS_ALLOWLIST)
    )

    def patched(self, payloads: dict[str, Any], extra_body: dict[str, Any]) -> None:
        original(self, payloads, extra_body)
        for key, value in _llm_kwargs.get().items():
            if key not in allowed:
                continue
            if key in getattr(self, "default_params", ()):
                payloads[key] = value
                extra_body.pop(key, None)
            else:
                payloads.pop(key, None)
                extra_body[key] = value

    return patched


class LLMKwargsPassthroughPatch:
    """修复 OpenAI-compatible Provider 丢弃插件 kwargs 的平台层缺陷。"""

    def __init__(self, target_class: type | None = None) -> None:
        self.applied = False
        self._target_class = target_class
        self._original_prepare: Any = None
        self._original_apply: Any = None
        self.allowlist: tuple[str, ...] = DEFAULT_LLM_KWARGS_ALLOWLIST

    def _resolve_target(self) -> type:
        if self._target_class is not None:
            return self._target_class
        from astrbot.core.provider.sources.openai_source import (
            ProviderOpenAIOfficial,
        )

        return ProviderOpenAIOfficial

    def install(self, config: dict[str, Any] | None = None) -> None:
        target = self._resolve_target()
        prepare = target.__dict__.get("_prepare_chat_payload")
        apply_overrides = target.__dict__.get(
            "_apply_provider_specific_request_overrides"
        )
        if prepare is None or apply_overrides is None:
            raise RuntimeError(
                "AstrBot OpenAI provider payload methods are unavailable"
            )

        if self.applied:
            return
        cfg = config or {}
        self.allowlist = normalize_llm_kwargs_allowlist(
            cfg.get("llm_kwargs_allowlist", DEFAULT_LLM_KWARGS_ALLOWLIST)
        )
        self._original_prepare = prepare
        self._original_apply = apply_overrides
        self._target_class = target
        target._prepare_chat_payload = make_patched_prepare(  # noqa: SLF001
            prepare,
            self.allowlist,
        )
        target._apply_provider_specific_request_overrides = (  # noqa: SLF001
            make_patched_apply_overrides(apply_overrides, self.allowlist)
        )
        self.applied = True

    def restore(self) -> None:
        if not self.applied or self._target_class is None:
            return

        target = self._target_class
        if self._original_prepare is not None:
            target._prepare_chat_payload = self._original_prepare
        if self._original_apply is not None:
            target._apply_provider_specific_request_overrides = self._original_apply
        self._original_prepare = None
        self._original_apply = None
        self.applied = False

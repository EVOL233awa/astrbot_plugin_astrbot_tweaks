from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from astrbot_tweaks.patches.reasoning_guard import (
    ReasoningOnlyGuardPatch,
    make_patched_parse_openai_completion,
)


class GuardError(RuntimeError):
    pass


def _error_factory(message: str) -> GuardError:
    return GuardError(message)


def test_reasoning_only_response_is_rejected() -> None:
    async def original(provider, completion, tools):
        return SimpleNamespace(
            completion_text="",
            tools_call_args=[],
            reasoning_content="thinking " * 100,
        )

    completion = SimpleNamespace(
        id="resp-1",
        choices=[SimpleNamespace(finish_reason="length")],
    )
    patched = make_patched_parse_openai_completion(
        original,
        error_factory=_error_factory,
    )

    with pytest.raises(GuardError, match="reasoning without final content"):
        asyncio.run(patched(SimpleNamespace(), completion, None))


def test_text_response_passes() -> None:
    async def original(provider, completion, tools):
        return SimpleNamespace(
            completion_text="final answer",
            tools_call_args=[],
            reasoning_content="reasoning",
        )

    completion = SimpleNamespace(
        id="resp-2",
        choices=[SimpleNamespace(finish_reason="stop")],
    )
    patched = make_patched_parse_openai_completion(
        original,
        error_factory=_error_factory,
    )

    response = asyncio.run(patched(SimpleNamespace(), completion, None))
    assert response.completion_text == "final answer"


def test_tool_call_response_passes() -> None:
    async def original(provider, completion, tools):
        return SimpleNamespace(
            completion_text="",
            tools_call_args=[{"path": "/tmp/file"}],
            reasoning_content="reasoning",
        )

    completion = SimpleNamespace(
        id="resp-3",
        choices=[SimpleNamespace(finish_reason="tool_calls")],
    )
    patched = make_patched_parse_openai_completion(
        original,
        error_factory=_error_factory,
    )

    response = asyncio.run(patched(SimpleNamespace(), completion, None))
    assert response.tools_call_args == [{"path": "/tmp/file"}]


def test_patch_install_and_restore_are_idempotent() -> None:
    class DummyProvider:
        async def _parse_openai_completion(self, completion, tools):
            return SimpleNamespace(
                completion_text="",
                tools_call_args=[],
                reasoning_content="reasoning",
            )

    original = DummyProvider._parse_openai_completion
    patch = ReasoningOnlyGuardPatch(target_class=DummyProvider)

    patch.install()
    first_patched = DummyProvider._parse_openai_completion
    patch.install()
    assert DummyProvider._parse_openai_completion is first_patched
    assert patch.applied

    patch.restore()
    assert DummyProvider._parse_openai_completion is original
    assert not patch.applied

    patch.restore()
    assert not patch.applied

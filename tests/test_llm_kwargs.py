import asyncio

from astrbot_tweaks.patches.llm_kwargs import (
    ALLOWED_LLM_KWARGS,
    LLMKwargsPassthroughPatch,
    extract_llm_kwargs,
    make_patched_apply_overrides,
    make_patched_prepare,
    with_llm_kwargs,
)


def test_llm_kwargs_allowlist_is_minimal() -> None:
    assert ALLOWED_LLM_KWARGS == frozenset({"temperature", "max_tokens"})


def test_extract_llm_kwargs_keeps_only_allowed_values() -> None:
    kwargs = {
        "temperature": 0.3,
        "max_tokens": 1024,
        "top_p": 0.9,
        "enable_thinking": False,
    }
    assert extract_llm_kwargs(kwargs) == {"temperature": 0.3, "max_tokens": 1024}


def test_extract_llm_kwargs_ignores_none_values() -> None:
    assert extract_llm_kwargs({"temperature": None, "max_tokens": 1024}) == {
        "max_tokens": 1024
    }


def test_patched_prepare_passes_original_result_and_records_kwargs() -> None:
    class Provider:
        pass

    original_calls = []

    async def original(self, *args, **kwargs):
        original_calls.append((args, kwargs))
        return {"messages": ["ok"]}, ["context"]

    async def scenario() -> None:
        patched = make_patched_prepare(original)
        result = await patched(
            Provider(),
            "prompt",
            temperature=0.3,
            max_tokens=1024,
            top_p=0.9,
        )

        assert result == ({"messages": ["ok"]}, ["context"])
        assert original_calls == [
            (
                ("prompt",),
                {"temperature": 0.3, "max_tokens": 1024, "top_p": 0.9},
            )
        ]

    asyncio.run(scenario())


def test_patched_apply_overrides_allowed_keys_after_custom_extra_body() -> None:
    class Provider:
        default_params = {"temperature", "max_tokens"}

    original_calls = []

    def original(self, payloads, extra_body):
        original_calls.append((payloads.copy(), extra_body.copy()))

    payloads = {
        "model": "qwen3.5-4b-q4kxl",
        "temperature": 0.2,
        "max_tokens": 600,
    }
    extra_body = {"temperature": 0.9, "max_tokens": 2048, "top_p": 0.9}

    with with_llm_kwargs({"temperature": 0.3, "max_tokens": 1024}):
        patched = make_patched_apply_overrides(original)
        patched(Provider(), payloads, extra_body)

    assert original_calls == [
        (
            {
                "model": "qwen3.5-4b-q4kxl",
                "temperature": 0.2,
                "max_tokens": 600,
            },
            {"temperature": 0.9, "max_tokens": 2048, "top_p": 0.9},
        )
    ]
    assert payloads["temperature"] == 0.3
    assert payloads["max_tokens"] == 1024
    assert extra_body["top_p"] == 0.9
    assert "temperature" not in extra_body
    assert "max_tokens" not in extra_body


def test_llm_kwargs_patch_install_and_restore_are_idempotent() -> None:
    class DummyProvider:
        default_params = {"temperature", "max_tokens"}

        def __init__(self) -> None:
            self.applied_kwargs = {}

        async def _prepare_chat_payload(self, *args, **kwargs):
            self.applied_kwargs.update(kwargs)
            return {"payload": True}, []

        def _apply_provider_specific_request_overrides(self, payloads, extra_body):
            extra_body.update({key: "provider" for key in extra_body})

    original_prepare = DummyProvider._prepare_chat_payload
    original_apply = DummyProvider._apply_provider_specific_request_overrides
    patch = LLMKwargsPassthroughPatch(target_class=DummyProvider)

    patch.install()
    first_prepare = DummyProvider._prepare_chat_payload
    patch.install()
    assert DummyProvider._prepare_chat_payload is first_prepare
    assert patch.applied

    async def scenario() -> None:
        provider = DummyProvider()
        await provider._prepare_chat_payload("prompt", temperature=0.3)
        assert provider.applied_kwargs["temperature"] == 0.3

    asyncio.run(scenario())

    patch.restore()
    assert DummyProvider._prepare_chat_payload is original_prepare
    assert DummyProvider._apply_provider_specific_request_overrides is original_apply
    assert not patch.applied

    patch.restore()
    assert not patch.applied

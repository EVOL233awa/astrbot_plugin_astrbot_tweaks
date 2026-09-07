import asyncio

from astrbot_tweaks.patches import context as context_patch


class FakeTruncator:
    def __init__(self) -> None:
        self.truncated_by_turns = False

    def truncate_by_turns(self, messages, keep_most_recent_turns, drop_turns):
        self.truncated_by_turns = True
        return messages

    @staticmethod
    def _split_system_rest(messages):
        return [], messages


class FakeCompressor:
    def __init__(self, should_compress: bool = False) -> None:
        self._should_compress = should_compress

    def should_compress(self, *args, **kwargs) -> bool:
        return self._should_compress


class FakeTokenCounter:
    @staticmethod
    def count_tokens(messages, trusted_token_usage: int = 0) -> int:
        return 10


class FakeManager:
    def __init__(self) -> None:
        self.config = type(
            "Config",
            (),
            {
                "enforce_max_turns": 3,
                "truncate_turns": 1,
                "max_context_tokens": 100,
            },
        )()
        self.truncator = FakeTruncator()
        self.compressor = FakeCompressor(should_compress=False)
        self.token_counter = FakeTokenCounter()
        self.compressed = False

    async def _run_compression(self, messages, total_tokens):
        self.compressed = True
        return messages


async def _make_original(calls: list[str]):
    async def original(manager, messages, trusted_token_usage=0):
        calls.append("original")
        return messages

    return original


def test_non_llm_path_truncates_by_turns(monkeypatch) -> None:
    monkeypatch.setattr(
        context_patch,
        "_uses_llm_summary_compressor",
        lambda manager: False,
    )

    async def scenario() -> None:
        manager = FakeManager()
        original = await _make_original([])
        patched = context_patch.make_patched_context_process(original)
        result = await patched(manager, ["user", "assistant"] * 5)
        assert manager.truncator.truncated_by_turns is True
        assert result == ["user", "assistant"] * 5

    asyncio.run(scenario())


def test_llm_path_skips_turn_truncation_and_forces_compression(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        context_patch,
        "_uses_llm_summary_compressor",
        lambda manager: True,
    )

    async def scenario() -> None:
        manager = FakeManager()
        original = await _make_original([])
        patched = context_patch.make_patched_context_process(original)
        result = await patched(manager, ["user", "assistant"] * 4)
        assert manager.truncator.truncated_by_turns is False
        assert manager.compressed is True
        assert result == ["user", "assistant"] * 4

    asyncio.run(scenario())


def test_missing_api_falls_back_to_original() -> None:
    async def scenario() -> None:
        manager = object()
        calls = []
        original = await _make_original(calls)
        patched = context_patch.make_patched_context_process(original)
        result = await patched(manager, ["message"])
        assert calls == ["original"]
        assert result == ["message"]

    asyncio.run(scenario())

import asyncio
from dataclasses import dataclass, field
from types import SimpleNamespace

from astrbot_tweaks.patches.subagent_bypass import (
    _subagent_active,
    make_patched_step,
    make_wrapped_execute_handoff,
    with_subagent_context,
)


@dataclass
class FakeComponent:
    data: dict


@dataclass
class FakeChain:
    chain: list[FakeComponent] = field(default_factory=list)


@dataclass
class FakeResponseData:
    chain: FakeChain


@dataclass
class FakeAgentResponse:
    type: str
    data: FakeResponseData


def _response(response_type: str, payload: dict) -> FakeAgentResponse:
    return FakeAgentResponse(
        type=response_type,
        data=FakeResponseData(chain=FakeChain(chain=[FakeComponent(payload)])),
    )


class FakeRunner:
    def __init__(self) -> None:
        self.final_llm_resp = None
        self.stats = SimpleNamespace(end_time=0.0)
        self.state = None

    def _transition_state(self, state: str) -> None:
        self.state = state

    def _resolve_unconsumed_follow_ups(self) -> None:
        self.followups_resolved = True


def _original_step_with_single_tool(runner: FakeRunner):
    async def original_step(self):
        yield _response(
            "tool_call",
            {"id": "call-1", "name": "read_text_file", "args": {"path": "/tmp"}},
        )
        yield _response("tool_call_result", {"id": "call-1", "result": "file text"})

    return original_step


async def _collect(responses):
    return [response async for response in responses]


def test_patched_step_short_circuits_whitelisted_single_tool(monkeypatch) -> None:
    runner = FakeRunner()

    def fake_finalize(target, result):
        target.final_llm_resp = SimpleNamespace(completion_text=result)
        target.state = "DONE"

    monkeypatch.setattr(
        "astrbot_tweaks.patches.subagent_bypass._finalize_direct_return",
        fake_finalize,
    )

    async def scenario() -> None:
        original = _original_step_with_single_tool(runner)
        patched = make_patched_step(original, {"subagent_bypass_tools": ["read_text_file"]})
        with with_subagent_context():
            responses = await _collect(patched(runner))

        assert [response.type for response in responses] == [
            "tool_call",
            "tool_call_result",
        ]
        assert runner.final_llm_resp.completion_text == "file text"
        assert runner.state == "DONE"

    asyncio.run(scenario())


def test_patched_step_ignores_non_whitelisted_tool() -> None:
    runner = FakeRunner()

    async def scenario() -> None:
        original = _original_step_with_single_tool(runner)
        patched = make_patched_step(original, {"subagent_bypass_tools": ["fetch"]})
        with with_subagent_context():
            await _collect(patched(runner))

        assert runner.final_llm_resp is None
        assert runner.state is None

    asyncio.run(scenario())


def test_patched_step_falls_back_to_raw_result_if_cleaner_fails(
    monkeypatch,
) -> None:
    runner = FakeRunner()

    def failing_cleaner(*args, **kwargs):
        raise RuntimeError("cleaner failed")

    def fake_finalize(target, result):
        target.final_llm_resp = SimpleNamespace(completion_text=result)
        target.state = "DONE"

    monkeypatch.setattr(
        "astrbot_tweaks.patches.subagent_bypass.clean_tool_result",
        failing_cleaner,
    )
    monkeypatch.setattr(
        "astrbot_tweaks.patches.subagent_bypass._finalize_direct_return",
        fake_finalize,
    )

    async def scenario() -> None:
        original = _original_step_with_single_tool(runner)
        patched = make_patched_step(
            original,
            {"subagent_bypass_tools": ["read_text_file"]},
        )
        with with_subagent_context():
            await _collect(patched(runner))

        assert runner.final_llm_resp.completion_text == "file text"
        assert runner.state == "DONE"

    asyncio.run(scenario())


def test_patched_step_ignores_multiple_tool_calls(monkeypatch) -> None:
    runner = FakeRunner()
    finalize_calls = []
    monkeypatch.setattr(
        "astrbot_tweaks.patches.subagent_bypass._finalize_direct_return",
        lambda target, result: finalize_calls.append((target, result)),
    )

    async def original_step(self):
        for tool_id in ("call-1", "call-2"):
            yield _response(
                "tool_call",
                {"id": tool_id, "name": "read_text_file", "args": {}},
            )
            yield _response(
                "tool_call_result",
                {"id": tool_id, "result": f"text-{tool_id}"},
            )

    async def scenario() -> None:
        patched = make_patched_step(
            original_step,
            {"subagent_bypass_tools": ["read_text_file"]},
        )
        with with_subagent_context():
            await _collect(patched(runner))

        assert runner.final_llm_resp is None
        assert runner.state is None
        assert finalize_calls == []

    asyncio.run(scenario())


def test_patched_step_ignores_main_agent_calls() -> None:
    runner = FakeRunner()

    async def scenario() -> None:
        original = _original_step_with_single_tool(runner)
        patched = make_patched_step(
            original,
            {"subagent_bypass_tools": ["read_text_file"]},
        )
        await _collect(patched(runner))

        assert runner.final_llm_resp is None
        assert runner.state is None

    asyncio.run(scenario())


def test_wrapped_execute_handoff_sets_and_resets_subagent_context() -> None:
    async def original(cls):
        yield _subagent_active.get()

    class DummyExecutor:
        pass

    wrapped = make_wrapped_execute_handoff(original)
    DummyExecutor._execute_handoff = classmethod(wrapped)

    async def scenario() -> None:
        assert [result async for result in DummyExecutor._execute_handoff()] == [True]
        assert _subagent_active.get() is False

    asyncio.run(scenario())

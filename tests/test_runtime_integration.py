import asyncio
from types import SimpleNamespace

import pytest


def _has_astrbot() -> bool:
    try:
        import astrbot  # noqa: F401

        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _has_astrbot(), reason="requires AstrBot runtime")


def test_context_patch_install_restore_is_idempotent() -> None:
    from astrbot.core.agent.context.manager import ContextManager

    from astrbot_tweaks.patches.context import ContextCompressionPatch

    original = ContextManager.process
    patch = ContextCompressionPatch()
    patch.install()
    first_patched = ContextManager.process
    patch.install()
    try:
        assert ContextManager.process is first_patched
    finally:
        patch.restore()
    assert ContextManager.process is original
    assert not patch.applied


def test_skill_prompt_patch_install_restore_is_idempotent() -> None:
    import astrbot.core.astr_main_agent as main_agent_module

    from astrbot_tweaks.patches.skill_prompt import SkillPromptPatch

    original = main_agent_module.build_skills_prompt
    patch = SkillPromptPatch()
    patch.install()
    first_patched = main_agent_module.build_skills_prompt
    patch.install()
    try:
        assert main_agent_module.build_skills_prompt is first_patched
    finally:
        patch.restore()
    assert main_agent_module.build_skills_prompt is original
    assert not patch.applied


def test_llm_kwargs_patch_install_restore_is_idempotent() -> None:
    from astrbot.core.provider.sources.openai_source import ProviderOpenAIOfficial

    from astrbot_tweaks.patches.llm_kwargs import LLMKwargsPassthroughPatch

    original_prepare = ProviderOpenAIOfficial._prepare_chat_payload
    original_apply = ProviderOpenAIOfficial._apply_provider_specific_request_overrides
    patch = LLMKwargsPassthroughPatch()

    patch.install()
    first_prepare = ProviderOpenAIOfficial._prepare_chat_payload
    patch.install()
    try:
        assert ProviderOpenAIOfficial._prepare_chat_payload is first_prepare
        assert ProviderOpenAIOfficial._prepare_chat_payload is not original_prepare
        assert patch.applied
    finally:
        patch.restore()

    assert ProviderOpenAIOfficial._prepare_chat_payload is original_prepare
    assert (
        ProviderOpenAIOfficial._apply_provider_specific_request_overrides
        is original_apply
    )
    assert not patch.applied


def test_subagent_direct_return_patch_install_restore_is_idempotent() -> None:
    from astrbot.core.agent.runners.tool_loop_agent_runner import ToolLoopAgentRunner
    from astrbot.core.astr_agent_tool_exec import FunctionToolExecutor

    from astrbot_tweaks.patches.subagent_bypass import SubAgentDirectReturnPatch

    original_execute_handoff = FunctionToolExecutor.__dict__[
        "_execute_handoff"
    ].__func__
    original_step = ToolLoopAgentRunner.step
    patch = SubAgentDirectReturnPatch()

    patch.install({"subagent_bypass_tools": ["read_text_file"]})
    first_step = ToolLoopAgentRunner.step
    patch.install({"subagent_bypass_tools": ["fetch"]})
    try:
        assert ToolLoopAgentRunner.step is first_step
        assert FunctionToolExecutor._execute_handoff is not original_execute_handoff
        assert patch.applied
    finally:
        patch.restore()

    assert (
        FunctionToolExecutor.__dict__["_execute_handoff"].__func__
        is original_execute_handoff
    )
    assert ToolLoopAgentRunner.step is original_step
    assert not patch.applied


def test_subagent_direct_return_skips_second_llm_call() -> None:
    from astrbot.core.agent.hooks import BaseAgentRunHooks
    from astrbot.core.agent.runners.tool_loop_agent_runner import ToolLoopAgentRunner
    from astrbot.core.agent.tool import FunctionTool, ToolSet
    from astrbot.core.astr_agent_tool_exec import FunctionToolExecutor
    from astrbot.core.provider.entities import LLMResponse, ProviderRequest

    from astrbot_tweaks.patches.subagent_bypass import (
        SubAgentDirectReturnPatch,
        with_subagent_context,
    )

    class FakeProvider:
        def __init__(self) -> None:
            self.provider_config = {"id": "fake", "max_context_tokens": 0}
            self.provider_settings = {}
            self.calls = 0

        async def text_chat(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return LLMResponse(
                    role="assistant",
                    tools_call_name=["read_text_file"],
                    tools_call_args=[{"path": "/tmp/file"}],
                    tools_call_ids=["call-1"],
                )
            raise AssertionError("second LLM call should not happen")

    async def handler(event, *, path):
        assert path == "/tmp/file"
        return "file text"

    patch = SubAgentDirectReturnPatch()
    patch.install({"subagent_bypass_tools": ["read_text_file"]})
    try:
        tool = FunctionTool(
            name="read_text_file",
            description="read",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            handler=handler,
        )
        tools = ToolSet()
        tools.add_tool(tool)
        provider = FakeProvider()
        runner = ToolLoopAgentRunner()
        run_context = SimpleNamespace(
            context=SimpleNamespace(
                context=SimpleNamespace(),
                event=SimpleNamespace(),
            ),
            tool_call_timeout=5,
        )

        async def scenario() -> None:
            await runner.reset(
                provider=provider,
                request=ProviderRequest(prompt="read it", func_tool=tools),
                run_context=run_context,
                tool_executor=FunctionToolExecutor(),
                agent_hooks=BaseAgentRunHooks(),
                streaming=False,
            )
            async for _ in runner.step_until_done(3):
                pass

        with with_subagent_context():
            asyncio.run(scenario())
        final = runner.get_final_llm_resp()

        assert provider.calls == 1
        assert final is not None
        assert final.completion_text == "file text"
        assert final.role == "assistant"
        assert runner.done()
    finally:
        patch.restore()


def test_default_registry_status_shape() -> None:
    from astrbot_tweaks.registry import get_patch_status

    status = get_patch_status()
    assert status["version"] == "v0.2.2"
    assert "context_compression_tweak" in status
    assert "minimal_skill_rules" in status
    assert "llm_kwargs_passthrough" in status
    assert "subagent_direct_return" in status

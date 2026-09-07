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


def test_default_registry_status_shape() -> None:
    from astrbot_tweaks.registry import get_patch_status

    status = get_patch_status()
    assert status["version"] == "v0.1.0"
    assert "context_compression_tweak" in status
    assert "minimal_skill_rules" in status

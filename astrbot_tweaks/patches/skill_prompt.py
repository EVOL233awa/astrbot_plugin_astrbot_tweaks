"""Skills 提示词精简补丁。"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from ..prompt_utils import build_minimal_skills_prompt

logger = logging.getLogger(__name__)

BuildSkillsPrompt = Callable[..., str]


def make_build_skills_prompt_patch(
    original: BuildSkillsPrompt,
) -> BuildSkillsPrompt:
    """生成带回退的 build_skills_prompt 包装函数。"""

    def patched_build_skills_prompt(skills: Any) -> str:
        try:
            official = original(skills)
        except Exception as exc:
            logger.exception("Astrbot Tweaks original skill prompt failed: %s", exc)
            raise

        if not isinstance(official, str):
            return official
        try:
            return build_minimal_skills_prompt(official)
        except Exception as exc:
            logger.exception("Astrbot Tweaks skill prompt patch failed: %s", exc)
            return official

    return patched_build_skills_prompt


class SkillPromptPatch:
    """包装 astr_main_agent.build_skills_prompt，并在恢复时还原原函数。"""

    _original: BuildSkillsPrompt | None = None
    _module = None

    @property
    def applied(self) -> bool:
        return self._original is not None

    def install(self) -> None:
        """安装补丁；重复调用不产生双重包装。"""
        if self.applied:
            return

        import astrbot.core.astr_main_agent as main_agent_module

        original = getattr(main_agent_module, "build_skills_prompt", None)
        if not callable(original):
            raise RuntimeError(
                "astr_main_agent.build_skills_prompt is missing or not callable",
            )

        main_agent_module.build_skills_prompt = make_build_skills_prompt_patch(
            original,
        )
        self._original = original
        self._module = main_agent_module
        logger.info("Astrbot Tweaks: minimal skill rules patch installed.")

    def restore(self) -> None:
        """恢复原始函数；未安装时 no-op。"""
        if not self.applied:
            return

        try:
            if self._module is not None:
                self._module.build_skills_prompt = self._original
        finally:
            self._original = None
            self._module = None

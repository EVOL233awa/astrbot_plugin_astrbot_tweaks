"""插件配置到补丁的注册与生命周期管理。"""

from __future__ import annotations

import logging
from typing import Any

from .compat import PLUGIN_VERSION, is_astrbot_version_supported
from .patches.context import ContextCompressionPatch
from .patches.empty_output_retry import EmptyOutputRetryPatch
from .patches.llm_kwargs import LLMKwargsPassthroughPatch
from .patches.reasoning_guard import ReasoningOnlyGuardPatch
from .patches.skill_prompt import SkillPromptPatch
from .patches.subagent_bypass import SubAgentDirectReturnPatch

logger = logging.getLogger(__name__)

_DEFAULT_ENABLED_PATCHES = {
    "context_compression_tweak",
    "empty_output_retry",
    "minimal_skill_rules",
    "reasoning_only_guard",
}


class TweakRegistry:
    """统一安装、恢复并报告各运行时补丁。"""

    def __init__(self) -> None:
        self._patches: dict[str, Any] = {
            "context_compression_tweak": ContextCompressionPatch(),
            "empty_output_retry": EmptyOutputRetryPatch(),
            "minimal_skill_rules": SkillPromptPatch(),
            "reasoning_only_guard": ReasoningOnlyGuardPatch(),
            "llm_kwargs_passthrough": LLMKwargsPassthroughPatch(),
            "subagent_direct_return": SubAgentDirectReturnPatch(),
        }

    def apply(self, config: dict[str, Any] | None) -> None:
        """根据配置应用补丁；重复调用前先恢复，避免双重包装。"""
        self.restore()

        cfg = config or {}
        if not cfg.get("enabled", True):
            return

        if not is_astrbot_version_supported():
            logger.warning(
                "Astrbot Tweaks %s: unsupported or unknown AstrBot version; "
                "runtime patches disabled. Plugin remains loaded.",
                PLUGIN_VERSION,
            )
            return

        for key, patch in self._patches.items():
            if not cfg.get(key, key in _DEFAULT_ENABLED_PATCHES):
                continue
            try:
                if key in {
                    "empty_output_retry",
                    "llm_kwargs_passthrough",
                    "reasoning_only_guard",
                    "subagent_direct_return",
                }:
                    patch.install(cfg)
                else:
                    patch.install()
            except Exception as exc:
                logger.exception(
                    "Astrbot Tweaks: %s patch skipped: %s",
                    key,
                    exc,
                )

    def restore(self) -> None:
        """恢复所有原始方法，保证插件重载或卸载后不残留。"""
        for patch in self._patches.values():
            try:
                patch.restore()
            except Exception as exc:
                logger.exception("Astrbot Tweaks failed to restore patch: %s", exc)

    def status(self) -> dict[str, Any]:
        """返回当前补丁状态，用于日志和测试。"""
        return {
            "version": PLUGIN_VERSION,
            "compatible": is_astrbot_version_supported(),
            **{
                key: bool(getattr(patch, "applied", False))
                for key, patch in self._patches.items()
            },
        }


_default_registry = TweakRegistry()


def install_patches(config: dict[str, Any] | None) -> None:
    """模块级入口，默认注册表执行配置应用。"""
    _default_registry.apply(config)


def restore_patches() -> None:
    """模块级入口，恢复默认注册表中的所有补丁。"""
    _default_registry.restore()


def get_patch_status() -> dict[str, Any]:
    """模块级入口，返回默认注册表状态。"""
    return _default_registry.status()

"""Astrbot Tweaks 插件入口。"""

from __future__ import annotations

from typing import Any

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star

from .astrbot_tweaks.compat import PLUGIN_VERSION
from .astrbot_tweaks.prompt_utils import remove_computer_use_warning
from .astrbot_tweaks.registry import (
    get_patch_status,
    install_patches,
    restore_patches,
)


class AstrbotTweaks(Star):
    """把 AstrBot 的三项自定义调整做成可配置运行时 tweak。"""

    def __init__(self, context: Context, config: Any | None = None) -> None:
        super().__init__(context)
        self.context = context
        self.config = config if config is not None else {}
        self._apply_patches()

    def _config_value(self, key: str, default: Any) -> Any:
        try:
            if hasattr(self.config, "get"):
                value = self.config.get(key, default)
                return value if value is not None else default
        except Exception:
            pass
        return default

    def _apply_patches(self) -> None:
        try:
            install_patches(
                {
                    "enabled": bool(self._config_value("enabled", True)),
                    "context_compression_tweak": bool(
                        self._config_value("context_compression_tweak", True)
                    ),
                    "minimal_skill_rules": bool(
                        self._config_value("minimal_skill_rules", True)
                    ),
                }
            )
        except Exception as exc:
            logger.exception("Astrbot Tweaks failed to install patches: %s", exc)

        logger.info(
            "Astrbot Tweaks %s loaded: enabled=%s remove_computer_use_warning=%s status=%s",
            PLUGIN_VERSION,
            self._config_value("enabled", True),
            self._config_value("remove_computer_use_warning", True),
            get_patch_status(),
        )

    @filter.on_llm_request()
    async def on_llm_request(
        self,
        event: AstrMessageEvent,
        req: ProviderRequest,
    ) -> None:
        """在 LLM 请求前移除官方英文 Computer Use 提示。"""
        if not self._config_value("enabled", True):
            return
        if not self._config_value("remove_computer_use_warning", True):
            return
        if not req:
            return

        prompt = getattr(req, "system_prompt", None)
        if not isinstance(prompt, str):
            return

        try:
            cleaned = remove_computer_use_warning(prompt)
        except Exception as exc:
            logger.error("Astrbot Tweaks failed to clean system prompt: %s", exc)
            return
        if cleaned != prompt:
            req.system_prompt = cleaned

    async def terminate(self) -> None:
        """插件卸载或重载时恢复 AstrBot 原始行为。"""
        restore_patches()
        logger.info(
            "Astrbot Tweaks %s unloaded: runtime patches restored.", PLUGIN_VERSION
        )

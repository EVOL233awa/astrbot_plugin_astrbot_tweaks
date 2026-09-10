"""配置空正文响应的自动重试次数。"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_EMPTY_OUTPUT_RETRY_ATTEMPTS = 3
MIN_EMPTY_OUTPUT_RETRY_ATTEMPTS = 1
MAX_EMPTY_OUTPUT_RETRY_ATTEMPTS = 10


def normalize_empty_output_retry_attempts(value: Any) -> int:
    """Clamp retry attempts to a safe range."""

    try:
        attempts = int(value)
    except (TypeError, ValueError):
        attempts = DEFAULT_EMPTY_OUTPUT_RETRY_ATTEMPTS
    return min(
        max(attempts, MIN_EMPTY_OUTPUT_RETRY_ATTEMPTS),
        MAX_EMPTY_OUTPUT_RETRY_ATTEMPTS,
    )


class EmptyOutputRetryPatch:
    """调整 ToolLoopAgentRunner 的空输出重试次数。"""

    def __init__(self, runner_class: type | None = None) -> None:
        self.applied = False
        self.attempts = DEFAULT_EMPTY_OUTPUT_RETRY_ATTEMPTS
        self._runner_class = runner_class
        self._original_attempts: int | None = None

    def _resolve_runner(self) -> type:
        if self._runner_class is not None:
            return self._runner_class
        from astrbot.core.agent.runners.tool_loop_agent_runner import (
            ToolLoopAgentRunner,
        )

        return ToolLoopAgentRunner

    def install(self, config: dict[str, Any] | None = None) -> None:
        """安装配置值并保存原始重试次数。"""

        if self.applied:
            return

        runner = self._resolve_runner()
        original = getattr(runner, "EMPTY_OUTPUT_RETRY_ATTEMPTS", None)
        if not isinstance(original, int):
            raise RuntimeError(
                "AstrBot ToolLoopAgentRunner.EMPTY_OUTPUT_RETRY_ATTEMPTS is unavailable"
            )

        cfg = config or {}
        attempts = normalize_empty_output_retry_attempts(
            cfg.get(
                "empty_output_retry_attempts",
                DEFAULT_EMPTY_OUTPUT_RETRY_ATTEMPTS,
            )
        )
        self._runner_class = runner
        self._original_attempts = original
        self.attempts = attempts
        runner.EMPTY_OUTPUT_RETRY_ATTEMPTS = attempts
        self.applied = True
        logger.info(
            "Astrbot Tweaks: empty-output retry attempts set to %s.",
            attempts,
        )

    def restore(self) -> None:
        """恢复原始重试次数。"""

        if not self.applied or self._runner_class is None:
            return

        if self._original_attempts is not None:
            self._runner_class.EMPTY_OUTPUT_RETRY_ATTEMPTS = self._original_attempts
        self._original_attempts = None
        self.applied = False

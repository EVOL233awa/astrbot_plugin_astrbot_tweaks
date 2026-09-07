"""AstrBot 版本与兼容性判断。"""

from __future__ import annotations

import re
from typing import Any

PLUGIN_VERSION = "v0.1.0"
MIN_SUPPORTED_VERSION = (4, 27, 0)
MAX_EXCLUDED_VERSION = (5, 0, 0)

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?")


def parse_astrbot_version(version: str) -> tuple[int, int, int] | None:
    """把 AstrBot 版本号解析为可用于范围判断的元组。"""
    if not isinstance(version, str) or not version.strip():
        return None
    match = _VERSION_RE.match(version.strip())
    if not match:
        return None
    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3) or 0),
    )


def current_astrbot_version() -> str | None:
    """读取当前 AstrBot 版本；读取失败时返回 None。"""
    try:
        import astrbot
    except Exception:
        return None

    version = getattr(astrbot, "__version__", "")
    return version if isinstance(version, str) and version else None


def is_astrbot_version_supported(version: str | None = None) -> bool:
    """检查 AstrBot 是否处于插件声明的已知兼容区间。"""
    if version is None:
        version = current_astrbot_version()

    parsed = parse_astrbot_version(version or "")
    if parsed is None:
        return False
    return MIN_SUPPORTED_VERSION <= parsed < MAX_EXCLUDED_VERSION


def safe_import_attribute(module_name: str, attribute: str) -> Any | None:
    """安全读取 AstrBot 内部对象，升级后缺失时返回 None。"""
    try:
        module = __import__(module_name, fromlist=[attribute])
    except Exception:
        return None
    return getattr(module, attribute, None)

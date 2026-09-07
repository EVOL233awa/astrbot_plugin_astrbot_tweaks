"""纯提示词转换工具，不依赖 AstrBot 运行时。"""

from __future__ import annotations

import re

COMPUTER_USE_WARNING = (
    "User has not enabled the Computer Use feature. "
    "You cannot use shell or Python to perform skills. "
    "If you need to use these capabilities, ask the user to enable Computer Use in the AstrBot WebUI -> Config."
)

MINIMAL_SKILL_RULES = (
    "### Skill rules\n\n"
    "1. 技能列表是完整清单；没有明确触发或明显匹配时不主动调用。\n"
    "2. 执行技能前必须用当前可用工具读取对应的 SKILL.md，禁止凭描述脑补内容。\n"
    "3. 只读 SKILL.md 直接引用的文件，禁止遍历或全量读取技能目录。\n"
    "4. 技能执行失败时不得伪称成功，简短说明后继续。\n"
)

_SKILLS_BLOCK_RE = re.compile(
    r"### Available skills\n\n(?P<skills>.*?)\n\n### Skill rules",
    re.DOTALL,
)


def remove_computer_use_warning(prompt: str) -> str:
    """从 system prompt 中移除官方英文 Computer Use 提示。"""
    if not prompt or COMPUTER_USE_WARNING not in prompt:
        return prompt
    cleaned = prompt.replace(COMPUTER_USE_WARNING, "")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip("\n")
    return cleaned + "\n" if cleaned else ""


def build_minimal_skills_prompt(official_prompt: str) -> str:
    """把官方长技能规则替换为精简规则，同时保留动态技能列表。"""
    if not official_prompt:
        return official_prompt

    normalized = official_prompt.replace("\r\n", "\n")
    match = _SKILLS_BLOCK_RE.search(normalized)
    if not match:
        return official_prompt

    skills_block = match.group("skills").strip("\n")
    if not skills_block:
        return official_prompt

    return (
        f"## Skills\n\n### Available skills\n\n{skills_block}\n\n{MINIMAL_SKILL_RULES}"
    )

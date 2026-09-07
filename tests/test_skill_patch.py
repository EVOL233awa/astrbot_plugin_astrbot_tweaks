from astrbot_tweaks.patches.skill_prompt import make_build_skills_prompt_patch
from astrbot_tweaks.prompt_utils import (
    MINIMAL_SKILL_RULES,
    build_minimal_skills_prompt,
)

OFFICIAL_SKILLS_PROMPT = (
    "## Skills\n\n"
    "### Available skills\n\n"
    "- **dynamic_state_switcher**: 动态状态切换。\n"
    "  File: `<skills_root>/dynamic_state_switcher/SKILL.md`\n\n"
    "### Skill rules\n\n"
    "1. **Discovery** - The list above is the complete skill inventory.\n"
)


def test_wrapped_prompt_uses_minimal_rules() -> None:
    calls = []

    def original(skills):
        calls.append(skills)
        return OFFICIAL_SKILLS_PROMPT

    patched = make_build_skills_prompt_patch(original)
    result = patched(["dynamic_state_switcher"])

    assert calls == [["dynamic_state_switcher"]]
    assert "dynamic_state_switcher" in result
    assert "Discovery" not in result
    assert "1. 技能列表是完整清单" in result


def test_wrapped_prompt_unknown_shape_returns_official() -> None:
    custom = "## Skills\n\ncustom\n"

    def original(skills):
        return custom

    assert make_build_skills_prompt_patch(original)(None) == custom


def test_build_minimal_skills_prompt_matches_wrapper_output() -> None:
    assert build_minimal_skills_prompt(OFFICIAL_SKILLS_PROMPT) == (
        "## Skills\n\n"
        "### Available skills\n\n"
        "- **dynamic_state_switcher**: 动态状态切换。\n"
        "  File: `<skills_root>/dynamic_state_switcher/SKILL.md`\n\n"
        f"{MINIMAL_SKILL_RULES}"
    )

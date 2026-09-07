from astrbot_tweaks.prompt_utils import (
    COMPUTER_USE_WARNING,
    MINIMAL_SKILL_RULES,
    build_minimal_skills_prompt,
    remove_computer_use_warning,
)

OFFICIAL_SKILLS_PROMPT = (
    "## Skills\n\n"
    "You have specialized skills - reusable instruction bundles stored "
    "in `SKILL.md` files.\n\n"
    "### Available skills\n\n"
    "- **dynamic_state_switcher**: 动态状态切换。\n"
    "  File: `<skills_root>/dynamic_state_switcher/SKILL.md`\n\n"
    "### Skill rules\n\n"
    "1. **Discovery** - The list above is the complete skill inventory.\n"
    "2. **When to trigger** - Use a skill if the user names it explicitly.\n"
    "3. **Mandatory grounding** - Before executing any skill you MUST "
    "first read its `SKILL.md`.\n"
)


def test_build_minimal_skills_prompt_preserves_skills() -> None:
    result = build_minimal_skills_prompt(OFFICIAL_SKILLS_PROMPT)
    assert "dynamic_state_switcher" in result
    assert "### Available skills" in result
    assert "### Skill rules" in result
    assert "1. 技能列表是完整清单" in result
    assert "Discovery" not in result


def test_build_minimal_skills_prompt_unknown_shape_fallback() -> None:
    prompt = "## Skills\n\ncustom prompt\n"
    assert build_minimal_skills_prompt(prompt) == prompt


def test_remove_computer_use_warning() -> None:
    prompt = "Persona\n\n" + COMPUTER_USE_WARNING + "\n\nIdentifier\n"
    result = remove_computer_use_warning(prompt)
    assert COMPUTER_USE_WARNING not in result
    assert "Persona" in result
    assert "Identifier" in result


def test_remove_computer_use_warning_noop() -> None:
    prompt = "Persona\n\nIdentifier\n"
    assert remove_computer_use_warning(prompt) == prompt


def test_minimal_skill_rules_is_compact() -> None:
    assert "技能列表是完整清单" in MINIMAL_SKILL_RULES
    assert len(MINIMAL_SKILL_RULES) < len(OFFICIAL_SKILLS_PROMPT)

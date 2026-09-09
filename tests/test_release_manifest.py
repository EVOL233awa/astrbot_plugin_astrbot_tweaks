import json
from pathlib import Path

import pytest

from astrbot_tweaks.compat import PLUGIN_VERSION
from astrbot_tweaks.patches.subagent_bypass import DEFAULT_SUBAGENT_BYPASS_TOOLS

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[1]


def test_metadata_required_fields_and_repo() -> None:
    metadata = yaml.safe_load((ROOT / "metadata.yaml").read_text(encoding="utf-8"))
    for field in ("name", "desc", "version", "author", "repo"):
        assert isinstance(metadata.get(field), str)
        assert metadata[field].strip()
    assert metadata["name"] == "astrbot_plugin_astrbot_tweaks"
    assert metadata["repo"].startswith("https://github.com/")


def test_metadata_version_matches_code() -> None:
    metadata = yaml.safe_load((ROOT / "metadata.yaml").read_text(encoding="utf-8"))
    assert metadata["version"] == PLUGIN_VERSION


def test_config_schema_defaults_match_plugin_intent() -> None:
    schema = json.loads((ROOT / "_conf_schema.json").read_text(encoding="utf-8"))
    assert schema["enabled"]["default"] is True
    assert schema["context_compression_tweak"]["default"] is True
    assert schema["remove_computer_use_warning"]["default"] is True
    assert schema["minimal_skill_rules"]["default"] is True
    assert schema["llm_kwargs_passthrough"]["default"] is False
    assert schema["subagent_direct_return"]["default"] is False
    assert schema["subagent_bypass_tools"]["default"] == list(
        DEFAULT_SUBAGENT_BYPASS_TOOLS
    )
    assert schema["subagent_search_top_k"]["default"] == 4
    assert schema["subagent_direct_max_chars"]["default"] == 30000
    assert schema["subagent_clean_fetch_html"]["default"] is True
    assert schema["subagent_clean_web_search"]["default"] is True

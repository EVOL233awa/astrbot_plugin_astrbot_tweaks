from astrbot_tweaks.compat import (
    PLUGIN_VERSION,
    is_astrbot_version_supported,
    parse_astrbot_version,
)


def test_plugin_version_is_v010() -> None:
    assert PLUGIN_VERSION == "v0.1.0"


def test_parse_astrbot_version_full() -> None:
    assert parse_astrbot_version("4.27.5") == (4, 27, 5)


def test_parse_astrbot_version_without_patch() -> None:
    assert parse_astrbot_version("4.27") == (4, 27, 0)


def test_parse_astrbot_version_invalid() -> None:
    assert parse_astrbot_version("") is None
    assert parse_astrbot_version("next") is None


def test_supported_version_boundaries() -> None:
    assert is_astrbot_version_supported("4.27.0")
    assert is_astrbot_version_supported("4.27.5")
    assert is_astrbot_version_supported("4.99.0")
    assert not is_astrbot_version_supported("4.26.9")
    assert not is_astrbot_version_supported("5.0.0")
    assert not is_astrbot_version_supported("unknown")

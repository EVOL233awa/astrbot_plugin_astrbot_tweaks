from astrbot_tweaks import registry
from astrbot_tweaks.patches.empty_output_retry import EmptyOutputRetryPatch
from astrbot_tweaks.patches.llm_kwargs import LLMKwargsPassthroughPatch
from astrbot_tweaks.patches.reasoning_guard import ReasoningOnlyGuardPatch
from astrbot_tweaks.patches.subagent_bypass import SubAgentDirectReturnPatch


class FakePatch:
    def __init__(self, key: str) -> None:
        self.key = key
        self.applied = False
        self.install_count = 0
        self.restore_count = 0

    def install(self) -> None:
        self.install_count += 1
        self.applied = True

    def restore(self) -> None:
        self.restore_count += 1
        self.applied = False


def _fake_registry(patch_keys: list[str]) -> registry.TweakRegistry:
    reg = registry.TweakRegistry()
    reg._patches = {key: FakePatch(key) for key in patch_keys}
    return reg


def test_apply_only_enabled_patches(monkeypatch) -> None:
    monkeypatch.setattr(registry, "is_astrbot_version_supported", lambda: True)
    reg = _fake_registry(["context_compression_tweak", "minimal_skill_rules"])

    reg.apply(
        {
            "enabled": True,
            "context_compression_tweak": True,
            "minimal_skill_rules": False,
        }
    )

    assert reg._patches["context_compression_tweak"].applied
    assert not reg._patches["minimal_skill_rules"].applied
    assert reg.status()["context_compression_tweak"] is True
    assert reg.status()["minimal_skill_rules"] is False


def test_disabled_config_restores_before_return(monkeypatch) -> None:
    monkeypatch.setattr(registry, "is_astrbot_version_supported", lambda: True)
    reg = _fake_registry(["context_compression_tweak"])
    reg.apply({"enabled": True, "context_compression_tweak": True})
    reg.apply({"enabled": False})
    assert not reg._patches["context_compression_tweak"].applied


def test_unsupported_version_disables_patches(monkeypatch) -> None:
    monkeypatch.setattr(registry, "is_astrbot_version_supported", lambda: False)
    reg = _fake_registry(["context_compression_tweak"])
    reg.apply({"enabled": True, "context_compression_tweak": True})
    assert not reg._patches["context_compression_tweak"].applied


def test_reapply_is_idempotent(monkeypatch) -> None:
    monkeypatch.setattr(registry, "is_astrbot_version_supported", lambda: True)
    reg = _fake_registry(["context_compression_tweak"])
    config = {"enabled": True, "context_compression_tweak": True}
    reg.apply(config)
    reg.apply(config)
    assert reg._patches["context_compression_tweak"].install_count == 2
    assert reg._patches["context_compression_tweak"].restore_count == 2
    assert reg._patches["context_compression_tweak"].applied


def test_registry_registers_v020_patches_disabled_by_default() -> None:
    reg = registry.TweakRegistry()
    assert isinstance(reg._patches["empty_output_retry"], EmptyOutputRetryPatch)
    assert isinstance(reg._patches["llm_kwargs_passthrough"], LLMKwargsPassthroughPatch)
    assert isinstance(reg._patches["subagent_direct_return"], SubAgentDirectReturnPatch)
    assert isinstance(reg._patches["reasoning_only_guard"], ReasoningOnlyGuardPatch)

    reg.apply({"enabled": True})
    assert not reg._patches["llm_kwargs_passthrough"].applied
    assert not reg._patches["subagent_direct_return"].applied


def test_registry_passes_new_settings_to_patches(monkeypatch) -> None:
    received = {}

    class FakePatch:
        applied = False

        def __init__(self, key):
            self.key = key

        def install(self, config=None):
            received[self.key] = config
            self.applied = True

        def restore(self):
            self.applied = False

    monkeypatch.setattr(registry, "is_astrbot_version_supported", lambda: True)
    reg = registry.TweakRegistry()
    reg._patches = {
        key: FakePatch(key)
        for key in ("empty_output_retry", "llm_kwargs_passthrough")
    }
    reg.apply(
        {
            "enabled": True,
            "empty_output_retry": True,
            "empty_output_retry_attempts": 7,
            "llm_kwargs_passthrough": True,
            "llm_kwargs_allowlist": ["top_p"],
        }
    )

    assert received["empty_output_retry"]["empty_output_retry_attempts"] == 7
    assert received["llm_kwargs_passthrough"]["llm_kwargs_allowlist"] == ["top_p"]


def test_registry_passes_subagent_config_to_patch(monkeypatch) -> None:
    received = {}

    class FakeSubAgentPatch:
        applied = False

        def install(self, config=None):
            received.update(config or {})
            self.applied = True

        def restore(self):
            self.applied = False

    monkeypatch.setattr(
        registry,
        "SubAgentDirectReturnPatch",
        FakeSubAgentPatch,
    )
    monkeypatch.setattr(registry, "is_astrbot_version_supported", lambda: True)
    reg = registry.TweakRegistry()
    reg._patches["subagent_direct_return"] = FakeSubAgentPatch()
    reg.apply(
        {
            "enabled": True,
            "subagent_direct_return": True,
            "subagent_bypass_tools": ["read_text_file"],
            "subagent_direct_max_chars": 1200,
        }
    )

    assert reg._patches["subagent_direct_return"].applied
    assert received["subagent_bypass_tools"] == ["read_text_file"]
    assert received["subagent_direct_max_chars"] == 1200

from astrbot_tweaks import registry


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

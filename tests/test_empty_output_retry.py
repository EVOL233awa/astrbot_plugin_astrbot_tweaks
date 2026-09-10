from __future__ import annotations

from astrbot_tweaks.patches.empty_output_retry import (
    DEFAULT_EMPTY_OUTPUT_RETRY_ATTEMPTS,
    EmptyOutputRetryPatch,
    normalize_empty_output_retry_attempts,
)


def test_normalize_empty_output_retry_attempts() -> None:
    assert normalize_empty_output_retry_attempts(None) == 3
    assert normalize_empty_output_retry_attempts("bad") == 3
    assert normalize_empty_output_retry_attempts(0) == 1
    assert normalize_empty_output_retry_attempts(7) == 7
    assert normalize_empty_output_retry_attempts(99) == 10


def test_patch_install_restore_and_idempotence() -> None:
    class Runner:
        EMPTY_OUTPUT_RETRY_ATTEMPTS = DEFAULT_EMPTY_OUTPUT_RETRY_ATTEMPTS

    original = Runner.EMPTY_OUTPUT_RETRY_ATTEMPTS
    patch = EmptyOutputRetryPatch(runner_class=Runner)

    patch.install({"empty_output_retry_attempts": 6})
    assert Runner.EMPTY_OUTPUT_RETRY_ATTEMPTS == 6
    assert patch.applied

    patch.install({"empty_output_retry_attempts": 9})
    assert Runner.EMPTY_OUTPUT_RETRY_ATTEMPTS == 6

    patch.restore()
    assert Runner.EMPTY_OUTPUT_RETRY_ATTEMPTS == original
    assert not patch.applied

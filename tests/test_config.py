from __future__ import annotations

from pathlib import Path

import pytest

from fabric_poc_automation.config import PocConfig

ROOT = Path(__file__).resolve().parents[1]


def test_default_config_is_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ["WHEEL_SOURCE", "SCALE_PROFILE", "ENABLE_SCALE_TEST", "RUN_SMOKE_TEST"]:
        monkeypatch.delenv(name, raising=False)
    config = PocConfig.load(ROOT, ROOT / "does-not-exist.env")
    assert config.wheel_source == "sample"
    assert config.wheel_import_name == "fabric_custom_wheel_sample"
    assert config.scale_profile.name == "smoke"
    assert config.run_smoke_test is False
    assert config.spark_runtime == "1.3"


def test_benchmark_is_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCALE_PROFILE", "benchmark")
    monkeypatch.setenv("ENABLE_SCALE_TEST", "false")
    with pytest.raises(ValueError, match="ENABLE_SCALE_TEST=true"):
        PocConfig.load(ROOT, ROOT / "does-not-exist.env")


def test_custom_source_requires_wheel_and_import(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WHEEL_SOURCE", "custom")
    monkeypatch.delenv("WHEEL_PATH", raising=False)
    monkeypatch.delenv("WHEEL_IMPORT_NAME", raising=False)
    with pytest.raises(ValueError, match="requires WHEEL_PATH"):
        PocConfig.load(ROOT, ROOT / "does-not-exist.env")


def test_custom_source_requires_import_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WHEEL_SOURCE", "custom")
    monkeypatch.setenv("WHEEL_PATH", "vendor/wheels/example.whl")
    monkeypatch.delenv("WHEEL_IMPORT_NAME", raising=False)
    with pytest.raises(ValueError, match="requires WHEEL_IMPORT_NAME"):
        PocConfig.load(ROOT, ROOT / "does-not-exist.env")

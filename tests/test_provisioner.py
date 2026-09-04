from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from fabric_poc_automation.config import PocConfig
from fabric_poc_automation.provisioner import PocProvisioner

ROOT = Path(__file__).resolve().parents[1]


def test_wheel_contract_accepts_submodule_import(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    wheel = tmp_path / "example-1.0-py3-none-any.whl"
    wheel.touch()
    config = replace(
        PocConfig.load(ROOT, ROOT / "does-not-exist.env"),
        wheel_import_name="example.submodule",
        wheel_distribution_name="example",
    )
    metadata = {"name": "example", "top_level_modules": ["example"]}
    monkeypatch.setattr("fabric_poc_automation.provisioner.inspect_wheel", lambda _path: metadata)
    assert PocProvisioner(config, None).validate_wheel_contract(wheel) == metadata


def test_wheel_contract_rejects_wrong_import(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    wheel = tmp_path / "example-1.0-py3-none-any.whl"
    wheel.touch()
    config = replace(PocConfig.load(ROOT, ROOT / "does-not-exist.env"), wheel_import_name="wrong")
    metadata = {"name": "fabric-custom-wheel-sample", "top_level_modules": ["example"]}
    monkeypatch.setattr("fabric_poc_automation.provisioner.inspect_wheel", lambda _path: metadata)
    with pytest.raises(RuntimeError, match="top-level modules"):
        PocProvisioner(config, None).validate_wheel_contract(wheel)

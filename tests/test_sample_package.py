from __future__ import annotations

from fabric_custom_wheel_sample import SampleTransformer, health, transform


def test_sample_is_deterministic_and_clearly_marked() -> None:
    assert transform("123-45-6789") == transform("123-45-6789")
    assert transform("123-45-6789") != transform("987-65-4321")
    assert transform("123-45-6789").startswith("SAMPLE_")


def test_sample_preserves_null() -> None:
    assert transform(None) is None


def test_health_disclaims_security() -> None:
    result = health()
    assert result["ok"] is True
    assert result["provider"] == "SAMPLE"
    assert "not a security" in result["warning"].lower()


def test_sample_class_is_executor_friendly() -> None:
    assert SampleTransformer().transform("x") == transform("x")

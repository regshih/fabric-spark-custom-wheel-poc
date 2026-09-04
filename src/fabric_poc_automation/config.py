"""Typed, environment-driven configuration for the Fabric wheel POC."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false, got {raw!r}")


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return default if raw in (None, "") else int(raw)


@dataclass(frozen=True)
class ScaleProfile:
    name: str
    rows: int
    partitions: int


@dataclass(frozen=True)
class PocConfig:
    root: Path
    workspace_id: str
    workspace_name: str
    capacity_id: str
    environment_name: str
    spark_runtime: str
    lakehouse_name: str
    pipeline_name: str
    wheel_source: str
    wheel_path: str
    wheel_import_name: str
    wheel_distribution_name: str
    wheel_test_callable: str
    enable_resource_creation: bool
    enable_scale_test: bool
    scale_profile: ScaleProfile
    run_smoke_test: bool
    set_workspace_default_environment: bool
    poll_seconds: int
    operation_timeout_seconds: int
    transformed_columns: tuple[str, ...]
    tables: dict[str, str]

    @classmethod
    def load(cls, root: Path | None = None, env_file: Path | None = None) -> PocConfig:
        project_root = (root or Path(__file__).resolve().parents[2]).resolve()
        load_dotenv(env_file or project_root / ".env", override=False)
        raw: dict[str, Any] = yaml.safe_load(
            (project_root / "config" / "poc.yaml").read_text(encoding="utf-8")
        )
        profile_name = os.getenv("SCALE_PROFILE", "smoke").strip().lower()
        if profile_name not in raw["profiles"]:
            raise ValueError(f"Unknown SCALE_PROFILE {profile_name!r}")
        if profile_name == "benchmark" and not _bool("ENABLE_SCALE_TEST", False):
            raise ValueError("benchmark profile requires ENABLE_SCALE_TEST=true")
        profile = raw["profiles"][profile_name]

        wheel_source = os.getenv("WHEEL_SOURCE", "sample").strip().lower()
        if wheel_source not in {"sample", "custom"}:
            raise ValueError("WHEEL_SOURCE must be 'sample' or 'custom'")
        wheel_path = os.getenv("WHEEL_PATH", "").strip()
        import_name = os.getenv("WHEEL_IMPORT_NAME", "").strip()
        distribution_name = os.getenv("WHEEL_DISTRIBUTION_NAME", "").strip()
        test_callable = os.getenv("WHEEL_TEST_CALLABLE", "").strip()
        if wheel_source == "custom" and not wheel_path:
            raise ValueError("WHEEL_SOURCE=custom requires WHEEL_PATH")
        if wheel_source == "custom" and not import_name:
            raise ValueError("WHEEL_SOURCE=custom requires WHEEL_IMPORT_NAME")
        if wheel_source == "sample":
            import_name = import_name or "fabric_custom_wheel_sample"
            distribution_name = distribution_name or "fabric-custom-wheel-sample"
            test_callable = test_callable or "fabric_custom_wheel_sample:transform"

        return cls(
            root=project_root,
            workspace_id=os.getenv("FABRIC_WORKSPACE_ID", "").strip(),
            workspace_name=os.getenv("FABRIC_WORKSPACE_NAME", "Fabric-Custom-Wheel-POC").strip(),
            capacity_id=os.getenv("FABRIC_CAPACITY_ID", "").strip(),
            environment_name=os.getenv("FABRIC_ENVIRONMENT_NAME", "Custom-Wheel-Spark-Env").strip(),
            spark_runtime=os.getenv("FABRIC_SPARK_RUNTIME", "1.3").strip(),
            lakehouse_name=os.getenv("FABRIC_LAKEHOUSE_NAME", "CustomWheelPOCLakehouse").strip(),
            pipeline_name=os.getenv("FABRIC_PIPELINE_NAME", "PL_Custom_Wheel_POC").strip(),
            wheel_source=wheel_source,
            wheel_path=wheel_path,
            wheel_import_name=import_name,
            wheel_distribution_name=distribution_name,
            wheel_test_callable=test_callable,
            enable_resource_creation=_bool("ENABLE_RESOURCE_CREATION", True),
            enable_scale_test=_bool("ENABLE_SCALE_TEST", False),
            scale_profile=ScaleProfile(profile_name, int(profile["rows"]), int(profile["partitions"])),
            run_smoke_test=_bool("RUN_SMOKE_TEST", False),
            set_workspace_default_environment=_bool("SET_WORKSPACE_DEFAULT_ENVIRONMENT", False),
            poll_seconds=_int("FABRIC_POLL_SECONDS", 15),
            operation_timeout_seconds=_int("FABRIC_OPERATION_TIMEOUT_SECONDS", 1800),
            transformed_columns=tuple(raw["transformed_columns"]),
            tables=dict(raw["tables"]),
        )

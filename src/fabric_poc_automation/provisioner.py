"""Idempotent Fabric item provisioning for the custom-wheel POC."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .config import PocConfig
from .fabric.client import FabricClient
from .fabric.definitions import (
    notebook_definition,
    pipeline_content,
    pipeline_definition,
    render_notebook_source,
)
from .wheel_inspection import inspect_wheel

NOTEBOOK_NAMES = (
    "01_Generate_Synthetic_Data",
    "02_Validate_Custom_Wheel",
    "03_Validate_Results",
)
BOOTSTRAP_NOTEBOOK = "00_Attach_POC_Dependencies"


class PocProvisioner:
    def __init__(self, config: PocConfig, client: FabricClient | None) -> None:
        self.config = config
        self.client = client

    def _require_client(self) -> FabricClient:
        if self.client is None:
            raise RuntimeError("A Fabric client is required for this operation")
        return self.client

    def configured_wheel_path(self) -> Path:
        if self.config.wheel_source == "sample":
            return self.build_sample_wheel()
        wheel = Path(self.config.wheel_path).expanduser()
        if not wheel.is_absolute():
            wheel = self.config.root / wheel
        return wheel.resolve()

    def validate_wheel_contract(self, wheel_path: Path) -> dict[str, Any]:
        metadata = inspect_wheel(wheel_path)
        import_name = self.config.wheel_import_name
        import_root = import_name.split(".", 1)[0]
        if import_root not in metadata["top_level_modules"]:
            raise RuntimeError(
                f"WHEEL_IMPORT_NAME={import_name!r} was not found in wheel top-level modules: "
                f"{metadata['top_level_modules']}"
            )
        configured_distribution = self.config.wheel_distribution_name
        if configured_distribution and configured_distribution.lower().replace("_", "-") != (
            metadata["name"] or ""
        ).lower().replace("_", "-"):
            raise RuntimeError(
                f"WHEEL_DISTRIBUTION_NAME={configured_distribution!r} does not match "
                f"wheel metadata Name={metadata['name']!r}"
            )
        return metadata

    def preflight(self) -> dict[str, Any]:
        client = self._require_client()
        workspace = self._match_workspace(client.list_workspaces())
        if not workspace and not self.config.enable_resource_creation:
            raise RuntimeError(
                f"Workspace {self.config.workspace_name!r} was not found and ENABLE_RESOURCE_CREATION=false"
            )
        if not workspace and not self.config.capacity_id:
            raise RuntimeError(
                "Target workspace does not exist. Set FABRIC_CAPACITY_ID to an existing active capacity; "
                "this POC never creates, resumes, pauses, or resizes capacity."
            )
        wheel = self.configured_wheel_path()
        metadata = self.validate_wheel_contract(wheel)
        return {
            "authentication": "PASS",
            "workspace_found": bool(workspace),
            "workspace_id": workspace.get("id") if workspace else None,
            "workspace_name": self.config.workspace_name,
            "capacity_id_for_creation": self.config.capacity_id or None,
            "wheel_source": self.config.wheel_source,
            "wheel": metadata,
            "scale_profile": self.config.scale_profile.name,
        }

    def _match_workspace(self, workspaces: list[dict[str, Any]]) -> dict[str, Any] | None:
        if self.config.workspace_id:
            match = next((w for w in workspaces if w.get("id") == self.config.workspace_id), None)
            if not match:
                raise RuntimeError(f"FABRIC_WORKSPACE_ID {self.config.workspace_id} is not accessible")
            if self.config.workspace_name and match.get("displayName") != self.config.workspace_name:
                raise RuntimeError("FABRIC_WORKSPACE_ID and FABRIC_WORKSPACE_NAME refer to different workspaces")
            return match
        matches = [w for w in workspaces if w.get("displayName") == self.config.workspace_name]
        if len(matches) > 1:
            raise RuntimeError("Multiple accessible workspaces share the configured name; set FABRIC_WORKSPACE_ID")
        return matches[0] if matches else None

    def ensure_workspace(self) -> dict[str, Any]:
        client = self._require_client()
        existing = self._match_workspace(client.list_workspaces())
        if existing:
            return existing
        response = client.request(
            "POST",
            "/workspaces",
            json={
                "displayName": self.config.workspace_name,
                "description": "Isolated workspace for validating a Python wheel on Fabric Spark",
                "capacityId": self.config.capacity_id,
            },
            expected=(201,),
        )
        return response.json()

    def build_sample_wheel(self) -> Path:
        package_root = self.config.root / "sample_package"
        out_dir = package_root / "dist"
        out_dir.mkdir(parents=True, exist_ok=True)
        expected = out_dir / "fabric_custom_wheel_sample-0.1.0-py3-none-any.whl"
        source_files = list((package_root / "src").rglob("*.py")) + [package_root / "pyproject.toml"]
        if expected.is_file() and all(path.stat().st_mtime <= expected.stat().st_mtime for path in source_files):
            return expected
        subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(out_dir), str(package_root)],
            cwd=self.config.root,
            check=True,
        )
        candidates = sorted(out_dir.glob("fabric_custom_wheel_sample-0.1.0-*.whl"))
        if len(candidates) != 1:
            raise RuntimeError(f"Expected one sample wheel, found: {candidates}")
        return candidates[0]

    def ensure_environment(self, workspace_id: str, wheel_path: Path) -> tuple[dict[str, Any], bool]:
        client = self._require_client()
        environment = client.find_item(workspace_id, self.config.environment_name, "Environment")
        changed = False
        if environment is None:
            response = client.request(
                "POST",
                f"/workspaces/{workspace_id}/environments",
                json={
                    "displayName": self.config.environment_name,
                    "description": "Reusable Fabric Spark environment for custom Python wheel validation",
                },
                expected=(201, 202),
            )
            client.wait_for_lro(response)
            environment = client.find_item(workspace_id, self.config.environment_name, "Environment")
            if environment is None:
                raise RuntimeError("Environment create completed but the item could not be found")
            changed = True
        environment_id = environment["id"]

        compute = client.request(
            "GET", f"/workspaces/{workspace_id}/environments/{environment_id}/staging/sparkcompute?beta=false"
        ).json()
        if compute.get("runtimeVersion") != self.config.spark_runtime:
            client.request(
                "PATCH",
                f"/workspaces/{workspace_id}/environments/{environment_id}/staging/sparkcompute?beta=false",
                json={"runtimeVersion": self.config.spark_runtime},
                expected=(200,),
            )
            changed = True

        response = client.request(
            "GET",
            f"/workspaces/{workspace_id}/environments/{environment_id}/staging/libraries?beta=false",
            expected=(200, 404),
        )
        libraries = [] if response.status_code == 404 else response.json().get("libraries", [])
        if wheel_path.name not in {item["name"] for item in libraries}:
            if wheel_path.stat().st_size > 100 * 1024 * 1024:
                raise RuntimeError(f"Fabric custom-library API limit is 100 MB: {wheel_path}")
            client.request(
                "POST",
                f"/workspaces/{workspace_id}/environments/{environment_id}/staging/libraries/{quote(wheel_path.name)}",
                data=wheel_path.read_bytes(),
                content_type="application/octet-stream",
                expected=(200,),
            )
            changed = True

        metadata = client.request("GET", f"/workspaces/{workspace_id}/environments/{environment_id}").json()
        state = ((metadata.get("properties") or {}).get("publishDetails") or {}).get("state")
        if changed or state != "Success":
            self.publish_environment(workspace_id, environment_id)
        return environment, changed

    def publish_environment(self, workspace_id: str, environment_id: str) -> None:
        client = self._require_client()
        response = client.request(
            "POST",
            f"/workspaces/{workspace_id}/environments/{environment_id}/staging/publish?beta=false",
            expected=(200, 202),
        )
        if response.status_code == 202:
            client.wait_for_lro(response)
        deadline = time.monotonic() + self.config.operation_timeout_seconds
        while time.monotonic() < deadline:
            environment = client.request("GET", f"/workspaces/{workspace_id}/environments/{environment_id}").json()
            details = (environment.get("properties") or {}).get("publishDetails") or {}
            state = details.get("state")
            if state == "Success":
                return
            if state in {"Failed", "Cancelled"}:
                raise RuntimeError(f"Environment publish failed: {details}")
            time.sleep(self.config.poll_seconds)
        raise TimeoutError("Environment publish did not reach Success before timeout")

    def ensure_lakehouse(self, workspace_id: str) -> dict[str, Any]:
        client = self._require_client()
        lakehouse = client.find_item(workspace_id, self.config.lakehouse_name, "Lakehouse")
        if lakehouse:
            return lakehouse
        response = client.request(
            "POST",
            f"/workspaces/{workspace_id}/lakehouses",
            json={
                "displayName": self.config.lakehouse_name,
                "description": "Synthetic input, wheel-validation output, and execution evidence",
            },
            expected=(201, 202),
        )
        client.wait_for_lro(response)
        lakehouse = client.find_item(workspace_id, self.config.lakehouse_name, "Lakehouse")
        if lakehouse is None:
            raise RuntimeError("Lakehouse create completed but the item could not be found")
        return lakehouse

    def ensure_notebook(self, workspace_id: str, display_name: str, source: str) -> dict[str, Any]:
        client = self._require_client()
        definition = notebook_definition(display_name, source)
        notebook = client.find_item(workspace_id, display_name, "Notebook")
        if notebook:
            response = client.request(
                "POST",
                f"/workspaces/{workspace_id}/notebooks/{notebook['id']}/updateDefinition?updateMetadata=true",
                json={"definition": definition},
                expected=(200, 202),
            )
            client.wait_for_lro(response)
            return notebook
        response = client.request(
            "POST",
            f"/workspaces/{workspace_id}/notebooks",
            json={"displayName": display_name, "definition": definition},
            expected=(201, 202),
        )
        client.wait_for_lro(response)
        notebook = client.find_item(workspace_id, display_name, "Notebook")
        if notebook is None:
            raise RuntimeError(f"Notebook create completed but {display_name!r} was not found")
        return notebook

    def ensure_notebooks(
        self, workspace_id: str, lakehouse: dict[str, Any], environment: dict[str, Any]
    ) -> dict[str, str]:
        ids: dict[str, str] = {}
        for name in (*NOTEBOOK_NAMES, BOOTSTRAP_NOTEBOOK):
            source = (self.config.root / "notebooks" / f"{name}.py").read_text(encoding="utf-8")
            if name != BOOTSTRAP_NOTEBOOK:
                source = render_notebook_source(
                    source,
                    workspace_id=workspace_id,
                    lakehouse_id=lakehouse["id"],
                    lakehouse_name=self.config.lakehouse_name,
                    environment_id=environment["id"],
                )
            notebook = self.ensure_notebook(workspace_id, name, source)
            ids[name] = notebook["id"]
        return ids

    def attach_notebook_dependencies(
        self, workspace_id: str, notebook_ids: dict[str, str], lakehouse_id: str, environment_id: str
    ) -> dict[str, Any]:
        parameters = [
            {
                "name": "target_notebook_ids",
                "value": ",".join(notebook_ids[name] for name in NOTEBOOK_NAMES),
                "type": "Text",
            },
            {"name": "workspace_id", "value": workspace_id, "type": "Text"},
            {"name": "lakehouse_name", "value": self.config.lakehouse_name, "type": "Text"},
            {"name": "environment_id", "value": environment_id, "type": "Text"},
        ]
        return self._require_client().run_notebook(
            workspace_id,
            notebook_ids[BOOTSTRAP_NOTEBOOK],
            parameters=parameters,
            environment_id=environment_id,
            lakehouse_id=lakehouse_id,
        )

    def ensure_pipeline(
        self, workspace_id: str, notebook_ids: dict[str, str], wheel_metadata: dict[str, Any]
    ) -> dict[str, Any]:
        client = self._require_client()
        content = pipeline_content(
            notebook_ids,
            workspace_id,
            wheel_source=self.config.wheel_source,
            wheel_import_name=self.config.wheel_import_name,
            wheel_distribution_name=self.config.wheel_distribution_name or wheel_metadata["name"],
            wheel_test_callable=self.config.wheel_test_callable,
            profile=self.config.scale_profile.name,
            enable_scale_test=self.config.enable_scale_test,
        )
        definition = pipeline_definition(self.config.pipeline_name, content)
        pipeline = client.find_item(workspace_id, self.config.pipeline_name, "DataPipeline")
        if pipeline:
            response = client.request(
                "POST",
                f"/workspaces/{workspace_id}/dataPipelines/{pipeline['id']}/updateDefinition?updateMetadata=true",
                json={"definition": definition},
                expected=(200, 202),
            )
            client.wait_for_lro(response)
            return pipeline
        response = client.request(
            "POST",
            f"/workspaces/{workspace_id}/dataPipelines",
            json={"displayName": self.config.pipeline_name, "definition": definition},
            expected=(201, 202),
        )
        client.wait_for_lro(response)
        pipeline = client.find_item(workspace_id, self.config.pipeline_name, "DataPipeline")
        if pipeline is None:
            raise RuntimeError("Pipeline create completed but the item could not be found")
        return pipeline

    def optionally_set_workspace_default(self, workspace_id: str) -> bool:
        if not self.config.set_workspace_default_environment:
            return False
        client = self._require_client()
        client.request("GET", f"/workspaces/{workspace_id}/spark/settings")
        client.request(
            "PATCH",
            f"/workspaces/{workspace_id}/spark/settings",
            json={"environment": {"name": self.config.environment_name, "runtimeVersion": self.config.spark_runtime}},
            expected=(200,),
        )
        return True

    def provision(self) -> dict[str, Any]:
        self.preflight()
        wheel = self.configured_wheel_path()
        wheel_metadata = self.validate_wheel_contract(wheel)
        workspace = self.ensure_workspace()
        environment, environment_changed = self.ensure_environment(workspace["id"], wheel)
        lakehouse = self.ensure_lakehouse(workspace["id"])
        notebooks = self.ensure_notebooks(workspace["id"], lakehouse, environment)
        pipeline = self.ensure_pipeline(workspace["id"], notebooks, wheel_metadata)
        state = {
            "workspace": workspace,
            "environment": environment,
            "environment_changed": environment_changed,
            "lakehouse": lakehouse,
            "notebooks": notebooks,
            "pipeline": pipeline,
            "wheel": wheel_metadata,
            "wheel_source": self.config.wheel_source,
            "workspace_default_environment_set": self.optionally_set_workspace_default(workspace["id"]),
        }
        state_path = self.config.root / "results" / "deployment-state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        return state

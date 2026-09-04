"""Builders for documented Fabric notebook and pipeline definitions."""

from __future__ import annotations

import base64
import json
import uuid
from typing import Any


def _b64_text(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def logical_id(display_name: str, item_type: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"fabric-spark-custom-wheel-poc/{item_type}/{display_name}"))


def platform_part(display_name: str, item_type: str, description: str) -> dict[str, str]:
    platform = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": item_type, "displayName": display_name, "description": description},
        "config": {"version": "2.0", "logicalId": logical_id(display_name, item_type)},
    }
    return {"path": ".platform", "payload": _b64_text(json.dumps(platform)), "payloadType": "InlineBase64"}


def notebook_definition(display_name: str, source: str) -> dict[str, Any]:
    return {
        "format": "fabricGitSource",
        "parts": [
            {"path": "notebook-content.py", "payload": _b64_text(source), "payloadType": "InlineBase64"},
            platform_part(display_name, "Notebook", "Fabric Spark custom-wheel validation POC"),
        ],
    }


def pipeline_definition(display_name: str, content: dict[str, Any]) -> dict[str, Any]:
    return {
        "parts": [
            {
                "path": "pipeline-content.json",
                "payload": _b64_text(json.dumps(content, separators=(",", ":"))),
                "payloadType": "InlineBase64",
            },
            platform_part(display_name, "DataPipeline", "Runs the custom-wheel validation notebooks in order"),
        ]
    }


def render_notebook_source(
    source: str, *, workspace_id: str, lakehouse_id: str, lakehouse_name: str, environment_id: str
) -> str:
    replacements = {
        "__WORKSPACE_ID__": workspace_id,
        "__LAKEHOUSE_ID__": lakehouse_id,
        "__LAKEHOUSE_NAME__": lakehouse_name,
        "__ENVIRONMENT_ID__": environment_id,
    }
    rendered = source
    for marker, value in replacements.items():
        rendered = rendered.replace(marker, value)
    unresolved = [marker for marker in replacements if marker in rendered]
    if unresolved:
        raise ValueError(f"Notebook source contains unresolved deployment markers: {unresolved}")
    return rendered


def notebook_activity(
    name: str,
    notebook_id: str,
    workspace_id: str,
    *,
    wheel_source: str,
    wheel_import_name: str,
    wheel_distribution_name: str,
    wheel_test_callable: str,
    profile: str,
    enable_scale_test: bool,
    depends_on: str | None = None,
) -> dict[str, Any]:
    dependencies = [] if depends_on is None else [{"activity": depends_on, "dependencyConditions": ["Succeeded"]}]
    parameters = {
        "run_id": {"value": "@pipeline().RunId", "type": "string"},
        "scale_profile": {"value": profile, "type": "string"},
        "wheel_source": {"value": wheel_source, "type": "string"},
        "wheel_import_name": {"value": wheel_import_name, "type": "string"},
        "wheel_distribution_name": {"value": wheel_distribution_name, "type": "string"},
        "wheel_test_callable": {"value": wheel_test_callable, "type": "string"},
        "enable_scale_test": {"value": enable_scale_test, "type": "bool"},
    }
    return {
        "name": name,
        "type": "TridentNotebook",
        "dependsOn": dependencies,
        "policy": {
            "timeout": "0.02:00:00",
            "retry": 0,
            "retryIntervalInSeconds": 30,
            "secureOutput": False,
            "secureInput": False,
        },
        "typeProperties": {
            "notebookId": notebook_id,
            "workspaceId": workspace_id,
            "parameters": parameters,
            "sessionTag": "fabric-custom-wheel-poc",
        },
    }


def pipeline_content(
    notebook_ids: dict[str, str],
    workspace_id: str,
    *,
    wheel_source: str = "sample",
    wheel_import_name: str = "fabric_custom_wheel_sample",
    wheel_distribution_name: str = "fabric-custom-wheel-sample",
    wheel_test_callable: str = "fabric_custom_wheel_sample:transform",
    profile: str = "smoke",
    enable_scale_test: bool = False,
) -> dict[str, Any]:
    common = {
        "workspace_id": workspace_id,
        "wheel_source": wheel_source,
        "wheel_import_name": wheel_import_name,
        "wheel_distribution_name": wheel_distribution_name,
        "wheel_test_callable": wheel_test_callable,
        "profile": profile,
        "enable_scale_test": enable_scale_test,
    }
    return {
        "properties": {
            "description": "Validates custom Python wheel distribution to Fabric Spark driver and executors",
            "activities": [
                notebook_activity("GenerateSyntheticData", notebook_ids["01_Generate_Synthetic_Data"], **common),
                notebook_activity(
                    "ValidateCustomWheel",
                    notebook_ids["02_Validate_Custom_Wheel"],
                    depends_on="GenerateSyntheticData",
                    **common,
                ),
                notebook_activity(
                    "ValidateResults",
                    notebook_ids["03_Validate_Results"],
                    depends_on="ValidateCustomWheel",
                    **common,
                ),
            ],
        }
    }

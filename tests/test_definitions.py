from __future__ import annotations

import base64

from fabric_poc_automation.fabric.definitions import (
    notebook_definition,
    pipeline_content,
    render_notebook_source,
)


def test_notebook_definition_uses_documented_parts() -> None:
    definition = notebook_definition("Example", "print('ok')")
    assert definition["format"] == "fabricGitSource"
    assert [part["path"] for part in definition["parts"]] == ["notebook-content.py", ".platform"]
    assert base64.b64decode(definition["parts"][0]["payload"]).decode() == "print('ok')"


def test_notebook_render_attaches_dependencies() -> None:
    source = "__WORKSPACE_ID__ __LAKEHOUSE_ID__ __LAKEHOUSE_NAME__ __ENVIRONMENT_ID__"
    assert render_notebook_source(
        source,
        workspace_id="ws",
        lakehouse_id="lh",
        lakehouse_name="Lake",
        environment_id="env",
    ) == "ws lh Lake env"


def test_pipeline_is_sequential_and_uses_documented_activity_parameters() -> None:
    ids = {
        "01_Generate_Synthetic_Data": "one",
        "02_Validate_Custom_Wheel": "two",
        "03_Validate_Results": "three",
    }
    content = pipeline_content(ids, "workspace")
    activities = content["properties"]["activities"]
    assert [a["type"] for a in activities] == ["TridentNotebook"] * 3
    assert activities[0]["dependsOn"] == []
    assert activities[1]["dependsOn"][0]["activity"] == "GenerateSyntheticData"
    assert activities[2]["dependsOn"][0]["dependencyConditions"] == ["Succeeded"]
    assert activities[0]["typeProperties"]["parameters"]["run_id"]["type"] == "string"
    assert activities[1]["typeProperties"]["parameters"]["wheel_import_name"]["value"] == "fabric_custom_wheel_sample"
    assert "parameters" not in content["properties"]

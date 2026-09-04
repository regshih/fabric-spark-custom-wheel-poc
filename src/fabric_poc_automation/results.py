"""Local machine- and human-readable POC result artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

RESULT_FIELDS = [
    "poc_run_id", "timestamp", "wheel_source", "wheel_name", "wheel_version",
    "environment", "workspace", "spark_runtime", "input_records", "output_records",
    "partitions", "duration_seconds", "rows_per_second", "validation_result",
    "executor_import_result", "spark_application_id", "pipeline_result",
    "attachment_result", "orchestration_duration_seconds",
]


def write_results(root: Path, result: dict[str, Any]) -> None:
    directory = root / "results"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "latest.json").write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    lines = ["# Latest Fabric custom-wheel POC result", ""]
    for key in RESULT_FIELDS:
        lines.append(f"- **{key.replace('_', ' ').title()}:** {result.get(key, 'not collected')}")
    lines.extend(["", "Results validate wheel distribution and the configured test hook only.", ""])
    (directory / "latest.md").write_text("\n".join(lines), encoding="utf-8")
    history = directory / "history.csv"
    exists = history.exists()
    with history.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=RESULT_FIELDS, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow({key: result.get(key, "") for key in RESULT_FIELDS})

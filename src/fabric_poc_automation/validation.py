"""Pure validation helpers shared by local tests and result collectors."""

from __future__ import annotations

from typing import Any


def evaluate_run_summary(summary: dict[str, Any]) -> list[dict[str, str]]:
    checks = [
        (
            "row_count",
            summary.get("input_rows") == summary.get("output_rows") and summary.get("input_rows") is not None,
            f"input={summary.get('input_rows')}, output={summary.get('output_rows')}",
        ),
        ("driver_import", bool(summary.get("package_version")), str(summary.get("package_version"))),
        ("executor_import", summary.get("executor_import_ok") is True, str(summary.get("executor_import_ok"))),
        ("distributed_partitions", int(summary.get("partitions") or 0) >= 2, str(summary.get("partitions"))),
    ]
    return [
        {"check_name": name, "status": "PASS" if passed else "FAIL", "detail": detail}
        for name, passed, detail in checks
    ]

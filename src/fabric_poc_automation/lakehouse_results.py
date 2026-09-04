"""Collect detailed Spark evidence through the Lakehouse SQL endpoint."""

from __future__ import annotations

import json
import struct
import time
from typing import Any

import pyodbc

from .config import PocConfig
from .fabric import FabricClient

SQL_SCOPE = "https://database.windows.net/.default"
SQL_COPT_SS_ACCESS_TOKEN = 1256


def _connection(client: FabricClient, server: str, database: str) -> pyodbc.Connection:
    token_bytes = client.credential.get_token(SQL_SCOPE).token.encode("utf-16-le")
    token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
    connection_string = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={server};DATABASE={database};Encrypt=yes;TrustServerCertificate=no;"
    )
    return pyodbc.connect(
        connection_string,
        attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct},
        timeout=60,
    )


def collect_lakehouse_evidence(
    config: PocConfig,
    client: FabricClient,
    state: dict[str, Any],
    result: dict[str, Any],
    *,
    max_attempts: int = 8,
) -> dict[str, Any]:
    workspace_id = state["workspace"]["id"]
    lakehouse_id = state["lakehouse"]["id"]
    detail = client.request("GET", f"/workspaces/{workspace_id}/lakehouses/{lakehouse_id}").json()
    sql = detail["properties"]["sqlEndpointProperties"]
    client.request(
        "POST",
        f"/workspaces/{workspace_id}/sqlEndpoints/{sql['id']}/refreshMetadata",
        expected=(200, 202),
    )

    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            with _connection(client, sql["connectionString"], config.lakehouse_name) as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "SELECT TOP 1 run_id, package_version, spark_application_id, input_rows, output_rows, "
                    "partitions, duration_seconds, rows_per_second, executor_import_ok, executor_probe_json, "
                    "runtime_context_json FROM custom_wheel_benchmark_results WHERE run_id=? "
                    "ORDER BY timestamp_utc DESC",
                    result["poc_run_id"],
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError(f"No benchmark evidence found for run {result['poc_run_id']}")
                benchmark = {column[0]: value for column, value in zip(cursor.description, row)}
                cursor.execute(
                    "SELECT check_name, status, detail FROM custom_wheel_validation WHERE run_id=? ORDER BY check_name",
                    result["poc_run_id"],
                )
                columns = [column[0] for column in cursor.description]
                checks = [dict(zip(columns, item)) for item in cursor.fetchall()]
                if not checks:
                    raise RuntimeError(f"No validation evidence found for run {result['poc_run_id']}")
            result.update({
                "wheel_version": benchmark["package_version"],
                "spark_application_id": benchmark["spark_application_id"],
                "input_records": benchmark["input_rows"],
                "output_records": benchmark["output_rows"],
                "partitions": benchmark["partitions"],
                "duration_seconds": benchmark["duration_seconds"],
                "rows_per_second": benchmark["rows_per_second"],
                "executor_import_result": "PASS" if benchmark["executor_import_ok"] else "FAIL",
                "executor_probe": json.loads(benchmark["executor_probe_json"]),
                "runtime_context": json.loads(benchmark["runtime_context_json"]),
                "validation_checks": checks,
                "validation_result": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL",
            })
            return result
        except (pyodbc.Error, RuntimeError) as exc:
            last_error = exc
            if attempt + 1 < max_attempts:
                time.sleep(config.poll_seconds)
                client.request(
                    "POST",
                    f"/workspaces/{workspace_id}/sqlEndpoints/{sql['id']}/refreshMetadata",
                    expected=(200, 202),
                )
    raise RuntimeError(f"Lakehouse evidence was not queryable after {max_attempts} attempts: {last_error}")

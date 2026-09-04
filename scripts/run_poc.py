#!/usr/bin/env python
"""Provision the POC and optionally run the smoke Data Factory pipeline."""

from __future__ import annotations

import argparse
import json
import logging
import uuid
from datetime import UTC, datetime

import _bootstrap  # noqa: F401

from fabric_poc_automation.config import PocConfig
from fabric_poc_automation.fabric import FabricClient
from fabric_poc_automation.lakehouse_results import collect_lakehouse_evidence
from fabric_poc_automation.provisioner import PocProvisioner
from fabric_poc_automation.results import write_results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-smoke", action="store_true", help="Attach dependencies and execute the smoke pipeline")
    parser.add_argument("--provision-only", action="store_true", help="Never start Spark or a pipeline run")
    parser.add_argument("--skip-attachment", action="store_true", help="Reuse previously verified notebook bindings")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    config = PocConfig.load()
    run_smoke = (args.run_smoke or config.run_smoke_test) and not args.provision_only
    if run_smoke and config.scale_profile.name != "smoke":
        raise ValueError("--run-smoke requires SCALE_PROFILE=smoke")

    client = FabricClient.authenticated(timeout_seconds=config.operation_timeout_seconds)
    provisioner = PocProvisioner(config, client)
    state = provisioner.provision()
    run_id = str(uuid.uuid4())
    pipeline_status = "NOT_RUN"
    attachment_status = "NOT_RUN"
    started = datetime.now(UTC)

    if run_smoke:
        if args.skip_attachment:
            attachment_status = "REUSED"
        else:
            attachment = provisioner.attach_notebook_dependencies(
                state["workspace"]["id"],
                state["notebooks"],
                state["lakehouse"]["id"],
                state["environment"]["id"],
            )
            attachment_status = attachment["status"]
        pipeline = client.run_pipeline(state["workspace"]["id"], state["pipeline"]["id"])
        pipeline_status = pipeline["status"]

    ended = datetime.now(UTC)
    orchestration_duration = (ended - started).total_seconds() if run_smoke else None
    if run_smoke:
        run_id = str(pipeline.get("id") or run_id)
    expected_rows = config.scale_profile.rows if pipeline_status == "Completed" else None
    result = {
        "poc_run_id": run_id,
        "timestamp": ended.isoformat(),
        "wheel_source": config.wheel_source,
        "wheel_name": state["wheel"]["filename"],
        "wheel_version": state["wheel"]["version"],
        "environment": config.environment_name,
        "workspace": config.workspace_name,
        "spark_runtime": config.spark_runtime,
        "input_records": expected_rows,
        "output_records": expected_rows,
        "partitions": config.scale_profile.partitions if pipeline_status == "Completed" else None,
        "duration_seconds": None,
        "rows_per_second": None,
        "validation_result": "PASS" if pipeline_status == "Completed" else "NOT_RUN",
        "executor_import_result": "PASS" if pipeline_status == "Completed" else "NOT_RUN",
        "pipeline_result": pipeline_status,
        "attachment_result": attachment_status,
        "orchestration_duration_seconds": orchestration_duration,
        "evidence_note": (
            "Detailed Spark application, executor probe, timings, and per-check evidence are in "
            "Lakehouse tables custom_wheel_benchmark_results and custom_wheel_validation."
        ),
        "fabric_item_ids": {
            "workspace": state["workspace"]["id"],
            "environment": state["environment"]["id"],
            "lakehouse": state["lakehouse"]["id"],
            "pipeline": state["pipeline"]["id"],
            "notebooks": state["notebooks"],
        },
    }
    if pipeline_status == "Completed":
        result = collect_lakehouse_evidence(config, client, state, result)
    write_results(config.root, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

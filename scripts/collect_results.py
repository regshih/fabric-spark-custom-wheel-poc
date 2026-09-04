#!/usr/bin/env python
"""Refresh the latest local summary from detailed Lakehouse SQL evidence."""

from __future__ import annotations

import json

import _bootstrap

from fabric_poc_automation.config import PocConfig
from fabric_poc_automation.fabric import FabricClient
from fabric_poc_automation.lakehouse_results import collect_lakehouse_evidence
from fabric_poc_automation.results import write_results


def main() -> None:
    latest_path = _bootstrap.ROOT / "results" / "latest.json"
    state_path = _bootstrap.ROOT / "results" / "deployment-state.json"
    if not latest_path.exists() or not state_path.exists():
        raise SystemExit("Local run/deployment state is missing; run scripts/run_poc.py first")
    config = PocConfig.load()
    client = FabricClient.authenticated(timeout_seconds=config.operation_timeout_seconds)
    result = json.loads(latest_path.read_text(encoding="utf-8"))
    state = json.loads(state_path.read_text(encoding="utf-8"))
    result = collect_lakehouse_evidence(config, client, state, result)
    write_results(config.root, result)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()

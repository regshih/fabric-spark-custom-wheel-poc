#!/usr/bin/env python
"""Delete only exact POC items recorded by this repository; never deletes capacity or workspace."""

from __future__ import annotations

import argparse
import json

import _bootstrap

from fabric_poc_automation.config import PocConfig
from fabric_poc_automation.fabric import FabricClient


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Required confirmation to delete recorded POC items")
    args = parser.parse_args()
    state_path = _bootstrap.ROOT / "results" / "deployment-state.json"
    if not state_path.exists():
        raise SystemExit("No deployment-state.json; refusing cleanup because exact item IDs are unknown")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    config = PocConfig.load()
    targets = [
        (state["pipeline"]["id"], config.pipeline_name, "DataPipeline"),
        *[(item_id, name, "Notebook") for name, item_id in state["notebooks"].items()],
        (state["lakehouse"]["id"], config.lakehouse_name, "Lakehouse"),
        (state["environment"]["id"], config.environment_name, "Environment"),
    ]
    print(json.dumps({"workspace": state["workspace"]["id"], "targets": targets}, indent=2))
    if not args.execute:
        print("Dry run only. Re-run with --execute to delete these exact items.")
        return
    client = FabricClient.authenticated(timeout_seconds=config.operation_timeout_seconds)
    workspace_id = state["workspace"]["id"]
    current = {item["id"]: item for item in client.list_items(workspace_id)}
    for item_id, expected_name, expected_type in targets:
        item = current.get(item_id)
        if item is None:
            continue
        if item.get("displayName") != expected_name or item.get("type") != expected_type:
            raise RuntimeError(f"Recorded item changed identity; refusing to delete: {item}")
        client.request("DELETE", f"/workspaces/{workspace_id}/items/{item_id}", expected=(200, 204))
        print(f"Deleted {expected_type} {expected_name} ({item_id})")


if __name__ == "__main__":
    main()

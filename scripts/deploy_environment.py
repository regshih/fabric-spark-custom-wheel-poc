#!/usr/bin/env python
from __future__ import annotations

import json

import _bootstrap  # noqa: F401

from fabric_poc_automation.config import PocConfig
from fabric_poc_automation.fabric import FabricClient
from fabric_poc_automation.provisioner import PocProvisioner


def main() -> None:
    config = PocConfig.load()
    client = FabricClient.authenticated(timeout_seconds=config.operation_timeout_seconds)
    provisioner = PocProvisioner(config, client)
    provisioner.preflight()
    wheel = provisioner.configured_wheel_path()
    provisioner.validate_wheel_contract(wheel)
    workspace = provisioner.ensure_workspace()
    environment, changed = provisioner.ensure_environment(workspace["id"], wheel)
    print(json.dumps({"workspace": workspace, "environment": environment, "changed": changed}, indent=2))


if __name__ == "__main__":
    main()

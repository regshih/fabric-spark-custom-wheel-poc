#!/usr/bin/env python
from __future__ import annotations

import json

import _bootstrap  # noqa: F401

from fabric_poc_automation.config import PocConfig
from fabric_poc_automation.provisioner import PocProvisioner
from fabric_poc_automation.wheel_inspection import inspect_wheel


def main() -> None:
    config = PocConfig.load()
    provisioner = PocProvisioner(config, client=None)  # type: ignore[arg-type]
    wheel = provisioner.build_sample_wheel()
    print(json.dumps(inspect_wheel(wheel), indent=2))


if __name__ == "__main__":
    main()

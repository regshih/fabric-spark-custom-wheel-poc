#!/usr/bin/env python
from __future__ import annotations

import argparse
import json

import _bootstrap  # noqa: F401

from fabric_poc_automation.wheel_inspection import inspect_wheel


def main() -> None:
    parser = argparse.ArgumentParser(description="Report wheel compatibility metadata without decompiling code")
    parser.add_argument("wheel")
    args = parser.parse_args()
    print(json.dumps(inspect_wheel(args.wheel), indent=2))


if __name__ == "__main__":
    main()

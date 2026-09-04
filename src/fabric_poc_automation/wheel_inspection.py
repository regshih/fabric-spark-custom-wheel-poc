"""Compatibility-focused wheel metadata inspection without decompilation."""

from __future__ import annotations

import hashlib
import zipfile
from email.parser import Parser
from pathlib import Path
from typing import Any


def inspect_wheel(path: str | Path) -> dict[str, Any]:
    wheel_path = Path(path).resolve()
    if not wheel_path.is_file() or wheel_path.suffix != ".whl":
        raise ValueError(f"Expected an existing .whl file, got {wheel_path}")
    digest = hashlib.sha256(wheel_path.read_bytes()).hexdigest()
    with zipfile.ZipFile(wheel_path) as archive:
        names = archive.namelist()
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        wheel_names = [name for name in names if name.endswith(".dist-info/WHEEL")]
        if len(metadata_names) != 1 or len(wheel_names) != 1:
            raise ValueError("Wheel must contain exactly one METADATA and one WHEEL file")
        metadata = Parser().parsestr(archive.read(metadata_names[0]).decode("utf-8", errors="replace"))
        wheel_metadata = Parser().parsestr(archive.read(wheel_names[0]).decode("utf-8", errors="replace"))
        modules = sorted(
            {
                name.split("/", 1)[0]
                for name in names
                if "/" in name and ".dist-info/" not in name and not name.startswith("__pycache__/")
            }
        )
    return {
        "filename": wheel_path.name,
        "size_bytes": wheel_path.stat().st_size,
        "sha256": digest,
        "name": metadata.get("Name"),
        "version": metadata.get("Version"),
        "requires_python": metadata.get("Requires-Python"),
        "dependencies": metadata.get_all("Requires-Dist", []),
        "tags": wheel_metadata.get_all("Tag", []),
        "top_level_modules": modules,
    }

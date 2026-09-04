from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from fabric_poc_automation.wheel_inspection import inspect_wheel

ROOT = Path(__file__).resolve().parents[1]


def test_build_and_inspect_sample_wheel(tmp_path: Path) -> None:
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp_path), str(ROOT / "sample_package")],
        check=True,
        capture_output=True,
        text=True,
    )
    wheels = list(tmp_path.glob("*.whl"))
    assert len(wheels) == 1
    metadata = inspect_wheel(wheels[0])
    assert metadata["filename"] == "fabric_custom_wheel_sample-0.1.0-py3-none-any.whl"
    assert metadata["version"] == "0.1.0"
    assert metadata["dependencies"] == []
    assert metadata["tags"] == ["py3-none-any"]
    assert metadata["top_level_modules"] == ["fabric_custom_wheel_sample"]

"""Read-only Raspberry Pi deployment preflight; does not open camera or actuators."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
from datetime import datetime, timezone

def probe_port(port: int) -> dict:
    try:
        result = subprocess.run(["ss", "-ltn"], capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {"port": port, "state": "unknown"}
    if result.returncode:
        return {"port": port, "state": "unknown"}
    lines = (line.split() for line in result.stdout.splitlines()[1:])
    used = any(parts[3].rsplit(":", 1)[-1] == str(port) for parts in lines if len(parts) >= 4)
    return {"port": port, "state": "occupied" if used else "free"}

def preflight() -> dict:
    deps = {name: bool(importlib.util.find_spec(name)) for name in ("cv2", "numpy", "flask", "serial", "quadruped")}
    camera = Path("/dev/video0")
    try:
        present = camera.exists()
        readable = os.access(camera, os.R_OK) if present else False
    except OSError:
        present, readable = False, False
    root = Path(__file__).resolve().parents[1]
    return {
        "schema": 1,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "architecture": platform.machine(),
        "platform": platform.system(),
        "camera_device": "/dev/video0",
        "camera": {"exists": present, "readable": readable},
        "imports_available": deps,
        "dashboard_tcp": probe_port(7000),
        "checkout_present": (root / "software/pi/quadruped").exists(),
        "git_available": shutil.which("git") is not None,
        "qualification": "READ_ONLY_PREFLIGHT_NOT_CAMERA_ACCEPTANCE",
        "physical_actuation_tested": False,
        "camera_frames_captured": 0,
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    result = preflight()
    body = json.dumps(result, indent=2) + "\n"
    print(body, end="")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body, encoding="utf-8")

if __name__ == "__main__":
    main()

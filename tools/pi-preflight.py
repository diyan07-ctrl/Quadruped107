"""Read-only Raspberry Pi deployment preflight; does not open camera or actuators."""
from __future__ import annotations
import argparse
import importlib.util
from importlib.metadata import version, PackageNotFoundError
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

def preflight(camera_device='/dev/video0',sensor_port=None,oled_bus=None) -> dict:
    deps = {name: bool(importlib.util.find_spec(name)) for name in ("cv2", "numpy", "flask", "serial", "quadruped")}
    camera = Path(camera_device)
    try:
        present = camera.exists()
        readable = os.access(camera, os.R_OK) if present else False
    except OSError:
        present, readable = False, False
    root = Path(__file__).resolve().parents[1]
    imports={}
    for name in deps:
        try:
            probe=subprocess.run([os.sys.executable,'-c','import '+name],capture_output=True,text=True,timeout=10)
            imports[name]={'ok':probe.returncode==0,'error':probe.stderr[-500:] if probe.returncode else None}
        except (OSError,subprocess.TimeoutExpired) as error:
            imports[name]={'ok':False,'error':str(error)}
    packages={}
    for name in ('numpy','opencv-python-headless','Flask','pyserial','smbus2','Pillow'):
        try: packages[name]=version(name)
        except PackageNotFoundError: packages[name]=None
    def device(path):
        if path is None: return {'selected':False}
        entry=Path(path)
        return dict(selected=True,path=str(entry),exists=entry.exists(),
                    readable=os.access(entry,os.R_OK),writable=os.access(entry,os.W_OK))
    return {
        "schema": 1,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "architecture": platform.machine(),
        "platform": platform.system(),
        "camera_device": camera_device,
        "camera": {"exists": present, "readable": readable},
        "imports_available": deps,
        "import_execution": imports,
        "package_versions": packages,
        "serial": device(sensor_port),
        "serial_by_id_candidates": sorted(str(p) for p in Path('/dev/serial/by-id').glob('*')),
        "oled": device(None if oled_bus is None else '/dev/i2c-'+str(oled_bus)),
        "physical_actuation_allowed": False,
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
    parser.add_argument('--camera-device',default='/dev/video0')
    parser.add_argument('--sensor-port')
    parser.add_argument('--oled-bus',type=int)
    args = parser.parse_args()
    result = preflight(args.camera_device,args.sensor_port,args.oled_bus)
    body = json.dumps(result, indent=2) + "\n"
    print(body, end="")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body, encoding="utf-8")

if __name__ == "__main__":
    main()

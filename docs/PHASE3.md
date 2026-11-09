# Phase 3: vision presets and recording (software-only checkpoint)

This development branch is stacked on Phase 2 and does **not** authorize physical servos, PCA9685, Uno motion, GPIO, or automatic motion enable. Physical ARM remains rejected by the Phase 2 application.

## Yellow tennis-ball detection

The original blue behavior and public `detect_blue_ball` API are preserved. The internal contour/circularity detector already accepts arbitrary HSV lower/upper bounds; Phase 3 adds an explicit `target_color` identifier and a yellow-green tennis-ball preset. The name of the legacy function does not imply the configured yellow detector ignores yellow.

- Blue configuration: `deploy/vision.example.json`
- Yellow configuration: `deploy/vision.yellow.json`
- Yellow starting bounds: HSV (20,70,70) to (45,255,255) in OpenCV's 0–179 hue domain.
- Explicit `hsv_lower`/`hsv_upper` entries override the preset.

Launch the existing explicit virtual-actuator app using the yellow configuration (no Uno, no servo power):

```bash
.venv-pi-virtual/bin/python -m quadruped.main --camera-backend usb --camera-device /dev/video0 --actuator-backend virtual --vision-config deploy/vision.yellow.json --host 127.0.0.1
```

Use `--simulator LAPTOP_PRIVATE_IP` only when the actual simulator bridge is already running; without it there is no network physics lease. The on-screen label and `vision.targetColor` report the configured color. The existing state field `vision.blueBall` remains as a backward-compatible legacy key and now describes the selected target.

Color segmentation is **not tennis-ball identification**: similarly colored circular objects can be misidentified. Thresholds must be verified on real frames with actual lighting. No model training required.

## Record a real USB-camera diagnostic clip on the Pi

The Pi recorder is *standalone*. Stop the running dashboard and any competing process that owns `/dev/video0` first. Only record while the camera is pointed at a nonprivate demonstration setup and you have permission to record; inspect the background and avoid sensitive material.

```bash
python3 tools/record-usb-camera.py --device /dev/video0 --seconds 10 --output build/recordings/tennis-ball.avi
```

The recorder uses V4L2/YUYV input and MJPEG-in-AVI output. Duration is capped at 30 seconds. Recordings remain in the local untracked `build/` directory. The program does not access physical actuators. Capturing the real camera on your Pi remains **NOT TESTED** by this GitHub-only change; an SSH shell or local Pi terminal is needed.

## Record the 3D simulation on a capable laptop

The existing `simulation.twin` now accepts `--record PATH.avi`, which uses PyBullet's TinyRenderer at 640×480, 30 frames per second, sampling every eight 240 Hz physics steps. A bounded `--steps` value (1–7200) is mandatory and caps recording at 30 simulated seconds. Rendering is from simulated graphics, not from the Pi camera.

```powershell
.venv-sim/Scripts/python.exe -m simulation.twin --headless --scenario single_obstacle --demo forward --arm-demo --steps 720 --record build/recordings/sim-forward.avi --report build/recordings/sim-forward.json
```

For interactive network-driven simulation, launch the normal Phase 2 `simulation.twin` and Pi app as described in `simulation/PHASE2.md`; bounded recording requires specifying `--steps`, so the simulator exits when it reaches that limit. No recorded clip proves physical locomotion. The virtual demo commands are offline, explicit and disconnected from production hardware.

## Current validation boundary

Unit/CI testing can confirm configuration semantics, detector behavior and model rendering paths. Actual Pi FPS, on-device recording, camera permission, background privacy, laptop GUI rendering, physical walking and sensor/power qualification remain unverified until measured. No credential should be placed in scripts or Git logs.

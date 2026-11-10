# Phase 3: integrated virtual demonstration

Status: IMPLEMENTED and AUTOMATED TESTED in GitHub Actions. Camera fixtures, actuators, sensing and physics tests are SIMULATED. No physical hardware acceptance is claimed. Continue the existing stacked [PR #5](https://github.com/diyan07-ctrl/Quadruped107/pull/5); do not merge the underlying phases automatically.

## Run the complete laptop demonstration

From the repository root, using Python 3.11+ (PyBullet is a laptop dependency):

```powershell
python -m venv .venv-demo
.venv-demo/Scripts/python.exe -m pip install -r software/pi/requirements-dev.txt -r simulation/requirements.txt -e software/pi
.venv-demo/Scripts/python.exe -m pip check
# Terminal 1: externally supported eight-joint articulation fixture, real-time stepping
.venv-demo/Scripts/python.exe -m simulation.twin --scenario empty --show-rays --host 127.0.0.1
# Terminal 2: synthetic camera, virtual Uno, mandatory simulator sensor/connection lease
.venv-demo/Scripts/python.exe -m quadruped.main --simulate --virtual-sensors --simulator 127.0.0.1 --vision-state build/state/vision.json --host 127.0.0.1
```

Open http://127.0.0.1:7000. On Linux replace Scripts/python.exe with bin/python. Keep both processes running. The model receives accepted virtual Uno output through the existing UDP bridge, rather than moving from UI intent alone. No Uno, GPIO or physical servo connection is needed or authorized.

1. While disarmed select Blue or Yellow in the dashboard and apply. Select the labeled SYNTHETIC target Left control; wait for a fresh, detected target and healthy virtual sensing/simulator.
2. Explicitly enable virtual actuators, then select OpenCV tracking. Move the synthetic target through Center and Right. The camera owner renders an interpolated colored circle; the normal detector and controller handle it. These controls never substitute for a USB/file camera.
3. Hide the target. Target loss stops/disarms. Camera or simulator faults also stop/disarm. Recovery needs a fresh observation, fresh simulator/sensors and explicit enable. There is no automatic re-arm.
4. To change target color, apply the new preset while stopped and show the matching synthetic circle. Applying configuration cancels motion, clears tracking and increments its revision, including when changed during an active session.
5. For bounded personality, explicitly enable, select Interactions and request Greeting, Attention, Tail wag or Neutral. These map to existing routines and stop after the configured interaction deadline (default two seconds); long routines may be interrupted. A second pending interaction is rejected. STOP, manual takeover, faults and obstacles preempt it.

The browser must remain open and connected to maintain ownership heartbeat. Its requested, intent-accepted, submitted and completed states are distinct from the virtual Uno's active routine. The bounded history records actual events with reasons; a request is not proof of execution. STOP remains available while other controls are disabled.

## Vision and tracking contract

Blue defaults to HSV (95,70,30)-(140,255,255); yellow/yellow-green defaults to (20,70,70)-(45,255,255). OpenCV hue is 0-179. Custom settings are accepted through revision-checked GET/POST /api/vision or --vision-config; see [example](../deploy/vision.yellow.json). Persisted schema-1 preferences use an atomic replacement at --vision-state (default build/state/vision.json), not source-file edits. A bad state file fails explicitly. An explicit --vision-config takes precedence. Failed persistence leaves outputs disarmed and the previous settings intact.

Defaults: minimum area 150 pixels, radius 8 pixels, maximum radius 0.38 of the smaller frame dimension and contour circularity at least 0.55. Morphological filtering and a maximum processing dimension of 640 bound work; at most 128 contours and eight candidates are considered. Diagnostics expose geometry, candidates and raw/smoothed horizontal error, not an invented confidence percentage. HSV/circularity cannot uniquely recognize a tennis ball.

Initial selection is deterministic: largest area, then coordinates. An active lock associates the nearest candidate within 0.20 normalized frame distance and radius ratio 0.5-2; ties use area/coordinates. Error uses EMA alpha 0.35 plus existing boundary hysteresis. Persistence requires two distinct capture timestamps, not repeated processing of one frame. Default maximum observation age is 0.5 s, loss timeout 0.35 s and motion period 0.6 s. Nearby reacquisition is bounded by 0.6 s; an enabled lock does not adopt an unrelated candidate after expiry. Stop and begin a new session to acquire another target. Disarmed previews can acquire a new lock.

The legacy detect_blue_ball API and vision.blueBall state key remain compatible and describe the selected color. Configuration revision/session barriers discard results from an old in-flight detector. Tracking requests turns or holds only; camera-only forward walking remains prohibited. Obstacle and critical sensor policy precede tracking/personality.

## Demonstration acceptance

| Scenario | Reproducible evidence |
| --- | --- |
| Blue and yellow; left, center, right | test_demonstration.py integrated Runtime/Flask/virtual Uno/UDP/PyBullet fixture |
| Target loss and stale observation | Integrated demo, vision readiness, preserved autonomy tests |
| Obstacle overrides tracking | Integrated demo plus Phase 2 ray/sensor/controller tests |
| Touch and bounded personality | Phase 2 debounce/stuck/simultaneous tests and live interaction API regression |
| Manual takeover and STOP | Preserved real controller/virtual Uno tests; interaction and integration cancellation |
| Camera failure | Integrated camera-source fault and fresh-frame recovery barrier |
| Simulator failure/reset | Actual UDP receiver reset/disconnect tests; explicit re-enable required |
| Configuration/color switch | Owner/revision/persistence and blocked in-flight detector race tests |
| Live synthetic controls | Camera-owner acquisition and detector test; real-camera rejection and browser ownership |

```bash
python -m unittest discover -s tests -v
python -m simulation.validate
python -m simulation.model_study
python simulation/build_model.py --check
python tools/generate-motion-data.py --check
```

See [validation](VALIDATION.md), [model investigation](MODEL_STUDY.md) and [Phase 2 scenarios](../simulation/PHASE2.md). The simulator's R key resets the scene/receiver and forces re-enable; use the touch scenario or existing simulation touch controls for contacts. The single_obstacle scenario supplies known geometry. A lone front ray does not establish safe side/reverse space. Physical wiring, local sensor safety and stopping remain unqualified.

## Raspberry Pi deployment: prepared, not executed

The authorized host probe could not resolve diyan07.local; the last-known 192.168.1.42 SSH connection was denied before authentication. No Pi command ran. Its present IP, Python packages, camera, services, CPU/RAM and FPS were not measured. The historical 7.7-7.8 FPS is user-provided information, not a new benchmark.

At a future authorized Pi terminal, inspect existing processes, port 7000, environments and services first. Preserve Telegram notifications and SSH. Use a new environment/configuration; do not replace a working service or install systemd automatically. Raspberry Pi OS OpenCV/NumPy should already import; qualify missing packages separately rather than changing system Python blindly.

```bash
python3 -c 'import sys, cv2, numpy; print(sys.version, cv2.__version__, numpy.__version__)'
python3 -m venv --system-site-packages .venv-phase3
.venv-phase3/bin/python -m pip install -r software/pi/requirements.txt -e software/pi
.venv-phase3/bin/python -m pip check
.venv-phase3/bin/python tools/qualify-demo.py --output build/diagnostics/pi-baseline.json
# On the trusted laptop, start simulation.twin --scenario empty --host LAPTOP_PRIVATE_IP
.venv-phase3/bin/python -m quadruped.main --camera-backend usb --camera-device /dev/video0 --width 640 --height 480 --fps 8 --actuator-backend virtual --virtual-sensors --simulator LAPTOP_PRIVATE_IP --vision-state build/state/pi-vision.json --host 127.0.0.1
.venv-phase3/bin/python tools/qualify-demo.py --url http://127.0.0.1:7000 --output build/diagnostics/pi-running.json
```

View locally or use an authorized SSH tunnel to loopback; exposing --host PI_PRIVATE_IP requires a trusted LAN and firewall. Restrict simulator UDP to the Pi. No public Internet exposure. The read-only diagnostic enumerates camera names and GETs state; it does not capture/store images, arm, configure services or inspect credentials. Diagnose pip-check warnings from actual output before changing packages. CI Python 3.13 execution and aarch64 wheel availability are compatibility checks, not Pi installation evidence. Picamera2 remains optional; USB V4L2 is the primary real-camera backend.

## Mechanical and local-safety boundaries

Simulation-only --smoothing-rate accepts 0-3 rad/s, default 0/off. It replaces one latest target vector, with no motion FIFO; STOP clears the active mask immediately. [Measured comparisons](MODEL_STUDY.md) show smaller motor-target increments but increased raw-target tracking lag, so smoothing is not enabled by default. Torque, collision checks, physical gait tables, CAD and calibration are unchanged. Fixed fixture, kinematic proxy, free-base physics and physical walking are separate claims.

Passive TEL1 parsing validates future diagnostic records without sending CAPS/TELEM or qualifying them for motion. Output-enable state is unknown in TEL1. See [extension contract](EXTENSIONS.md). No physical sensor/watchdog implementation or test is added here.

## Optional recordings

Recordings are debugging aids, not acceptance requirements. Do not capture private scenes. Stop other owners of /dev/video0 before the standalone tool. Outputs stay in ignored build/recordings; never commit private video.

```bash
python tools/record-usb-camera.py --device /dev/video0 --seconds 10 --output build/recordings/target.avi
python -m simulation.twin --headless --scenario empty --demo forward --arm-demo --steps 720 --record build/recordings/virtual.avi --report build/recordings/virtual.json
```

The standalone camera duration caps at 30 s; simulation recording needs 1-7200 steps and uses bounded TinyRenderer frames. Optional manual CI record_demo retains the earlier recording feature. No recording proves physical locomotion.

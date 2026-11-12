# Sensor commissioning release — 12 November 2026

**SOFTWARE READINESS PARTIAL. Non-actuating candidate; physical locomotion is not qualified.**

Candidate branch: `release/sensor-commissioning`. Integration merge `488b837a90cb214e07eaaa5846b4df3f1d364d85` combines the tested PR #7 merge with `origin/main`, preserving both parents, authorship, CAD, gait and calibration data. Qualified implementation `1246f7af4be6d87fc5132ab323aa269ffdd2d223` contains the fixes below; the Pi archive was `9fe42b1` with identical application/firmware/simulator source. Final source/evidence identities and CI are recorded in the [release evidence](../evidence/release-2026-11-12/README.md).

## Audited state and integration

GitHub default branch is `main`, fetched at `f625250`. PR [#6](https://github.com/diyan07-ctrl/Quadruped107/pull/6) merged into Phase 3 at `e5ac1be` on 11 November 2026; PR [#7](https://github.com/diyan07-ctrl/Quadruped107/pull/7) merged into Phase 3 at `6e0d578` the same day. Neither merge is present in `main`. Before integration, Phase 3 was 23 ahead / 6 behind `main`, with merge base `ffd2294`. The six main-side commits are preceding stacked PR merges and the author-information edit. Integration required no conflict resolution and retained that edit. [Phase 3 merge CI passed](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/43056929603).

The original local checkout remains on `phase5/software-hardware-readiness` at `edf08eb`; candidate work is isolated in sibling `Quadruped107-release`. No reset, rebase or automatic main merge was performed. Existing development branches and historical evidence remain intact. Firmware gait `motion.h` and all 51 preservation-check assets retain original content hashes. The suspected damaged PCA and all actuators were untouched.

## Findings and repairs

| Severity | Finding | Implemented response |
| --- | --- | --- |
| High | Final integration absent from main; current docs still called merged PRs open | Preserve both histories in an isolated integration merge; supersede stale current status, retaining historical reports |
| High | Circular objects touching a frame edge could pass geometry checks | Explicit clipped-contour rejection; centered blue/yellow acceptance and four-edge regressions |
| Medium | Qualification runner returned success even when individual checks failed | Aggregate nonzero exit and regression; record dirty paths at start |
| Medium | Offscreen recording had no black/flat-frame gate or per-video-frame measured joint evidence | Validate capture, record bounded render diagnostics, write `.joints.jsonl` with measured positions and separate requested/motor targets, STOP offline engine on exit, close renderer after capture failure |
| Medium | Supported four-touch profile and some polarities lacked qualification coverage | Native and AVR matrix for all 3/4/5 counts, active high/low; actual C++ no-echo TEL2 replay into Pi, ARM rejection and urgent STOP assertions |
| Medium | Preflight checked module discovery rather than actual import/ABI success, assumed video0 | Bounded subprocess imports, package versions, explicit camera/serial/I2C existence/permissions and stable serial candidates; no device opens |
| Medium | Virtual Pi launch omitted explicit virtual sensor selection | Select virtual sensor source in the existing simulator-backed launch |
| Low | Windows checkout translated LICENSE despite exact-byte preservation check | Pin LICENSE to LF; original Git blob is unchanged |

No HSV, contour shape, freshness, challenge, watchdog, lease or mechanical limits were relaxed. No new sensor, AI pipeline, physical driver or PWM path was introduced.

## Verification scope

| Check | Status | Actual scope |
| --- | --- | --- |
| Integrated baseline | PASS | 215 Python tests; initial three local validation failures diagnosed as missing Node dependencies and license checkout line endings |
| Regression | PASS | 222 Python tests; all 14 established local checks after environment correction |
| Native firmware | PASS | 12 executable mock variants; real sketch parser and no-echo/valid TEL2 → actual Pi SensorManager |
| AVR | PASS | 10 configurations compile, including 7 sensor variants, disabled calibration, inhibited production and generated virtual Uno; no upload |
| Recorded vision | PASS | Same frozen real yellow source frames and background crops evaluated before/after; unknown screenshot labels remain unknown; no known false positives |
| Recorded virtual output | PASS | Video decoded and frame count matched measured eight-joint sidecar; requested states kept separate; virtual output disarmed at exit |
| Genuine visible GUI | PASS, bounded observation only | Foreground OpenGL robot observed and image retained; not a 900-second active run |
| Initial disarmed GUI attempt | FAIL | Joint limit excursion at step 4474; this passive disarmed model case is retained as a failure, not physical instability evidence |
| Subsequent disarmed GUI observation | PASS | 28800 steps completed without simulation fault; no active control/endurance claim |
| New headless 905-second attempt | FAIL at admission | HTTP 409 before active collection; zero active seconds/samples. The discarded response body prevents exact retrospective diagnosis; helper now retains endpoint/reason |
| Active visible GUI endurance / final live transport fault matrix / Windows-owned heartbeat | NOT TESTED | Smoke observation and Pi-owned admission failure do not substitute; historical Windows-owned tunnel failure remains separate |
| Actual Pi 3.13 imports and selected tests | PASS | 79 tests in six modules, zero skips, existing isolated environment on actual aarch64 Pi; original binary diff and staged status preserved |
| Live yellow placement | FAIL | Operator-ready 8.078-second trial: 0/9 sampled frames detected. Earlier illuminated scene selected a tiny fragment rather than the ball. Actual frames and diagnostics preserved |
| Physical sensors/OLED/AVR resources/electrical STOP | NOT TESTED | Software mocks and compiler results do not qualify connected devices, stack high-water, reset electrical behavior or physical stop |

Recorded yellow images show both low saturation and incomplete outlines. Threshold changes alone do not establish a valid target. Offline evaluation reports source hash, category where known, rejection, coordinates, circularity/fill, runtime and false-positive observations. Live target trials still need centered/left/right, movement/loss/reacquisition, multiple objects, distractors and color switching with measured virtual joint output. The camera must be illuminated and the entire ball outline visible.

OpenGL window capture in the background initially showed the underlying terminal; activation exposed the genuine robot view. This is evidence of capture/foreground sensitivity, not proof of the historical black capture's root cause. TinyRenderer recording validation cannot certify an OpenGL screen recording. Keep the GUI foreground for operator captures; retain failed attempts. Browser screenshot automation also encountered a URL-verification tool blocker; do not represent a camera frame as a dashboard screenshot.

## Architecture and authority

USB camera → single Pi capture owner → bounded HSV/identity tracker → existing MotionController. The controller owns mode/intent/STOP arbitration and the virtual Uno protocol backend. PyBullet consumes virtual actuator traces and records measured simulated joint state. Optional OLED runs on an isolated worker at no more than 5 Hz; missing/wrong-address/blocked transfers cannot own STOP.

| Sensor source | Actuators | Permission |
| --- | --- | --- |
| Explicit virtual simulator telemetry | Explicit virtual Uno | Existing guarded simulation modes, fresh disarmed handshake and explicit enable |
| Physical sensor-only Uno | Explicit virtual Uno | Monitoring and guarded manual virtual poses/joints only; real telemetry owns SensorManager and cannot be overwritten by simulator sensors |
| Any source | Future physical actuator hardware | Inhibited; no working physical-actuation launch |

Physical URM37 does not prove swept body clearance. Physical exploration, reverse and turns remain inhibited. Sensor data cannot ARM. Missing, invalid, old, duplicated, reordered, reset or disconnected observations cannot renew authority. STOP cancels queued work and recovery stays disarmed. Digital touch presence cannot be inferred from an inactive input; electrical verification remains mandatory.

## Deployment and rollback

Use an isolated checkout of the reviewed candidate. Preserve `git status --porcelain`, binary diff and environment versions from any existing Pi checkout before doing work. Do not overwrite it, install services or change OS Python, network, firewall, SSH or Telegram. The existing Pi `.venv-pi-virtual` may be used after successful imports and `pip check`; its system Python alone lacks Flask. Candidate tests ran from `/tmp` without altering the environment.

For a new environment on an already prepared Pi OS:

```sh
git status --short
git rev-parse HEAD
python3 -m venv --system-site-packages .venv-pi-virtual
.venv-pi-virtual/bin/python -c 'import cv2,numpy'
.venv-pi-virtual/bin/python -m pip install -r software/pi/requirements.txt -e software/pi
.venv-pi-virtual/bin/python -m pip check
.venv-pi-virtual/bin/python tools/pi-preflight.py --output build/preflight.json
```

This uses existing OS OpenCV/NumPy; missing packages are an operator prerequisite, never an automatic apt action. Hardware-free developer/CI installation instead uses `software/pi/requirements-dev.txt` and `simulation/requirements.txt` (OpenCV headless 4.11.0.86, PyBullet 3.2.7). The preserved Windows environment has PyBullet 3.2.5 and is explicitly not equivalent. Freeze the actual environment with `python -m pip freeze` in session evidence; CI separately resolves the pinned simulator environment and Python 3.13/aarch64 wheels.

Start a simulator with an explicit scene where virtual sensing is required:

```sh
python -m simulation.twin --headless --scenario empty --host VERIFIED_LAPTOP_PRIVATE_IP --port 7002
```

Run one Pi launch at a time, using `PY=.venv-pi-virtual/bin/python`. Ports must be free and the camera must have one owner.

```sh
# 1. Completely virtual camera, sensing and output (simulator already running).
$PY -m quadruped.main --simulate --actuator-backend virtual --sensor-source virtual --simulator VERIFIED_LAPTOP_PRIVATE_IP
# 2. Real USB camera, virtual sensing and output.
$PY -m quadruped.main --camera-backend usb --camera-device /dev/video0 --actuator-backend virtual --sensor-source virtual --simulator VERIFIED_LAPTOP_PRIVATE_IP
# 3. Verified real Uno sensors and virtual output; stable device identity required.
$PY -m quadruped.main --camera-backend usb --camera-device /dev/video0 --actuator-backend virtual --sensor-source physical_uno --sensor-port /dev/serial/by-id/VERIFIED_UNO --sensor-config deploy/sensors.three.json
# 4. OLED mock with explicitly synthetic camera and virtual output.
$PY -m quadruped.main --simulate --actuator-backend virtual --sensor-source none --oled mock
# 5. Verified physical OLED; camera/output remain virtual.
$PY -m quadruped.main --simulate --actuator-backend virtual --sensor-source none --oled ssd1306 --oled-bus 1 --oled-address 0x3c
```

Use the [bench procedure](SENSOR_BENCH.md) before launch 3 or 5. Install optional `requirements-oled.txt` only into the chosen environment after module verification. `none` is explicit no-sensing, not fallback to fictitious readings. `--sensor-source physical_uno` requires an explicit port, cannot coexist with virtual/test sensors and never silently switches provider. No launch selects physical actuators.

Rollback means STOP, confirm virtual active mask zero, terminate only candidate-owned foreground processes, and return to the previously recorded checkout/environment. Do not reset or clean the operator checkout. Keep `/tmp` and local logs until reviewed. Reverting these commits requires separate review; switching back never authorizes physical operation.

## Remaining release gates

Frozen implementation CI passes on push and PR, including Linux full regression, Python 3.13, aarch64 wheels, native/AVR builds and packaging/web checks. Logs and SHA-256 manifest are frozen in the evidence index. Remaining gates are the live target matrix, new headless admission/transport diagnosis, coordinated active GUI/endurance/fault tests and dashboard screenshot where tooling permits. These remaining live software qualification failures keep **SOFTWARE READINESS PARTIAL**. Physical sensor identity/voltage/wiring, distance accuracy, touch bias/noise/presence, OLED compatibility, MCU stack/ISR/reset timing and independent electrical STOP remain separate hardware gates. Successful sensor commissioning will still not qualify servos, safe standing, gaits or physical autonomy.

The candidate-owned Pi processes and temporary SSH tunnel were stopped. Three genuine images (real camera, OpenCV diagnostic rejection, visible PyBullet) were saved to Desktop `Quadruped107-LinkedIn-2026-11-12`, within the requested five-image maximum. The dashboard screenshot remains blocked by browser URL verification; its actual state JSON is saved separately. No LinkedIn post was made.

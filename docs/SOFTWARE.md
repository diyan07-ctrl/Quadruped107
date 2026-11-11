# Software and development

## Current Phase 2 development configuration

Use the [local laptop instructions](../simulation/PHASE2.md). Add --virtual-sensors with explicit virtual actuators and a simulator endpoint; --navigation-config / --sensor-config select reviewed JSON assumptions. Flask, camera, serial and ownership remain; no new dependency is introduced.

The bounded virtual-autonomy worker is independent of camera capture/vision. Sensor ingress can submit asynchronous priority STOP; the controller guard and admission checks repeat safety validation. One sensor manager owns freshness/debounce; there is no competing motor controller. The dashboard exposes only supported modes and labels all sensor states simulated.

**Pi deployment is postponed.** No SSH, OS, service or network changes are performed in Phase 2. Pi commands below are retained Phase 1 installation references, not tasks executed or prerequisites for these simulations. Actual Pi CPU/RAM/camera measurements remain unperformed.


## Active configuration

Use Python 3, Flask/HTTP/MJPEG, OpenCV/NumPy and pySerial. Preserve Arduino C++/Adafruit PCA9685 for the future mandatory Uno. No framework migration, ROS, broker or cloud dependency is needed. Pi 4 (2 GB, user-reported Raspberry Pi OS 64-bit Trixie) is primary; PyBullet runs on a development laptop.

**This assignment prohibits physical actuation.** Default CLI actuator mode is `serial-monitor`; its ARM endpoint is rejected. Explicit `--actuator-backend virtual` selects the host Uno emulator. `--simulate` explicitly selects both synthetic camera and protocol virtual actuators. A real USB camera plus virtual outputs requires both `--camera-backend usb --actuator-backend virtual`. No missing-device fallback occurs.

## Raspberry Pi installation

Review existing processes and ports before startup. These commands install only the selected checkout's environment:

```bash
sudo apt update
sudo apt install python3-venv python3-opencv python3-numpy
sh deploy/install-virtual-pi.sh
sh deploy/run-virtual-pi.sh LAPTOP_PRIVATE_IP
```

The launcher selects /dev/video0, V4L2/YUYV, 640×480, requested 8 FPS, explicit virtual outputs, editable [vision settings](../deploy/vision.example.json) and the simulator lease. Requested FPS is not a measurement or camera guarantee. Use --camera-device, --width, --height and --fps to change capture settings. Picamera2 is lazily imported only for --camera-backend picamera2 and may be installed separately through OS packages. Broken CSI initialization never blocks USB mode.

Start [laptop simulation](../simulation/README.md) first. Open http://PI_IP:7000 on the trusted LAN; explicitly enable virtual actuators and select OpenCV. The inherited service is not installed or started for this assignment. Existing Telegram and system services are untouched. SSH was inaccessible from the development session; these Pi commands are reproducible instructions, not executed evidence.

## Development and packaging

```bash
python -m venv .venv
.venv/bin/python -m pip install -r software/pi/requirements-dev.txt -r simulation/requirements.txt -e software/pi
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python simulation/build_model.py --check
.venv/bin/python tools/generate-motion-data.py --check
.venv/bin/python -m quadruped.main --simulate --host 127.0.0.1
```

Windows uses .venv/Scripts/python.exe. The Pi uses OS native OpenCV/NumPy through --system-site-packages; do not install the laptop development wheels into that environment. Flask and pySerial versions remain pinned in [requirements](../software/pi/requirements.txt). Node/Mermaid are CI tools, not runtime requirements. PyBullet is an optional laptop dependency. Original code/license obligations remain unchanged.

## Ownership, concurrency and freshness

Run exactly one application process. Camera capture owns its native device; one serial worker owns USB or virtual serial; one vision worker processes latest frames; the existing scheduler and independent browser/observation lease guard arbitrate movement. The optional network bridge and its independent guard never wait for OpenCV. Threaded Flask serves one trusted operator, with same-site ownership cookies and generation checks. STOP is available to every same-origin browser.

Camera frames are BGR. USB capture requests YUYV and one driver buffer; driver support is not guaranteed. Publication records capture-call start using monotonic time (conservative software age, not sensor exposure time). Frames/read calls older than 800 ms are rejected; vision results older than 500 ms are rejected. The default five-second identical-pixel heuristic conservatively detects possible freeze; truly static scenes may trigger it. Failed open/read retries after 500 ms and releases its resource. Latest-frame semantics bound application backlog. A blocked native camera call cannot be forcefully interrupted; the independent guard stops control and process restart may be needed. No second capture owner is opened.

Blue detection uses configurable HSV, morphology and principal valid contour. It reports bbox, center, normalized horizontal error, area, circularity and software timestamp. These are geometric diagnostics, not a calibrated probability. FSM persistence defaults to two frames, entry/exit error .32/.20, requests at most every .6 s, target loss .35 s and observation age .5 s. Center holds stand; no default forward exploration or unbounded search. Optional bounded search must be enabled in JSON. Obstacle injection is virtual-only. Real local sensing remains unimplemented.

Serial ordinary queue depth four, dispatch freshness 250 ms and priority STOP preserve Phase 0.1 contracts. Controller generations prevent old ARM/MOVE/SERVO completion from reinstating motion. Local inhibition precedes eventual wire STOP acknowledgment; no physical stop-time guarantee exists. Missing simulator acknowledgments or reset latch a stop; receiver lease removes virtual forces. Restart requires a disarmed handshake and explicit enable.

## Diagnostics and targets

/api/state exposes camera health/errors/reconnects/actual FPS/frame age, processing FPS/time, detection/FSM transitions, virtual ticks/active mask, bridge acknowledgments, STOP/inhibition, process CPU and Linux RSS/available RAM. CPU is process-time divided by elapsed wall time (100% is one logical core); values can exceed 100%. Missing host counters are null. Dashboard text reports the same fields. /api/camera-frame and /video-feed expose latest annotated JPEG.

Design targets, **not Pi measurements**: capture approximately the camera's sustainable 8 FPS; processing ≤100 ms/frame at 640×480; observation ≤500 ms; RSS <350 MiB and process average <150% CPU on Pi 4; no frame FIFO; bridge acknowledgment ≤150 ms and recovery to diagnostics within 5 s; fresh private-LAN STOP dispatch normally <100 ms excluding native/OS stalls. Timeout values specify software policy rather than hard real-time bounds. Existing Uno SRAM/flash measurements and remaining electrical tests are in [validation](VALIDATION.md) and [verification](HARDWARE_VERIFICATION.md).

Native V4L2/libcamera/OpenCV, DNS initialization and the inherited threaded HTTP streaming server do not have hard bounded execution/resource guarantees. Keep one browser/video consumer, never expose ports to the Internet, and measure real workloads before optimizing. Hand-gesture support is optional and requires its separately supplied compatible model; it is not a requirement for blue-object integration.

Shutdown inhibits motion before closing bridge, serial, camera and detector workers. Bounded joins warn if native code remains blocked. Foreground launch avoids altering boot behavior while hardware is unqualified. [Power](../hardware/Power/README.md) and [safety](SAFETY.md) remain mandatory for future physical deployment.

## Phase 3 runtime contract

See [operator guide](PHASE3.md) for reproducible laptop/Pi commands. GET/POST /api/vision applies bounded validated settings with an expected revision; atomic schema-1 preferences default to ignored build/state/vision.json. Applying a change cancels motion and resets target/session state. The owner camera thread alone renders explicit synthetic fixtures; POST /api/simulation/target is unavailable for real cameras.

Decision history holds at most 128 events, with requested/accepted/submitted/completed/rejected status. UI displays at most 32, using textContent. Personality is explicitly selected, sensor-gated and deadline-bounded; no new production poses. Optional simulation interpolation uses one latest eight-value vector and immediate STOP mask removal. Passive TEL1 diagnostics are never motion-qualified.

CI executes the full suite on Python 3.11 and selected vision/telemetry checks on Python 3.13, checks dependency consistency and downloads cp313/abi3 aarch64 OpenCV/NumPy wheels. This does not validate Pi OS packages or native-device performance. tools/qualify-demo.py records read-only imports, pip-check and optional local application diagnostics; it captures no images or secrets.
## Sensor-only software readiness

The [software-readiness record](SOFTWARE_READINESS.md) describes the separate non-actuating Uno target, negotiated TEL1/TEL2 monitoring provider, optional Pi OLED and disabled calibration preparation. Select sensors explicitly with `--sensor-source`; actuator selection remains independent. Physical monitoring requires virtual actuators and does not permit navigation or physical ARM. Existing virtual/PyBullet behavior remains available with its original source selection.

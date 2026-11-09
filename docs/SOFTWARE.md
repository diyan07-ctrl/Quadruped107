# Software and development

## Stack decisions

Use a current supported 64-bit Raspberry Pi OS release (the current documentation describes Trixie), Python 3.11+, Picamera2/libcamera, OpenCV/NumPy, pySerial, Flask, and plain HTML/CSS/JavaScript. Use Arduino C++ and Adafruit PWM Servo Driver Library, Arduino CLI, unittest, GitHub Actions and systemd.

Retain Flask and same-port HTTP/MJPEG: there is an existing tested implementation, no measured latency deficit, and changing to FastAPI/WebSockets would add migration and concurrency work. WebSockets can be evaluated later if measured command or telemetry requirements justify them. No ROS 2, database, broker, cloud inference or paid API is required.

Pi camera/NumPy/OpenCV come from OS packages to keep native dependencies compatible. Flask 3.1.2 and pySerial 3.5 remain pinned. Development uses OpenCV headless 4.11.0.86; optional MediaPipe is separately constrained and requires a compatible OS/Python/model. Dependency upgrades require tests, not automatic replacement during a structural refactor.

Sources: [Raspberry Pi OS](https://www.raspberrypi.com/documentation/computers/os.html), [camera software](https://www.raspberrypi.com/documentation/accessories/camera-software.html), [Picamera2 installation](https://github.com/raspberrypi/picamera2), [Flask threading/deployment](https://flask.palletsprojects.com/en/stable/deploying/).

## Pi installation

From the repository root on Pi:

```bash
sudo apt update
sudo apt install -y python3-venv python3-picamera2 python3-opencv python3-numpy python3-serial rpicam-apps
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r software/pi/requirements.txt -e software/pi
rpicam-hello --list-cameras
rpicam-still --nopreview -o /tmp/quadruped-camera.jpg
sudo usermod -aG dialout "$USER"
```

Log out/in after group changes. Keep --system-site-packages; do not install requirements-dev.txt into the hardware Pi environment, since it adds a separate OpenCV wheel. Use the modern camera stack. Qualify package availability on the selected OS image.

Flash the [Uno sketch](../firmware/uno/README.md), close Serial Monitor and connect its USB to Pi. Start:

```bash
.venv/bin/python -m quadruped.main --serial-port /dev/serial/by-id/<your-uno-device>
```

Open http://PI_IP:7000 on the trusted LAN. Auto-detection is the default; ambiguous serial candidates are rejected. Startup and reconnect do not enable servos. Read [SAFETY](SAFETY.md) before enabling.

## Hardware-free development

```bash
python -m venv .venv
.venv/bin/python -m pip install -r software/pi/requirements-dev.txt -e software/pi
.venv/bin/python -m quadruped.main --simulate --host 127.0.0.1
.venv/bin/python -m compileall -q software/pi/quadruped tests tools
.venv/bin/python -m unittest discover -s tests -v
node --check software/pi/quadruped/web/app.js
node tools/check-repository.mjs
```

On Windows use .venv/Scripts/python.exe. Node is validation tooling, not a Pi runtime dependency. The editable install makes imports and packaged web assets available outside the source directory. See [CONTRIBUTING](../CONTRIBUTING.md) for standards.

## Processes and configuration

Run one process, not multiple web workers: one camera owner, one serial I/O owner, a scheduler, a lease guard, a vision worker, and threaded HTTP handling. The camera publishes the latest frame; no vision FIFO is built. Expiry uses publication time, so capture backlog and latency still need measurement. The serial worker maintains heartbeats independently of video. Review [architecture targets](ARCHITECTURE.md) before optimizing.

The existing Werkzeug threaded server is retained for the single-operator trusted-LAN prototype. It has no authentication, TLS, rate limiting, or bounded multi-user streaming capacity. Do not expose it to the Internet or put several operators on it. A production-server change requires hardware-owner lifecycle tests.

Options and API are in [software/pi](../software/pi/README.md). Environment variables: QUADRUPED_HOST (0.0.0.0), QUADRUPED_PORT (7000), QUADRUPED_SERIAL_PORT (auto), QUADRUPED_CAMERA_INDEX (0), QUADRUPED_GESTURE_MODEL (unset). --simulate is explicit and has no environment toggle.

## Boot service

For an editable install in ~/Quadruped107:

```bash
mkdir -p ~/.config/systemd/user
cp deploy/quadruped107.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now quadruped107
journalctl --user -u quadruped107 -f
```

The [service](../deploy/quadruped107.service) uses the checkout virtual environment and python -m quadruped.main. Edit paths if installation differs. Optional configuration is ~/.config/quadruped107.env (KEY=value; never commit credentials). For boot without login, sudo loginctl enable-linger "$USER". Restarts reconnect disarmed. Confirm camera permissions for the chosen user session and stop any manually started duplicate process.

Pi 5 portability requires OS/camera/power qualification, not a new messaging layer. The optional OLED and pan servo introduce no required Pi dependencies.

## Phase 0.1 concurrency and ownership

The same Flask/MJPEG stack remains. ARM sets a same-site HttpOnly control cookie; API clients must persist cookies. Only the owner may send modes, servo adjustments or lease heartbeats; STOP is available to other same-origin clients. Ownership generations prevent delayed requests from acting after STOP/re-arm. This is local arbitration, not Internet authentication.

Serial submit/wait separates queue admission from acknowledgment waiting. Up to four ordinary requests are bounded by 250 ms dispatch freshness; a separate coalesced STOP slot cancels older work. Controller reservations and generations prevent concurrent ARM/MOVE/SERVO races; no state lock is held through an acknowledgment timeout. Late old acknowledgments cannot re-enable motion. The existing OS write timeout can still delay dispatch; physical stop time is unmeasured.

Picamera2 uses queue=False and no extra real-camera wait. Native capture and inference can still block; safety has independent threads and Uno timeout. Startup cleanup now covers server creation/start failures; shutdown inhibits motion before camera teardown. Detector teardown is skipped if inference has not returned by the join deadline. Resource/recovery targets and unbounded HTTP/native-call limits are explicit in [ARCHITECTURE](ARCHITECTURE.md).

[Calibration profiles](CALIBRATION.md) are validated offline only. [Telemetry/accessory contracts](EXTENSIONS.md) are not activated. Pi-side OLED is optional and does not share Uno I2C. See [Power](../hardware/Power/README.md) and [physical qualification](HARDWARE_VERIFICATION.md) before a hardware deployment.

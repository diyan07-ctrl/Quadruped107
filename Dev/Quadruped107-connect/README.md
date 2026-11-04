# Quadruped107 Connect — Pi 4 + Uno R3

The active runtime uses **Raspberry Pi OS + Picamera2 + Flask + USB serial**. Flash `sketch/sketch.ino` to an **Arduino Uno R3**, and run `python/main.py` on the Pi 4. Follow the [main setup guide](../../README.md) and [wiring / architecture](../../docs/architecture.md).

## Configuration

| CLI option | Environment variable | Default |
| --- | --- | --- |
| `--host` | `QUADRUPED_HOST` | `0.0.0.0` |
| `--port` | `QUADRUPED_PORT` | `7000` |
| `--serial-port` | `QUADRUPED_SERIAL_PORT` | `auto` |
| `--camera-index` | `QUADRUPED_CAMERA_INDEX` | `0` |
| `--gesture-model` | `QUADRUPED_GESTURE_MODEL` | Unconfigured |
| `--simulate` | None | Off; synthetic video and serial when selected |

## API

All control requests use JSON POST bodies. Reads never start motion. There is no Arduino Bridge or App Lab dependency.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/state` | Uno link, servo enable, camera, vision and motion status |
| GET | `/api/mode` | Current motion state |
| GET | `/api/camera-frame` | Base64 JPEG snapshot |
| GET | `/video-feed` | MJPEG stream, same port as the web app |
| POST | `/api/arm` | Enable servos without starting a pose |
| POST | `/api/stop` | Abort and disable servo outputs |
| POST | `/api/mode` | `{"mode":"stand"}` or another motion / control mode |
| POST | `/api/heartbeat` | `{"motion":null}` or the currently held direction |
| POST | `/api/servo` | `{"channel":0,"pulse":278}` for individual calibration |

The browser sends a heartbeat every 250 ms. Outputs are disabled after one second without it. Directional commands repeat only while held; on release the browser requests `stand`. STOP can interrupt a pose or gait. A missing USB heartbeat disables Uno outputs after 1.5 seconds. There is no automatic arming after startup, reset, reconnect, or STOP.

## Calibration

The Uno uses the existing channel mapping and pulse tables in [motion.h](sketch/motion.h). The Pi does not generate servo PWM. Pulse values are PCA9685 ticks at 50 Hz, **not angles or microseconds**; each tick is approximately 4.88 μs. The firmware's broad 50–600 bounds do not establish the mechanical travel limits of a particular joint.

Use an isolated, supported joint. Keep a browser heartbeat active by leaving the control page open, enable servos, and wait for any pose to finish. Then, from a terminal on the Pi:

```bash
# Example only: verify the assembled joint's safe limits first.
curl -X POST http://127.0.0.1:7000/api/servo \
  -H 'Content-Type: application/json' -d '{"channel":0,"pulse":278}'
curl -X POST http://127.0.0.1:7000/api/stop \
  -H 'Content-Type: application/json' -d '{}'
```

The calibration API makes a temporary adjustment. Persist verified gait / pose targets by editing `motion.h` and flashing the Uno again. It does not silently rewrite firmware or apply the same calibration to all eight joints. The files under `Dev/Tools/` are historical UNO Q tools and are not compatible with this serial firmware.

## Optional Hand Gestures

The app uses [MediaPipe Tasks Gesture Recognizer](https://ai.google.dev/edge/mediapipe/solutions/vision/gesture_recognizer/python), replacing the UNO Q-specific Edge Impulse integration. Install only on a Python / Raspberry Pi OS combination supported by MediaPipe:

```bash
.venv/bin/python -m pip install -r Dev/Quadruped107-connect/python/requirements-gestures.txt
```

Obtain a compatible `gesture_recognizer.task` model from the official MediaPipe guide and keep its license with your deployment. The repository does not include or automatically download a model. Start with:

```bash
.venv/bin/python Dev/Quadruped107-connect/python/main.py \
  --gesture-model /absolute/path/to/gesture_recognizer.task
```

| Standard model gesture | Pose |
| --- | --- |
| Open_Palm | Initial |
| Thumb_Up | Stand |
| Victory | Greeting |
| Closed_Fist | Tail wag |

Detections require confidence ≥ 0.65 and two consecutive frames. A held gesture runs once until the hand is removed / changes. Camera processing and motion stay on separate threads. If MediaPipe or the model cannot load, the app reports this and disables gesture selection; it does not treat model failure as a working mode.

## Troubleshooting

- **No Uno:** select the correct serial device; inspect `/dev/serial/by-id/`; check `dialout` membership and close Serial Monitor.
- **Firmware handshake failed:** upload this Uno sketch at 115200 baud. The old UNO Q sketch speaks a different protocol.
- **PCA9685 missing:** verify Uno A4/A5, 5 V logic supply, common ground, and address `0x40`.
- **No Pi camera:** check `rpicam-hello --list-cameras`, the CSI ribbon, camera index, and apt-installed Picamera2. A USB webcam is not the default camera backend.
- **Control heartbeat expired:** return to one visible control browser and enable servos again. Background tabs may throttle timers.
- **Servos do not move:** confirm external servo power and D8/OE wiring; then verify safe pulse targets one joint at a time.

Changes made on 2026-11-04 for the Pi 4 / Uno R3 port. GPL-3.0.

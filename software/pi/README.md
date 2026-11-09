# Pi application

One camera owner, one serial owner, latest-frame vision and Flask/MJPEG browser controls. See [software guide](../../docs/SOFTWARE.md) for dependencies, configuration, concurrency and current safety restrictions.

- Synthetic camera + protocol emulator: `python -m quadruped.main --simulate --host 127.0.0.1`.
- Real Pi USB camera + emulator: `python -m quadruped.main --camera-backend usb --camera-device /dev/video0 --actuator-backend virtual`.
- Add `--simulator LAPTOP_PRIVATE_IP` to require the network receiver lease.
- `--camera-backend picamera2` preserves optional CSI support; no CSI dependency exists in USB mode.
- `--vision-config deploy/vision.example.json` selects editable HSV/FSM thresholds.
- Default actuator mode is a physically inhibited serial monitor, with no automatic simulation fallback.

GET: /api/state, /api/mode, /api/camera-frame, /video-feed.
POST JSON: /api/arm, /api/stop, /api/mode, /api/heartbeat, /api/servo.
POST /api/simulation/obstacle accepts {"blocked":true} only with virtual actuators. Clearing it does not re-arm.
Owner clients retain the HttpOnly control cookie. STOP is available to all same-origin clients. An explicit enable is required after startup, reconnect, fault or STOP.

The existing HTTP/MJPEG interface and browser assets remain lightweight. Physical ARM is prohibited on this branch. See [simulation](../../simulation/README.md), [deployment](../../deploy/README.md) and [validation](../../docs/VALIDATION.md).

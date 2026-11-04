# Pi 4 / Uno R3 Port Validation

Validation date: 2026-11-04. Tests were run on a Windows development computer, without a connected Raspberry Pi, CSI camera, Uno, PCA9685, or robot.

## Automated Checks

- **Uno R3 compilation:** Arduino AVR core 1.8.8, Adafruit PWM Servo Driver Library 3.0.2, Adafruit BusIO 1.17.4. Uses **10,198 bytes flash (31%)** and **998 bytes global SRAM (48%)**, leaving 1,050 bytes for stack / locals. No firmware upload was performed.
- **Python behavior tests:** serial ID correlation, heartbeat / STOP during a pending move, no command replay after link failure, disarmed startup, browser lease expiry, autonomous single-step scheduling, reset handling, invalid calibration inputs, stale frames, API validation, static assets, JPEG snapshots, and MJPEG streaming.
- **Vision checks:** synthetic BGR blue circles select left / forward / right; a close ball stops; a red circle is rejected.
- **HTTP smoke test:** launches the real CLI in `--simulate` mode, fetches the page and video stream over localhost, enables simulated servos, issues a motion, sends a heartbeat, and stops.
- **Static checks:** Python bytecode compilation, JavaScript syntax, README target paths, and Git whitespace checks.

Run the hardware-free suite with:

```bash
python -m unittest discover -s tests -v
```

The GitHub workflow runs the Python suite and Uno compilation. Simulation never opens real camera or serial hardware.

## Hardware Checks Still Required

1. Install the Pi dependencies and confirm `rpicam-hello --list-cameras` detects your camera model. Verify video orientation, colour and sustained capture on the actual Pi 4.
2. Flash the Uno R3, verify the USB identity handshake and selected serial device, and confirm a fresh connection leaves outputs disabled.
3. With servo power disconnected, measure D8/OE: HIGH during Uno reset and STOP, LOW only after explicit enable. Confirm the external 10 kΩ pull-up and shared ground.
4. Check servo-rail voltage, polarity, current capacity, and the physical disconnect independently of Pi/Uno logic power.
5. Support the chassis and calibrate each joint. The inherited pulse tables, 50–600 firmware bounds, and initial software position estimate are not a calibration certificate for your assembly.
6. Test each pose and gait step with mechanical clearance. Verify release-to-stand and STOP during a long pose.
7. Unplug USB / stop the Pi process and verify the Uno's 1.5-second heartbeat watchdog disables outputs. Close or hide the browser and verify the browser lease also disables outputs.
8. Disconnect / obstruct the camera during vision mode and verify the robot disables outputs instead of acting on stale video. Then verify tracking on real images and lighting.
9. If enabling MediaPipe, validate package availability, model loading, recognition accuracy, and frame rate on your specific OS / Python combination. The gesture model is not bundled and this path has not been run on hardware.
10. Adapt the original CAD mounting and cooling to the Pi 4, Uno R3, CSI camera and cables. The original CAD geometry is retained.

These checks separate a software port from a verified physical robot. Avoid treating compile / simulation results as proof of reliable locomotion, electrical safety, camera compatibility, or gesture recognition on the assembled platform.

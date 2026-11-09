# Validation

Phase 0 inspection began from fb5bacc on 2026-11-09. No Raspberry Pi, CSI camera, Uno, PCA9685, sensors, or robot was accessed. Hardware results remain pending.

## Reproducible commands

From the repository root after installing dependencies as described in [SOFTWARE](SOFTWARE.md):

```bash
python -m compileall -q software/pi/quadruped tests tools
python -m unittest discover -s tests -v
python tools/check-installed.py
node --check software/pi/quadruped/web/app.js
node tools/check-repository.mjs
arduino-cli core update-index
arduino-cli compile --profile uno firmware/uno/sketch
git diff --check
```

The CI Python job also builds and installs a wheel before checking imports and browser assets outside the checkout. The repository validator requires baseline history; CI uses a full clone.

## Results and environment

- Local saved virtual environment is unusable: its Python 3.11 executable no longer exists.
- uv discovery found no usable interpreter. A workspace-local Python installation attempt failed because outbound network access was restricted.
- Arduino CLI was not found on PATH or in the inspected installation locations; no local firmware compilation was performed.
- Local JavaScript syntax, repository links/paths, credential-pattern review, and Git staged whitespace checks passed. The repository check verified 56 preserved baseline blobs and classified four intentional identical-STL groups.
- Python tests, dependency installation, installed-package checks and Uno compilation await remote CI; local unavailability is not a successful result.
- No dependencies were installed locally. A passing CI dependency-install step must establish the remote test environment separately.

The inherited validation document reported a 2026-11-04 Uno compile at 10,198 bytes flash and 998 bytes global SRAM, plus software tests. These are historical reported results, not reruns and not physical validation. Current firmware source is preserved; new CI results take precedence once available.

## Coverage and limits

The existing suite covers serial request correlation, heartbeat and STOP during a pending move, queue clearing on link failure, disarmed startup, browser lease expiry, single-step autonomous scheduling, reset handling, calibration input validation, stale frames, API validation, static assets, synthetic vision and JPEG/MJPEG HTTP simulation. It does not emulate AVR instruction timing, physical servos, load dynamics, obstacle sensing or a real camera pipeline.

Simulation generates synthetic video and command completions without opening hardware. It is not a physics simulation or proof of stable walking. Optional MediaPipe inference/model loading is not part of the required suite.

## Hardware tests pending

1. Verify camera model/ribbon, OS packages, real BGR colour/orientation, sustained rate, capture freshness and Pi resource use.
2. Verify USB identity and stable device selection; measure startup/reset/reconnect behavior with outputs disabled.
3. Measure OE HIGH through reset/STOP and LOW only after explicit ARM; verify pull-up against the actual breakout.
4. Check servo rail voltage, polarity, transient capacity, regulator cooling, fusing, ground routing and physical power disconnect.
5. Calibrate channel/direction/neutral/endpoints on supported joints; test poses and gait clearances before free walking.
6. Measure STOP during long motion, browser lease expiry, USB loss, Pi termination and reboot; confirm no automatic motion replay.
7. Qualify physical stop integration and MCU hardware watchdog after Phase 1 implements them; the current firmware has neither.
8. Verify URM37 revision/mode/pinout, HC-SR04 and touch logic before adding drivers. Test missing/stale/invalid readings and crosstalk in Phase 2.
9. Test missing camera during vision, real ball tracking and optional gesture model behavior under load.
10. Check Pi/Uno mounting, cooling, cable strain relief, balance, pinch points and a contained demonstration surface.

See [SAFETY](SAFETY.md) for the required supported-test sequence. Pending hardware qualification is a Phase 1 dependency, not an unperformed successful Phase 0 test.

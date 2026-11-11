# Phase 4 — Pi camera and virtual hardware-in-the-loop qualification

## Remediation status — 10 November 2026

**PARTIALLY VERIFIED.** The repaired real-camera/Pi/LAN/virtual-actuator headless run passed 905.094 s, with 904.559 s continuous healthy simulator output and all eight measured joints moving. See the [remediation report](../evidence/phase4/2026-11-10-remediation/reports/REMEDIATION.md). Separate GUI endurance, controlled blue/yellow target trials, real autonomous pursuit and the complete recording set remain unqualified. Physical outputs remain prohibited; do not merge PR #6 or begin powered Phase 5.

Use the existing isolated Pi qualification worktree; preserve the original checkout and staged work. The tested runtime is `ff3827690b635510198d16516237dc77d98013e3`. New instrumentation commands and exact evidence are linked in the report. The sections below retain the original procedures.

Stacked on Phase 3. **No physical actuator tests authorized.** Keep the Uno, PCA9685 and all servos disconnected/unpowered. Preserve existing SSH and Telegram services.

## Read-only Pi preflight

On the Pi, inspect the checkout before switching branches. Preserve local edits and any branch commits.

~~~bash
cd ~/Quadruped107
git status --short --branch
git branch -avv
git config --get-all remote.origin.fetch
git rev-parse HEAD
~~~

A single-branch clone may have a remote-tracking ref from an explicit fetch while its persistent fetch refspec still excludes that branch. If the current refspec excludes Phase 4, add the branch to the tracked set. Fetch before switching:

~~~bash
git remote set-branches --add origin phase4/pi-hil-qualification
git fetch origin
git switch --track origin/phase4/pi-hil-qualification
git branch --show-current
git rev-parse HEAD
test -f tools/pi-preflight.py
~~~

If the local Phase 4 branch already exists, switch to it and set its upstream with `git branch --set-upstream-to=origin/phase4/pi-hil-qualification`. Inspect divergence before moving it. If local edits prevent the switch, leave them in place until their disposition is clear.

Run `python3 tools/pi-preflight.py` for the OS interpreter, then run it with the selected application interpreter to see the deployment dependencies. The import flags check discovery. Verify actual imports independently with `.venv-pi-virtual/bin/python -c 'import cv2, numpy, flask, serial, quadruped'` when using the standard deployment environment.

The script checks Python imports, /dev/video0 existence/access, port 7000 listener state, and checkout presence. It does not open the camera, take frames, launch services, read passwords, use GPIO or contact any other machine. Its output deliberately does not contain IP addresses, user names or private data.

## Separate HIL acceptance

After the preflight, use the [Pi installation procedure](PHASE3.md). On Windows, use the [simulator setup](../simulation/README.md). Start the simulator with `--scenario empty --host WINDOWS_PRIVATE_IP`. The scenario supplies virtual sensor telemetry for the Pi's `--virtual-sensors` option. Use the actual private interface and verify UDP 7002 from the Pi.

Open the camera once, after checking for other consumers. In a Pi foreground shell run:

~~~bash
.venv-pi-virtual/bin/python -m quadruped.main --camera-backend usb --camera-device /dev/video0 --width 640 --height 480 --fps 8 --actuator-backend virtual --virtual-sensors --simulator WINDOWS_PRIVATE_IP --vision-state build/state/pi-vision.json --host 127.0.0.1 --port 7000
~~~

From Windows, forward the loopback dashboard with `ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:17000:127.0.0.1:7000 PI_USER@PI_ADDRESS` and open `http://127.0.0.1:17000`. Confirm the camera is fresh, the virtual sensor data is valid, and the bridge has a disarmed handshake before any explicit virtual enable.

Measure actual camera and perception FPS, frame age, CPU/RSS and Stop/re-enable behavior. Confirm that **real camera -> OpenCV -> decision -> virtual Uno -> UDP -> articulated PyBullet** is functioning; synthetic tests do not establish this. Record genuine tests where recording is available, retain full logs, and keep large or private footage out of normal Git history.

For a simulator restart, verify disarm and zero active outputs before and after reconnection. A Winsock reset from a closed UDP port is recoverable on both the application and simulator sockets. A reset cannot refresh the receiver lease or substitute for a new disarmed handshake.

## Qualification record

### Current hardware session — 10 November 2026

**PARTIALLY VERIFIED.** Authenticated Pi access, clean isolated worktree,
successful preflight, real USB capture at both resolutions, real blue-object
observations, Pi-to-Windows UDP, live dashboard, virtual STOP/fault tests and
measured motion of all eight PyBullet joints were executed. The repaired Windows
suite passed 163 tests and both Uno sketches compiled without upload.

Yellow tracking and sustained freshness/endurance did not meet all acceptance
gates. Do not mark this PR complete or begin powered actuator qualification.
The [current qualification report](PHASE4_VALIDATION.md),
[test matrix](PHASE4_TEST_MATRIX.md), [performance report](PHASE4_PERFORMANCE.md),
[safety report](PHASE4_SAFETY.md) and
[evidence index](../evidence/phase4/2026-11-10/README.md) supersede the earlier
access-blocked status below. Exact instrumented launches are preserved with the
evidence; the GUI session used UDP 17012 and the headless retest UDP 7002.

### Historical checkpoint before this session

- **AUTOMATED TESTED** — Reproduced the restricted-refspec tracking error in a disposable single-branch checkout. Adding the Phase 4 refspec repaired the checkout and made the preflight script available. The Windows suite passed 161 tests, up from the Phase 3 baseline of 157. The model generator, motion data, power tables, simulator validation, model study, proxy probe, and dashboard DOM checks also passed. Both production and virtual Uno sketches compiled locally.
- **WINDOWS SIMULATOR VERIFIED** — Windows 11 rendered the model in the PyBullet OpenGL window and bound UDP 7002 on the private interface. The PyPI 3.2.7 pin required an MSVC source build on this machine. Local simulator runs used conda-forge PyBullet 3.25 with Python 3.11. The repository pin remains 3.2.7 for CI.
- **SIMULATED ONLY** — A Windows synthetic-camera application and a separate headless PyBullet process exchanged UDP traces. Both presets tracked left/right and centered. Blue target loss and yellow operator STOP each cleared the virtual Uno output mask. The receiver recorded 46 distinct armed target vectors, measured eight joint angles, and finished with a zero output mask. Neither run automatically rearmed. The GUI run showed intermittent sensor expiry and failed closed. Use `--headless` for the timed LAN run if the GUI cannot keep telemetry fresh. Keep the existing lease and sensor expiry limits.
- **BLOCKED** — The Pi answered SSH, but unattended authentication was rejected. Pi checkout repair, preflight, real camera capture and performance, physical blue/yellow targets, and Pi-to-Windows HIL remain pending. The synthetic evidence does not qualify the webcam or a physical tennis ball.

Physical movement remains gated by docs/HARDWARE_VERIFICATION.md and hardware/Power/TEST_PLAN.md: inspect/replace damaged PCA9685, qualify servo power/fusing/disconnect/OE, local Uno watchdog/sensing, mechanical calibration and supported-body checks before ever powering a servo.

# Phase 4 — Pi camera and virtual hardware-in-the-loop qualification

Stacked on Phase 3. **No physical actuator tests authorized.** Keep the Uno, PCA9685 and all servos disconnected/unpowered. Preserve existing SSH and Telegram services.

## Read-only Pi preflight

On the user's existing Pi SSH terminal, check out this branch and run:

~~~bash
cd ~/Quadruped107
git fetch origin
git switch phase4/pi-hil-qualification
python3 tools/pi-preflight.py
~~~

The script checks Python imports, /dev/video0 existence/access, port 7000 listener state, and checkout presence. It does not open the camera, take frames, launch services, read passwords, use GPIO or contact any other machine. Its output deliberately does not contain IP addresses, user names or private data.

## Separate HIL acceptance

After the preflight, use the existing docs/PHASE3.md Pi installation and laptop simulator procedure. Open the camera only when it is not owned by another process. Use real USB camera input with explicitly virtual actuator backend and virtual sensors; simulator on a trusted private LAN. The Pi dashboard should remain bound to loopback, reachable via an authorized SSH tunnel.

Measure actual camera and perception FPS, frame age, CPU/RSS and Stop/re-enable behavior. Confirm that **real camera -> OpenCV -> decision -> virtual Uno -> UDP -> articulated PyBullet** is functioning; synthetic tests do not establish this. No camera recordings are required.

Physical movement remains gated by docs/HARDWARE_VERIFICATION.md and hardware/Power/TEST_PLAN.md: inspect/replace damaged PCA9685, qualify servo power/fusing/disconnect/OE, local Uno watchdog/sensing, mechanical calibration and supported-body checks before ever powering a servo.

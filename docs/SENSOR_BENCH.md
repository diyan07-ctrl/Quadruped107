# Sensor-only bench session — 12 November 2026

This is a procedure for a separately authorized hardware session. No upload or physical sensor connection was performed by this release. Physical ARM remains inhibited; sensor records cannot authorize it. Read the [release report](SENSOR_COMMISSIONING_RELEASE.md) and [electrical gates](HARDWARE_VERIFICATION.md) first.

1. Disconnect the PCA9685, every servo signal and supply, battery motor supply, D12 calibration output, unverified HC-SR04 and voltage circuits. Do not connect or power the suspected damaged PCA. Photograph the isolated bench. USB logic power is the only proposed Uno power source.
2. Record the actual URM37 PCB revision, labels, documented supply and logic levels, jumper/EEPROM mode, output polarity and reference manual. Profile 1 is only for verified V5 low-pulse PWM trigger mode. A generic product photograph is insufficient. Other modes remain unsupported.
3. Verify each touch board's supply, output topology, polarity and bias requirements. An inactive digital input cannot prove that a board exists. Leave the compile-time mask at zero until connections and electrical compatibility are verified. Configure exactly 3, 4 or 5 contiguous inputs; mixed polarity is supported by the enabled-bit active-low mask.
4. Review allocated interfaces against the actual pinout:

| Interface | Allocated signal |
| --- | --- |
| URM37 COMP/TRIG | Uno D4 |
| URM37 ECHO/PWM | Uno D2 |
| Touch 1 / 2 / 3 / 4 / 5 | Uno D6 / D7 / D9 / D10 / D11 |
| Uno host link | USB serial, 115200 8N1 |
| USB camera | Pi USB |
| Verified SSD1306 SDA / SCL | Pi physical pins 3 / 5 |
| Verified OLED supply / ground | Pin 1 (3.3 V, only if supported) / pin 6 |

These are assignments, not proof of voltage tolerance, actual board pinout or safe pull-ups. Verify supply and common ground before wiring. OLED must have Pi-compatible 3.3 V I2C levels; an address ACK alone does not identify its controller.

5. Build the sensor-only target from the reviewed checkout. Example for verified V5 and three active-high touches:

```sh
git status --short
git rev-parse HEAD
arduino-cli version
arduino-cli compile --profile uno --export-binaries --build-property "compiler.cpp.extra_flags=-DURM37_PROFILE=1 -DTOUCH_ENABLED_MASK=7 -DTOUCH_ACTIVE_LOW_MASK=0" firmware/uno/sensor_only
find firmware/uno/sensor_only/build -type f -name '*.hex' -exec sha256sum {} \;
```

Use masks 7/15/31 for three/four/five boards, with active-low bits only where measured. Default profile 0 and mask 0 intentionally provide no valid physical readings. Record commit, clean/dirty status, exact flags, CLI/core/library versions, complete build log and HEX hash. Never substitute production or calibration binaries.

6. Before uploading, independently review the isolated wiring, USB device identity, binary hash and build flags. **Upload requires separate physical-session authorization.** This release deliberately supplies no automatic upload script. Do not upload to a powered actuator system. After authorized upload, use one serial owner; close the terminal before starting the Pi application.
7. With a terminal or reviewed serial test client, verify `HELLO` → `READY Quadruped107 1`; `CAPS 1` → `caps_sensor2_t3`, `_t4`, `_t5` or `_t0` matching the build. `ARM 2`, `MOVE 3 stand`, and `SERVO 4 0 300` must return `sensor_only`; `STOP 5` must acknowledge. No servo/PWM pins may be connected.
8. Request `TELEM 6 5 2`. Send a unique `POLL 0 <uint16 token>` every 200 ms and `PING` at least every 300 ms; token wraps modulo 65536. A missing heartbeat stops the stream after 1500 ms. Inspect TEL2 sequence, uptime, flags, acquisition ages and faults. A terminal without periodic PING is intentionally unsuitable for sustained collection.
9. Measure known distances (for example 0.2, 0.5 and 1.0 m) against a ruler, including angled/soft targets and minimum/maximum range. Scope trigger/echo and record actual accuracy and latency. Firmware converts the documented profile at 5 us/mm, accepts 20–4000 mm, waits at least 200 ms between triggers and times out at 60 ms. These are implemented policies, not measured module calibration. Missing/invalid echo must be invalid, never free space.
10. Test touch startup held, stable release, bounce, simultaneous contacts, hold over two seconds, stuck fault and release recovery. Firmware debounce is 20 ms; Pi debounce is separately 30 ms. Confirm polarity and absent-board bias electrically. HELLO/reconnect must discard old interaction events. Do not use a software-valid input as proof of board presence.
11. On the Pi, preserve the original worktree and services. Use a clean isolated candidate checkout and its selected environment. Set the verified stable device path and matching touch count:

```sh
PY=.venv-pi-virtual/bin/python
UNO=/dev/serial/by-id/REPLACE_WITH_VERIFIED_DEVICE
$PY tools/pi-preflight.py --sensor-port "$UNO" --camera-device /dev/video0 --output build/bench-preflight.json
$PY -m quadruped.main --camera-backend usb --camera-device /dev/video0 --actuator-backend virtual --sensor-source physical_uno --sensor-port "$UNO" --sensor-config deploy/sensors.three.json --oled mock --host 127.0.0.1
```

Use `--simulator VERIFIED_LAPTOP_PRIVATE_IP` only when a separately started PyBullet receiver is desired. Its telemetry cannot replace physical readings. Forward/reverse/turn and autonomous modes remain inhibited because real swept clearance is unavailable. Valid physical readings permit only explicitly enabled guarded manual virtual poses/joints; they never grant even virtual ARM automatically. Default startup is disarmed.
12. Check dashboard source, measured metres, validity/age, touch faults/events, camera status, virtual output authorization, physical-actuation-disabled flag, serial capabilities and OLED status. For OLED hardware, first verify controller, supply, pull-ups, bus and address; then replace `--oled mock` with `--oled ssd1306 --oled-bus 1 --oled-address 0x3c` (or verified 0x3d). Missing bus/address/transfer faults must stay optional; no more than 5 Hz updates.
13. Under separately enabled virtual manual output, disconnect/reconnect sensor USB, remove echo, hold a safety touch and interrupt telemetry. Acquisition freshness remains 300 ms including conservative transport allowance. Observe virtual STOP, output mask zero and disarmed recovery. Releasing a fault must require explicit re-enable. Test dashboard STOP while the optional display is absent/failing. Record command latency; software tests do not prove electrical stop time.
14. Confirm no physical ARM is possible on the sensor link or production firmware. Confirm no PCA/servo supply or signal was connected. Capture firmware identity, source/binary hashes, raw TEL2, Pi state, timestamps, distance ruler readings, touch/display observations and failures without relabeling them as passes.
15. Select STOP, verify virtual mask zero, terminate the foreground application, close serial owners and leave the bench disarmed. Restore no services or network settings unless the operator separately authorizes a change. Preserve logs and operator changes.

Future single-servo commissioning stays separate. The [disabled calibration target and prerequisites](SOFTWARE_READINESS.md) retain unknown joint profiles, D12 disconnected, single-channel/rate/session/lease limits, measured neutral/endpoints requirements and independent power-disconnect review. No calibration enable, automatic sweep or physical locomotion is authorized here.

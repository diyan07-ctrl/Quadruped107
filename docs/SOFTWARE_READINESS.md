# Software readiness before hardware commissioning

Status: qualification in progress; physical verification PENDING. PR [#7](https://github.com/diyan07-ctrl/Quadruped107/pull/7) remains unmerged. No hardware upload, PWM output, physical ARM, wiring change, Pi deployment or servo power operation is part of this qualification.

## Baseline and source audit

PR #6 merge `e5ac1be32c1b8211924b830fb4a148db5c568792` has parents `ffd2294` (Phase 3) and `cb05e92` (Phase 4 reporting); it contains runtime `ff38276`, Phase 2 `69ad36f` and Phase 1 `a15c397`. Fetched `main` at `f625250` lacks this merge. The clean new branch starts at `e5ac1be`, targets `phase3/vision-recording-readiness`, and preserves all prior evidence. Initial code commit: `6c58563`.

Confirmed missing in that baseline: physical acquisition in Uno firmware; capability/rate negotiation; acquisition-age-qualified telemetry; physical SensorManager provider; optional OLED backend; MCU single-servo commissioning policy/test target. Existing calibration validation in `quadruped/calibration.py`, OpenCV detection/identity, gait data, controller leases, STOP scheduling, UDP/PyBullet providers and dashboard were retained.

The baseline passes 179 tests (0 failures, 0 skips) and all 14 checks in `tools/phase4-local-checks.py`. The old `.venv` points to a missing Python installation; local checks use preserved `build/phase4-toolchain/python311/python.exe` (3.11.18). CI separately tests 3.13. Historical Phase 4 results remain unchanged.

## Implemented modules and deliberate restrictions

| Source | Implementation / boundary |
| --- | --- |
| `firmware/uno/sensor_only/` | Standalone fixed-buffer Uno target. No Servo, Wire, PCA or gait imports. All actuator verbs rejected, STOP always accepted. No sensor output initialized unless configured. |
| `sensor_only/acquisition.h` | Testable time/edge state machine; 200 ms minimum ping interval, 60 ms timeout, wrap-safe pulse timestamps; independent touch debounce/stuck handling. |
| `sensor_only/config.h` | Profile 0 unconfigured; profile 1 confirmed V5 PWM-trigger interface only. Three, four or five contiguous touch inputs and active-low mask. No guessed auto-detection. |
| `quadruped/telemetry.py`, `serial_link.py` | Legacy TEL1 diagnostics and negotiated TEL2 acquisition-age bounds, sequence/uptime wrap, dropped records, poll expiry, reconnect clearing and separate acknowledgment routing. Sensor-link commands can never ARM. |
| `quadruped/physical_sensors.py`, `sensors.py`, `main.py` | One authoritative manager, explicitly selected source, metres, age propagation, absent inputs invalid, actuator selection independent. Physical source is monitoring only; no HC-SR04/sweep data is fabricated. |
| `quadruped/display.py` | Pi-owned mock / explicit SSD1306 backend. Dedicated worker, 5 Hz maximum, bounded mock history, two-second retry, fault status; blocked I2C never runs on the STOP thread. |
| `firmware/uno/libraries/QuadrupedSafety/` | Unqualified joint templates, neutral/direction/bounds/rate validation and bounded one-channel session policy. Units are explicit and separate between PCA ticks and direct microseconds. |
| `firmware/uno/direct_calibration/` | Separate disabled-by-default D12 signal target; unknown profiles reject all enables; review gate, single selected logical joint, 5 s session / 500 ms lease, at most 10 us per accepted step and ±25 us around measured neutral. Compile/mock only. |
| `firmware/uno/sketch/` | Physical ARM unconditionally rejected pending commissioning; commanded OE off, driver-missing / fault-latched / STOP-feedback-unknown status, AVR watchdog reset preparation. `motion.h` unchanged byte for byte. |
| `quadruped/vision.py` | Bounded HSV rejection and contour/clipping diagnostics. No threshold relaxation, replacement detector or motion-policy change. Frozen real yellow images retain their historical rejection. |
| existing Flask web files | Sensor identity, measured URM37 and age, validity, touch states/events, faults, serial/rate/last acquisition, OLED, inhibits and physical-actuation-disabled status. Existing STOP/browser protection retained. |

Physical monitoring restricts mode choices to manual/idle/sensor_test. Fresh configured URM37 and touch observations permit explicitly enabled manual virtual poses or virtual single-joint commands under the existing safety guard. Invalid/stale readings or safety contacts stop those outputs. URM37 alone cannot establish whole-body or swept clearance: forward/reverse/turn travel remains inhibited because those observations are absent, and autonomous modes are unavailable. Virtual PyBullet remains the only permitted actuator backend for this mode; its bridge can display joint state, but its sensor batches cannot overwrite the selected physical manager. Receiving valid telemetry never automatically enables even virtual outputs. Original virtual-source autonomy remains available separately.

Digital touch boards have no presence-identification wire: an unplugged/floating configured input cannot be distinguished reliably from an inactive board by software alone. Only explicitly verified connections may be configured; absence of that verification must keep the mask at zero. Firmware validity means configured, sampled, debounced and not stuck, **not independently proven electrical presence**. Missing URM37 echoes invalidate range. No physical observation ever sets `controlQualified=true`.

HC-SR04 remains optional and unimplemented; no automatic fallback is enabled. Other URM37 revisions, UART/RS232 modes, pack sensing, servo rail sensing and electrical STOP feedback remain unavailable. This is explicit in status/invalid observations rather than guessed clearance or voltage.

## Build and mock verification

```sh
python -m pip install -r software/pi/requirements-dev.txt -r simulation/requirements.txt -e software/pi
python -m unittest discover -s tests -v
python tools/test-firmware.py
arduino-cli compile --profile uno firmware/uno/sensor_only
arduino-cli compile --profile uno --build-property "compiler.cpp.extra_flags=-DURM37_PROFILE=1 -DTOUCH_ENABLED_MASK=31" firmware/uno/sensor_only
arduino-cli compile --profile uno firmware/uno/direct_calibration
arduino-cli compile --profile uno firmware/uno/sketch
python tools/generate-virtual-firmware.py
arduino-cli compile --profile uno build/virtual/sketch
```

Native tests use g++ on CI; Windows can supply `--zig build/phase5/native-tools/ziglang/zig.exe` (tested 0.13.0). Eight executables exercise the real sketch parsers and fake pins/time/interrupts, plus acquisition/session policy. Actual mock-sketch wire records are ingested by the real Pi TelemetryStream and SensorManager. These mocks do not emulate AVR electrical timings, bootloader behavior or stack high-water. No test runner opens a serial device or uploads firmware.

`python tools/qualify-firmware.py --arduino-cli <executable> [--zig <executable>]` captures exact commands, source commit, dirty paths, logs and six compile configurations under ignored `build/phase5/firmware-evidence`. It returns failure if any check fails.

Arduino AVR core 1.8.8 and existing Adafruit dependencies remain pinned in sketch profiles. Shared local library paths use Arduino CLI profile `dir:` entries; use sketch directories, not `.ino` filenames. Direct calibration pins Servo 1.3.0. OLED is optional: install `software/pi/requirements-oled.txt` only when using its hardware backend. No OLED framebuffer exists on the Uno.

Final resource values, test counts, CI results and exact source commits are recorded in the evidence matrix linked here after qualification. Global SRAM headroom is a compile result; measured worst-case stack margin is still PENDING.

## First sensor-only hardware session (not performed)

1. Preserve the Pi worktree and deployment first; do not overwrite existing changes. Keep every servo and PCA signal/power connection isolated from this standalone USB-powered sensor Uno. Do not use the suspected damaged PCA. No battery or power-distribution changes are needed.
2. Photograph and identify the URM37 PCB revision, pin names, jumper/EEPROM mode, signal polarity and logic levels against that exact revision's documentation. Profile 1 supports only verified V5 PWM trigger mode. D4 goes to COMP/TRIG and D2 to ECHO/PWM only if the module's actual pinout/mode confirms them. Do not connect RS232 TX/RX to GPIO. The [DFRobot V5 reference](https://wiki.dfrobot.com/sen0001/docs/21980) defines low-pulse width at 50 us/cm and invalid width ≥50,000 us. Firmware narrows acceptance to 20–4,000 mm. This conversion is a documented profile, not a measured calibration of the present module.
3. Compile the sensor-only profile with `URM37_PROFILE=1` only after that check. Keep touch mask zero until its boards are verified. Uploading sensor-only firmware is a separate next-session action; never upload production or calibration movement firmware during this procedure. Capture the exact compiled SHA/configuration and verify `CAPS 1` reports `caps_sensor2_t0`. `ARM 2`, `MOVE 3 stand` and `SERVO 4 0 300` must all return `sensor_only`; `STOP 5` must acknowledge without any signal output.
4. At 115200 8N1 send HELLO, CAPS, `TELEM 6 5 2`, then a unique `POLL 0 <uint16-token>` every 200 ms and PING at least every 300 ms. A serial terminal that omits heartbeat intentionally triggers the 1,500 ms stream watchdog. Check invalid/no-echo → valid recovery, measured known distances (e.g. 0.2/0.5/1.0 m), repeated samples, pulse width on a scope/logic analyzer, acquisition ages, timeout, physical unplug/reconnect, startup warm-up and clock/session reset. Record error against a ruler before calling the module calibrated. No echo must remain invalid, never free space.
5. Identify 3–5 touch boards and confirm supply/output levels, push-pull/open-drain behavior, active polarity and required external bias against their datasheets. Configure contiguous D6/D7/D9/D10/D11 mask 7, 15 or 31 and active-low bits as appropriate. Configure the Pi's `touch_count` to match. Test boot-held contact (invalid until debounced release), 20 ms press/release debounce, simultaneous contacts, >2 s stuck contact and release recovery. Unplugged inputs require an electrical presence/bias assessment; software alone cannot certify a missing digital board. HELLO must clear interval history and produce no new boot-held interaction event. Record electrical noise/latency before relying on taps.
6. Run on the Pi with its existing environment, explicit sensor port and virtual actuators only: `python -m quadruped.main --actuator-backend virtual --sensor-source physical_uno --sensor-port /dev/serial/by-id/<verified-device>`. A separately selected `--simulator-host` can show PyBullet joint state; it cannot supply missing physical clearance. Confirm dashboard source/age/invalid flags, no ARM bytes on sensor USB, telemetry expiry at 300 ms, STOP throughout disconnects, and no automatic recovery into motion. A test-only provider must be explicitly selected and never used as missing-hardware fallback.
7. Identify the OLED controller, address and voltage/pull-ups with its actual datasheet before connection. Confirm Pi-compatible 3.3 V I2C signalling; an SSD1306-compatible address ACK alone does not prove controller identity. Reference pins: Pi physical 3 SDA / 5 SCL; supply only as verified for the module. Enable I2C using the existing system procedure, then use `--oled ssd1306 --oled-bus 1 --oled-address 0x3c` (or verified 0x3d). Check startup/idle/target/search/distance/obstacle/touch/expressions/STOP/fault screens, 5 Hz maximum, removal/reconnection, wrong-address fault and STOP while display I/O is failing. Use `--oled mock` before hardware. Do not put a framebuffer on Uno.

## Separate future servo-calibration prerequisites

Do not deploy the direct calibration target during sensor qualification. It currently has no qualified joint entries and cannot enable a signal, even with the review macro set. Future use requires a new reviewed build with one known supported servo connected to D12, individually documented microsecond neutral/endpoints/direction/rate, reviewed external current-limited power and common-ground arrangement, mechanical support and safe access to a real power disconnect. Check the actual Servo library output pulse range and oscilloscope behavior before attaching a servo. Never infer mechanical limits from `motion.h` or the library's clamp values.

Only after that review may a future session use the explicit `ENABLE <logical-channel> POWER_SUPPORT_REVIEWED` gate, heartbeat and bounded STEP requests. Exactly one physical signal is supported; changing channel requires STOP first. STOP detaches the signal; it is **not an independently verified electrical disconnect**. Session/lease expiration latches rejection until MCU reset. Reconnect/HELLO disables output; no sweep or automatic re-enable exists.

Production remains inhibited even if templates are filled: electrical OE feedback, independent STOP hardware/status, measured supported reset behavior, calibrated gait bounds/rate integration and physical stopping/power qualification must be designed and reviewed before enabling its ARM path. AVR watchdog initialization and fake reset tests do not prove behavior of the real Uno bootloader or servo power electronics. No safe standing or locomotion is claimed.

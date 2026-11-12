# Phase 6 — two real touch inputs and first sensor commissioning

**SENSOR COMMISSIONING PARTIAL. Physical actuators disabled.**

Baseline: PR #8 head `b18e897e13baefc452606b37a1804ca9e672d2a5`. Work is isolated on `phase6/two-touch-commissioning`; prior evidence, CAD, calibration tables and authorship are preserved. Original operator work was not reset, stashed or restored; the connected audit below records an unexplained new deletion rather than claiming an unchanged checkout. This report separates implemented/mock-tested software from actual hardware observations. Electrical identification has not passed. No serial port was opened and no firmware was uploaded during the blocked preflight.

Qualified implementation: `07acf1f7cda9678bcf60c991419157b04e2dea65`; [draft PR #9](https://github.com/diyan07-ctrl/Quadruped107/pull/9). **PASS:** 248 Python tests, all 14 established checks, 16 native mocks, 15 AVR variants and push/PR CI including the new Python 3.13 tests. [Frozen logs, flags, resources, hashes and provenance](../evidence/phase6/two-touch-commissioning/README.md). This is software evidence only.

Latest connected preflight (12 November 2026): SSH now works as `diyan07@192.168.1.42`. [Superseding connected-Pi evidence and results](../evidence/phase6/connected-preflight-2026-11-12/README.md) records the actual dirty operator checkout, isolated candidate/environment, USB metadata and Pi tests/builds. The operator attests electrical checks and actuator isolation, but explicitly reports both TTP223B polarity/momentary settings unknown and no meter or pad-identification method available. Normal firmware selection and serial/upload gates remain blocked. No Uno port has been opened or firmware uploaded. The earlier frozen timeout reports remain unchanged.

## A–P commissioning record

| Item | Status | Result / evidence boundary |
| --- | --- | --- |
| A. GitHub / Pi state | PASS audit / FAIL preservation comparison | Draft PR #9 targets PR #8 release branch. Pi original HEAD `a15c397` has staged operator work, preserved in place. A new unstaged deletion of `hardware/Power/power_budget.py` appeared during the session; actor/cause unestablished. HEAD and staged patch hash unchanged. No restoration attempted; see connected evidence |
| B. Firmware adaptation | PASS, source/mock scope | Mask 3 is supported; CAPS reports `caps_sensor2_t2`; only D6/D7 enabled. Existing 0/7/15/31 profiles remain. No Servo/Wire/PCA/gait imports in sensor-only target |
| C. Semantic mapping | PASS, mock scope | Explicit `back_front_bottom_v1`: bit 0/D6 → `touch_back` / BACK_TOUCH / REAR_LOWER; bit 1/D7 → `touch_front_bottom` / FRONT_BOTTOM_TOUCH / FRONT_LOWER. Virtual legacy ordering is unchanged |
| D. Regression | See frozen evidence | Full Python/local/DOM checks and new recorder/touch tests have reproducible logs; native programs consume the real sketch with fake UART/pins/time. Mock observations are not physical readings |
| E. AVR / binary identity | PASS, compile scope | Two-touch active-high, active-low, both mixed polarities, and unconfigured URM profile compiled alongside the existing matrix. Exact commands, source, sizes and HEX SHA-256 are in the evidence matrix |
| F. Electrical preflight | BLOCKED | Operator attests supply/wiring/isolation checks, but actual touch polarity and momentary/toggle settings remain explicitly unknown. Model name alone does not identify board options. No automatic polarity fallback |
| G. Actual serial device | PASS metadata / BLOCKED board association | CH340 `1a86:7523`, `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0`, USB path `0:1.1:1.0`, no unique serial. Confirm association with intended Uno before upload. No port opened |
| H. Upload | BLOCKED | Not authorized or executed. No upload log or flash verification exists |
| I. Real URM37 measurements | BLOCKED | No physical ruler distances or range records collected |
| J. Real D6/D7 observations | BLOCKED | No measured polarity or genuine physical touch records collected |
| K. Actual Pi SensorManager integration | BLOCKED | Native/replay → actual Python provider tests pass independently; live hardware path remains untested |
| L. Dashboard / virtual gestures | PASS in mocks / BLOCKED live | Exact count, mapping, full capability, semantic request and calibration-pending status shown. Virtual controller dispatch tested; no measured sit/bow pose is claimed |
| M. Fault / STOP / reconnect | PASS in mocks / BLOCKED physical | Invalid/stale packets, no echo, simultaneous touch, stuck/boot-held inputs, STOP, takeover and epochs fail closed; recovery remains disarmed |
| N. Remaining blockers | BLOCKED | Touch output/mode evidence, selected binary, intended-board association, separate concrete upload authorization and actual measurement/fault matrix. Original-checkout preservation comparison failed on an unexplained deletion, left untouched |
| O. Source / firmware revisions | See evidence | Qualified source revision, dirty paths, flags, tool versions and each HEX hash are retained; never infer flashed identity from a compile |
| P. Next safe hardware phase | BLOCKED at touch-configuration gate | Identify actual module option settings/output behavior, review selected binary/device and obtain separate upload approval. Pi software environment and uploader are ready in an isolated session. No physical servo phase authorized |

## Software behavior and authority

Use `deploy/sensors.two.json` with `--sensor-source physical_uno --actuator-backend virtual`. Count 2 requires the explicit physical profile; it never means legacy head/back and never fabricates a third sensor. The profile is rejected for a virtual/test sensor manager. Missing/unknown capability, wrong count, absent configured data, out-of-profile bits and corrupted records invalidate sensing. A rejected packet cannot resurrect the preceding acquisition. Epoch/profile/count changes clear debounce/event state; boot-held contact creates no activation event.

The existing MotionController remains the sole executor. After explicit enable while both inputs are released, the operator may select **Touch gestures (virtual placeholders)** (`interaction`). Each qualified press requests exactly one bounded existing virtual `stand` routine, labeled REAR_LOWER or FRONT_LOWER and **physical calibration PENDING**. That routine is a neutral placeholder: it does not demonstrate a lowered rear, bowed front, calibrated sitting or physical clearance. No gait/calibration array was edited.

Outside that explicitly selected virtual-only placeholder mode, front-bottom contact is protective and stops manual output. This is an explicit scope distinction, not a global harmless-contact reclassification. Left/right/body safety contacts always stop; simultaneous D6/D7 stops rather than selecting a winner. Invalid/stale range or touch, no echo, low front clearance, communication failure, STOP, mode takeover and the existing two-second action bound cancel output. The placeholder mode accepts only `stand`, never travel or a generic personality API request. The existing front-distance caution/freshness/lease limits are unchanged. Release/reconnect never arms. Physical exploration, tracking travel, reverse and turns stay blocked; PyBullet cannot overwrite physical sensor evidence.

There is no OLED/LCD/HC-SR04/PCA or servo supply in this phase. Launch with `--oled off`; do not install display dependencies or scan I2C. Touch input configuration is not proof of electrical board presence: an unplugged biased/floating digital input may resemble an untouched board.

## Electrical gate — operator facts required before serial access

Record the actual specimen markings/documentation and measured conditions:

- URM37 manufacturer/model/PCB revision; documented supported supply and measured actual supply; confirmed V5 low-pulse PWM-trigger mode if selecting profile 1; D4 COMP/TRIG, D2 ECHO/PWM, logic levels and common ground. Other UART/RS232/revision modes remain unsupported.
- Each touch module's actual model, supply and digital output levels, active polarity, push-pull/open-drain topology and required bias. D6 is BACK; D7 is FRONT_BOTTOM. A generic photograph or observed GPIO level is insufficient identification/presence evidence.
- Uno power arrangement (proposed Pi USB logic power only), sensor ground, and operator confirmation that PCA, all servo signals/supplies, D12 calibration output, motor supplies and unverified circuits are disconnected.
- Current Pi SSH address/name and confirmation of the intended Uno USB identity. Then execute the read-only audit first, preserving original status/diff hashes, services/processes, device ownership, Python environment and free disk.

Do not change wiring or power remotely. Do not open USB serial, toggle DTR/reset the Uno, probe sensor pins or upload to compensate for missing electrical facts.

## Exact build and upload handoff

Builds do not access physical devices:

```sh
python -m unittest discover -s tests -v
python tools/phase4-local-checks.py --output build/phase6/software
python tools/qualify-firmware.py --arduino-cli /verified/path/arduino-cli --output build/phase6/firmware
arduino-cli compile --profile uno --build-path build/phase6/reviewed-two --build-property "compiler.cpp.extra_flags=-DURM37_PROFILE=1 -DTOUCH_ENABLED_MASK=3 -DTOUCH_ACTIVE_LOW_MASK=0" firmware/uno/sensor_only
sha256sum build/phase6/reviewed-two/sensor_only.ino.hex
```

Only choose `URM37_PROFILE=1` after actual V5/mode/electrical verification. Polarity mask: 0 = both active-high; 3 = both active-low; 1 = D6 low/D7 high; 2 = D6 high/D7 low. These are conditional build alternatives, not assertions about connected boards. Profile 0 leaves ultrasonic acquisition unconfigured and invalid.

Before a hardware write, review the clean source, exact flags, actual device identity, selected HEX hash, electrical facts and isolation. Ask the operator to authorize that concrete upload separately. Only then may the reviewed sensor-only HEX be copied into a new isolated Pi candidate directory and uploaded:

```sh
# FUTURE AUTHORIZED ACTION ONLY. Replace with verified device and exact reviewed HEX.
arduino-cli upload --verify --fqbn arduino:avr:uno --port /dev/serial/by-id/VERIFIED_UNO --input-file build/phase6/reviewed-two/sensor_only.ino.hex
```

Retain the actual upload/verification log. Never substitute production or D12 calibration firmware. Compilation alone does not identify what is flashed.

## Raw serial acquisition before Flask

Use a clean isolated checkout, preserve the original Pi checkout and use the separately prepared isolated environment. The old environment has pre-existing unrelated `pip check` failures and was left untouched. Check `fuser`/permissions and ensure no terminal/dashboard owns the Uno. Set `PYTHONPATH` to the candidate's `software/pi` when reusing an existing environment, so an old editable installation cannot override candidate imports.

The recorder below does **not upload**. Its explicit flags are operator attestations, not proof. Execute only after this session's electrical review and separate upload authorization/verification have passed:

```sh
SESSION=/home/diyan07/Quadruped107-phase6-session.r7D1jJ
cd "$SESSION/candidate"
PY="$SESSION/venv/bin/python"
export PYTHONPATH="$PWD/software/pi"
UNO=/dev/serial/by-id/VERIFIED_UNO
HEX=build/phase6/reviewed-two/sensor_only.ino.hex
SHA=REPLACE_WITH_REVIEWED_BINARY_SHA256
$PY tools/commission-two-sensors.py --port "$UNO" --binary "$HEX" --firmware-sha256 "$SHA" --electrical-verified --upload-verified --label untouched --seconds 10 --output build/phase6/real/untouched
```

This is one USB owner at 115200 8N1 with bounded reads/writes. It requires exact READY and `caps_sensor2_t2` before sending intentional ARM/MOVE/SERVO rejection probes. Unknown firmware never receives ARM. It checks STOP acknowledgment, samples TEL1 diagnostics, negotiates TEL2 at 5 Hz, PINGs at least every 300 ms and polls every 200 ms. It logs actual TX/RX and feeds real TEL2 into the actual Pi TelemetryStream/PhysicalSensorProvider/SensorManager. No mock fallback or actuator backend exists. Reset/fault/corruption fails the capture; invalid measured range is recorded as invalid, never free space. STOP is sent and the port closed on exit.

Recorder PASS means only its stated transport/rejection/capture scope. It does not qualify electrical facts, distance accuracy, touch presence, physical stopping, or the overall milestone.

For ruler trials, physically measure the reference first; do not invent it from the label:

```sh
$PY tools/commission-two-sensors.py --port "$UNO" --binary "$HEX" --firmware-sha256 "$SHA" --electrical-verified --upload-verified --label ruler-20cm --reference-m 0.20 --seconds 10 --output build/phase6/real/ruler-20cm
```

Repeat with measured 0.50 m and 1.00 m and independent labels/directories. Retain counts, valid/invalid samples, reported metres, error, acquisition age, sequence, uptime, source flags and raw lines. Test no echo, stationary/moving/out-of-range targets and timeout. Do not disconnect or alter sensor wiring under power unless its verified electrical procedure permits it; otherwise power down under operator control first. Sensor loss/recovery must stay invalid/disarmed until fresh evidence and explicit re-enable.

For each touch, separately record untouched → press → release, repeated press, hold beyond two seconds, boot-held/reset and reconnect, then simultaneous activation. D6 must always identify BACK_TOUCH/REAR_LOWER; D7 must always identify FRONT_BOTTOM_TOUCH/FRONT_LOWER. Check both firmware and Pi debounce/event timestamps; held input must not repeatedly trigger. Board absence/bias/noise still require physical assessment.

## Actual application integration after raw tests pass

```sh
$PY -m quadruped.main --camera-backend usb --camera-device /dev/video0 --actuator-backend virtual --sensor-source physical_uno --sensor-port "$UNO" --sensor-config deploy/sensors.two.json --oled off --host 127.0.0.1
```

Confirm dashboard count 2, mapping, `caps_sensor2_t2`, range/touch validity/age/fault, semantic events, virtual gesture status, physical actuation disabled and STOP. Only after valid raw readings and released contacts may the operator explicitly enable virtual output and select the placeholder mode. For approved PyBullet observation add `--simulator VERIFIED_LAPTOP_PRIVATE_IP`; its sensor callback remains disconnected from the physical manager.

Test each touch request, simultaneous-contact STOP, no echo/stale/USB loss/reset, manual takeover and browser STOP. Observe virtual output mask zero and disarmed recovery; release/reconnect must not automatically enable. Capture real serial and Pi state, and measured virtual joint output if a receiver is used. End with STOP, terminate only candidate-owned processes and preserve evidence. Never reset/clean/stash/rebase or modify operator work, services, network, SSH, firewall or Telegram.

## Scope of the eventual milestone

Use **REAL SENSOR INTEGRATION VERIFIED — PHYSICAL ACTUATORS DISABLED** only after actual electrical/USB/upload/range/touch/Pi/fault observations pass. Until then use **SENSOR COMMISSIONING PARTIAL**. Prior yellow detection failure, HTTP 409 endurance admission, active GUI endurance and real pursuit remain separate unresolved qualifications; this phase does not rerun them for a badge.

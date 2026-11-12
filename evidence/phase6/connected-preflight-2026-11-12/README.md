# Connected Pi preflight — 12 November 2026

**SENSOR COMMISSIONING PARTIAL — physical actuators disabled.** No physical Uno serial port was opened, no DTR/reset requested, and no firmware uploaded. No GPIO/I2C/actuator access occurred. This record supersedes only the earlier connectivity blocker; it preserves previous failed and blocked evidence.

Candidate: `phase6/two-touch-commissioning`, software/test revision `7f4768e` (full identity in final Windows/Pi logs), [draft PR #9](https://github.com/diyan07-ctrl/Quadruped107/pull/9), based on PR #8 release head `b18e897e13baefc452606b37a1804ca9e672d2a5`. Runtime/firmware source is unchanged since `07acf1f`; subsequent changes improve test measurement/synchronization and record evidence.

| Result | Status | Evidence and boundary |
| --- | --- | --- |
| SSH and read-only Pi inventory | PASS | [Connected audit](pi-audit-connected.log), [final metadata](pi-final-readonly.log). Pi aarch64, Python 3.13.5, 12 GB root disk free at final audit. Services/processes and device ownership inventoried without changes |
| Original operator checkout | PASS identity / FAIL unchanged comparison | `/home/diyan07/Quadruped107`, branch `phase1/software-vision-digital-twin`, HEAD `a15c39775a4063b396c3cd844f66324cd250021c`. Existing staged work retained. [Before/after snapshots](pi/qualified) and final log show a new unstaged deletion `hardware/Power/power_budget.py`. Cause/actor unestablished; no restoration attempted. HEAD and staged patch hash remain unchanged. This failed comparison is not represented as preservation PASS |
| Original Python environment | FAIL, pre-existing | [pip check](pi/pip-check.log) reports missing unrelated apt-listchanges/types package dependencies. No packages changed in that environment |
| Isolated candidate / environment | PASS | `/home/diyan07/Quadruped107-phase6-session.r7D1jJ/candidate`, clean detached candidate, separate `venv`; [installation procedure](pi-software-env.sh), [pinned requirements plus resolved freeze](pi/isolated-freeze.txt). New pip check passes. Python 3.13.5, OpenCV 4.11.0, NumPy 2.5.4, Flask 3.1.2, pyserial 3.5. No OLED packages or I2C probing |
| Pi software regressions | PASS, mock/replay scope | Six selected modules, **84 tests**: telemetry 6, readiness 32, two-touch 22, recorder 4, runtime 17, preflight 3. [Final execution](pi-final-tests.log), [per-module logs](pi/final-tests). No physical sensor data |
| Full Windows regression / established checks | PASS, software scope | **248 tests and 14/14 checks**, [matrix](windows-final/reports/local-checks.json), [suite log](windows-final/reports/REG-PY.log). Includes controller, dashboard DOM and headless PyBullet integration; separate native qualification below supplies real-sketch replay |
| Qualified code CI | PASS | [Push](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/43229178884) and [PR](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/43229193386), exact revision `7f4768e97fd55d0f897fbe2e8b588b7b26f6a3d7`; Python/full package, Python 3.13 and Uno jobs all passed. Final documentation/evidence commit is recorded by Git and its own subsequent CI |
| Native mocks / AVR matrix | PASS, software scope | **16 native executables, 15 AVR variants**; [native log](firmware-final/native.log), [matrix](firmware-final/matrix.json). Physical calibration target remains disabled, production ARM inhibited |
| Pi AVR cross-build | PASS, compile only | Four two-touch polarity configurations compiled on actual Pi; [commands and SHA-256](pi-qualify-updated.log), [size logs](pi/qualified). HEX hashes exactly match Windows outputs. No selected hardware polarity or flashed identity |
| Isolated uploader preparation | PASS, software only | [Log](pi-uploader-prepare.log), [script](pi-uploader-prepare.sh). Official Arduino CLI 1.5.1 ARM64 archive verified against official release SHA-256 `1e69e077479f300614d4551334e0a33f08ee40b04315d83b8e7e0e94f0d0ee62`; AVR core 1.8.8 installed in session-only directories with post-install hooks skipped. Upload help inspected; no upload/discovery/monitor executed |
| USB endpoint metadata | PASS / BLOCKED intended-board association | `/dev/ttyUSB0`, CH340/ch341 VID `1a86`, PID `7523`; `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0`. USB location path below. Generic ID has no unique serial; operator must confirm intended Uno association. No owner PID observed at audit time; this does not reserve the port |
| Electrical/profile selection | BLOCKED | Operator reports URM37 V5 D4/D2/5V/GND, two TTP223B boards D6/D7, Uno USB and attests electrical/isolation checks. Later explicitly reports touch polarity/momentary mode unknown and neither meter nor board/pad identification available. Do not infer common TTP223 defaults from the model label |
| Firmware upload / negotiation / physical STOP | BLOCKED | No selected polarity/mode, no separate concrete upload authorization, no flash/serial observations |
| Real URM37 ruler measurements / D6/D7 touches | BLOCKED | No raw physical records, measured errors or touch observations. Unit tests/replay are not substitutes |
| Pi dashboard and virtual gestures with actual sensors | BLOCKED | Software mocks pass; real session must first pass raw electrical/upload/telemetry tests. Existing `stand` placeholders are labeled REAR_LOWER/FRONT_LOWER requests with physical calibration pending, not verified sit/bow poses |
| Physical servos / walking / physical autonomy | NOT APPLICABLE | Outside authorized non-actuating session; actuator paths remain inhibited |
| Yellow target / new 905 s admission / visible GUI / pursuit | NOT TESTED in this follow-up | Historical yellow 0/9 and HTTP 409 before active endurance remain failures; visible GUI and real pursuit remain unqualified |

## Retained failed attempts and corrections

The first Pi mock-display regression failed after 2.3895 seconds; [original failure](pi/test_readiness.py.log) is retained. Its timer included cold Flask/test-client setup. A separate [timing observation](pi-stop-timing.log) measured the STOP request at 0.006184 seconds on that attempt; it does not establish the cause of the earlier delay. Commit `01f0bb9` moves setup before the timer, keeps the original 0.5-second threshold, and verifies the mock display is still blocked when STOP completes. No real OLED exists in this session.

The subsequent Windows suite had 247/248 pass: [failed log](windows-release-race-failed/reports/REG-PY.log), [13/14 matrix](windows-release-race-failed/reports/local-checks.json). A replay test attempted ARM after a fixed 0.1-second release delay; the controller correctly returned HTTP 409 because it still observed a pressed contact. Commit `7f4768e` waits for an actual valid, debounced release before explicit re-enable. No production threshold or interlock changed. Final results are recorded separately.

The Pi qualification script's original-checkout comparison exited nonzero after all 84 tests and four builds passed. The only observed status delta was the unstaged deletion above. The original staged patch hash is still `aafbf94f210114bfc4d53e52f9437fdb0931e9617436ec89c3ce968f0b787357`; the whole HEAD-to-worktree patch changed to `8b63fef61ca744073766cb08f4d1beb919dbcaa05c170c3d6ff00c93c0eca32e`. Do not reset or restore operator files to make this comparison pass.

## Conditional sensor-only binaries

All use `URM37_PROFILE=1`, `TOUCH_ENABLED_MASK=3`, Uno profile, AVR core 1.8.8. Actual V5 PWM mode must still be confirmed before selection. Each uses 510 bytes global SRAM; 1538 bytes remainder is **not measured stack margin**. Mock watchdog results do not prove physical bootloader/reset safety.

| Active-low mask | D6 / D7 | Flash bytes | HEX SHA-256 |
| --- | --- | --- | --- |
| 0 | high / high | 7240 | `77b27b39734c6d08cd539a9d65ae5c15619f13f5dcfe0d92072b2e5145b18aa0` |
| 1 | low / high | 7256 | `7d49cd537b5f49247e75f30c23930bf5682eb7bbb5567de58e0e5b0872d18cfb` |
| 2 | high / low | 7272 | `3bd3a9e584aa8b282a41fe93b1c2a06ccdfe276496b0c84376594d6595cb8462` |
| 3 | low / low | 7240 | `ea54d4005e77303e6fadbaf7171f54f77c2387bf40197b21167919fb420b46c5` |

## Next session and rollback

Read-only/software commands ready now:

```sh
ssh diyan07@192.168.1.42
SESSION=/home/diyan07/Quadruped107-phase6-session.r7D1jJ
cd "$SESSION/candidate"
git status --short
git rev-parse HEAD
"$SESSION/venv/bin/python" -m pip check
ls -l /dev/serial/by-id/ /dev/serial/by-path/
fuser /dev/ttyUSB0 /dev/video0
```

Allocated device location: `/dev/serial/by-path/platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.1:1.0-port0`. Do not open it until the touch gate is cleared. Obtain actual board front/back markings/pad evidence or qualified output/mode measurements for **each** TTP223B. Do not move wiring or assume a generic module photo identifies these specimens. Unknown mode/polarity is not corrected through software guessing.

After electrical verification, intended Uno association, binary review and separate explicit upload approval, use the isolated CLI and selected exact reviewed binary as documented in [the commissioning procedure](../../../docs/PHASE6_SENSOR_COMMISSIONING.md). CLI configuration is `$SESSION/arduino-cli.yaml`, executable `$SESSION/tools/arduino-cli`, conditional HEX files `$SESSION/compiled/two-0/` through `two-3/`. Capture upload verification before using the raw recorder, then ruler and touch trials, then Flask with `deploy/sensors.two.json --oled off`. The recorder flags attest completed prerequisites; they do not grant authorization.

Rollback: STOP and terminate only candidate-owned application/recorder processes if a later authorized session starts them. Current session started no persistent robot service and flashed no firmware, so no firmware rollback is required. Leave the original checkout and its unexplained deletion untouched. Isolated environment/toolchain can remain for reproducibility; no OS configuration restoration is needed. Never restore production motion firmware as part of sensor rollback.

See `manifest.json` for file SHA-256 and `ci-final-*.json` for final code CI identity. Historical evidence is not overwritten.

# Phase 6 two-touch qualification — 12 November 2026

**SENSOR COMMISSIONING PARTIAL.** Actual hardware observations are BLOCKED. No physical USB serial port was opened, no Uno reset/DTR action was requested, no firmware was uploaded, and no GPIO/I2C/servo/PCA operation occurred. The operator reports connected sensors; that does not establish electrical compatibility.

Qualified source: `07acf1f7cda9678bcf60c991419157b04e2dea65`, baseline `b18e897e13baefc452606b37a1804ca9e672d2a5`. [Source and preservation checks](source.json), [commits](commits.txt), [manifest](manifest.json), [Phase 6 A–P report and exact bench procedure](../../../docs/PHASE6_SENSOR_COMMISSIONING.md), [draft PR #9](https://github.com/diyan07-ctrl/Quadruped107/pull/9). Evidence is separate from immutable Phase 4/5/release records.

| Check | Result | Scope and logs |
| --- | --- | --- |
| Python full suite | PASS | [248 tests, no failures/errors/skips](profile-qualified-software/reports/REG-PY.log); committed runtime source; documentation/evidence dirty paths are recorded |
| Existing local checks | PASS | [14/14](profile-qualified-software/reports/local-checks.json), including package imports/pip, model/gait/power, simulation, JavaScript/DOM, preserved repository assets and Mermaid |
| Native firmware | PASS | [16 executable mocks](profile-qualified-firmware/native.log), actual C++ sketch parsers with fake UART/pins/time. Four two-touch polarity variants replay actual mock TEL2 into the actual Pi provider and exact semantic inputs |
| AVR | PASS | [15 compile variants](profile-qualified-firmware/matrix.json), plus native/generator steps. All 2/3/4/5 profiles retained; no upload |
| Two-touch/controller/recorder regressions | PASS | Full suite includes exactly two identities, both requests, debounce/bounce/held/release/stuck, reset/reconnect/configuration epochs, wrong capabilities/bits, malformed data, simultaneous STOP, no echo/stale STOP, manual takeover, no re-arm and no physical command path |
| Dashboard DOM | PASS | [Log](profile-qualified-software/reports/REG-DOM.log): count 2, full t2 capability, D6/D7 semantic names, request status, disabled physical output and available STOP |
| Python 3.13 / CI | PASS | [PR run](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/43219326274), [push run](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/43219315676); [PR CI record](ci-profile-pr.json), [push record](ci-profile-push.json). New two-touch and raw-recorder tests also run in 3.13 |
| Sensor-only linked implementation | PASS, software scope | [Five ELF symbol audits](sensor-only-link-audit.json): no Servo, TwoWire, PCA9685/Adafruit PWM, analogWrite or tone implementation linked. Arduino core `turnOffPWM` may appear; it is not proof of a physical output measurement |
| Pi read-only audit | BLOCKED | [Original endpoint timeout](preflight/pi-audit.log), [retry](preflight/pi-retry.log), [operator-endpoint retry](preflight/pi-audit-operator-endpoint.log). Timeout occurs before authentication; hostname resolution also failed. No Pi checkout/service mutation was attempted. Bounded LAN discovery did not find the previously recorded Pi Wi-Fi MAC; the other responding client had port 22 closed |
| Electrical identification | BLOCKED | [Operator facts and remaining gates](operator-preflight.json). URM37 V5, D4/D2/5V/GND, TTP223B and Uno USB are operator-reported; actual mode/voltage/polarity/module configuration and explicit isolation still need verification |
| Actual serial-device identity | BLOCKED | No current `/dev/serial/by-id` identity or exclusive ownership observation obtained |
| Upload | BLOCKED | No authorization, selected electrical profile, actual upload log or flash verification |
| Real URM37 / D6 / D7 / Pi-to-virtual chain | BLOCKED | Zero actual range/touch samples. Ruler, press/release, loss/reconnect and live controller observations remain unexecuted |
| Physical actuation / displays | NOT APPLICABLE | No servo controller, signals/supply, battery/SMPS power, OLED/LCD or HC-SR04 belongs to this bench |

## Conditional two-touch firmware builds — none selected or uploaded

All paths, flags, source identities and resource results are in [firmware-resources.json](firmware-resources.json). Pin mask is always 3 (D6/D7). `URM37_PROFILE=1` is conditional on actual V5 TTL/PWM/electrical verification. The unconfigured build intentionally has invalid range. The local delivery archive `build/phase6/sensor-only-two-touch-NOT-UPLOADED.zip` contains only these sensor-only alternatives, never production/calibration binaries.

| Variant | Active-low mask | Flash | Global SRAM | Sensor-only HEX SHA-256 |
| --- | ---: | ---: | ---: | --- |
| Both high | 0 | 7240 | 510 | `77b27b39734c6d08cd539a9d65ae5c15619f13f5dcfe0d92072b2e5145b18aa0` |
| Both low | 3 | 7240 | 510 | `ea54d4005e77303e6fadbaf7171f54f77c2387bf40197b21167919fb420b46c5` |
| D6 low / D7 high | 1 | 7256 | 510 | `7d49cd537b5f49247e75f30c23930bf5682eb7bbb5567de58e0e5b0872d18cfb` |
| D6 high / D7 low | 2 | 7272 | 510 | `3bd3a9e584aa8b282a41fe93b1c2a06ccdfe276496b0c84376594d6595cb8462` |
| Ultrasonic unconfigured | 0 | 6106 | 483 | `044b97e99df62d01a399604a22588576c72fdd4be75d3531f06bfb2ecbb50d2b` |

Static SRAM is not measured stack margin. AVR ISR/reset/bootloader/electrical timings remain hardware tests. [Local dependency versions](profile-qualified-software/environment/ENV-DEPS.log) retain Windows Python 3.11.18/OpenCV 4.11.0/NumPy 2.4.6/PyBullet 3.2.5; CI separately uses its pinned PyBullet 3.2.7 and Python 3.13. Arduino CLI 1.5.1, AVR core 1.8.8 and Zig 0.13.0 were used locally. No new Pi environment/version is claimed because SSH did not connect.

## Failure preservation and limitations

[Initial software check](software/reports/REG-PY.log) failed one added manual-stand API test: the existing physical-source endpoint rejected non-travel virtual poses even though the controller safety policy allowed them. The admission check was corrected without allowing travel; the frozen regression passes. Earlier new-fixture attempts initially tried ARM before the virtual link connected; waiting for actual link readiness corrected the fixture. No historical HTTP 409/endurance or yellow-tracking result is reclassified.

The existing `stand` is deliberately only a bounded neutral virtual placeholder for REAR_LOWER and FRONT_LOWER requests. No actual sitting/bowing geometry, physical joint calibration, measured body clearance or physical PWM is qualified. Front-bottom contact remains protective outside the explicit virtual-only placeholder mode. Simultaneous contacts and all critical sensor faults still stop; release/reconnect never re-arms. Digital board absence cannot be proved from an inactive input.

The guarded recorder is prepared but has not been run against real serial hardware. Its missing-gate/hash/unknown-capability/corruption tests use UART doubles and explicitly label evidence TEST DOUBLE. Its PASS means only the stated transport/rejection/capture scope. Hardware qualification additionally requires electrical review, actual flash identity, ruler and touch observations, Pi/virtual integration and fault testing.

Manufacturer documents reviewed: [DFRobot V5 PWM example](https://wiki.dfrobot.com/sen0001/docs/21980) specifies TTL preparation; [Tontek TTP223 family page](https://www.tontek.com.tw/product/product2?idx=243&lang=en) documents configurable output polarity/mode. These are references for checking the actual specimen, not proof that a board called “TTP223B” is the cited BA6 variant or configured a particular way.

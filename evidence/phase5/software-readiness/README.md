# Software-readiness qualification — 2026-11-11

**PARTIAL milestone: all applicable compile/mock/software checks pass; physical timing, resource and commissioning gates remain PENDING.** No serial hardware was opened, no firmware uploaded, no physical ARM/PWM generated, and no servo/PCA power or wiring changed. The Pi worktree/services were untouched.

Source under test: `b84f48577c0e915384dcc335adc97a4e1b7fe29c`, clean worktree. Integrated baseline: PR #6 merge `e5ac1be32c1b8211924b830fb4a148db5c568792`. [Commit list](commits.txt), [changed source files](source-changes.txt), [machine-readable matrix](test-matrix.json), [implementation and exact first-hardware procedures](../../../docs/SOFTWARE_READINESS.md).

| Check | Actual result | Evidence |
| --- | --- | --- |
| Initial baseline | 179 tests, 0 failures/errors/skips; 14/14 runner checks | [unit log](baseline/reports/REG-PY.log), [baseline matrix](baseline/matrix.json) |
| Final suite | 215 tests, 0 failures/errors/skips | [full test log](software/reports/REG-PY.log) |
| Final existing checks | 14/14 PASS: environment/deps/pip, unit tests, CAD model, gait data, power budget, simulation, model study, proxy, JS, DOM, repository, Mermaid | [software matrix with commands/durations/commit](software/matrix.json) |
| Firmware mock programs | 8/8 PASS, real sketch parsers with fake pins, time, edges and UART | [native log](firmware/native.log) |
| Wire integration | Actual C++ mock URM37/touch TEL2 records → Pi TelemetryStream → SensorManager; touch interaction event; no physical ARM | [native log](firmware/native.log) |
| Physical-source / virtual-output arbitration | Explicit manual virtual output, invalid-range STOP, no automatic re-arm; PyBullet sensor callback cannot overwrite physical source | [full test log](software/reports/REG-PY.log), `test_readiness.ProviderTests` |
| OLED faults and STOP | Missing/wrong-address/transfer faults, reconnect, rate limits, all semantic screens; blocked OLED worker cannot block STOP | [full test log](software/reports/REG-PY.log), `test_readiness.DisplayTests` |
| Real recorded yellow frames | 4 offline cases PASS; clipped low-saturation targets remain rejected; background/identity diagnostics bounded | [full test log](software/reports/REG-PY.log), `test_recorded_vision` |
| AVR Uno R3 | 6/6 configurations compile; no upload | [firmware matrix](firmware/matrix.json) |
| Source CI | PASS for push and PR, including Python 3.11 full suite, selected 3.13 checks, aarch64 wheel resolution, native mocks, AVR variants, packaging and web/repository checks | [PR run](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/43054188142), [push run](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/43054176144), [CI record](ci.json) |

The native programs are policy, default sensors, five active-high sensors, three active-low sensors, disabled direct calibration, reviewed-but-unknown direct calibration, production with PCA present, and production with PCA missing. Pure policy tests exercise timeout, invalid/out-of-range pulse, recovery, microsecond wrap, debounce, boot-held, stuck/release, neutral/direction/limits/rate/session/lease/STOP. Mock watchdog service/reset flags do not emulate a real AVR watchdog or Uno bootloader.

| Firmware variant | Flash bytes | Global SRAM bytes | Remaining stack/locals bytes |
| --- | ---: | ---: | ---: |
| Sensor-only default/unconfigured | 5,276 | 410 | 1,638 |
| URM37 V5 + five active-high touches | 7,240 | 510 | 1,538 |
| URM37 V5 + three active-low touches | 7,240 | 510 | 1,538 |
| Direct calibration, disabled/unknown | 5,012 | 459 | 1,589 |
| Production, commissioning gate closed | 10,430 | 1,120 | 928 |
| Generated virtual Uno | 7,002 | 927 | 1,121 |

All are below 28 KiB flash / 1,300-byte global-SRAM targets. Remaining bytes are **not a measured stack high-water margin**; the ≥400-byte worst-case measured margin remains a hardware/emulator gate. Arduino AVR core 1.8.8, Servo 1.3.0 (direct target), existing pinned Adafruit libraries and local shared policy are recorded in profiles/logs. Native compiler was Zig 0.13.0 on Windows; CI uses g++. Local Python 3.11.18 / OpenCV 4.11.0 / NumPy 2.4.6 / Flask 3.1.2 / pyserial 3.5 / PyBullet 3.2.5 are preserved in [environment evidence](software/environment/ENV-DEPS.log). CI PyBullet remains 3.2.7; these environments are not claimed equivalent.

The first CI revision `6c58563` failed the repository preservation check because the active `sketch.yaml` evolved to add a local policy dependency. Subsequent commits keep strict byte preservation for gait `motion.h` and the remaining historical assets; evolving command code/manifest remain in Git history. Final `b84f485` runs pass. Earlier local `.venv` launch failed because its interpreter path no longer exists; the preserved toolchain reproduced the baseline and final results without modifying the old environment.

Pending gates: identify actual URM37 revision/mode and distance accuracy; validate touch electrical presence/bias/noise; identify OLED controller/address/voltage/pull-ups and test real I2C/screens; measure AVR stack/ISR/timing/reset behavior; design/verify independent electrical STOP/OE feedback; measure each supported joint and power system before any calibration signal; repeat the inherited Phase 4 real-target/visible-GUI evidence. HC-SR04 is optional and remains unimplemented, explicitly unavailable. No safe standing, physical pursuit, calibrated servo position or real locomotion is verified.

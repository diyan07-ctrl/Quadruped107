# Final stabilization evidence — 12 November 2026

**SOFTWARE READINESS PARTIAL.** No upload, real serial device access, physical ARM, servo PWM, PCA or servo supply operation occurred. Real camera work and virtual output are distinguished below.

Integration `488b837` preserves PR #7 merge `6e0d578` and main `f625250`. Implementation checkpoint `9fe42b1` is the Pi archive source. The [release report](../../docs/SENSOR_COMMISSIONING_RELEASE.md) and [sensor bench instructions](../../docs/SENSOR_BENCH.md) define the non-actuating scope. No firmware upload, real serial-device access, PCA, servo power or physical PWM was performed.

Qualified implementation: `1246f7af4be6d87fc5132ab323aa269ffdd2d223`, clean source at test start. Later commits freeze documentation/evidence only. [Source/CI identity](source.json), [implementation commits](commits.txt), [SHA-256 manifest](manifest.json), [draft PR #8](https://github.com/diyan07-ctrl/Quadruped107/pull/8).

| Test | Result | Executed scope / evidence |
| --- | --- | --- |
| Integrated baseline | PASS | [215 Python tests](baseline/reports/REG-PY.log); initial DOM/Mermaid failures were missing Node dependencies; LICENSE preservation failure was Windows checkout line endings |
| Frozen regression | PASS | [222 tests, zero failures/errors/skips](frozen-source/reports/REG-PY.log), [14/14 established checks](frozen-source/reports/local-checks.json) |
| Native firmware | PASS | [12 executable mock variants](firmware/native.log); actual sketch valid/no-echo TEL2 into actual Pi SensorManager; ARM rejection and urgent STOP |
| AVR | PASS | [10 build variants and commands](firmware/matrix.json), [flash/SRAM and HEX hashes](firmware/resources.json); no upload |
| Package/build | PASS | [Compileall, dependency freeze, wheel build, extracted-wheel import/assets, recording](extra/matrix.json) |
| Recorded vision | PASS, offline scope | [10 before/after evaluations](extra/vision-comparison.json); no known false positives; unknown historical screenshot labels remain unknown |
| Recording | PASS, simulated scope | [AVI](extra/virtual-forward.avi), [measured joint sidecar](extra/virtual-forward.joints.jsonl), [report](extra/virtual-forward.json); tests decode video, match counts and verify exit disarm |
| Source CI | PASS | [PR run](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/43180688378), [push run](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/43180680839), both on `1246f7a`; Linux full suite, 3.13 subset, aarch64 wheel resolution, native/AVR and package/web/repository checks |
| Actual Pi 3.13 | PASS, selected scope | [79 tests across six modules, no skips](pi/test-summary.json), [preflight](pi/preflight.json), [actual imports](pi/dependency-imports.json), [environment freeze](pi/dependency-freeze.txt) |
| Operator preservation | PASS | [Before hash](pi/operator-before.sha256), [final hash](pi/operator-final.sha256); status also identical; executed cmp commands in [collection log](session/pi-stop-collect.log) |
| Foreground GUI | PASS, bounded observation | [Genuine OpenGL screenshot](session/gui-foreground.png); [separate disarmed 28800-step run](session/gui-observation.json) completed; no active endurance claim |
| Initial passive GUI attempt | FAIL | [Joint-limit excursion at step 4474](session/gui-smoke.json); simulated disarmed model, not physical instability evidence |
| Live yellow placement | FAIL | [8.078 seconds, 0/9 sampled frames](live-yellow/result.json), [original](live-yellow/frame-001-original.png), [raw diagnostics](session/yellow-diagnostics.json); [earlier tiny-fragment selection](session/yellow-lit-state.json) retained |
| New 905-second attempt | FAIL at admission | [HTTP 409, zero active seconds/samples](pi/hil-run/result.json); [later disarmed state](pi/admission-state.json), [Pi trace](pi/hil-pi/state.jsonl.gz), [source trace](hil-twin/trace.jsonl.gz) |
| Active GUI/endurance fault matrix / Windows-owned remote heartbeat | NOT TESTED | New Pi-owned admission failure is separate from the historical Windows-owned tunnel timeout |
| Dashboard screenshot | BLOCKED | Browser could not verify Windows URL; UI automation stopped. Camera diagnostic images are not dashboard screenshots |
| Physical sensors/OLED/resource/electrical tests | NOT TESTED | No connected Uno/OLED qualification, stack high-water, ISR timing, bootloader/reset behavior or independent STOP measurement |
| Physical actuator operation | NOT APPLICABLE | Deliberately excluded; enable paths remain inhibited |

Windows: Python 3.11.18 / OpenCV 4.11.0 / NumPy 2.4.6 / Flask 3.1.2 / pyserial 3.5 / PyBullet 3.2.5 ([environment](frozen-source/environment/ENV-DEPS.log)). Arduino CLI 1.5.1 (`01f3d4f2b`), Zig 0.13.0, AVR core 1.8.8, Servo 1.3.0 and existing pinned Adafruit profiles. CI uses PyBullet 3.2.7. Pi: Python 3.13.5 / OpenCV 4.10.0 / NumPy 2.2.4. Environments are not claimed equivalent; Pi system Python alone lacked Flask, while its existing environment imported successfully.

| AVR target | Flash bytes | Global SRAM bytes |
| --- | ---: | ---: |
| Sensor default | 5276 | 410 |
| Each V5 3/4/5 touch high/low profile | 7240 | 510 |
| Disabled calibration | 5012 | 459 |
| Inhibited production | 10430 | 1120 |
| Generated virtual Uno | 7002 | 927 |

Remaining SRAM is not measured stack margin. Firmware qualification logged `a5d488c` with then-uncommitted preflight changes; [source identity check](extra/firmware-source-identity.log) proves firmware and native harness paths unchanged at `1246f7a`. Pi archive source `9fe42b1` has identical application/firmware/simulator paths; only the qualification HTTP diagnostic helper changed afterward. Pi tests used PYTHONPATH into an isolated `/tmp` archive; no pip install, service/network change or operator checkout mutation occurred.

Preserved failed attempts: [sandbox toolchain restriction](baseline-firmware/native.log), [new replay test's initial timeline failure](firmware-before-timeline-fix/native.log), followed by the corrected native PASS. Injected all-checks-fail output inside `test_release` deliberately tests runner exit propagation; it is not a failure of the final 14 checks.

The old HIL client discarded the HTTP 409 body, so the first admission reason cannot be reconstructed. Later disarmed telemetry shows intermittent virtual range ages above 300 ms; that does not prove the original rejection cause. The helper now retains endpoint/status/bounded server response, with regression coverage. No freshness rule changed, no automatic re-arm occurred and no full trial was repeated merely for PASS. Driver evidence reports YUYV 640×480 / 1280-byte stride and nominal 15 FPS while capture measured about 8.33 FPS. Raw images retain duplicated-looking outlines/color shift; device/scene root cause remains unproven.

Three genuine images were saved to Desktop `Quadruped107-LinkedIn-2026-11-12`: real camera, OpenCV rejection diagnostics and foreground PyBullet, below the requested five-image maximum. No social-media post was made. Candidate processes and the task-owned SSH tunnel were stopped; the operator SSH connection was preserved.

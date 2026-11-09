> Phase 0 evidence below is historical. Phase 0.1 results are recorded separately at the end. No physical testing was performed.

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
- Remote CI completed Python tests, dependency installation, installed-package checks and Uno compilation successfully; see the evidence below. These were not local runs.
- No dependencies were installed locally. CI successfully installed the development dependencies in Ubuntu 24.04 with Python 3.11.18.

The inherited validation document reported a 2026-11-04 Uno compile at 10,198 bytes flash and 998 bytes global SRAM, plus software tests. These are historical reported results, not reruns and not physical validation. Current firmware source is preserved; new CI results take precedence once available.

## Phase 0 CI evidence

[Push run 42574997426](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42574997426) and [PR run 42575045535](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42575045535) both passed for commit ef997ce8b4f7c886697faf63b00219bf3db0e432 on 2026-11-09.

| Check | Result |
| --- | --- |
| Dependency installation and editable package | Passed; Flask 3.1.2, pySerial 3.5, OpenCV headless 4.11.0.86, NumPy 2.4.6 |
| Python compileall | Passed for active application, tests and tools |
| unittest discovery | 18 tests passed in 4.297 s in the push run |
| HTTP simulation | Real subprocess CLI, synthetic camera, controls, JPEG/MJPEG and stop passed |
| Wheel build, replacement install, imports/assets outside checkout | Passed; no real hardware opened |
| Browser JavaScript syntax | Passed |
| Repository validator | 111 files; 56 preserved baseline blobs; four intentional identical-STL groups |
| Uno compile | Passed; AVR core 1.8.8, PWM library 3.0.2, BusIO 1.17.4 |
| Firmware size | 10,198 bytes flash / 32,256; 998 bytes global SRAM / 2,048; 1,050 bytes remain for stack/locals |

The final tooling commit updates checkout/setup-python to verified Node 24 releases and adds pip check. Arduino's latest setup action remains v2.0.0, declared for Node 20; the hosted runner executes it on Node 24 successfully but reports an upstream deprecation warning. This warning does not indicate a firmware compile failure. The tooling commit 50d776f47dcdb1854961de1d741a52fd7af09cf8 passed both Python and Uno jobs in [push run 42575330234](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42575330234), including pip check. The final documentation-only commit records this result; its PR checks are verified before marking ready.

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

## Phase 0.1 validation status

Branch phase0.1/architecture-power starts from unmerged PR #1 head 6ce7fcb. Host changes add priority STOP, queue cancellation/capacity/freshness, controller generation barriers, single-browser ownership, camera queue configuration and offline calibration contracts. The standard-library Power calculator adds deterministic engineering scenarios and table checks.

Local Python/Arduino remain unavailable; software and firmware validation will use GitHub Actions. Local repository links/paths/preserved blobs, JavaScript/tool syntax and whitespace checks pass at preparation. Initial [push CI 42582299428](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42582299428) and [PR CI 42582307102](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42582307102) passed at 58e40dd: 42 tests (3.704 s in push), package/wheel import and assets, dependency consistency, Python compilation, calculator-generated tables, repository integrity and four Mermaid diagrams. Uno compiled unchanged at 10,198 bytes flash / 998 bytes globals. Canonical Power tables were copied from the actual calculator output.

Follow-up code adds generation/session-safe inference, a separate 0.8 s observation guard, first-fault latching, and tests using the real serial worker through reconnection and a blocked vision worker. The follow-up [push run 42583286602](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42583286602) and PR run 42583295472 executed 46 tests successfully (10.702 s in push), passed table consistency, wheel/assets, Mermaid and Uno compilation. The workflow correctly failed its final git-diff guard: inherited vision.py had original CRLF bytes but an LF normalization attribute, producing a checkout-only difference on Linux. Phase 0.1 fixes that attribute to preserve the original bytes; a complete passing run is required before marking ready.

Reproduce additional checks with:

```bash
python hardware/Power/power_budget.py --check
python hardware/Power/power_budget.py --json
python -m unittest discover -s tests -v
npm install --prefix build/mermaid --no-save mermaid@12.3.0 jsdom@26
node tools/check-mermaid.mjs
```

Power runtime/current outputs are estimates only. All electrical/mechanical, battery, load, watchdog, partial-power, resource and stop-timing measurements remain pending in [HARDWARE_VERIFICATION](HARDWARE_VERIFICATION.md).

### Complete Phase 0.1 software verification

The attribute fix at c769bd2 passed [push run 42583604285](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42583604285) and [PR run 42583611037](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42583611037), including the clean-tree guard. Evidence covers 46 tests, Python syntax, dependency consistency, priority/cancellation/races, timeout/reconnect/no replay, blocked-vision guard, camera configuration stub, power/calibration validation, deterministic Markdown tables, wheel imports/assets, four Mermaid diagrams, and Uno compilation. Firmware remains 10,198 bytes flash / 998 bytes globals; hardware/resource/timing measurements remain pending.

The final documentation/deployment freeze clarifies external distribution, independent overvoltage power-cut requirements, A/B/C/D cost/mass tradeoffs and a 20 s service shutdown grace. Its final-head workflows are checked before PR readiness. No previously failed check is hidden or treated as a successful full run. No power source, regulator, current waveform, stopping latency, physical watchdog or assembled-robot test is claimed verified.

Final architecture freeze 99b2614 passed [push workflow 42584023952](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42584023952) and [PR workflow 42584032557](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42584032557), including all 46 tests, power-table checks, installed assets, four diagrams, clean-tree guard and Uno build. The closing documentation clarification defines best-effort touch coalescing without stale replay; it activates no sensor code.

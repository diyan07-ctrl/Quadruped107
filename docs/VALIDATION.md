# Validation evidence

## Phase 3 integrated checkpoint

[PR run 42734353977](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42734353977), source cc085f3c7acecb8ad6437509c7e4b2a7529087bb, passed **154 tests in 59.428 s**, retaining the 128-test incoming Phase 3 baseline. All three jobs passed: Python 3.11, selected Python 3.13 vision/telemetry checks and production/virtual Uno compilation. The final synthetic operator controls and documentation receive their own head checks before PR readiness.

- PASS — dependency consistency, Python compilation, package wheel/install/import/assets, original motion/model/power consistency, JavaScript/DOM, links/repository integrity, Mermaid and clean-checkout guards.
- PASS — [integrated synthetic camera evidence](evidence/PHASE3_INTEGRATION.json): both colors accepted left/right and centered, eight joints, 58 distinct accepted virtual target vectors; obstacle override, camera fault, simulator reset and STOP disarmed without automatic re-arm. This is SIMULATED, not a real webcam measurement.
- PASS — [fifteen controlled model experiments](evidence/PHASE3_MODEL_STUDY.json), with unchanged collision checks, torque cap, canonical CAD/gaits and physical calibration. Smoothing reduced target increments but increased lag and retained self-contact; default remains off.
- PASS — Python 3.13 x86_64 execution and cp313/abi3 aarch64 OpenCV/NumPy wheel availability. This is not Pi OS native installation validation.
- NOT TESTED — real Pi camera/FPS/CPU/RAM, GUI/mobile rendering on actual devices, physical sensor/Uno/PCA/servos, electrical protection, stopping time and walking. No SSH command ran on Pi: hostname resolution failed and last-known-IP connection was denied before authentication. No credentials, services or recordings were accessed.

The earlier workflow YAML run had no executable jobs because an unquoted colon-containing pip option was parsed as YAML. The quote fix restored execution. The subsequent integration failure exposed a recovery fixture using an old detected observation while Camera.latest was unavailable; recovery now requires a newly available camera frame and fresh perception. Production readiness gates and assertions were retained. Configuration-race coverage additionally rejects an old detector result after a color change. Failed runs are not counted as successful validation.

Exact launch/test procedures are in [Phase 3](PHASE3.md). Local Python/Arduino tools were unavailable; Python/firmware results above were executed in GitHub Actions. Local Node/Git/repository checks are reported separately. Earlier phase evidence follows for history.


Phase 2 starts from verified unmerged Phase 1 head a15c39775a4063b396c3cd844f66324cd250021c, whose [final CI](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42675810285) passed 75 tests and both Uno builds. Work is on phase2/autonomy-sensors-simulation; [PR #4](https://github.com/diyan07-ctrl/Quadruped107/pull/4) targets phase1/software-vision-digital-twin. No existing PR is merged.

## Executed evidence

- [First Phase 2 push 42679290045](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42679290045), c1ef144: **110 tests passed in 28.482 s**, dependencies, model/gait/power checks, installed wheel/assets, links, Mermaid and both firmware builds.
- Wider integration revealed stale re-arm readiness, drifting nominal fixture pose and explicit-fixture polling contention. These were repaired with stop-epoch acknowledgment, an explicit external fixture constraint, atomic takeover/STOP retirement and bounded fixture polling. Original gait values, torque cap, collisions and physical firmware remain unchanged. The Phase 1 integration fixture now waits for the strengthened fresh-disarmed readiness barrier before re-arm; no assertion was removed.
- [Push 42681826866](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42681826866) and [PR 42681837310](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42681837310), 0ae7b21: **117 tests and every CI check passed** after those repairs.
- [Measured model study](MODEL_STUDY.md) and [machine-readable evidence](evidence/PHASE2_MODEL_STUDY.json) preserve the source commit/run for simulated results. [Push 42682345230](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42682345230) and PR 42682357154 at 9e44cff passed **120 tests (44.947 s in push)**, all checks and twelve model experiments. Later scene-reset, stronger obstacle assertions and DOM additions are verified by the final PR checks.

## Final implementation validation

[Push 42683896441](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42683896441) and [PR 42683905992](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42683905992), source c0a083af91d5a97112dbb2dbed9ba56b40650711, passed **122 tests in 44.277 s** in push. This preserves all 75 Phase 1 tests and adds 47 Phase 2 tests. Both jobs passed, including dependencies, syntax, all eight scenarios, UDP/application integration, reset/reconnect, prerecorded camera, touch-after-enable, eight-routine articulation, twelve model experiments, installed package/assets, seven Mermaid diagrams, dashboard DOM checks and a clean checkout.

Production Uno: **10,198 bytes flash / 998 bytes globals**, 1,050 bytes remain for locals/stack. Separate virtual build: **6,756 / 831**, 1,217 bytes remain. Neither firmware was uploaded or tested on a board. The documentation-only freeze commit records these completed implementation checks; its own PR checks are also verified before review.

The full twenty-case scope matrix and deliberately untested physical/GUI categories below remain authoritative. The initial DOM failure was a test fetch fixture treating URL objects as strings; it was corrected without changing production behavior or removing an assertion.

## Complete acceptance checkpoint

[Push 42683505923](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42683505923) at 9dc2180 passed **121 tests in 45.032 s**, all twelve model experiments, installed sensor/navigation imports/assets, both firmware builds, seven Mermaid diagrams, dashboard DOM checks and the clean-checkout guard. The DOM fixture was corrected to accept URL objects like browser fetch; its earlier failure did not indicate a backend test pass.

[Network scenario evidence](evidence/PHASE2_NAVIGATION.json) records approximately 0.05850 m proxy advance, 0.59325 m front range at observed disarm, zero proxy contacts and activeMask=0. This is a simulated integration snapshot, **not a physical stopping-distance measurement**. The final touch-scene regression clocks its scheduled event from explicit enable rather than scene startup; final head checks are linked on PR #4.

Local repository validation verifies 53 protected historical blobs, four intentionally identical STL groups and no matched credential patterns. A direct Phase 1 comparison confirms hardware, production firmware, calibration, LICENSE and AUTHORS unchanged. Git integrity and whitespace checks pass; generated videos/reports/caches remain ignored.

## Scenario coverage

Tests live in [test_phase2.py](../tests/test_phase2.py), with the preserved 75-test Phase 1 suite in the other test files. Tests use deterministic clocks/fixtures unless explicitly classified as threaded or UDP integration.

| Requested scenario | Evidence scope |
| --- | --- |
| 1 Empty exploration | Pure policy plus actual Runtime/controller/virtual Uno |
| 2 Obstacle ahead | Policy and PyBullet rays → UDP → runtime → Uno → proxy stop |
| 3 Threshold/hysteresis | Deterministic exact-boundary unit test |
| 4 Invalid range | Zero/negative/out-of-range/NaN/type tests |
| 5 Timeout | Acquisition age and expiration tests |
| 6 Missing sensor | Required range/touch records fail closed |
| 7 Conflicting readings | Independent front values beyond tolerance |
| 8 Blue target | Existing BGR detector, synthetic camera and real application path |
| 9 Target behind obstacle | Policy and tracking integration preemption |
| 10 Target loss | Preserved Phase 1 integration and navigation loss deadline |
| 11 Manual tracking takeover | Real tracking API/controller cancellation |
| 12 STOP during recovery | Unit deadline/priority plus actual controller/Uno STOP |
| 13 Simulator disconnect | Actual UDP/Runtime loss and disarm |
| 14 Touch interaction | Debounced event → existing greeting routine → bounded STOP |
| 15 Bounce | Deterministic press/release filtering |
| 16 Stuck touch | Held duration fault |
| 17 Simultaneous touches | Priority safety contact inhibition |
| 18 Delayed telemetry | Source+transport age, duplicates and unexpected sender |
| 19 Reconnection | Actual reset/disconnect/reconnect; no auto re-arm |
| 20 Mode switching | Bounded policy transitions, actual takeover/idle and stale-generation rejection |

All eight named environments are instantiated and checked against known geometry. Scene reset changes the receiver epoch and reproduces seeded observations while disarmed. The blue prerecorded-camera generator is exercised through the real file backend. DOM checks verify supported mode exposure, escaped diagnostic text, disabled movement when disarmed, always-available STOP and Phase 1 compatibility. DOM testing is not screenshot/mobile-device qualification.

## Reproduction

```bash
python -m pip install -r software/pi/requirements-dev.txt -r simulation/requirements.txt -e software/pi
python -m pip check
python -m compileall -q software/pi/quadruped tests tools simulation
python simulation/build_model.py --check
python -m simulation.proxy_probe
python -m unittest discover -s tests -v
python -m simulation.validate
python -m simulation.model_study
python tools/generate-motion-data.py --check
python hardware/Power/power_budget.py --check
python -m pip wheel --no-deps software/pi -w build/wheels
python -m pip install --no-deps --force-reinstall build/wheels/*.whl
python tools/check-installed.py
node --check software/pi/quadruped/web/app.js
node tools/check-repository.mjs
npm install --prefix build/mermaid --no-save mermaid@12.3.0 jsdom@26
node tools/check-mermaid.mjs
node tools/check-dashboard.mjs
arduino-cli compile --profile uno firmware/uno/sketch
python tools/generate-virtual-firmware.py
arduino-cli compile --profile uno build/virtual/sketch
git diff --check
git fsck --no-dangling
```

Python/Arduino execution uses GitHub Actions because the local saved interpreter/toolchain remains unavailable. Local Node syntax, repository/protected-blob/link/credential-pattern checks and Git checks run on Windows. Shell syntax is checked in CI. No Pi access is attempted or required. Existing historical SSH attempts below belong to Phase 1 only.

## Qualification status

| Category | Status |
| --- | --- |
| Software interfaces and policies | IMPLEMENTED |
| Range rays, touches, scenarios and proxy | SIMULATED |
| Referenced unit/integration/compile/packaging checks | AUTOMATED TESTED when their CI step passed |
| Real Pi camera, CPU/RAM/latency | NOT TESTED — deliberately postponed |
| Sensors/Uno/PCA/servo/power/physical stopping | PHYSICAL HARDWARE TESTED: none |
| Physical locomotion and correct CAD dynamics | NOT TESTED; provisional model and self-contacts remain |
| Laptop GUI visual/mobile rendering | NOT TESTED; headless physics and DOM checks only |

Production Uno compile remains 10,198 bytes flash / 998 bytes globals; virtual build 6,756 / 831 in preceding checks. Recompile logs are the authority; compile memory is not stack high-water. No new physical firmware allocation was added. Bounded queues/logs and Pi design targets remain documented; no Pi performance measurement is claimed.

---

# Historical Phase 1 evidence

# Software integration validation

These results concern branch phase1/software-vision-digital-twin, based on verified Phase 0.1 head a629397e3cce82819e5d8a52db8938aa93af840c. PRs #1 and #2 were unmerged when inspected. [PR #3](https://github.com/diyan07-ctrl/Quadruped107/pull/3) targets the Phase 0.1 branch; no merge is authorized or performed.

## Evidence and classification

| Scope | Classification | Evidence / limitation |
| --- | --- | --- |
| First USB/vision/virtual-Uno checkpoint | PASS | [Run 42670685320](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42670685320), d926f29: 64 tests in 13.859 s, package/dependency/firmware checks |
| Initial bridge and model checkpoint | FAIL, repaired in subsequent commits | [Run 42673376451](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42673376451): 73 tests; one assertion read virtual output before STOP acknowledgment. It now waits separately for local inhibition and output-off |
| Production and virtual firmware | PASS (compile only) | [PR run 42673388763](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42673388763): 10,198 bytes flash / 998 bytes globals production; 6,756 / 831 virtual; no board uploaded |
| Extended bidirectional integration | FAIL, model correction added | [Run 42674667131](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42674667131): passive joint exceeded provisional limit after STOP. Solver substeps/iterations and modeled velocity cap added; strict excursion guard retained |
| Optional artifact-upload initialization | FAIL, optional dependency removed | Runs 42674092245/42674428014 did not create a Python job; firmware was separate. Standard job logs now carry JSON evidence; no checks are skipped to publish |
| Real Pi/webcam deployment | BLOCKED — NETWORK ACCESS DENIED | SSH port 22 Permission denied before authentication for both reported IP/hostname; no Pi command ran |
| Physical Uno, PCA, servo, sensor or electrical testing | BLOCKED — HARDWARE UNAVAILABLE / PROHIBITED | Uno disconnected, damaged PCA isolated, servos unpowered, no uploads or power switching |
| CSI camera / actual optional gesture model | NOT TESTED | CSI reported faulty; no compatible gesture model supplied |
| Physical gait feasibility / realistic dynamics | NOT TESTED | CAD surfaces reused; axes, pivots, masses, collision proxies and angle conversion remain provisional |

[Run 42675186244](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42675186244) at 80a48df passed all **74 tests in 21.519 s**, dependencies, compileall, canonical model/gait/power checks, eight-routine headless articulation, wheel installation/imports/assets, shell/JavaScript syntax, links/protected blobs, five Mermaid diagrams, clean checkout and both Uno builds. [Machine-readable simulation evidence](evidence/SIMULATION_CI.json) records the actual run.

The earlier passive-joint excursion was corrected with solver substeps/iterations and a modeled velocity cap, without widening the excursion guard. The next test failure was a fixture sending a missing-key heartbeat during requested forward motion; it correctly triggered the release safeguard and was corrected to match browser behavior. Output queue overflow additionally has a fail-closed regression.

Fixed-base maximum transient joint error was approximately 0.51–0.65 rad. Maximum self-contact counts were initial 2, forward 4, turn_left 2, turn_right 2 and greeting 2; stand/backward/tail_wag reported zero. These are contacts between provisional collision proxies and expose unresolved geometry/gait assumptions. No fixed-base finite-state fault occurred, but this is not collision-free or mechanically qualified walking. The separate free-base stand probe in [run 42675542675](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42675542675), commit 5238cc4, completed 720 steps (three virtual seconds) without a configured fall/tilt/divergence fault; maximum contacts 12 and self-contact zero. Its provisional base ended at approximately (-0.0171, 0.0005, 0.2291) m. This is a numerical gravity probe with invented inertial/axis assumptions, not measured physical balance or walking. That run also passed all 74 tests in 21.574 s and every CI check. A final construction-boundary regression additionally prevents a simulation flag from relabeling an injected physical link; final results are verified on the PR. Unit fixtures, simulated integration, compile results and real hardware observations are separate categories.

## Reproduction

On a laptop or CI with Python 3.11:

```bash
python -m pip install -r software/pi/requirements-dev.txt -r simulation/requirements.txt -e software/pi
python -m pip check
python -m compileall -q software/pi/quadruped tests tools simulation
python simulation/build_model.py --check
python -m unittest discover -s tests -v
python -m simulation.validate
python tools/generate-motion-data.py --check
python hardware/Power/power_budget.py --check
python -m pip wheel --no-deps software/pi -w build/wheels
python -m pip install --no-deps --force-reinstall build/wheels/*.whl
python tools/check-installed.py
node --check software/pi/quadruped/web/app.js
node tools/check-repository.mjs
npm install --prefix build/mermaid --no-save mermaid@12.3.0 jsdom@26
node tools/check-mermaid.mjs
arduino-cli core update-index
arduino-cli compile --profile uno firmware/uno/sketch
python tools/generate-virtual-firmware.py
arduino-cli compile --profile uno build/virtual/sketch
git diff --check
```

CI runs these on Ubuntu, including installed wheel imports/assets and packaged gait JSON outside the checkout. Local Python is unavailable (saved interpreter removed, replacement download blocked); Arduino CLI is unavailable locally. Local Node syntax, links/preserved-asset/credential-pattern checks and staged whitespace checks execute on Windows. No test execution is inferred from writing code.

The simulation evidence runner writes build/simulation/articulation.json and a TinyRenderer stand.png, then prints its JSON. These are generated, ignored outputs, not physical photographs or certified mechanical parameters. The strict headless integration uses a synthetic blue target, actual controller/serial worker/emulator, real UDP loopback and PyBullet DIRECT. It covers both turns, centered hold, target-loss disarm, explicit re-enable and manual STOP. Other tests cover malformed/stale/duplicate traces, network loss, camera open/read/freeze/recovery, ownership and queue/timeout/reset behavior.

Pi resource targets are in [SOFTWARE](SOFTWARE.md); none are measured here. Production Uno leaves 1,050 bytes static headroom for locals/stack; virtual build leaves 1,217 bytes. Compile accounting does not measure peak stack/interrupt use. No full OLED framebuffer or new production sensor allocation was added.

See [baseline diagnostics](evidence/ENVIRONMENT_BASELINE.md), [simulation acceptance procedure](../simulation/README.md), [deploy instructions](../deploy/README.md) and [physical verification](HARDWARE_VERIFICATION.md). No physical stop time, power measurement, live Pi FPS or locomotion qualification is claimed.

---

## Historical Phase 0 / 0.1 record

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

## Final Phase 3 implementation checkpoint

Source 45c15df523f1b606a0124acc1fb7aa6e23aa8b97 passed [PR workflow 42735297964](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42735297964): **157 tests in 59.664 s**, preserving all 128 incoming tests and adding 29 focused regressions. Python 3.13 passed 17 vision/readiness tests and six telemetry tests, read-only diagnostics and ARM64 wheel download. All three jobs succeeded. Production Uno remained 10,198 bytes flash / 998 bytes globals; separate virtual firmware 6,756 / 831. Neither was uploaded.

The integrated demonstration observed 61 distinct virtual eight-target vectors in this run; counts vary with threaded scheduling and are not a performance benchmark. Both colors turned left/right and held center; target loss, obstacle override, camera fault, simulator reset and STOP remained disarming, with no automatic re-enable. The preserved 58-vector evidence file identifies its earlier source/run explicitly.

Eight Mermaid diagrams parsed successfully. Package installation/assets, dependency consistency, model/gait/power checks, DOM behavior, clean checkout and repository checks passed (185 files, 53 protected historical blobs, four intentional duplicate STL groups). A direct Git comparison against incoming Phase 3 confirms no changes to hardware assets, firmware, model files, LICENSE or AUTHORS. Local JavaScript syntax, repository validation, whitespace and Git object integrity checks also passed; dangling intermediate objects are not tracked changes.

The closing documentation/DOM commit adds assertions for synthetic target payload/visibility and records this completed checkpoint. Its head checks must also pass before marking PR #5 ready. Actual Pi, webcam and physical hardware results remain NOT TESTED/BLOCKED as stated above.

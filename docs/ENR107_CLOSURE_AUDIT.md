# ENR107 closure audit — 22 November 2026

## Baseline and scope

Audited repository: diyan07-ctrl/Quadruped107. GitHub metadata confirms default branch `main`; fetched main is `f625250` (author-information edit). The original working tree was clean on `phase5/software-hardware-readiness` at `edf08eb`. Closure branch `docs/enr107-final-project-closure` starts from `origin/main`, avoiding an unreviewed integration of later experimental work. No local/remote branches, experimental source, CAD, calibration or media were removed.

The closure brief is the source for Group 11, concluded academic development, the Uno/PCA/URM37/3S configuration and reported academic activities. Submission receipt, final uploaded sketch and final academic video were not supplied or located. Status is **Completed / Submission prepared; Further Development: On Hold**. Historical technical reports retain their original session evidence and are marked with scope notices where their architecture could conflict with academic closure.

## Structure and component inventory

The complete tracked main-branch path inventory appears below. Generated build directories, local virtual environments and sibling repositories are not project source. No applicable AGENTS.md was found in the workspace/repository search.

| Area | Findings |
| --- | --- |
| Arduino Uno R3 | firmware/uno/sketch/sketch.ino, motion.h and pinned sketch.yaml; USB-host-controlled PCA commands and movement tables; no URM37 acquisition in main |
| Historical UNO Q | archive/uno-q retains control station and single-channel calibrator, Python/web assets and board-specific Bridge dependencies |
| Raspberry Pi / vision | software/pi retains Flask UI, serial/controller ownership, camera, vision, navigation, gestures and virtual Uno; deploy contains experimental launch/configuration assets |
| ESP32 | Mentioned in the closure brief; no dedicated firmware or branch located in fetched history. No matching ESP32 source found by repository text search; location unknown |
| Simulation | simulation contains PyBullet runtime, provisional URDF, CAD manifest, parameters, model study, bridge/proxy and validation; not physical gait proof |
| CAD / mechanics | hardware/cad has Fusion F3Z and STEP; hardware/stl has named STL parts and original ZIP; no mechanical redesign |
| Calibration / power | Original XLSX files and profile example retained; hardware/Power contains conditional designs/calculator, not measured final 3S approval |
| Testing | tests contains Python regression modules; tools contains repository/link, model/motion, dashboard/Mermaid and qualification helpers; CI compiles Uno and runs software tests |
| Documentation / media | docs contains phase reports, technical contracts, evidence JSON, build/design images and exploded MP4; no identified final academic demonstration recording |

## Branches and recent history

Fetched refs at audit time; ahead/behind counts are relative to `origin/main`, not academic completion scores. Existing local phase branches and sibling worktrees remain in place.

| Remote branch | Tip | Ahead / behind main |
| --- | --- | --- |
| `main` | `f625250` | 0 / 0 |
| `phase0.1/architecture-power` | `5d35cb9` | 0 / 3 |
| `phase0/architecture-foundation` | `05e5b1e` | 0 / 2 |
| `phase1/software-vision-digital-twin` | `fa1588c` | 0 / 4 |
| `phase2/autonomy-sensors-simulation` | `4e03188` | 0 / 5 |
| `phase3/vision-recording-readiness` | `6e0d578` | 23 / 6 |
| `phase4/pi-hil-qualification` | `cb05e92` | 14 / 6 |
| `phase5/software-hardware-readiness` | `edf08eb` | 22 / 6 |
| `phase6/two-touch-commissioning` | `8c5f4db` | 39 / 0 |
| `release/sensor-commissioning` | `beddc8b` | 40 / 0 |

The main history includes PR merges #1–#5 and the original Pi/Uno port. The Phase 3 branch later absorbed PR #6 (Pi HIL) and #7 (software readiness), which are not in main. Phase 4 records headless HIL evidence with unresolved physical qualification. Phase 5 adds non-actuating sensor-only and gated direct-servo firmware, software safety and readiness checks. Phase 6 adds two-touch commissioning and connected-Pi checks, with unknown physical touch configuration and blocked upload/range acquisition. Release tip `beddc8b` merges PR #9; it preserves later development without establishing final academic firmware.

Selected immutable records: [release status at beddc8b](https://github.com/diyan07-ctrl/Quadruped107/blob/beddc8b/docs/SENSOR_COMMISSIONING_RELEASE.md), [Phase 6 record](https://github.com/diyan07-ctrl/Quadruped107/blob/8c5f4db/docs/PHASE6_SENSOR_COMMISSIONING.md), [Phase 5 firmware guide](https://github.com/diyan07-ctrl/Quadruped107/blob/edf08eb/firmware/uno/README.md). Later records include source/mock/AVR passes and actual Pi software tests, as well as failed live vision/admission attempts. They explicitly retain physical sensor/upload gates. These records were reviewed as historical evidence; their implementation was not merged into closure.

## Firmware and hardware reconciliation

All reachable sketch paths and sketch-changing commits were inspected with Git history. Main maintains one Uno R3 sketch and two archived UNO Q sketches. Later refs add direct_calibration and sensor_only. No conclusive final academic D5/D3 URM37 sketch or standalone Uno R3 channel-sweep test was located. Individual PCA channel commands and basic movement sequences remain documented in the [firmware inventory](../firmware/uno/README.md). No firmware source, dependencies, pulse targets or movement logic changed.

Source map in motion.h: FL shoulder/leg 0/1, FR 2/3, BL 4/5, BR 6/7. This is not proof of the final physical mapping. The latter remains unknown. Retained source uses 0x40/50 Hz and D8-controlled OE; academic brief allows OE grounded where applicable. Grounding OE with that firmware would defeat its inhibit behavior and can short D8. Historical sensor proposal assigns URM37 D4/D2 and HC-SR04 D5/D3; academic URM37 uses D5/D3. Earlier power studies discuss 2S packs; academic brief uses regulated 3S. These configurations are explicitly separated in the README; no pin or electrical changes were made.

## Results and limitations

Implemented code, reported activities, software-tested behavior, physical test evidence and demonstration evidence are separated in [project status](../PROJECT_STATUS.md). Build images and CAD support the assembly record, not electrical operation. The exploded MP4 is design media, not walking proof. URM37 integration and academic video preparation are reported activities; actual distance logs, final video and submission confirmation remain absent. Stable autonomous walking, continuous obstacle avoidance and advanced navigation are not verified. The coding agent performed no physical test, upload, power switching or device commissioning.

## Closure verification

Verification results are recorded here after execution. Checks operate on the retained default-branch code; later branch test totals are historical and are not substituted for this run.

Environment: Windows AMD64, Python 3.11.18 from the existing local toolchain, Node 24.22.3 and Arduino CLI 1.6.0. The pre-existing `.venv` points to an unavailable Python installation, so the existing standalone toolchain was used without changing tracked dependencies.

| Check | Result / scope |
| --- | --- |
| Repository links, tracked-file rules, source token patterns and original asset preservation | PASS: `node tools/check-repository.mjs`; 187 files including closure additions, 53 preserved blobs and four intentional identical-STL groups |
| Historical source secret-pattern review | No findings in 1192 distinct reachable text blobs; known token/private-key formats and literal credential assignments checked. Values were not printed |
| Dependencies | PASS: `python -m pip check` |
| Python syntax | PASS: `python -m compileall -q software/pi/quadruped tests tools simulation` |
| Main Uno R3 compile | PASS: `arduino-cli compile --profile uno --build-path build/enr107-uno firmware/uno/sketch`; 10198 bytes flash, 998 bytes globals; no upload |
| Generated virtual Uno compile | PASS after `python tools/generate-virtual-firmware.py`; 6756 bytes flash, 831 bytes globals; no upload |
| Motion, power and model consistency | PASS: `python tools/generate-motion-data.py --check`, `python hardware/Power/power_budget.py --check`, `python simulation/build_model.py --check` |
| Dashboard and diagram syntax | PASS: `node tools/check-dashboard.mjs`, `node tools/check-mermaid.mjs` (seven diagrams), `node --check software/pi/quadruped/web/app.js` |
| Articulation and model study | PASS execution: `python -m simulation.validate`, `python -m simulation.model_study`; provisional model results, including model limitations, remain virtual evidence |
| Full Python regression | **FAIL:** 157 tests in 64.961 s, one failure; `python -m unittest discover -s tests -v` |
| Phase 2 regression recheck | **FAIL:** 47 tests in 28.022 s, same reconnect failure; `python -m unittest discover -s tests -p test_phase2.py -v` |
| Whitespace and change scope | PASS after removing new trailing whitespace; all modifications/additions are Markdown, no deleted tracked files, source and binary assets unchanged |

The reproduced failure is `test_phase2.LifecycleRegressionTests.test_reset_disconnect_and_reconnect_never_rearm`, at test_phase2.py:617: waiting for `bridge.snapshot()["readyToArm"]` times out, with the bridge reporting “Simulation network disconnected.” Source/tests are unchanged from main. This run does not establish a root cause or physical consequence; the failure is disclosed rather than hidden or repaired by merging later experiments. The other 156 tests in the full run passed. Review CI and decide how to track this existing software issue before merging. Local raw logs and compiler outputs are under ignored `build/enr107-*`; they are not submitted as physical evidence.

Secret scans report paths/categories only, never credential values. Pattern checks are heuristic and do not establish that all historical media, compressed archives or credentials of unknown formats are clean. No new credential material is introduced by this documentation-only change.

## Complete tracked baseline inventory

Baseline inventory is generated from `git ls-tree -r --name-only origin/main`, before closure additions. Existing experimental files outside main remain in the refs listed above.

```text
.gitattributes
.github/workflows/validate.yml
.gitignore
AUTHORS.md
CONTRIBUTING.md
LICENSE
README.md
archive/uno-q/README.md
archive/uno-q/control-station/README.md
archive/uno-q/control-station/app.yaml
archive/uno-q/control-station/assets/app.js
archive/uno-q/control-station/assets/index.html
archive/uno-q/control-station/assets/styles.css
archive/uno-q/control-station/python/main.py
archive/uno-q/control-station/python/requirements.txt
archive/uno-q/control-station/sketch/sketch.ino
archive/uno-q/control-station/sketch/sketch.yaml
archive/uno-q/servo-calibrator/README.md
archive/uno-q/servo-calibrator/app.yaml
archive/uno-q/servo-calibrator/assets/app.js
archive/uno-q/servo-calibrator/assets/index.html
archive/uno-q/servo-calibrator/assets/styles.css
archive/uno-q/servo-calibrator/python/main.py
archive/uno-q/servo-calibrator/python/requirements.txt
archive/uno-q/servo-calibrator/sketch/sketch.ino
archive/uno-q/servo-calibrator/sketch/sketch.yaml
deploy/README.md
deploy/install-virtual-pi.sh
deploy/navigation.example.json
deploy/quadruped107.service
deploy/run-virtual-pi.sh
deploy/sensors.example.json
deploy/vision.example.json
deploy/vision.yellow.json
docs/ARCHITECTURE.md
docs/AUDIT.md
docs/CALIBRATION.md
docs/DECISIONS.md
docs/EXTENSIONS.md
docs/HARDWARE.md
docs/HARDWARE_VERIFICATION.md
docs/MODEL_STUDY.md
docs/PHASE2.md
docs/PHASE3.md
docs/PROJECT.md
docs/PROTOCOL.md
docs/Quadruped107_exploded.mp4
docs/ROADMAP.md
docs/SAFETY.md
docs/SENSORS.md
docs/SOFTWARE.md
docs/VALIDATION.md
docs/WIRING.md
docs/evidence/ENVIRONMENT_BASELINE.md
docs/evidence/PHASE2_MODEL_STUDY.json
docs/evidence/PHASE2_NAVIGATION.json
docs/evidence/PHASE3_INTEGRATION.json
docs/evidence/PHASE3_MODEL_STUDY.json
docs/evidence/SIMULATION_CI.json
docs/images/electrical-diagram.png
docs/images/fullscreen.png
docs/images/mechanical-complete-design.png
docs/images/mechanical-exploded-view.png
docs/images/mobilapp.jpeg
docs/images/part-base-cover.png
docs/images/part-base.png
docs/images/part-camera-base.png
docs/images/part-case.png
docs/images/part-foot.png
docs/images/part-leg.png
docs/images/part-shoulder.png
docs/images/physical-build-1.png
docs/images/physical-build-2.png
docs/images/web-control-interface.png
firmware/uno/README.md
firmware/uno/sketch/motion.h
firmware/uno/sketch/sketch.ino
firmware/uno/sketch/sketch.yaml
hardware/Power/BATTERY_COMPARISON.md
hardware/Power/COMPONENT_LOADS.md
hardware/Power/DISTRIBUTION.md
hardware/Power/POWER_BUDGET.md
hardware/Power/PROTECTION.md
hardware/Power/README.md
hardware/Power/REGULATOR_SELECTION.md
hardware/Power/RUNTIME_ESTIMATES.md
hardware/Power/SERVO_ANALYSIS.md
hardware/Power/SOURCES.md
hardware/Power/TEST_PLAN.md
hardware/Power/power_budget.py
hardware/README.md
hardware/cad/Quadruped107.f3z
hardware/cad/Quadruped107.step
hardware/calibration/Servo calibration table.xlsx
hardware/calibration/key bindings (Rog_Ally).xlsx
hardware/calibration/profile.example.json
hardware/stl/Base.stl
hardware/stl/Case.stl
hardware/stl/Dec_Front_2.stl
hardware/stl/Dec_back_1.stl
hardware/stl/Dec_back_2.stl
hardware/stl/Dec_back_3.stl
hardware/stl/Dec_back_4.stl
hardware/stl/Dec_front_1.stl
hardware/stl/Dec_side_1.stl
hardware/stl/Dec_side_2.stl
hardware/stl/Dec_side_3.stl
hardware/stl/Dec_side_4.stl
hardware/stl/FootBL.stl
hardware/stl/FootBR.stl
hardware/stl/FootFL.stl
hardware/stl/FootFR.stl
hardware/stl/LegBL.stl
hardware/stl/LegBR.stl
hardware/stl/LegFL.stl
hardware/stl/LegFR.stl
hardware/stl/STL_Final.zip
hardware/stl/ShoulderBL.stl
hardware/stl/ShoulderBR.stl
hardware/stl/ShoulderFL.stl
hardware/stl/ShoulderFR.stl
simulation/PHASE2.md
simulation/README.md
simulation/__init__.py
simulation/build_model.py
simulation/environment.py
simulation/model/cad_manifest.json
simulation/model/parameters.json
simulation/model/robot.urdf
simulation/model_study.py
simulation/proxy_probe.py
simulation/requirements.txt
simulation/twin.py
simulation/validate.py
software/pi/LICENSE
software/pi/README.md
software/pi/pyproject.toml
software/pi/quadruped/__init__.py
software/pi/quadruped/autonomy.py
software/pi/quadruped/bridge.py
software/pi/quadruped/calibration.py
software/pi/quadruped/camera.py
software/pi/quadruped/controller.py
software/pi/quadruped/data/motions.json
software/pi/quadruped/diagnostics.py
software/pi/quadruped/explain.py
software/pi/quadruped/gestures.py
software/pi/quadruped/main.py
software/pi/quadruped/navigation.py
software/pi/quadruped/sensors.py
software/pi/quadruped/serial_link.py
software/pi/quadruped/telemetry.py
software/pi/quadruped/virtual_uno.py
software/pi/quadruped/vision.py
software/pi/quadruped/vision_config.py
software/pi/quadruped/web/app.js
software/pi/quadruped/web/index.html
software/pi/quadruped/web/poses/greeting.webp
software/pi/quadruped/web/poses/initial.webp
software/pi/quadruped/web/poses/stand.webp
software/pi/quadruped/web/poses/tail-wag.webp
software/pi/quadruped/web/styles.css
software/pi/requirements-dev.txt
software/pi/requirements-gestures.txt
software/pi/requirements.txt
tests/test_demonstration.py
tests/test_http_smoke.py
tests/test_phase2.py
tests/test_phase3.py
tests/test_power_calibration.py
tests/test_runtime.py
tests/test_safety.py
tests/test_simulation.py
tests/test_software_vision.py
tests/test_telemetry.py
tests/test_vision_readiness.py
tools/check-dashboard.mjs
tools/check-installed.py
tools/check-mermaid.mjs
tools/check-repository.mjs
tools/generate-blue-video.py
tools/generate-motion-data.py
tools/generate-virtual-firmware.py
tools/qualify-demo.py
tools/record-usb-camera.py
```

# Phase 4 test matrix

**PARTIALLY VERIFIED.** Source `d29dfdb`; 10 November 2026. Each result is limited to its stated evidence class. [Full records](../evidence/phase4/2026-11-10/reports/test-matrix.json) include commands, preconditions, environment, expected/actual results and limitations.

| Test ID | Result | Observation / evidence |
| --- | --- | --- |
| ENV-SSH | PASS | [Real SSH commands executed; public-key handoff repaired access](../evidence/phase4/2026-11-10/preflight/pi-audit.log) |
| ENV-GIT | PASS | [Added missing refspec; isolated d29dfdb worktree; original patch hashes unchanged](../evidence/phase4/2026-11-10/udp/pi-protocol-and-tests.log) |
| A-PREFLIGHT | PASS | [Required imports/dependencies, camera permissions, memory/disk/network and 0x0 throttling verified](../evidence/phase4/2026-11-10/preflight/pi-isolated-checkout.log) |
| B-640 | PASS | [5952 frames / 300.008 s = 19.839 FPS; zero failed reads](../evidence/phase4/2026-11-10/camera/benchmark.json) |
| B-320 | PASS | [5953 frames / 300.029 s = 19.841 FPS; detector 5.080 ms; CPU 27.64%](../evidence/phase4/2026-11-10/camera/benchmark.json) |
| C01-BLUE-CENTER | PASS | [Session HSV saturation floor 40: 54/55 detected samples over 12 s](../evidence/phase4/2026-11-10/vision/blue-tuned-center.json.gz) |
| C02-BLUE-LEFT | PASS | [Operator moved physical blue object; locked left candidates retained with coordinates; continuous closed-loop pursuit remains unqualified](../evidence/phase4/2026-11-10/reports/runtime-analysis.json) |
| C03-BLUE-RIGHT | PASS | [Operator moved physical blue object; locked right candidates retained with coordinates; continuous closed-loop pursuit remains unqualified](../evidence/phase4/2026-11-10/reports/runtime-analysis.json) |
| C04-YELLOW-CENTER | FAIL | [Genuine locks occurred, but controlled tuned interval had 0/68 detections; overexposure/low saturation unresolved](../evidence/phase4/2026-11-10/vision/yellow-tuned-center.json) |
| C05-YELLOW-LEFT | BLOCKED | [No complete controlled qualifying run; incidental/background candidates are not credited](../evidence/phase4/2026-11-10/reports/runtime-analysis.json) |
| C06-YELLOW-RIGHT | BLOCKED | [No complete controlled qualifying run; incidental/background candidates are not credited](../evidence/phase4/2026-11-10/reports/runtime-analysis.json) |
| C07-PERSISTENCE | BLOCKED | [No complete controlled qualifying run; incidental/background candidates are not credited](../evidence/phase4/2026-11-10/reports/runtime-analysis.json) |
| C09-MULTIPLE | BLOCKED | [No complete controlled qualifying run; incidental/background candidates are not credited](../evidence/phase4/2026-11-10/reports/runtime-analysis.json) |
| C08-TARGET-LOSS | BLOCKED | [Operator removal was logged in perception; later controlled active sweep could not establish all prerequisites](../evidence/phase4/2026-11-10/vision/blue-live-result.json) |
| C10-NO-TARGET | PASS | [Searching/mask_too_small observations occurred during operator removal; this is perception evidence](../evidence/phase4/2026-11-10/endurance/pi-state.jsonl.gz) |
| C11-STALE | PASS | [Stopped capture owner during blue tracking; stale vision caused disarm/mask zero; recovery stayed disarmed](../evidence/phase4/2026-11-10/safety/camera-fault.json) |
| C12-COLOR-SWITCH | PASS | [Blue/yellow revisions persisted; color changes disarmed and old detector context was replaced](../evidence/phase4/2026-11-10/vision/blue-center.json.gz) |
| D-UDP | PASS | [Observed peer 192.168.1.42 and accepted/rejected traces on Windows LAN receiver](../evidence/phase4/2026-11-10/pybullet/packets.jsonl.gz) |
| D-VUNO | PASS | [Separate virtual Uno accepted forward, rejected disarmed/out-of-range commands, ended disarmed](../evidence/phase4/2026-11-10/udp/pi-protocol-and-tests.log) |
| D-JOINTS | PASS | [Measured armed joint ranges 0.205-0.493 rad; requested ticks separately retained](../evidence/phase4/2026-11-10/reports/runtime-analysis.json) |
| D-DASHBOARD | PASS | [Observed live camera, rates, target mode, decisions, sensors, bridge and output-mask status](../evidence/phase4/2026-11-10/screenshots/pi-dashboard.png) |
| E-STAND | PASS | [Virtual command accepted and STOP mask zero](../evidence/phase4/2026-11-10/autonomy/manual-lan.json) |
| E-FORWARD | PASS | [Virtual command accepted and STOP mask zero](../evidence/phase4/2026-11-10/autonomy/manual-lan.json) |
| E-BACKWARD | PASS | [Virtual command accepted and STOP mask zero](../evidence/phase4/2026-11-10/autonomy/manual-lan.json) |
| E-TURN_LEFT | PASS | [Virtual command accepted and STOP mask zero](../evidence/phase4/2026-11-10/autonomy/manual-lan.json) |
| E-TURN_RIGHT | PASS | [Virtual command accepted and STOP mask zero](../evidence/phase4/2026-11-10/autonomy/manual-lan.json) |
| E-GREETING | PASS | [Virtual command accepted and STOP mask zero](../evidence/phase4/2026-11-10/autonomy/manual-lan.json) |
| F-INVALID | PASS | [Virtual command accepted and STOP mask zero](../evidence/phase4/2026-11-10/autonomy/manual-lan.json) |
| F-UDP-LOSS | PASS | [Observed required short-case assertion; deliberate re-enable between cases; virtual sensors only](../evidence/phase4/2026-11-10/safety/lan-faults.json) |
| F-SIM-RESET | PASS | [Observed required short-case assertion; deliberate re-enable between cases; virtual sensors only](../evidence/phase4/2026-11-10/safety/lan-faults.json) |
| F-SENSOR-STALE | PASS | [Observed required short-case assertion; deliberate re-enable between cases; virtual sensors only](../evidence/phase4/2026-11-10/safety/lan-faults.json) |
| F-OBSTACLE | PASS | [Observed required short-case assertion; deliberate re-enable between cases; virtual sensors only](../evidence/phase4/2026-11-10/safety/lan-faults.json) |
| E-VIRTUAL-TOUCH | PASS | [Observed required short-case assertion; deliberate re-enable between cases; virtual sensors only](../evidence/phase4/2026-11-10/safety/lan-faults.json) |
| E-INTERACTION | PASS | [Observed required short-case assertion; deliberate re-enable between cases; virtual sensors only](../evidence/phase4/2026-11-10/safety/lan-faults.json) |
| E-EXPLORE | PASS | [Explore produced accepted forward before the simulated touch case](../evidence/phase4/2026-11-10/safety/lan-faults.json) |
| E-AVOIDANCE | PASS | [Automated known-geometry/navigation cases passed; this is simulated coverage, not physical sensing or a qualified real-target pursuit](../evidence/phase4/2026-11-10/retest/reports/REG-PY.log) |
| F-STOP | PASS | [Six manual routines ended with output mask zero; observed RTT 125-235 ms](../evidence/phase4/2026-11-10/autonomy/manual-lan.json) |
| F-APP-RESTART | PASS | [Fresh process session 0, disarmed, mask zero, ready handshake](../evidence/phase4/2026-11-10/safety/restart-state.json) |
| F-SIM-PROCESS-RESTART | PASS | [New receiver accepted a disarmed Pi trace; no automatic enable; final mask zero](../evidence/phase4/2026-11-10/safety/final-cleanup.log) |
| F-VIRTUAL-ONLY | PASS | [Runtime physicalActuationAllowed=false, virtual://uno; compilation only; no physical upload/GPIO/PCA9685 operations](../evidence/phase4/2026-11-10/safety/restart-state.json) |
| G-GUI | FAIL | [Initial 3167 s log snapshot; longest fully healthy segment only 560.807 s](../evidence/phase4/2026-11-10/reports/runtime-analysis.json) |
| G-WINDOWS-CONTROL | FAIL | [Stale motion intent at about 6.4 s; attempt interrupted; not a full successful run](../evidence/phase4/2026-11-10/endurance/windows-attempt.jsonl.gz) |
| G-PI-CONTROL | FAIL | [Completed 900.219 s monitoring; unexpected stale front range at 29.625 s; no automatic re-arm](../evidence/phase4/2026-11-10/endurance/pi-headless-result.json) |
| REG-PY | PASS | [163/163 passed; original 160/161 failure retained separately](../evidence/phase4/2026-11-10/retest/reports/REG-PY.log) |
| REG-PI-SUBSET | PASS | [8/8 passed on the actual Pi](../evidence/phase4/2026-11-10/udp/pi-protocol-and-tests.log) |
| REG-UNO | PASS | [Production 10198/998 bytes; virtual 6756/831 bytes; no upload](../evidence/phase4/2026-11-10/reports/uno-production.log) |
| REG-CHECKS | PASS | [All 14 checks passed in the repaired local-checks run](../evidence/phase4/2026-11-10/retest/reports/local-checks.json) |
| VIDEO-SET | BLOCKED | [Genuine USB/GUI captures retained; black dashboard capture and incomplete synchronized/target/endurance demonstrations are explicitly identified](../evidence/phase4/2026-11-10/videos/README.md) |

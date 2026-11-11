# Remediation test matrix

Separate from the unchanged historical 48-case matrix. Test timestamps are recorded in referenced logs; matrix assembly timestamps are metadata only.

{"PASS": 23, "FAIL": 5, "BLOCKED": 23}

| Test ID | Result | Actual observation / evidence |
| --- | --- | --- |
| R-AUDIT | PASS | [104/104 historical manifest hashes match; original staged/unstaged patch hashes unchanged](../reports/performance-analysis.log) |
| R-BASELINE | PASS | [163 Python tests and all 14 existing check-runner cases passed before edits](../baseline/reports/REG-PY.log) |
| R-REGRESSION | PASS | [179 passed, 0 failed in 63.098 s](../final-checks/reports/REG-PY.log) |
| R-CHECKS | PASS | [All 14 check-runner cases passed](../final-checks/reports/local-checks.json) |
| R-CI | PASS | [Python, Python 3.13, Uno jobs succeeded at ff38276; run 42814624459](../reports/ci.json) |
| R-UNO-COMPILE | PASS | [Production 10198 flash/998 global bytes; virtual 6756/831 bytes](../repair-checks/arduino-production.log) |
| R-PREFLIGHT | PASS | [Debian 13.7/aarch64, Python 3.13.5; required imports/camera readable; throttled=0x0; original work preserved](../repair-checks/pi-final-checks.log) |
| R-PI-SUBSET | PASS | [41 run: 39 passed, 2 PyBullet acquisition cases skipped](../preflight/pi-subset.log) |
| R-PI-BROAD | FAIL | [173 run: 163 passed, 6 errors requiring absent Windows-only PyBullet, 4 skipped. Not claimed as passing full Pi suite.](../preflight/pi-regression.log) |
| R-SNAPSHOT | PASS | [Both deterministic concurrency failures reproduced before repair and passed after; genuine expiry retained](../baseline/sensor-race-before.log) |
| R-ACQUISITION | PASS | [Old 200 ms request gap returned 200 ms-old sample; owner cadence repairs acquisition; deterministic test passes](../baseline/acquisition-before.log) |
| R-CACHE | PASS | [Old batch seq stayed 1 after new sample became available; repaired source returns sample 2 at age 21 ms](../repair-checks/batch-cache-after.log) |
| R-UDP-LOSS | PASS | [Old next HELLO delayed 160 ms; repaired deterministic recovery <=81 ms; nonce original expiry retained](../repair-checks/targeted-loss-after.log) |
| R-STOP-ORDER | PASS | [Old deterministic STOP order 2 after disarmed trace 1; repaired ordering passes](../repair-checks/stop-order-after.log) |
| R-INTENT | PASS | [Independent finite renewal survives blocked telemetry; failure/cancel ends renewal; generic heartbeat cannot refresh stale direction](../repair-checks/stop-order-after.log) |
| R-CLOCK | PASS | [GetTickCount64 15.625 ms resolution replaced by monotonic QPC 100 ns for 240 Hz simulator owner](../repair-checks/windows-clock-info.json) |
| R-PREVIEW-IO | PASS | [Actual WinError 5 preserved; error recorded without terminating control; deterministic PermissionError regression passes](../repair-checks/preview-write-failure.log) |
| R-WINDOWS-HEARTBEAT | FAIL | [Stopped at 29.610 s on heartbeat HTTP TimeoutError; no automatic retry or re-arm](../endurance/windows-owned/result.json) |
| R-LAN-90 | PASS | [90.060 s, 407 healthy samples, no unexpected fault](../endurance/robust-smoke/result.json) |
| R-JOINTS | PASS | [876 active source samples; each joint moved 0.220–0.493 rad; maximum source tick 5.139 ms during matched 90 s interval](../reports/healthy-90-joints.json) |
| R-PERFORMANCE | PASS | [Capture mean 8.3317 FPS; vision 8.3311 FPS; CPU 44.46%; RSS 178.70–178.92 MB; sampled front age max 209.6 ms](../reports/healthy-90-performance.json) |
| R-HEADLESS-905 | FAIL | [Failed after 60.943 s; first unhealthy sample at 60.921 s, range age 459.7 ms, ACK age 382.9 ms, intent age 56.8 ms](../endurance/headless-905/result.json) |
| R-HEADLESS-5G-905 | PASS | [905.094 s / 4081 healthy Pi samples; 904.559 s continuous healthy source output; every full 10 s window moved all eight measured joints; no re-arm or journal drop](../endurance/headless-fiveg-905/analysis.json) |
| R-5G-NETWORK | PASS | [Laptop 5 GHz channel 36; Pi power save OFF; Public-profile allow scoped to Pi IP and UDP 7002; fresh handshake observed while disarmed](../reports/network-configuration.json) |
| R-GUI-905 | BLOCKED | [Visible GUI prepared disarmed. User stopped Computer Use with Escape before active GUI qualification. No active GUI endurance claimed.](../reports/operator-interruption.json) |
| R-GUI-CAPTURE | FAIL | [Five-second actual two-window sample: camera/telemetry readable, PyBullet side black. Failed method retained; not a complete integration clip.](../screenshots/gui-capture-sample.png) |
| R-RECOVERY-LATCH | PASS | [Actual failed run stayed disabled; later fresh sensors/bridge and simulator restart remained disarmed; startup explicitly inhibited](../screenshots/recording-sample-v2.png) |
| R-LIVE-FAULT-RETEST | BLOCKED | [Software faults covered by 179-test suite and actual stale-range disarm observed; full new-head active fault sequence not executed after Computer Use was stopped. Historical actual faults retained separately.](../reports/operator-interruption.json) |
| R-V-BLUE-CENTER | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-V-BLUE-LEFT | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-V-BLUE-RIGHT | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-V-BLUE-HORIZONTAL | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-V-BLUE-TEMPORARY-LOSS | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-V-BLUE-PERMANENT-REMOVAL | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-V-BLUE-REAPPEARANCE | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-V-BLUE-MULTIPLE-CANDIDATES | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-V-BLUE-BACKGROUND-DISTRACTORS | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-V-BLUE-COLOR-SWITCH | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-V-YELLOW-CENTER | FAIL | [Timed actual trial 3/19 detected over 8.172 s; 16 contour-shape rejects. Ball bottom clipped. Reposition requested; operator unavailable.](../vision/yellow-center-initial/result.json) |
| R-V-YELLOW-LEFT | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-V-YELLOW-RIGHT | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-V-YELLOW-HORIZONTAL | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-V-YELLOW-TEMPORARY-LOSS | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-V-YELLOW-PERMANENT-REMOVAL | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-V-YELLOW-REAPPEARANCE | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-V-YELLOW-MULTIPLE-CANDIDATES | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-V-YELLOW-BACKGROUND-DISTRACTORS | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-V-YELLOW-COLOR-SWITCH | BLOCKED | [Targets available, but operator could not reposition; no substitute synthetic success claimed. Historical blue results remain historical.](../reports/REMEDIATION.md) |
| R-PURSUIT | BLOCKED | [Physical target matrix and stable LAN are incomplete; 90 s manual movement is not autonomous pursuit](../reports/REMEDIATION.md) |
| R-RECORDING | PASS | [4 s actual viewer, 40 encoded frames at 10 FPS; readable real feed and fault latch. Not a successful tracking/endurance demonstration.](../screenshots/recording-sample-v2.png) |
| R-CLIPS-A-F | BLOCKED | [Only capture-method/fault-latch sample established; full blue/yellow, autonomous, active safety and successful endurance clips remain incomplete](../videos/README.md) |

# Phase 4 qualification — 10 November 2026

## Current remediation result

**PARTIALLY VERIFIED.** [New evidence index](../evidence/phase4/2026-11-10-remediation/README.md) and [remediation report](../evidence/phase4/2026-11-10-remediation/reports/REMEDIATION.md) supersede current-status conclusions while retaining every original failure below.

- Repaired implementation: `ff3827690b635510198d16516237dc77d98013e3`; 179 Windows tests passed, 39 Pi subset tests passed with 2 skips; Python/Python 3.13/Uno CI passed.
- New 5 GHz headless qualification: 905.094 s, 4,081 healthy Pi samples, 904.559 s continuous healthy source output, all eight actual virtual joints moving in every full 10 s window.
- Earlier remediation endurance failed at 60.943 s on genuine stale range; it remains FAIL. The preceding successful 90 s trial is separate.
- New controlled yellow trial: 3/19 sampled frames detected with a clipped ball; not a successful full-outline trial. Physical reposition was unavailable.
- GUI endurance and full synchronized capture remain unqualified. Computer Use was stopped by operator Escape before active GUI testing. CLI cleanup verified STOP and released the webcam.

No safety age/lease threshold was increased; no physical actuator was operated. Current status on 12 November: PR #6 is merged into Phase 3, followed by PR #7. See the [current release report](SENSOR_COMMISSIONING_RELEASE.md). The historical qualification report follows unchanged; its draft-status requirement describes that earlier snapshot.

**PARTIALLY VERIFIED. Phase 4 is not complete; PR #6 must remain draft.**

Tested implementation: `d29dfdbfc42f6f49c0e96837cc53d816bbf8a47e` on
`phase4/pi-hil-qualification`. [PR #6](https://github.com/diyan07-ctrl/Quadruped107/pull/6).
Documentation/evidence commits follow that implementation commit.

Authenticated SSH, Pi preflight, real USB capture, real blue-object detection,
Pi-to-Windows UDP, virtual Uno commands, live dashboard and actual PyBullet joint
motion were executed. Yellow detection was unreliable. The initial GUI and
headless endurance attempts encountered freshness/intent faults and failed
closed. No successful uninterrupted 15-minute autonomous demonstration is claimed.

See the [test matrix](PHASE4_TEST_MATRIX.md), [benchmark](PHASE4_PERFORMANCE.md),
[fault report](PHASE4_SAFETY.md), [remaining issues](PHASE4_REMAINING_ISSUES.md),
and [evidence index](../evidence/phase4/2026-11-10/README.md). Machine-readable
results and original observations are retained alongside these reports.

## Environment and checkout preservation

The Pi authenticated at `192.168.1.42` as `diyan07`. Debian 13.7/aarch64,
Python 3.13.5, OpenCV 4.10.0, NumPy 2.2.4, Flask 3.1.2 and pyserial 3.5 imported.
The initial audit found 1,509 MiB available RAM, approximately 20 GiB free disk,
and `vcgencmd get_throttled` = `0x0`. The USB2.0 PC CAMERA was `/dev/video0`;
the account belonged to `video` and the device was readable.

The original Pi checkout was on Phase 1 with 64 staged changed files. It was
preserved. The missing Phase 4 remote refspec was added, fetched, and a detached
worktree was created at `~/Quadruped107-phase4-qualification`. The original
`.venv-pi-virtual` was reused with `PYTHONPATH=software/pi` selecting the clean
worktree source. No system packages, systemd units or Telegram service were changed.

Global `pip check` reported inherited `apt-listchanges` and typing-stub package
warnings. Flask/pyserial and their active dependencies were separately imported
and checked against their distribution requirements; those application checks passed.

Windows used the working conda-forge Python 3.11.18 environment at
`build/phase4-toolchain/python311/python.exe`. Its installed PyBullet distribution
reported **3.2.5**; the repository/CI pin is 3.2.7. This is an explicit environment
difference, not an assertion that the laptop used the pinned version. The older
`.venv-hil` could not launch from the sandbox. Windows LAN address was
`192.168.1.43`; UDP traffic from the Pi was observed without changing the firewall.

## Executed integration

The real Pi app used USB/V4L2, 320×240, requested 30 FPS, explicit virtual
actuators, virtual simulator sensors and loopback Flask port 7000. Windows
initially ran the GUI receiver on UDP 17012; the headless retest used UDP 7002.
An SSH tunnel exposed the dashboard at `http://127.0.0.1:17000` on Windows.
The evidence includes the exact launch scripts, source and commands.

The GUI rendered the original CAD fixture. The live Pi accepted STAND, FORWARD,
BACKWARD, TURN LEFT, TURN RIGHT and GREETING; STOP cleared its output mask after
each. Measured PyBullet joint ranges across armed samples were 0.464, 0.206,
0.493, 0.240, 0.424, 0.229, 0.479 and 0.205 rad for channels 0–7 respectively.
These are simulated joint measurements, distinct from requested ticks. The
fixed chassis, contacts, masses and joint calibration remain provisional.

The real-camera fault test enabled blue tracking with nonzero virtual outputs,
stopped acquisition, observed `Stale vision result` and mask zero, restarted
acquisition, and verified no automatic re-enable. This injected a capture-worker
failure; it was **not a physical USB unplug**.

## Vision findings

Physical blue and yellow objects were placed and moved by the operator. The
continuous Pi logs contain real blue candidates at center/left/right and missing
target observations. The blue session saturation floor was lowered from 70 to
40 after analysis of the actual low-saturation camera image; 54/55 samples in a
12-second centered interval detected the object. This is a sampled observation,
not ground-truth precision/recall or proof of unique object identity.

The tennis ball was overexposed and intermittently rejected. A session-only
yellow HSV trial `[15,40,70]..[45,255,255]` retained all shape/freshness gates,
but its timed centered trial still produced zero detections in 68 samples.
Later genuine locked yellow observations occurred; they do not turn the failed
trial into a pass. Yellow left/right pursuit, uninterrupted identity persistence
and controlled multiple-object selection remain unqualified. Repository defaults
were not broadened to force acceptance. Color switching itself was executed.

## Repair and regression

The original Windows run passed 160 of 161 tests; simulator re-enable failed
intermittently after reset. A deterministic regression demonstrated that a bridge
guard could read an old fault, then stop a later explicit enable. The repair
samples the motion generation before bridge health and passes it to STOP. A
stale observation cannot affect a newer generation; current faults still stop.

Before/after regression logs are preserved. The repaired suite passed **163/163**,
including both new guard regressions. CAD generation, gait data, power tables,
simulation validation, model study, navigation proxy, dashboard DOM, JavaScript,
Mermaid and repository checks passed. Both Uno sketches compiled with Arduino
CLI 1.5.1: production 10,198 bytes flash / 998 bytes globals; virtual 6,756 / 831.
Neither was uploaded. [Implementation CI passed](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42767613972).

The local repaired run recorded the previous HEAD while the fix was uncommitted;
the linked CI subsequently verified the frozen `d29dfdb` implementation. The
actual Pi also passed eight preflight/telemetry subset tests on Python 3.13.5.

The final Pi-owned headless monitoring run completed **900.219 s**, with 788
samples. An unexpected stale-front-range stop occurred at **29.625 s**; the
runner did not re-arm. Camera/vision reported means were 8.322/8.332 FPS, CPU
35.324% of one core, RSS 164.4–165.6 MiB, camera errors zero and bridge error
increments zero within that window. There was no recorded HTTP exception in
that Pi-local run. This is a completed **failed** endurance test, not a successful
15-minute motion run. The interrupted Windows-owned attempt separately stopped
on stale motion intent after about 6.4 s and was not credited as full duration.

The simulator process was subsequently restarted and a new disarmed trace was
accepted over LAN. Final STOP showed `enabled=false`, `armed=false`, mask zero
and physical actuation prohibited. Qualification application/simulator processes
were then shut down and the webcam released; original user services were left alone.

## Acceptance decision

Freshness failures remain release blockers. Successful reconnects, new camera
frames and returned targets did not automatically enable motion. Dashboard
tunnel interruptions and failed endurance attempts are retained, not erased.
The final endurance result and statistics are in the evidence index/matrix.

**Do not begin powered Phase 5 actuator qualification on this evidence.**
Unpowered inspection and planning may continue. Repair/replace the suspected
PCA9685 and separately qualify power, fusing, disconnect/OE, Uno watchdog,
sensing and supported mechanical calibration under the existing hardware plan.
No physical actuator, physical sensor accuracy, walking or electrical stopping
claim is established by Phase 4.

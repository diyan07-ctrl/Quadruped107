# Phase 4 remediation qualification

**PARTIALLY VERIFIED. Physical outputs remain prohibited. PR #6 stays draft.**

This report is separate from the unchanged [original qualification](../../2026-11-10/README.md).
Its 38 PASS / 4 FAIL / 6 BLOCKED results, yellow 0/68 trial, 29.625 s sensing
failure, 6.4 s Windows intent failure and failed endurance remain historical
observations. The historical manifest was checked again: **104/104 hashes match**.

Runtime under final software verification: `ff3827690b635510198d16516237dc77d98013e3`.
Existing branch: `phase4/pi-hil-qualification`; [draft PR #6](https://github.com/diyan07-ctrl/Quadruped107/pull/6).
Initial remediation audit confirmed local/PR head `1cb9a0e`, before changes.
The original Pi checkout remains at `a15c397` with its staged work preserved;
the isolated `~/Quadruped107-phase4-qualification` worktree was used.

## What was proved and repaired

| Issue | Proven defect / repair | Before and after evidence |
| --- | --- | --- |
| Safety snapshot race | `SensorManager.snapshot` obtained time before its lock. A concurrent sample could appear future-dated; waiting for the lock could hide real expiry. Read time inside the same locked snapshot. | [Failing deterministic cases](../baseline/sensor-race-before.log), [repaired regressions](../repair-checks/stop-order-after.log) |
| Sensor acquisition tied to requests | Virtual range acquisition was driven by UDP telemetry encoding. A 200 ms request gap returned the preceding 200 ms-old sample despite a configured 10 Hz sensor. Acquire on the physics-owner cadence. | [Before](../baseline/acquisition-before.log), [targeted tests](../repair-checks/targeted-final.log) |
| Old cached range batch | A newly available sample could remain hidden behind the 50 ms telemetry cache. Invalidate the batch when available range sample identifiers change; preserve original sample age. | [Before](../baseline/batch-cache-before.log), [after](../repair-checks/batch-cache-after.log) |
| Slow single-loss recovery | One lost HELLO/challenge/trace/ACK caused a full challenge-timeout wait. Retry HELLO every 50 ms; reuse the outstanding nonce with its original birth/expiry and retransmit the same bounded trace. | [Before: 160 ms gap](../baseline/loss-recovery-before.log), [after: <=81 ms](../repair-checks/targeted-loss-after.log) |
| STOP/re-enable ordering | A STOP occurring during `recvfrom` could be emitted after a disarmed handshake, invalidating a new explicit ARM. Detect that transition before dispatching a disarmed trace. | [Failing order](../baseline/stop-order-before.log), [passing order](../repair-checks/stop-order-after.log) |
| Windows pacing resolution | This Windows Python exposes `monotonic` through GetTickCount64 at 15.625 ms resolution, unsuitable for 4.167 ms ticks. Use monotonic QPC `perf_counter` for simulator scheduling and its receiver/source clock. | [Clock properties](../repair-checks/windows-clock-info.json), [actual 90 s source timing](healthy-90-joints.json) |
| Qualification heartbeat coupling | Old instrumentation renewed intent on the same thread as blocking state requests and cookie-file writes. Use finite independent matching-intent renewal, ending on deadline, cancellation or any failed renewal. It never sends ARM. | [Deterministic intent tests](../repair-checks/stop-order-after.log), [90 s live result](../endurance/robust-smoke/result.json) |
| Optional preview file crash | A real Windows `WinError 5` replacing `latest.json` killed the HIL source. Record optional preview-write errors in the journal without terminating the control/physics loop. Required final results remain explicit writes. | [Original traceback](../repair-checks/preview-write-failure.log), [179-test suite](../final-checks/reports/REG-PY.log) |

The changed production locations are `software/pi/quadruped/sensors.py`,
`controller.py`, `bridge.py`, `simulation/environment.py` and `simulation/twin.py`.
Instrumentation is in `tools/phase4-hil.py`, `hil_lease.py`, `phase4-vision-study.py`
and the read-only `phase4-live-view.py`. Regression coverage is in
`tests/test_phase4_remediation.py`. No firmware motion, wiring, gait or physical
driver feature was added.

These are reproducible defects, **not proof that each caused the historical
29.625 s event**. That event lacks the new per-measurement trace. Likewise, the
historical Windows 6.4 s stop lacks enough heartbeat-body/timing evidence to name
its exact cause. The old errors are retained rather than retrospectively relabeled.

## Actual integration results and remaining transport failure

The first instrumented sensor trial still failed at 0.644 s: true front age was
314 ms (sender age + conservative locally measured RTT bound + receiver elapsed
time). Camera and packet receive ages alone were insufficient. A later Pi-local
trial failed at 1.698 s on genuine range expiry. Both stopped safely.

After the acquisition, cache, transport and ordering repairs, a **90.060 s**
Pi-owned trial passed with **407 healthy samples**. The actual Pi webcam,
OpenCV, controller, virtual Uno, LAN UDP and eight measured PyBullet joints were
active. This was held manual forward movement, **not autonomous ball pursuit**.

Measured virtual joint ranges for channels 0–7 were **0.464, 0.223, 0.493,
0.241, 0.484, 0.229, 0.479, 0.220 rad**. There were 876 active source physics
samples in the matched interval; maximum source tick was 5.139 ms.
[Joint evidence](healthy-90-joints.json) matches Pi-logged source acquisition
timestamps to that same Windows monotonic clock. It does not subtract clocks
from different machines or equate requested targets with actual motion.

The following **905 s attempt failed at 60.943 s**. First unhealthy sample:
front age **459.7 ms**, ACK age **382.9 ms**, intent age **56.8 ms**.
The controller disarmed and stayed disarmed. This is **FAIL**, not 15 minutes of
healthy movement. [Full result](../endurance/headless-905/result.json).
The source trace shows a **567 ms incoming-packet gap**, followed by queued HELLO
packets, while physics tick maxima stayed about **4.6 ms** through that gap.
[Source event](../repair-checks/headless-source-event.json). This rules out a
physics-owner stall for that reproduced event; the exact radio/driver/AP origin
of buffering is not established.

A separate Windows-owned run failed at **29.610 s** after an SSH-tunnel HTTP
heartbeat timeout. Its finite renewal worker stopped rather than retrying or
silently restoring motion. [Result](../endurance/windows-owned/result.json).
This is distinct from the Pi-local stale-range event.

Pi Wi-Fi power saving was observed ON, then the operator set it OFF with
`sudo /usr/sbin/iw dev wlan0 set power_save off`; OFF was authenticated and
verified. This alone did not eliminate the later 60.943 s failure. The laptop
was on 2.4 GHz while the Pi was on 5 GHz. The operator subsequently connected
the laptop to 5 GHz, channel 36, 866.7 Mbps, retaining its LAN address.
The new Windows network profile was Public. Its existing executable allow rules
were Private-only. An administrator-elevated rule was added permitting only
Pi `192.168.1.42` to laptop `192.168.1.43` UDP port 7002 on Public. Fresh UDP
handshake was then observed while the controller remained disarmed.

Bulk historical log transfers were stopped before the separate 5 GHz endurance
trial to avoid measuring a deliberately saturated network. An earlier GUI
process exited without a normal result while disarmed; its idle lifetime is
not a GUI endurance pass.

### Successful separate 5 GHz headless qualification

The new trial completed **905.094 s with 4,081 healthy Pi samples** and no
automatic re-arm or journal drop. Matching actual source records establishes
**904.559 consecutive seconds of healthy simulator output**, exceeding the
900 s gate. All eight measured joints moved in every complete 10 s window.
The acquisition-aligned envelope includes two initial boundary records before
active output (one disarmed and one armed/mask zero); they are excluded from
the 904.559 s active interval rather than hidden or counted as movement.
[Complete result](../endurance/headless-fiveg-905/result.json),
[full-duration analysis](../endurance/headless-fiveg-905/analysis.json).

| Measure | Successful 905 s trial |
| --- | --- |
| Capture / vision mean | 8.330 / 8.340 FPS |
| Camera age p95 / maximum | 235.6 / 254.5 ms |
| Front-range age p95 / maximum | 175.9 / 243.0 ms |
| Intent age maximum | 111.4 ms |
| ACK age maximum | 119.4 ms |
| Process CPU mean / maximum, one-core basis | 44.26 / 52.33% |
| RSS minimum / maximum | 178.84 / 179.25 MB decimal |
| Maximum physics tick interval | 61.43 ms |
| Bridge error increment / source rejected datagrams | 0 / 1 |
| Duplicate/out-of-order sensor batch rejections | 1,920 |

Repeated cached batch identifiers are still rejected, rather than refreshing
old measurements. The 1,920 counter increments all have that rejection reason;
they are not falsely reported as zero transport anomalies or counted as new
acquisitions. Individual fresh sample identifiers and original ages continued
to advance. One source datagram was rejected; the full trace retains it.
The combined repaired software/5 GHz/Pi power-save-OFF configuration passed
this run. These changes were not isolated in a controlled radio A/B experiment,
so the result does not uniquely identify the radio-level cause of the old gaps.

The separate visible-GUI 900 s gate remains **BLOCKED**. A genuine two-window
recording sample displayed the camera correctly but recorded a black PyBullet
side. Before further GUI input or active GUI testing, Computer Use was stopped
by the operator's physical Escape key. UI/recording work stopped; no active
GUI endurance result or complete synchronized clip is claimed. Safe STOP,
application shutdown and webcam release were subsequently verified through CLI
cleanup only. [Interruption](operator-interruption.json),
[failed capture sample](../screenshots/gui-capture-sample.png),
[shutdown evidence](../safety/shutdown.log).

## Real yellow target investigation

The operator declared yellow centered. The timed real-camera trial observed
**3/19 sampled frames detected over 8.172 s**, with 16 `no_circular_candidate`
rejections. The raw images show the ball's bottom outside the 320×240 frame.
This does not establish controlled full-outline centered detection.
[Actual frames, masks and overlays](../vision/yellow-center-initial/frame-001-comparison.png),
[trial JSON](../vision/yellow-center-initial/result.json).

A manually declared interior circular ROI (center 154,198; radius 40 pixels)
had hue median **33**, saturation median **80**, value median **246**;
**43.95%** of ROI pixels had V >=250. Hue percentiles 10/25/50/75/90 were
30/30/33/35/37. Thus clipping and weak/overexposed color mask regions are actual
observations, rather than a claim that hue is outside the yellow preset.
[Statistics and offline experiments](../vision/yellow-center-initial/roi-analysis.json).

Offline saturation-floor experiments on the actual saved JPEG-derived images
improved candidate acceptance at S=50 in two representative frames. This is
**offline diagnosis**, not a successful controlled physical trial, unique
tennis-ball classification, or justification to relax contour safeguards.
Production HSV defaults, circularity/size gates, locking and blue presets were
not broadened. The initial endpoint stored decoded JPEG originals; the later
endpoint also provides lossless raw PNG from the same actual frame.

The operator could not reposition the ball when asked for a complete 60–80 pixel
outline. Controlled blue/yellow left/right, motion, disappearance, reappearance,
multiple-object, distractor and color-switch trials therefore remain BLOCKED.
The historical blue 54/55 observation is not substituted for a new-head test.
Real target-controlled steering and target-loss recovery with actual joint
motion remain unqualified.

## Performance and environment

| Measure | Successful 90 s interval |
| --- | --- |
| Capture FPS, mean / min / max | 8.3317 / 8.25 / 8.40 |
| Vision FPS, mean / min / max | 8.3311 / 7.83 / 8.74 |
| Camera age, mean / maximum | 181.0 / 245.3 ms |
| Individual front range age, mean / maximum | 116.2 / 209.6 ms |
| Intent age, mean / maximum | 80.6 / 102.1 ms |
| ACK age, mean / maximum | 35.4 / 99.9 ms |
| Pi process CPU, mean / maximum | 44.46 / 51.07% of one core |
| Pi RSS minimum / maximum | 178.70 / 178.92 MB (decimal) |

[Machine-readable statistics](healthy-90-performance.json). These are sampled
state measurements, not a promise about unobserved instantaneous peaks.
Instrumentation overhead differs from the historical benchmark.
The current dim scene remains approximately 8.3 FPS versus historical bright
19.84 FPS. The camera advertises **YUYV only**, not MJPEG. Available V4L2 controls
do not expose qualified manual exposure/white-balance settings. Scene dependence
is observed; exposure integration time and driver-level frame drops remain
unmeasured. Processing FPS, capture FPS and encoded recording FPS are separate.

Pi: Debian 13.7/aarch64, Python 3.13.5, OpenCV 4.10.0, NumPy 2.2.4, Flask 3.1.2,
pyserial 3.5. Windows: Python 3.11.18, OpenCV 4.11.0, PyBullet metadata **3.2.5**.
CI pins **3.2.7**. Both environments pass their applicable checks; no evidence
establishes that this version difference caused the WLAN buffering, so it was
not changed during this investigation. Physics timestep stays **1/240 s**.

## Software, safety and recording acceptance

Unchanged baseline: **163 passed** before edits. Final repaired Windows suite:
**179 passed / 0 failed**. All 14 runner checks passed. Actual Pi selected suite:
**41 run, 39 passed, 2 PyBullet acquisition tests skipped**. An exploratory broader
Pi run had 173 tests: 163 passed, 6 errors requiring absent Windows-only PyBullet,
4 skipped; its failure log is preserved and is not presented as a passing suite.
Both Uno sketches compiled without upload. [Current-runtime CI: Python, Python
3.13 and Uno passed](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42814624459).

Deterministic regressions retain stale individual measurements in fresh packets,
packet loss/order rejection, restart, concurrent evaluation, invalid/missing
ranges, explicit recovery, repeated identical fresh distances and stale intent
inhibition. Challenge TTL 150 ms, bridge lease 300 ms and sensor expiration
300 ms were not increased. STOP precedence and explicit re-enable remain intact.

Actual reproduced range expiry safely stopped movement. Subsequent fresh data
and reconnection did not re-arm it. The successful 90 s interval ended with an
explicit STOP. No physical Arduino/PCA9685/servo API was used. Electrical
power/OE inactivity was not independently measured; virtual-only software
inhibition is not physical electronics qualification.

An exploratory invalid-mode HTTP request returned **409** at the stale-sensor/
control precondition rather than the harness's expected 400 mode-validation
response. Its [saved result](../repair-checks/invalid-live.json) is retained.
It demonstrates inhibited dispatch in that state, not a completed new-head
semantic invalid-command test under healthy armed preconditions.

A genuine four-second native viewer capture was validated: 40 encoded frames
at 10 FPS, showing actual camera/telemetry and a latched fault. It is a
capture-method/fault-latch sample, not the requested successful six-clip set.
The original GDI attempt failed on odd height; padded encoding succeeded. The
native viewer uses Tk because the installed OpenCV wheel is headless. No
fabricated animation or success overlay was created. Large media/runtime traces
are kept outside normal Git history with release links and hashes in the index.

## Reproduction and next acceptance action

Use `tools/phase4-ssh.py` to run the reviewed scripts retained in evidence logs.
Its commands use existing noninteractive SSH, never private-key contents.
Launch the Windows source with `tools/phase4-hil.py twin --host 192.168.1.43
--port 7002 --seconds 14400 --output <unique-directory>`; add `--gui` only for the
separate GUI trial. Run the Pi application with `pi`, actual USB camera and
explicit virtual outputs, then Pi-local `run --seconds 905` with a unique output
directory. The collector stops on the first unhealthy sample and sends STOP;
never concatenate failed intervals or automatically restart after faults.

Before Phase 4 completion, retain the successful headless interval and obtain
the separate healthy 900-second active GUI interval, finish the controlled physical target matrix and
autonomous pursuit/fault demonstrations, then publish the complete genuine
recording set. **Do not begin powered Phase 5 qualification on the present
evidence.** The suspected PCA9685, supply/OE, local watchdog, physical sensors
and mechanical gates remain separate unqualified work.

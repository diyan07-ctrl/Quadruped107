# Phase 4 remaining issues

## Current remaining acceptance work

The [remediation report](../evidence/phase4/2026-11-10-remediation/reports/REMEDIATION.md) proves a successful separate 905 s headless trial after acquisition, snapshot, cache, transport and STOP-order repairs and a qualified 5 GHz setup. Do not reinterpret the historical failures below as passes.

1. Complete the separate visible-GUI 900 s healthy active run; operator Escape stopped Computer Use before it began.
2. Resolve black PyBullet capture in the two-window recording sample and complete genuine demonstration clips. No further UI input was issued after the stop.
3. Reposition the real yellow ball fully inside the frame; complete controlled blue/yellow center/left/right/motion/loss/reappearance/multiple-candidate/distractor/switch trials. Current yellow trial was 3/19, clipped; offline saturation experiments are not physical success.
4. Demonstrate real target-controlled autonomous decisions with separately measured virtual joint motion, then repeat the full active safety/fault sequence on the final network setup. Synthetic and old-head tests do not substitute for these gates.
5. Preserve the qualified setup: Pi radio power-save OFF is a runtime setting; laptop 5 GHz and a Pi-only Public-profile UDP 7002 rule were verified. The successful combined configuration does not uniquely identify the old radio buffering cause.
6. Repeat the Windows-owned finite remote-heartbeat trial on the final 5 GHz setup. Its earlier 29.610 s SSH-tunnel timeout remains FAIL; the successful Pi-owned run establishes local healthy intent renewal, not remote HTTP reliability.

The uncurated broad Pi attempt had six missing-PyBullet errors; the selected application subset passes 39 tests with two intentional Windows-only acquisition skips. The Windows suite passes all 179. PyBullet remains local 3.2.5 versus CI 3.2.7, explicitly documented. Powered Phase 5 remains unapproved.

### Historical remaining-issues assessment

1. **Release blocker — sustained virtual sensing.** GUI and headless operation
   intermittently exceeded front-range freshness. The receiver/host failed closed.
   The first fully healthy contiguous interval was only 560.807 s. The Pi-local
   heartbeat retest completed 900.219 s of monitoring but disarmed at 29.625 s
   on stale front range and remained disarmed. Establish the
   network/scheduling/sensor-acquisition age cause, preserve current age/lease
   bounds, and rerun a clean full-duration integration test. Do not increase
   freshness limits simply to make it pass.
2. **Release blocker — yellow vision matrix.** Overexposure/low saturation caused
   intermittent rejection. A session HSV trial did not establish reliable centered
   detection or confirmed left/right pursuit. Qualify controlled, reproducible
   lighting and repeat both colors, full-outline left/right/center, disappearance,
   moving-target persistence and multiple candidate objects with genuine video.
3. **Incomplete end-to-end autonomy.** Blue candidates were observed at all three
   horizontal positions and real blue tracking produced virtual output, but
   sustained closed-loop left/right pursuit and target-loss motion recovery have
   not all been verified with controlled physical targets. Keep these distinct
   from passing synthetic integration and manual LAN movement.
4. **Dashboard transport.** Tool-hosted SSH tunnels suffered resets/timeouts while
   the Pi app continued. A dedicated hidden tunnel and Pi-local test heartbeat
   avoid depending on that session for control, but do not solve the independent
   virtual-sensor freshness issue. Preserve explicit recovery.
5. **Camera limitations.** The webcam advertises 15/30 FPS YUYV yet delivered about
   19.84 FPS in the bright benchmark and about 8.3 FPS in a darker live scene.
   Exact exposure/driver causes and driver-level dropped frames are unmeasured.
   Current camera settings expose no qualified exposure-time measurement.
6. **Evidence gaps.** Camera/host recordings and full logs exist, but the seven
   requested complete synchronized demonstration clips were not all produced.
   A failed/partial clip is not a successful demonstration. The evidence index
   identifies each recording and its limitations.
7. **Environment difference.** Local Windows PyBullet reports 3.2.5; CI is pinned
   to 3.2.7. Do not silently equate the environments. Pi uses its existing system
   OpenCV/NumPy and isolated project environment.
8. **Physical work remains unqualified.** Suspected PCA9685 damage, power/fusing,
   battery and regulator qualification, OE/disconnect, local Uno watchdog and
   sensor acquisition, mechanical calibration and supported stopping remain
   separate Phase 5 gates. No physical movement was tested.

The repaired stale guard-generation race is closed by deterministic before/after
evidence and the 163-test suite. It does not close the remaining runtime issues.

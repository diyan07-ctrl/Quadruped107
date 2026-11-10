# Phase 4 remaining issues

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

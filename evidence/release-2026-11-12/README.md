# Final stabilization evidence — 12 November 2026

**SOFTWARE READINESS PARTIAL. Evidence collection in progress.**

Integration `488b837` preserves PR #7 merge `6e0d578` and main `f625250`. Implementation checkpoint `9fe42b1` is the Pi archive source. The [release report](../../docs/SENSOR_COMMISSIONING_RELEASE.md) and [sensor bench instructions](../../docs/SENSOR_BENCH.md) define the non-actuating scope. No firmware upload, real serial-device access, PCA, servo power or physical PWM was performed.

Executed so far: integrated 215-test baseline, 221-test regression, 14 local checks after checkout/dependency correction, 12 native firmware executables and 10 AVR builds. Original failed attempts remain retained in the local `build/release` collection and will be frozen here with exact source/environment/log identities before final review.

The real Pi is reachable using its existing Python 3.13.5 environment. Six selected test modules pass from an isolated `/tmp` source directory. Its original staged work/status and binary diff hashes are unchanged. A real USB camera and disarmed virtual output are running for operator-requested image capture. Live image failure/false-target observations are separate from offline regression results.

Visible OpenGL foreground capture shows the robot. An initial passive disarmed trial failed on simulated joint limits; a separate 28800-step disarmed run completed. Neither qualifies active GUI endurance. Browser capture encountered a URL-verification tool blocker. Live tracking success, coordinated final-head active endurance and physical sensor/display qualification are not asserted.

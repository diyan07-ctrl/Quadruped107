# Phase 4 performance measurements

All values below came from the real Pi USB webcam on 10 November 2026. Raw data:
[benchmark JSON](../evidence/phase4/2026-11-10/camera/benchmark.json),
[full log](../evidence/phase4/2026-11-10/camera/benchmark.log),
[V4L2/environment audit](../evidence/phase4/2026-11-10/preflight/pi-audit.log).

The benchmark ran from the original Pi checkout (`a15c397` plus its preserved
staged Phase 4 overlay), before the isolated integration worktree was launched.
[Source provenance](../evidence/phase4/2026-11-10/environment/pi-source-provenance.log)
confirms its detector blob exactly matches Phase 4 (`110ffb83241941b63006b24477a378f9f3a583d6`).
The benchmark script itself was subsequently committed in `d29dfdb`; its complete
executed source is retained in `camera/start.log`. The benchmark was not executed
from an otherwise clean `d29dfdb` checkout.

| Resolution | Request | Duration | Successful reads | Failed reads | Capture FPS | Detector mean | Read mean / p95 | Process CPU |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 640×480 | 8 FPS | 20.015 s | 388 | 0 | 19.386 | 13.807 ms | 37.748 / 54.100 ms | 70.32% |
| 640×480 | 30 FPS | 300.008 s | 5,952 | 0 | 19.839 | 15.324 ms | 35.066 / 52.211 ms | 78.21% |
| 320×240 | 30 FPS | 300.029 s | 5,953 | 0 | 19.841 | 5.080 ms | 45.304 / 60.819 ms | 27.64% |

CPU uses process CPU seconds / monotonic wall seconds ×100 (one-core basis).
Peak process high-water RSS was approximately 137 MiB, not a current RSS trend.
Resources were sampled every five seconds. Driver-level dropped frames were not
available through OpenCV; zero failed reads does not establish zero USB drops.

The standalone loop processes every successful read, so observed detector
throughput equals the acquisition-loop FPS by construction. Detector compute
capacity is reported separately in JSON; it is **not camera FPS**. The live app
has separate capture and vision workers and records their rates independently.
Its darker-scene readings later fell to approximately 8.3 capture/vision FPS;
the faster bright-scene benchmark must not be presented as all-scene performance.

V4L2 advertised **YUYV only**, with 15/30 FPS intervals at both tested sizes.
It did not advertise MJPEG. Requesting 8 FPS reported 15 FPS, while measured
successful delivery was about 19.4 FPS. Requested/reported intervals are therefore
not accepted as measurements. Both sizes delivered about 19.84 FPS when asked
for 30; reducing detector cost did not improve acquisition rate. Lighting
changes correlated with delivery changes, but exposure timing/unique exposures
were not instrumented and the exact camera/driver limitation remains unresolved.
No unsupported MJPEG mode or higher rate is claimed.

320×240 was selected for integration because detector time fell about 67% and
process CPU about 65% relative to 640×480 in these runs. This was a launch
configuration choice; no interlock was weakened. Default one-buffer YUYV capture
was retained. No physical camera performance claim derives from synthetic tests.

Capture timings use local monotonic clocks. `read_mean_ms` includes the blocking
OpenCV read, not sensor exposure-to-host latency. STOP request/observed-mask RTTs
were 125–235 ms on the Windows manual probe. Camera-worker fault injection to
observed output-off was 1,146 ms, including the instrumentation's one-second
control-file polling interval; that is not a camera-disconnect safety deadline.
No unsynchronized cross-machine one-way latency was calculated.

The benchmark implementation initially named its completion timestamp
`started_utc`; interpret that field as interval completion for this preserved
run. Duration is the correctly measured monotonic interval. Script launch time
is independently retained in `camera/start.log`. The current tool separately
records `started_utc` and `ended_utc`; the original data has not been relabeled.

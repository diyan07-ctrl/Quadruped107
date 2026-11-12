# Phase 4 evidence — 2026-11-10

**PARTIALLY VERIFIED.** Tested implementation:
`d29dfdbfc42f6f49c0e96837cc53d816bbf8a47e`.
[PR #6](https://github.com/diyan07-ctrl/Quadruped107/pull/6) remains draft/unmerged.

- [Qualification report](../../../docs/PHASE4_VALIDATION.md)
- [Complete test matrix](../../../docs/PHASE4_TEST_MATRIX.md), [JSON](reports/test-matrix.json), [CSV](reports/test-matrix.csv)
- [Performance](../../../docs/PHASE4_PERFORMANCE.md) and [benchmark JSON](camera/benchmark.json)
- [Safety/fault report](../../../docs/PHASE4_SAFETY.md)
- [Remaining issues](../../../docs/PHASE4_REMAINING_ISSUES.md)
- [Recording index and limitations](videos/README.md)

## Evidence organization

| Directory | Contents |
| --- | --- |
| `environment/` | Timestamped Windows dependency/status snapshots and actual Pi app instrumentation source. |
| `preflight/` | Authenticated Pi audit, V4L2 modes, isolated checkout/refspec repair, preflight JSON and application dependency checks. The first quoted-shell attempt's error is retained. |
| `camera/` | Five-minute real USB tests at both resolutions, complete source/launch and measured read/processing/resource samples. No synthetic frames. |
| `vision/` | Physical-target observations, rejected/default and tuned trials, real-JPEG HSV analysis, failed controlled tracking attempt. A candidate is not guaranteed unique ball identity. |
| `udp/` | Pi virtual protocol acceptance/rejection, eight Pi subset tests, original edit-preservation hashes and pre-fix recovery tracing. |
| `pybullet/` | Instrumentation source and compressed receiver/joint traces; actual joint positions are separate from requested ticks. Sensors/world remain simulated. |
| `autonomy/` | Actual Pi/LAN virtual manual routines and command/STOP observations. |
| `safety/` | Deterministic guard failure/retest, short LAN fault cases, camera acquisition-stop and restart evidence. |
| `endurance/` | Original Pi full-duration logs, interrupted Windows-owned attempt, completed 900.219 s Pi-owned **failed** retest, statistics and source. |
| `screenshots/` | Genuine Pi camera and live Windows GUI/dashboard captures. Rejected observations retain their failure meaning. |
| `videos/` | Durable release links, hashes and honest clip limitations. Media binaries are release assets. |
| `reports/` | Before/after automated checks, both Uno compile logs, matrix and derivation scripts. |

`.jsonl.gz` and `.log.gz` are gzip-compressed original text logs. Uncompress with
Python's `gzip.open(path, 'rt')`; each JSONL line is one observation. Large JSON
observation arrays are similarly compressed to avoid redundant multi-megabyte
text. The manifest gives SHA-256 hashes. Source scripts make derivation reviewable.

## Measurement and acceptance limits

Real webcam capture was 19.839/19.841 FPS in the five-minute bright tests.
In the darker 900.219 s Pi-controlled retest, reported capture averaged 8.322
FPS and vision 8.332 FPS; CPU averaged 35.324% of one core, RSS approximately
164.4–165.6 MiB. There were zero failed camera reads/owner errors and zero bridge
parse/error increments in that window. At 29.625 s the controller had disarmed
on stale virtual front range; it stayed disarmed. The monitoring period
completed, **the stability acceptance test failed**. See
[statistics](endurance/statistics.json) and [outcome](endurance/pi-headless-result.json).

No synthetic test is credited as physical target verification, virtual ray/touch
telemetry is not physical sensor evidence, and PyBullet joint motion is not
physical servo motion. No cross-machine one-way latency was inferred from UTC
timestamps. Source-local durations use monotonic clocks. STOP timings include
API/observation overhead, and file-driven injections include polling delay.

The original Pi staged and unstaged patch hashes remained identical. Its checkout,
system packages, SSH service and Telegram notification service were preserved.
Only the public-key authorization handoff, Phase 4 fetch configuration and
isolated qualification artifacts were added. No physical actuator was activated.

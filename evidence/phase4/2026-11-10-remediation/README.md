# Phase 4 remediation evidence — 10 November 2026

**PARTIALLY VERIFIED. Virtual actuators only. PR #6 remains draft.**

The new 5 GHz headless qualification passed: **905.094 s**, 4,081 healthy Pi
samples, **904.559 s continuous healthy source output**, and measured movement
of all eight joints in every full 10 s window. The separate GUI endurance,
controlled physical blue/yellow matrix, autonomous pursuit and complete
recording set remain unqualified. Computer Use was stopped by the operator
with Escape before active GUI qualification.

- [Full remediation report](reports/REMEDIATION.md)
- [51-case matrix: 23 PASS / 5 FAIL / 23 BLOCKED](reports/TEST_MATRIX.md)
- [Machine-readable JSON](reports/test-matrix.json) and [CSV](reports/test-matrix.csv)
- [Successful headless result](endurance/headless-fiveg-905/result.json) and [analysis](endurance/headless-fiveg-905/analysis.json)
- [Earlier failed 905 s attempt, stopped at 60.943 s](endurance/headless-905/result.json)
- [Successful 90 s trial](endurance/robust-smoke/result.json)
- [Real yellow raw frame / mask / annotated comparison](vision/yellow-center-initial/frame-001-comparison.png)
- [Actual Pi preflight](preflight/preflight.json), [39 passing Pi subset tests / 2 skips](preflight/pi-subset.log)
- [179 passing Windows tests](final-checks/reports/REG-PY.log), [all 14 checks](final-checks/reports/local-checks.json)
- [Runtime CI](reports/ci.json), [current-run workflow](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42814624459)
- [Operator interruption](reports/operator-interruption.json), [final STOP state](safety/final-before-shutdown.json), [shutdown/webcam release](safety/shutdown.log)

Tested production implementation: `ff3827690b635510198d16516237dc77d98013e3`.
Per-case implementation differences and execution commands are in the JSON
matrix and timestamped logs. Matrix assembly timestamps are not substituted
for execution timestamps. SSH wrapper logs retain the exact shell source.
The analyzer is committed at `tools/phase4-analyze-run.py`.

The [original evidence](../2026-11-10/README.md) is unchanged: 104/104 manifest
hashes matched during remediation. Original failures are not reclassified.
The original Pi staged and unstaged patch hashes matched at final shutdown.
No SSH configuration, Telegram service, battery wiring or physical actuator
operation was changed by this remediation.

## Durable large artifacts

[Remediation release](https://github.com/diyan07-ctrl/Quadruped107/releases/tag/phase4-remediation-evidence-2026-11-10)
contains the full compressed headless samples, Windows UDP/physics traces,
closed Pi runtime logs and genuine recording samples. These are outside normal
Git history. [Archive URL and SHA-256](reports/archive.json),
[per-file hashes and sizes](reports/artifacts.json).

After extracting the ZIP into `build/phase4-remediation/public-artifacts`, its
`endurance/headless-fiveg-905/samples.jsonl.gz` is the full-duration Pi state log.
`pybullet/twin-fiveg/trace.jsonl.gz` is the corresponding full source trace,
including idle time outside qualification. Only the independently matched
904.559 s interval counts toward acceptance. To rerun the analyzer, decompress
the latter into `build/phase4-remediation/twin-fiveg/trace.jsonl` and run:

~~~text
python tools/phase4-analyze-run.py headless-fiveg-905 twin-fiveg
~~~

The cancelled bulk transfer of the large `pi-v4` idle/runtime log was incomplete;
its [status](reports/interrupted-transfer.json) is retained. The partial copy
was excluded from the archive. Its full source remains on the Pi, and complete
state/result logs for every executed qualification attempt were separately
preserved. [Media details](videos/README.md).

Terminal logs in this directory were transcoded to UTF-8 where PowerShell had
written UTF-16; observed text, warnings and failures were retained. No control
cookies, private keys, passwords or tokens are included.

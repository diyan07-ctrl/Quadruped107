# Genuine recording evidence and limitations

Media is in the [remediation archive](https://github.com/diyan07-ctrl/Quadruped107/releases/tag/phase4-remediation-evidence-2026-11-10).
Encoded recording FPS is not camera acquisition FPS.

| File inside archive | Actual content | Result |
| --- | --- | --- |
| `videos/viewer-fault-latch-sample.mp4` | Four seconds, 40 encoded frames at 10 FPS. Actual Pi feed, telemetry and latched sensor fault. Readable native viewer capture verified. | PASS for capture method only |
| `videos/gui-capture-failed-black-pybullet.mp4` | Five-second simultaneous two-window capture. Actual camera/telemetry on left; PyBullet side black. | FAIL for synchronized capture |

[Readable sample frame](../screenshots/recording-sample-v2.png),
[failed two-window sample frame](../screenshots/gui-capture-sample.png).
The first single-window H.264 attempt failed because captured height was odd;
padding produced a valid readable clip. All method logs are retained here.

The complete A–F set was not produced. There is no successful full-duration
GUI recording, controlled blue/yellow motion clip, autonomous pursuit clip,
or complete new-head active STOP/fault demonstration. The successful headless
905 s run has complete telemetry and actual joint traces, but no full-duration
screen recording was made. Computer Use was stopped by the operator with
Escape before further UI/recording work. No animation, black capture or manual
motion is represented as successful autonomous hardware evidence.

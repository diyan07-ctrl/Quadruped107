# Genuine recordings and gaps

Durable large media: [Phase 4 evidence release](https://github.com/diyan07-ctrl/Quadruped107/releases/tag/phase4-hil-evidence-2026-11-10).
See `recordings.json` for exact capture commands, source, frame counts, hashes and limitations.
Recordings show executed software/camera output; no fabricated demonstration was generated.

| Requested recording | Outcome |
| --- | --- |
| 1 — authenticated Pi preflight | Complete executed SSH/preflight logs retained; no qualification screen clip captured. |
| 2 — actual USB/OpenCV | `real-usb-camera.mp4`: genuine annotated live Pi MJPEG stream, 25 s. Encoded 25 FPS includes repeated frames and is not camera capture FPS. |
| 3 — physical blue/yellow sweeps | Real blue centered footage and snapshots/logs exist. Complete controlled blue/yellow sweep clip not established. |
| 4 — complete camera + PyBullet demonstration | `pybullet-manual-lan.mp4`: genuine 45 s Windows GUI capture from the LAN session; separate actual camera clip. A synchronized successful full demonstration was not completed. |
| 5 — safety | STOP/output-off events retained in full JSON/UDP/joint logs; host/failed-attempt media are partial. No complete narrated STOP/re-enable screen demonstration is claimed. |
| 6 — virtual obstacle/autonomy | Executed obstacle, touch and interaction logs retained. No complete synchronized screen clip. |
| 7 — endurance | Full 900.219 s failed-run logs/statistics retained. `headless-attempt.avi` is an earlier actual TinyRenderer capture of executed receiver state, predominantly disarmed; it is not a successful endurance movie. |

`real-camera-dashboard.mp4` is a failed near-black GDI browser capture. It is
retained as a capture failure, not credited as live dashboard verification.
The dashboard screenshot and live API observations provide that evidence instead.
The GUI's empty built-in panels titled “Synthetic Camera RGB/Depth/Segmentation”
are PyBullet debug panels, not the Raspberry Pi's camera source.

Only non-identifying object footage was retained. No passwords, private keys,
control cookies or unrelated browser/terminal content are included. Videos stay
in ignored `build/` locally and release assets remotely, outside normal Git history.

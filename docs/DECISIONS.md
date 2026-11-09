# Phase 0.1 architecture decision record

Freeze basis: Phase 0 PR #1 remains unmerged as inspected on 2026-11-09; main is fb5bacc and Phase 0 head is 6ce7fcb. Phase 0.1 branches from that head and is stacked on PR #1. No branch was merged or force-pushed.

The freeze is a software/interface design baseline with explicit physical qualification gates. It does not certify the assembled robot.

| Decision | Disposition and engineering reason | Acceptance / consequence |
| --- | --- | --- |
| Pi 4 + Uno R3 + PCA9685 / USB | Retain. Fits course digital interfaces and separates video from gait execution | Pi 5 upgrade requires power/cable qualification; no ROS/message broker |
| Flask / HTTP / MJPEG | Retain. Existing tests, small dependency surface, no measured migration benefit | Single process, one camera/serial owner; LAN only; resource tests pending |
| Serial v1 | Retain baud, framing, command formats and identity | Host scheduling changes do not require a firmware change |
| STOP behind FIFO / operation lock | Improve now. Separate coalesced urgent slot; cancel ordinary pending work; no acknowledgment wait while holding controller state lock | Tests cover full queue, blocked ARM/SERVO, old acknowledgments, timeouts and disconnect |
| Race between selection/submission/STOP | Improve now. Submit under state lock, compare generations, reserve one controller operation and retire only its ticket | Late completion cannot enable or overwrite a stopped/new operation |
| Unbounded transport work | Improve now. Four ordinary pending requests max, 250 ms queue TTL, finite deadlines and 11-digit IDs | Capacity rejects immediately; STOP has independent capacity and ID 0 fallback |
| Operator ownership | Improve now. First ARM claims HttpOnly same-site cookie lease; other clients cannot drive/renew it; STOP remains available | Browser works unchanged; API clients must retain cookies. No authentication claim |
| Stale intent / mode transition | Improve now. 500 ms unsent action/held-direction TTL; held heartbeat renews; stand remains a release intent | Mode switches while a MOVE is active reject; explicit STOP interrupts. New pose/direction is latest-only |
| Camera latency | Improve queue behavior now using documented queue=False; remove redundant non-simulated wait | Capture remains blocking; publication age is not exposure age; hardware metadata qualification still required |
| Startup/shutdown | Improve cleanup ordering; stop motion before camera/inference teardown | Hung camera/inference may exceed join deadlines; independent motor hardware protection still required |
| Independent watchdog / physical stop | Design frozen; implement and qualify in Phase 1 | No watchdog or stop-circuit protection is falsely claimed in existing firmware |
| First servo movement | Defer hardware actuation changes; introduce offline versioned calibration contract | Current estimate of 300 ticks is not sensed. Supported commissioning is mandatory |
| OLED on Uno | Reject full framebuffer. A 1024-byte image consumes nearly all existing headroom | Optional OLED belongs to Pi-side 3.3 V I2C; no core dependency |
| Sensor/monitoring extension | Specify optional negotiated TEL1 records, no current firmware driver | Preserves v1 peers; sensing and local policy remain on Uno |
| Power choice | A is minimum-cost conditional candidate; D is robust fallback with independent logic bank | None of the current packs/converters is qualified. See [Power](../hardware/Power/README.md) |
| Duplicate control implementations | Retain historical UNO Q only in archive; reject active Bridge dependencies | Preserve provenance and spreadsheets; no duplicate active runtime |
| Free software / learning outcomes | Retain Python/Arduino/OpenCV/Picamera2/Flask/pySerial/GitHub tooling; optional models require license review | Demonstrate PWM, GPIO, I2C, USB framing, state/fault logic, energy calculations and measured validation through Phase 5 |

## Known residual software limits

STOP must still wait for an OS write already in progress (configured 500 ms write timeout), parser service, bus calls and physical electronics. Serial heartbeat uses a 300 ms cadence; reads wait up to 50 ms. Host real-time scheduling is not guaranteed. A cancellation barrier cannot retract bytes already delivered to Uno.

HTTP ownership is a trusted-LAN arbitration mechanism, not security against malicious clients or DNS rebinding. The retained development server can create multiple HTTP threads; viewer/request concurrency and inference resource budgets require Pi measurement. No Internet exposure is approved.

The MCU can retain PWM during a freeze; a failed regulator can damage servos even with PWM inhibited. Software changes cannot repair absent physical protection, sense actual joint positions, or establish electrical current limits. See [HARDWARE_VERIFICATION](HARDWARE_VERIFICATION.md), [calibration](CALIBRATION.md), and [power protection](../hardware/Power/PROTECTION.md).

# Architecture freeze — Phase 0.1

This is a conditional design freeze. Solid control paths are implemented unless explicitly labelled proposed; power wiring and sensor circuits have not been physically verified. [Decisions](DECISIONS.md), [Power](../hardware/Power/README.md) and [HARDWARE_VERIFICATION](HARDWARE_VERIFICATION.md) govern the freeze.

```mermaid
flowchart TB
    Browser["One browser owner: HTTP JSON / MJPEG"] <--> Pi["Raspberry Pi 4: Flask / OpenCV / scheduler"]
    Camera["Pi CSI camera / Picamera2"] -->|CSI| Pi
    Bank["Qualified USB bank: proposed logic source"] -->|5V USB-C| Pi
    Pi <-->|USB serial 115200 / Uno logic power| Uno["Uno R3: gaits / communication timeout"]
    Uno -->|A4 SDA / A5 SCL and logic VCC| PCA["PCA9685 0x40 / 50Hz"]
    Uno -->|D8 enable request| OE["OE inhibit: external fail-safe circuit proposed"]
    OE --> PCA
    PCA -->|PWM signals 0-7 only| Legs["Eight servos"]
    Sensors["Proposed URM37 / HC-SR04 / 3-5 touch"] -.->|Uno GPIO; local safety priority| Uno
    Monitor["Proposed A0 pack / A1 rail sensing"] -.-> Uno
    Pi -.->|Separate 3.3V I2C1| OLED["Optional OLED: Pi-owned"]
    PCA -.->|Reserved PWM channel 8| Pan["Optional pan servo"]
    Battery["A: qualified existing pack OR D: qualified 3S pack"] --> Fuse["Fuse / DC-rated physical disconnect"]
    Stop["Independent physical STOP: proposed"] -.-> Fuse
    Fuse --> Converter["Qualified servo converter: 6V candidate"]
    Converter --> PDB["External protected motor distribution"]
    PDB --> Legs
    PDB -.-> Pan
    PDB -.-> Supervisor["Proposed rail power-good / UV / OV latch"]
    Supervisor -.->|Fault dominates enable| OE
    Ground["Common control reference / controlled high-current returns"] --- Uno
    Ground --- PCA
    Ground --- PDB
```

Power domains are independent supplies with common reference, not galvanic isolation. PWM inhibition does not remove motor power. The proposed supervisor must prevent motion on partial power and rail restoration; it does not exist in current hardware evidence.

## Responsibility and control hierarchy

Pi owns camera, image processing, behavior selection, HTTP, mode management and telemetry presentation. Uno owns the sole servo I2C bus, deterministic gait sequences, and the communication watchdog. Local sensing, joint-limit enforcement, hardware watchdog and rail/physical-stop logic are assigned to Uno or independent circuits and staged into Phase 1/2 as specified.

Priority is emergency stop/hardware fault → local safety → manual → interaction → autonomy → idle. No feature may write PWM around this path. A single MotionController reserves ARM/MOVE/SERVO transactions, serializes submission under a short state lock and never holds that lock while awaiting acknowledgments. STOP cancels previous intent and pending transport work. The serial worker alone performs USB I/O.

The first HTTP ARM claims one browser cookie lease; other clients cannot move or renew it. Any same-origin client may STOP. Requests validated before a STOP/mode change carry a generation check so they cannot act in a newer session. Cookie ownership is arbitration, not authentication; trusted LAN remains required.

```mermaid
stateDiagram-v2
    [*] --> Disabled
    Disabled --> Arming: explicit owner ARM
    Arming --> EnabledIdle: matching acknowledgment and generation
    Arming --> Disabled: STOP / timeout / link change
    EnabledIdle --> Manual: fresh pose or direction
    EnabledIdle --> Tracking: selected mode / fresh camera
    Manual --> EnabledIdle: one step completed / no repeat
    Tracking --> EnabledIdle: owner selects manual while idle
    Manual --> Disabled: STOP / stale intent / lease or link fault
    Tracking --> Disabled: STOP / camera or lease fault
    EnabledIdle --> Disabled: STOP / fault
    Disabled --> Disabled: reconnect or rail fault; no replay
```

Busy control-mode switches reject rather than waiting behind a long routine. Latest pose/direction selection may replace unsent intent during MOVE; stand remains the release intent. Old action intent expires after 500 ms; held direction is renewed only by the owner's matching heartbeat. A failed active MOVE latches a stop even if a newer desired direction exists. Explicit re-arm clears a fault only after the STOP barrier/previous operation retires.

## Timing, blocking and resource gates

| Path | Implementation / design target |
| --- | --- |
| Camera | One capture owner, queue=False, latest frame only, requested 640×480 at 20 fps; actual target ≥10 fresh fps |
| Frame age | 0.8 s publication expiry implemented; exposure timestamp/clock-domain age still requires HV14 measurement |
| Vision | Separate worker, 60 ms wait, two stable observations and 1.5 s action cooldown; inference may block, never owns serial |
| Browser | 250 ms heartbeat, 1 s lease and 50 ms guard; background timers can throttle and therefore disarm |
| Serial | One I/O owner, four ordinary pending max, one coalesced urgent STOP, 250 ms ordinary queue TTL; no replay |
| I/O blocking | Serial reads 50 ms, writes up to configured 500 ms; STOP cannot retract a write already started |
| Completion | ARM/SERVO 3 s, STOP 2 s, MOVE 20 s deadlines including queued time; timeout disconnects/disarms |
| Heartbeats | PING 300 ms; host missing-PONG 1.2 s; Uno PING timeout >1.5 s when loop responsive |
| Host dispatch | Target ≤100 ms normal command dispatch; STOP dispatch target ≤100 ms in normal load, not worst-case guarantee |
| Physical stop | Measure USB-to-OE and torque loss separately; no certified stop latency is claimed |
| Uno | Current 998 bytes globals; future ≤1300 bytes globals, ≥400 bytes measured stack margin, ≤28 KiB flash target |
| Pi 4 | Target app RSS <1 GiB, process CPU <200%, capture-to-display <250 ms with one viewer; all unmeasured |
| Recovery | Target reconnect/identity within 8 s after a device becomes available; explicit ARM required |
| Shutdown | Stop motion/link before camera teardown; joins are bounded attempts, not proof native capture/inference terminated |

Hidden waits remain: Picamera2 capture, JPEG encoding, inference, HTTP streaming socket writes, serial OS writes, repeated I2C transactions and thread joins. Uno cooperative delays service serial, but a bus/MCU freeze still needs independent watchdog/hardware protection. A 1 s hardware-watchdog candidate and progress/brownout design are in [SAFETY](SAFETY.md). Driver buffers/threads and viewer count require load qualification; no bounded HTTP-worker claim is made.

## Phase 1–5 expansion

Versioned offline [calibration profiles](CALIBRATION.md) preserve inherited targets. [EXTENSIONS](EXTENSIONS.md) freezes optional TEL1 telemetry, pins, freshness, local fault policy and SRAM budgets. Optional OLED moves to Pi's separate 3.3 V bus; camera pan stays reserved/off. Person/object inference remains a Pi worker publishing expiring motion intent.

No ROS 2, cloud inference, paid APIs, database, heavyweight frontend or broker is required. [Power candidates A/D](../hardware/Power/README.md) preserve the same control topology when the source changes; no structural software redesign is needed.

# Protection and power-fault behavior

The following circuits are **proposed**, not installed or verified.

- Battery positive: correctly located fuse near the pack, protected connector and accessible DC-rated disconnect. A stop control must remove all servo branches together. Use switches/contactors/electronic switches rated for DC interruption, inrush and prospective fault current.
- Separate logic and motor branches: no servo load through USB or logic regulator. Verify USB/VIN/5V paths to prevent Uno or power-bank backfeeding. In the baseline, Uno receives logic power only from Pi USB.
- Reverse polarity: keyed connectors plus a suitably rated reverse-protection design; never assume a clone converter/PCA board includes it.
- Short circuit: fuse and electronic current limiting complement one another. Fusing protects conductors; it is not fast servo torque control.
- Battery/BMS: verify individual-cell limits, balancing, overcurrent/short behavior, charging requirements and condition. A BMS trip can be abrupt and is not a normal operating cutoff.
- Voltage supervision: independent qualified servo-rail power-good/UV/OV inhibit and latch are required before free walking. A pack ADC alone does not detect every regulator/servo-rail failure.
- Temperature/stall: converter thermal protection plus supervised load tests and an overload cutoff; do not infer an individual stalled joint from total current alone.
- Pi shutdown: power-bank low-state indication and enough reserve for graceful OS shutdown must be qualified. An unexpected bank cutoff risks SD corruption; motor disarm should precede planned shutdown.

## Provisional coordination example

At the modeled high load, A draws 8.49 A at 6 V input and D draws 5.66 A at 9 V. A 25% allowance gives 10.61 A and 7.07 A respectively. These are input fuse/conductor design currents, **not final fuse selections**. A 10–15 A input-fuse class for A or 7.5–10 A class for D would need actual time-current/I²t curves, ambient derating, load-step duration, pack/BMS limits and wire ratings reviewed before selection. If the pack cannot support that protection envelope, reject A rather than installing a larger fuse.

Four-servo output branches model 3.6 A high load and 10 A upper stall; individual leads can be damaged before a large branch/trunk fuse opens. Coordinate downstream protection and electronic cutoff with the weakest conductor/contact. Verify interrupt capacity against prospective battery short current; this remains unknown.

## Failure matrix

| Failure | Existing software behavior | Required independent protection / acceptance |
| --- | --- | --- |
| Pi power fails, servo battery stays on | Uno also loses USB logic; firmware cannot run | OE must default inhibited even with logic absent; signal backpower test, hardware power disconnect |
| Servo pack/rail fails while Pi survives | Existing firmware has no rail measurement and may remain logically armed | Hardware power-good latch inhibits OE; restoring voltage must not restore motion; explicit recovery/re-arm |
| Uno freezes | Software heartbeat checks stop running; PCA can retain PWM | Qualified MCU watchdog plus OE reset circuit; physical disconnect remains independent |
| I2C bus stuck | Existing Wire timeout only partially limits operations | Early OE HIGH on fault, bounded bus transaction handling, watchdog/reset recovery |
| Converter fails high | STOP may inhibit signal but cannot remove overvoltage from servo electronics | Rated overvoltage disconnect/clamp design, fuse where appropriate; do not rely on software |
| Battery undervoltage / BMS trip | No pack monitor implemented | Pack-specific cutoff, rail latch, no oscillatory auto-restart |
| Short / overload / hot wiring | No reliable software detection | Coordinated fuse/current/thermal protection and accessible disconnect |

A pull-up to Uno 5 V only proves a logic level while that rail is present. It does not by itself qualify OE when PCA or servo power remains while Uno logic is absent. Review actual breakout pull resistors, leakage and partial-power behavior; add a qualified fail-safe buffer/supervisor/power switch as needed. All power-fault recovery requires investigation and explicit enable, not automatic rail reapplication while PWM remains active.

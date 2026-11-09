# Safety and test procedure

## Power and batteries

Use a regulated supply within the exact servo voltage specification. Raw nominal 7.4 V / 2S Li-ion packs can exceed a 6 V-rated servo's limit. Do not supply servos from Pi, Uno 5V, or USB. Use common ground, suitably rated wire/connectors, protection, and an accessible servo-power disconnect.

Verify battery protection, cell condition, discharge capability, polarity, regulator cooling and transient response. Use the matching battery charger; do not charge damaged packs or unattended. Do not infer current capability from 1800 mAh capacity. Keep the three packs separate unless a qualified design supports combining them. Qualify the power bank for Pi load and prevent backfeeding or unintended dual powering of Uno.

## Calibration and motion

The chassis may collapse when pulses stop. Support it so legs cannot strike people or bind. Keep fingers and cables clear. Inherited targets and spreadsheet values are reference data, not approved endpoints. Current pulses start from a software estimate of 300 ticks, without position feedback; the first commanded position may jump.

Check one joint at a time for channel, direction, neutral, clearance, and safe endpoints. The 50–600 tick firmware bounds are broad syntactic guards, not safe limits for each mechanism. Never sweep that whole range to discover endpoints. Calibration API writes are temporary; persistent values require reviewed firmware changes and reflash.

## Stops and communication loss

Startup, HELLO and STOP disable outputs. ARM only enables signals and does not issue a pose. Browser STOP / X asks Uno to abort and drive OE HIGH; this is a software stop, not a certified emergency stop. A hardware servo-power disconnect is the independent stop available to the operator.

Browser lease expiry is 1 s; Pi PING loss causes Uno software disarm after more than 1.5 s when its loop remains responsive. Neither is an MCU hardware watchdog. Frozen code, queued commands, I2C hangs, or failed electronics can defeat timing. The physical-stop input, MCU watchdog, runtime bus-fault handling, and per-joint calibrated limits remain Phase 1 work.

Reconnect clears queued commands and requires explicit enable. Release-to-stand waits for the current gait step; it does not stop immediately. Only one visible browser may control the robot. The server has no authentication and must stay on a trusted local network.

## Sensor limitations

Range sensing and touch acquisition are not implemented. Ultrasonic sensing can miss angled, soft, small, or out-of-range targets; invalid/stale readings must not mean clear space. Touch sensing is not a substitute for a collision-safe structure. There is no cliff sensor, IMU balance loop, force feedback, or reliable localization.

Existing blue-ball tracking turns to search when it sees no ball; it does not detect obstacles or edges. Gesture recognition is optional and unqualified on hardware. Test on a clear, level, contained surface, away from stairs, pets, and people.

## Safe sequence

1. Disconnect servo power. Inspect wiring against the proposed map and module-specific manuals; confirm common ground and polarity.
2. Measure regulator voltage and check rated capacity/protection. With logic only, verify OE HIGH during reset, startup, STOP and disconnect recovery.
3. Test camera, USB identity and disarmed startup. Confirm a physical power disconnect works independently of Pi software.
4. Support the chassis. Calibrate isolated joints using small known-safe increments; record actual endpoints and orientation.
5. Test individual poses and gait steps at limited exposure, watching supply voltage, heating and mechanical interference.
6. While supported, test STOP during motion, browser lease loss, Pi termination, USB loss, Uno reset, and camera expiry in vision mode. Measure timing and confirm no automatic restart.
7. Permit unsupported walking only after electrical, calibration, stop and mechanical tests pass. Log failures and conditions in [VALIDATION](VALIDATION.md).

Phase 0 performs no physical tests. Compilation and simulation cannot establish electrical safety, stopping reliability, stability, or load capacity.

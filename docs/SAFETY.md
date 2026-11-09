# Safety and test procedure

## Power and batteries

Use a regulated supply within the exact servo voltage specification. Raw nominal 7.4 V / 2S Li-ion packs can exceed a 6 V-rated servo's limit. Do not supply servos from Pi, Uno 5V, or USB. Use common ground, suitably rated wire/connectors, protection, and an accessible servo-power disconnect.

Verify battery protection, cell condition, discharge capability, polarity, regulator cooling and transient response. Use the matching battery charger; do not charge damaged packs or unattended. Do not infer current capability from 1800 mAh capacity. Keep the three packs separate unless a qualified design supports combining them. Qualify the power bank for Pi load and prevent backfeeding or unintended dual powering of Uno.

## Calibration and motion

The chassis may collapse when pulses stop. Support it so legs cannot strike people or bind. Keep fingers and cables clear. Inherited targets and spreadsheet values are reference data, not approved endpoints. Current pulses start from a software estimate of 300 ticks, without position feedback; the first commanded position may jump.

Check one joint at a time for channel, direction, neutral, clearance, and safe endpoints. The 50–600 tick firmware bounds are broad syntactic guards, not safe limits for each mechanism. Never sweep that whole range to discover endpoints. Calibration API writes are temporary; persistent values require reviewed firmware changes and reflash.

## Stops and communication loss

Startup, HELLO and STOP disable outputs. ARM only enables signals and does not issue a pose. Browser STOP / X asks Uno to abort and drive OE HIGH; this is a software stop, not a certified emergency stop. An independently rated physical servo-power disconnect is required; its presence and behavior have not been verified.

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

## Phase 0.1 watchdog and power-fault design

No AVR watchdog is enabled by this task. The Phase 1 design uses the ATmega328P watchdog's independent oscillator in reset mode, with an initial **1 s nominal candidate** subject to oscillator tolerance and bootloader qualification. Software PING expiry remains 1.5 s: a healthy loop pets the hardware watchdog only after bounded control/safety progress, while absent PING separately inhibits motion. Do not pet the watchdog from a timer interrupt that could hide a frozen main loop.

Before activation, capture/reset MCUSR early, clear WDRF and disable/reconfigure WDT using the required timed sequence. Verify the installed bootloader handles watchdog resets without a reset loop. Assert OE inhibit before I2C initialization and never ARM automatically after WDRF, brownout or USB reset. Reserve a reset-cause fault for telemetry. See the [Microchip watchdog/reset specification](https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/Atmel-7810-Automotive-Microcontrollers-ATmega328P_Datasheet.pdf); select the exact installed part/bootloader documentation before coding.

Keep nominal healthy progress gaps below 250 ms as a design target, including all I2C failures and parser work. Existing 25 ms Wire timeout configuration does not prove a complete sequence is bounded or that write faults are acted on. Phase 1 must check transaction status, drive OE HIGH first on a bus fault, latch the fault and service bounded recovery. Choose the final watchdog interval from measured worst-case valid work plus tolerance; the candidate is not a guaranteed physical stop deadline.

Inspect actual brownout fuses and the minimum valid 16 MHz supply voltage. Do not assume the shipped BOD threshold protects every clock/voltage state. Add/qualify external voltage supervision where needed. A logic-rail OE pull-up cannot establish safe behavior when logic is absent but servo power remains; partial power, leakage and reset must be tested.

Independent hardware protection must cover an inaccessible/frozen MCU, servo-rail restoration, overvoltage, short circuit and overload. A proposed servo-rail power-good/UV/OV latch dominates enable and requires deliberate recovery after supply faults. D12 is proposed stop status; the accessible DC-rated power disconnect must work with Pi/Uno absent. Do not connect an asserted supervisor output directly against D8; qualify a proper fail-safe buffer/open-drain/gating circuit.

## Failure response boundaries

Software can reject conflicting/stale commands, cancel host queues, expire browser/serial leases and request OE inhibition while its hardware path works. It cannot retract buffered bytes, remove an overvoltage supply, sense true joint position, recover a dead CPU by itself, guarantee stopped torque, or protect an unqualified wire against a battery short.

The Phase 0.1 STOP priority path cancels ordinary requests and ignores late acknowledgments. It may still wait for a write already in progress, parser service or bus activity. Fault reason stays latched until explicit enable. Every normal mode change clears older intent; busy control-mode switches reject and request explicit STOP for immediate inhibition.

Servo battery fails while Pi survives: current software does not detect it; a proposed independent rail latch is required to prevent old pulses taking effect when power returns. Pi fails while servo power survives: Uno USB logic can disappear, so OE/power gating must default safe without firmware or 5 V. See the full [power failure matrix](../hardware/Power/PROTECTION.md).

Sensor/motion faults must inhibit their dependent moving behavior and latch locally; an invalid range is not permission to explore. These local drivers are not implemented. Optional OLED/inference failure may degrade presentation but must never block a safety path. All unresolved part-specific facts are in [HARDWARE_VERIFICATION](HARDWARE_VERIFICATION.md); [calibration](CALIBRATION.md) and [Power](../hardware/Power/README.md) define commissioning gates.

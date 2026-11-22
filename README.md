# Quadruped107 — ENR107 Digital Electronics

An eight-degree-of-freedom quadruped robot developed by Group 11 for ENR107 — Digital Electronics. The academic project explores microcontroller programming, I²C communication, PWM servo control, mechanical assembly and basic ultrasonic distance sensing. Each of the four legs has two servo-driven joints.

**ENR107 Academic Project: Completed / Submission prepared**

**Further Development: On Hold**

Submission-phase development has concluded according to the project closure brief. A submission receipt and final academic demonstration video are unavailable in the audited repository, so confirmed submission is not claimed. All code, CAD, earlier experiments and Git history are preserved for future improvements. See [project status](PROJECT_STATUS.md) and the [closure audit](docs/ENR107_CLOSURE_AUDIT.md).

## Group 11

Course: **ENR107 — Digital Electronics**

Project: **Quadruped Robot**

- Diyan Patel
- Vishwam Anghan
- Vedant Kakadiya
- Aarush Doshi

## Hardware components

This is the academic configuration supplied for closure. Installed module ratings and final electrical measurements remain unverified.

| Component | Purpose |
| --- | --- |
| Arduino Uno R3 | Main microcontroller; sequences joint commands and reads sensor signals |
| PCA9685 | 16-channel, 12-bit PWM controller generating servo control pulses |
| Eight MG996R/MG995-class servos | Two joints on each of four legs |
| URM37 ultrasonic sensor | Basic obstacle-distance measurements in PWM-trigger mode |
| 11.1 V nominal 3S LiPo battery | Main energy source for the regulated servo supply |
| CC/CV buck converter | Reduces battery voltage to a servo-compatible voltage and limits current |
| Four-legged mechanical chassis | Structure and servo mounting; original CAD is retained |

## System architecture

```text
Arduino Uno R3 -- I²C --> PCA9685 -- PWM signals --> eight servo motors
      ^                                                   ^
      | trigger / echo                                    | regulated power
    URM37                       3S LiPo --> CC/CV buck --> servo distribution

Arduino, PCA9685, sensor and servo supply share a ground reference.
Arduino logic uses a suitable separate regulated/USB supply.
```

The academic focus is **Arduino Uno R3 → PCA9685 → Servo Motors**, with URM37 distance sensing. Raspberry Pi, ESP32 wireless control, computer vision, navigation and digital-twin experiments belong to earlier development. They are not requirements or verified completed features of the academic demonstration. The exact sketch uploaded for that demonstration could not be identified.

## Arduino–PCA9685 I²C communication

The Uno sends channel and pulse-width commands over SDA and SCL. The PCA9685 generates the pulses independently, allowing eight servo signals to be controlled over one digital bus. Retained firmware requests address `0x40`; confirm the actual board's address jumpers. Uno A4 is SDA and A5 is SCL. Logic power VCC is separate from servo power V+.

## Servo movement using PWM

The retained program requests 50 Hz, a nominal 20 ms period. The PCA9685 divides the period into 4096 counts, approximately 4.88 μs per count at that frequency. Changing the high-pulse duration requests a different servo position; counts are not angles or measured joint positions.

The source includes initial, stand, greeting, tail-wag, forward, backward and turn sequences. Their presence does not prove stable walking. Each installed servo needs verified direction, neutral position, endpoints and mechanical clearance. The inherited 50–600 count guards are broad software bounds, not verified safe joint limits.

## URM37 obstacle detection

In the supplied academic PWM-trigger configuration, the Uno triggers a measurement and times the echo pulse. Distance conversion and timing depend on the exact URM37 revision and configured mode. Match the installed module's labels, voltage levels and manufacturer manual before selecting conversion constants. Missing echoes must be treated as invalid measurements, not a clear path.

URM37 integration is reported in the closure brief, but no matching final D5/D3 sketch or measured distance log was found. Later sensor-only experiments remain on separate branches with physical measurement gates unresolved. Basic distance sensing does not establish continuous obstacle avoidance or advanced navigation.

## Battery and buck converter power architecture

The supplied academic path is **11.1 V nominal 3S LiPo → CC/CV buck input → regulated servo distribution**. Nominal battery voltage is not maximum voltage. Verify converter input range, output voltage, polarity, current limit and thermal capacity against the actual battery and servos before connecting loads. Do not feed raw 3S voltage to servo V+, PCA logic VCC or the Uno 5V pin.

Eight loaded servos can draw substantial simultaneous and transient current. No approved current setting or measured runtime is established here. Current limiting can collapse the servo rail and cause erratic motion. Use rated wiring, connectors, fusing and an accessible disconnect. Do not carry servo current through the Uno, USB, breadboard rails or unqualified PCA traces/terminals. Use appropriate external distribution, common ground and high-current returns separate from thin logic wiring. Disconnect power before rewiring; check battery polarity and unloaded regulation before attaching servos.

Earlier [power studies](hardware/Power/README.md) consider other packs and conditional designs; they do not verify the installed 3S system. Historical reports of a suspected damaged PCA9685 remain unresolved. Closure does not clear it for use; review the [hardware verification register](docs/HARDWARE_VERIFICATION.md) before resuming physical work.

## Wiring and pin connections

These connections reproduce the academic closure brief, not a newly inspected assembly. Match them to the actual uploaded sketch before use.

| Uno / supply | Destination | Purpose |
| --- | --- | --- |
| A4 | PCA9685 SDA | I²C data |
| A5 | PCA9685 SCL | I²C clock |
| 5V | PCA9685 VCC | Logic supply only |
| GND | PCA9685 GND | Common reference |
| GND, where applicable | PCA9685 OE | Always-enabled configuration; see conflict below |
| D5 | URM37 COMP/TRIG | Academic PWM trigger |
| D3 | URM37 ECHO | Academic pulse input |
| 5V / GND | URM37 VCC / GND | Verify exact module rating and labels |
| 3S LiPo positive / negative | Buck input positive / negative | Main servo energy source |
| Buck regulated output | Servo power distribution | Servo-compatible supply |
| Servo supply negative | Uno GND and PCA GND | Common ground |

**Configuration conflict:** retained `firmware/uno/sketch` drives OE from **D8**, with HIGH disabling outputs and an external pull-up. Do not ground OE while using that firmware or short a driven output to ground. Earlier experimental assignments use URM37 **D4/D2** and reserve **D5/D3** for HC-SR04. No code or electrical assignments were changed for closure. [Historical wiring](docs/WIRING.md) describes that experimental configuration.

### Servo-to-channel mapping

The actual final demonstration mapping is **not verified**. The following is verified only in retained [motion.h](firmware/uno/sketch/motion.h). Confirm physical leads before adopting it; do not assume earlier mappings survived rewiring.

| PCA channel | Joint named in source |
| --- | --- |
| 0 | Front-left shoulder |
| 1 | Front-left leg |
| 2 | Front-right shoulder |
| 3 | Front-right leg |
| 4 | Back-left shoulder |
| 5 | Back-left leg |
| 6 | Back-right shoulder |
| 7 | Back-right leg |

## Firmware installation and usage

**Final academic firmware: not conclusively identified.** The maintained Uno R3 sketch is a Pi/USB-command implementation with individual servo control and movement routines. It has no URM37 acquisition or standalone obstacle-detection loop. Do not substitute it for an unidentified final sketch.

To inspect/build the maintained program, open `firmware/uno/sketch/sketch.ino` in Arduino IDE and select **Arduino Uno**. Install **Adafruit PWM Servo Driver Library 3.0.2** and **Adafruit BusIO 1.17.4**; `Wire` comes with the AVR core. The [profile](firmware/uno/sketch/sketch.yaml) pins **arduino:avr 1.8.8**. From the repository root with Arduino CLI:

```bash
arduino-cli core update-index
arduino-cli compile --profile uno firmware/uno/sketch
arduino-cli board list
```

Before any future upload, disconnect servo power and verify the board, port and wiring conflicts. [Firmware documentation](firmware/uno/README.md) provides the upload command, sketch inventory and [USB protocol](docs/PROTOCOL.md). The sketch starts disarmed and needs a 115200-baud host, heartbeat and explicit ARM; powering it does not start a walking demo. Archived UNO Q programs use different board-specific dependencies and must not be flashed to Uno R3.

## Demonstrated functionality and project results

The closure brief describes assembly, servo connections, Uno programming, PCA9685 control, PWM experiments, basic leg movement, URM37 integration and academic video preparation. Evidence levels are distinguished below.

| Work | Supported status |
| --- | --- |
| Four-legged, two-joint-per-leg assembly | Reported assembly; [build photo 1](docs/images/physical-build-1.png), [photo 2](docs/images/physical-build-2.png) and CAD retained; electrical operation is not proved by photos |
| Uno programming and multiple-servo PCA9685 control | Implemented in source; historical [validation](docs/VALIDATION.md) includes compile/software evidence |
| Individual channel control and PWM experiments | Code and calibration workbook retained; final physical test record and safe endpoints not verified |
| Basic movement sequences | Implemented and exercised virtually; final physical gait performance not verified |
| URM37 distance measurements | Project integration reported; matching final sketch and physical distance log not verified |
| Academic demonstration video | Preparation reported; final playable recording or submission link not located |
| Vision, navigation and digital twin | Experimental software with bounded test evidence; not completed physical autonomy |

“Implemented” means code exists. “Hardware-tested” requires an identified physical setup and result. “Demonstrated” requires an identifiable demonstration record. No new physical hardware tests were performed by the coding agent during closure.

## Known limitations

The final uploaded sketch, actual final channel map, URM37 measurements, converter settings and submission confirmation are missing. Stable autonomous walking, continuous obstacle avoidance, balance, odometry and advanced physical navigation are not verified. Inherited pulse targets and provisional simulation joints are not physical calibration.

## Future development possibilities

Further development is on hold. Future work can recover the final sketch/video, document actual wiring and calibration, qualify the servo supply and assessed/replacement PCA9685, measure sensor behavior and evaluate supported gait trials. ESP32 control, Pi integration, vision and digital-twin improvements remain separately scoped opportunities. See [resume steps](PROJECT_STATUS.md#steps-to-resume-development).

## Project documentation and media

| Location | Contents / scope |
| --- | --- |
| [Project status](PROJECT_STATUS.md) | Academic closure, limitations and resume checklist |
| [Closure audit](docs/ENR107_CLOSURE_AUDIT.md) | Complete structure inventory, branch findings and checks |
| [Firmware](firmware/uno/README.md) | Sketch purposes, dependencies and unresolved final selection |
| [Hardware](hardware/README.md) | Fusion/STEP CAD, STL parts and calibration spreadsheets |
| [Images](docs/images/) / [exploded animation](docs/Quadruped107_exploded.mp4) | Design and build media; animation is not a walking demonstration |
| [Historical technical project](docs/PROJECT.md) | Previous Pi/Uno development scope |
| [Pi software](software/pi/README.md) / [deployment](deploy/README.md) | Preserved experimental runtime and setup |
| [Simulation](simulation/README.md) / [validation](docs/VALIDATION.md) | Virtual model and historical software evidence |
| [Tests](tests/) / [tools](tools/) | Available non-hardware checks |
| [UNO Q archive](archive/uno-q/README.md) | Historical station and calibrator |

Interface references: [Arduino Uno R3](https://docs.arduino.cc/hardware/uno-rev3/), [Adafruit PCA9685 wiring and separate servo power](https://learn.adafruit.com/16-channel-pwm-servo-driver/hooking-it-up), and [DFRobot URM37 interface guidance](https://wiki.dfrobot.com/sen0001/docs/21981). Match manufacturer documentation to the actual installed modules, including TTL/RS232 mode where applicable.

[GNU GPL v3](LICENSE). Existing attribution and Git history are retained; see [credits](AUTHORS.md).

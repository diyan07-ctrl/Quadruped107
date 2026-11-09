# Hardware

The supplied inventory is recorded in [PROJECT](PROJECT.md). Connections have not been inspected on the assembled robot. “Verified in source” below means an inspected software assignment, not a measured wire.

## Mechanical assembly

The robot is assembled with two joints per leg, conventionally named shoulder and leg. Original Fusion 360, STEP, 24 STL parts, and a printable ZIP remain under [hardware](../hardware/README.md). Images and an exploded animation remain under [docs/images](images/) and [the animation](Quadruped107_exploded.mp4).

The supplied CAD retains its original UNO Q mounting arrangement. Pi 4, Uno R3, CSI ribbon clearance, strain relief, cooling, mass distribution, and optional sensor mounts need fit checks. No link lengths, material strength, loaded torque, or battery runtime are established.

## Joint map, verified in source

View front/back and left/right from the robot's forward-facing orientation; confirm this against actual wiring before power-on.

| PCA channel | Joint | Initial / stand ticks |
| --- | --- | --- |
| 0 | Front-left shoulder | 175 / 278 |
| 1 | Front-left leg | 513 / 110 |
| 2 | Front-right shoulder | 440 / 328 |
| 3 | Front-right leg | 90 / 500 |
| 4 | Back-left shoulder | 405 / 295 |
| 5 | Back-left leg | 75 / 495 |
| 6 | Back-right shoulder | 175 / 283 |
| 7 | Back-right leg | 525 / 110 |
| 8 | Optional camera pan | Reserved, not supported by current firmware |
| 9–15 | Unassigned | Leave unused |

Targets come from [motion.h](../firmware/uno/sketch/motion.h); they are inherited values, not verified calibration for this assembly. PCA9685 uses address 0x40 and requested 50 Hz. Ticks are 1/4096 of the nominal period, approximately 4.88 microseconds at 50 Hz; oscillator tolerance changes actual pulse width. Broad 50–600 tick guards are not joint-specific safety limits.

## Electrical interfaces

Uno R3 uses 5 V logic; Pi GPIO uses 3.3 V logic. Pi–Uno communication is USB only. The proposed Uno–PCA9685 wiring uses 5 V logic VCC, A4/A5 I2C, and D8 OE. Servo V+ is an independent regulated rail, with common ground.

Prefer URM37 pulse-trigger sensing after verifying its revision, interface mode, labels, supply, and output levels. HC-SR04 is an optional alternative/additional range sensor, with independent trigger scheduling to avoid crosstalk. Touch sensors connect to reserved Uno GPIO after output type and polarity checks. Sensors do not currently have drivers.

SSD1306 OLED may share Uno I2C only after address/pull-up/logic compatibility checks. A 128 × 64 monochrome framebuffer alone consumes 1024 bytes, significant on Uno's 2 KiB SRAM; the display must not compromise safety memory. It is not a required dependency.

## Hardware-dependent facts

Verify servo make/revision and rated voltage; stall/load current; battery cell count, protection, discharge rating and charger; regulator continuous/transient ratings; switch/fuse/wire ratings; USB power-bank capability; camera model and cable; touch module voltage/polarity; URM37 and HC-SR04 revisions; actual OE breakout circuitry; joint endpoints/directions; and mechanical clearances.

Nominal 7.4 V and 1800 mAh describe the supplied packs, not usable peak current or runtime. Do not connect the three packs together in series or parallel without a specifically engineered battery system.

Sources: [Uno R3](https://docs.arduino.cc/hardware/uno-rev3/), [PCA9685 wiring](https://learn.adafruit.com/16-channel-pwm-servo-driver/hooking-it-up), [URM37 manufacturer guide](https://wiki.dfrobot.com/sen0001/docs/21984). Module-specific documentation takes precedence over family-level examples.

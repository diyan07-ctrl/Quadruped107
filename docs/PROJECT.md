# Project

Quadruped107 is an autonomous-robotics course project for ENR107 Digital Electronics. It connects digital GPIO and serial interfaces, PWM generation, power distribution, embedded control, and computer vision in an assembled eight-joint walking platform.

## Inventory

| Item | Quantity / status |
| --- | --- |
| Raspberry Pi 4 | 1; primary computer |
| Raspberry Pi 5 | Optional future upgrade |
| Arduino Uno R3 | 1; mandatory embedded controller |
| PCA9685 | 1; servo PWM driver |
| MG996R/MG995-family servos | 8 assembled, two joints per leg |
| Pi CSI camera | 1; exact model unverified |
| URM37 / HC-SR04 | 1 each; revision and pinout unverified |
| Touch sensors | 3–5; module type unverified |
| Li-ion battery packs | 3 × nominal 7.4 V, 1800 mAh; ratings unverified |
| USB power bank | 1; output capability unverified |
| Camera-pan servo / SSD1306 OLED | Optional; not core dependencies |
| Servo regulator, protection, disconnect, wiring | Required; selection and ratings pending |

## Scope and current capability

The complete project covers calibrated manual motion, obstacle-aware exploration, touch interaction, vision/gesture tracking, telemetry, and a final integrated demonstration. The browser controls, gait routines, synthetic simulation, blue-ball detector, and optional gesture interface already exist. They are preserved through Phase 0, without treating their presence as completion of later integration phases.

The robot has no verified odometry, localization, balance feedback, or joint-position feedback. Existing vision is heuristic tracking, not safe navigation. There are no active range or touch drivers and no sensor telemetry.

## Engineering objectives and success criteria

- Establish one documented owner per hardware interface and one route for motion arbitration.
- Preserve existing commands and calibrated-source data through a reproducible repository restructure.
- Demonstrate explicit enable, stop, communication-loss disarm, and no motion replay after reconnect on hardware before locomotion acceptance.
- Qualify individual joint limits, power delivery, and mechanical clearances before unsupported walking.
- Reject stale observations and motion intent; measure response time on Pi 4 against documented targets.
- Complete each phase using its [roadmap](ROADMAP.md) acceptance tests; record evidence and limitations in [validation](VALIDATION.md).

Phase 0 succeeds when documentation, repository organization, automated validation, attribution, and branch/PR publication are complete. Physical tests are separately marked pending; no hardware measurement is invented.

Phase 0.1 adds tested host arbitration, a reproducible [power study](../hardware/Power/README.md), and explicit [design decisions](DECISIONS.md). No physical motion calibration or autonomous feature phase is completed by those changes.

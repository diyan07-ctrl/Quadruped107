# ENR107 project closure

**ENR107 Academic Project: Completed / Submission prepared**

**Further Development: On Hold**

Closure audit date: 22 November 2026.

Group 11 developed an eight-degree-of-freedom quadruped for ENR107 — Digital Electronics. Members: Diyan Patel, Vishwam Anghan, Vedant Kakadiya and Aarush Doshi. Submission-phase development has concluded according to the closure brief. Submission confirmation is unavailable, so the status is “Submission prepared,” not “Submitted.” The repository is preserved for future development; this closure does not archive the GitHub repository or remove branches.

## Academic scope and hardware configuration

The academic focus is Arduino Uno R3 → PCA9685 → eight MG996R/MG995-class servos, two per leg, plus URM37 basic distance sensing. The reported supply is an 11.1 V nominal 3S LiPo feeding a CC/CV buck converter and servo distribution with common ground. Actual converter settings, ratings and currents are unverified.

The brief specifies A4/SDA, A5/SCL, 5V/VCC and GND for PCA9685; D5/COMP-TRIG, D3/ECHO, 5V/VCC and GND for URM37; OE grounded where applicable. These are reported academic connections. Retained Pi/Uno firmware requires D8-controlled OE; historical sensor proposals use D4/D2 for URM37. Do not combine configurations. See [wiring and the source-only channel map](README.md#wiring-and-pin-connections). The actual final physical servo map remains unknown.

## Verified functionality and evidence boundaries

| Classification | Finding |
| --- | --- |
| Implemented | Main-branch Uno firmware has PCA setup, individual servo commands, movement sequences, arm/disarm and cooperative communication timeout |
| Software-tested | Historical virtual control, vision, model and Uno compile checks; closure results appear in the [audit](docs/ENR107_CLOSURE_AUDIT.md) |
| Hardware-tested | No final academic current, distance or gait test record located; no new physical tests performed by the coding agent |
| Demonstrated | Build photos and exploded CAD animation retained; final academic video/actions not independently established |
| Reported work | Assembly, servo connections, Uno programming, PWM experiments, basic leg sequences, URM37 integration and video preparation in the closure brief |
| Experimental | Pi/vision/browser control, virtual Uno, simulation/navigation, UNO Q tools and later sensor commissioning |
| Not verified | Final demo sketch, channel wiring, confirmed submission, stable autonomous walking, continuous obstacle avoidance and advanced navigation |

## Known limitations

The final academic firmware is not identified. The main Uno sketch needs a USB host and has no URM37 driver. Channel constants do not prove final wiring; spreadsheets and broad pulse guards are not accepted safe calibration. Historical reports of suspected PCA9685 damage and unqualified power hardware remain unresolved.

Previous documents describe different dates, architectures and battery options. Their session-specific statements are historical. This status and the root README define academic closure; earlier technical documents preserve experimental evidence and limitations.

## Previous development work and unfinished features

All existing main-branch code, CAD, media and tests remain intact. Phase branches and `release/sensor-commissioning` retain later sensor-only firmware, direct calibration work, Pi qualification and unsuccessful live trials. The [branch audit](docs/ENR107_CLOSURE_AUDIT.md#branches-and-recent-history) records their scope. This PR merges none of those changes.

The closure brief also identifies ESP32 wireless experiments. No dedicated ESP32 source or branch was located in fetched refs; its location remains unknown. No replacement was invented or external folder imported.

Unfinished work includes final URM37 commissioning, actual servo and supply qualification, measured stop behavior, physical gait stability, odometry/balance feedback and integrated autonomous navigation. Later software passes and virtual recordings do not complete these physical tasks.

## Potential future improvements

Recover and version the final academic sketch, channel map and video first. Then consider measured per-joint calibration, robust range sensing, power/protection qualification, supported gait trials and separately reviewed ESP32/Pi/vision/simulation improvements. These are opportunities, not new closure features or active commitments.

## Steps to resume development

1. Review this status, the [audit](docs/ENR107_CLOSURE_AUDIT.md), branch histories and [hardware register](docs/HARDWARE_VERIFICATION.md). Start a new branch from a deliberately selected baseline, preserving earlier work.
2. Obtain the uploaded sketch/binary provenance, video/submission evidence, actual channel map and installed-module details. Reconcile discrepancies before selecting firmware.
3. Inspect/replace the suspected damaged PCA9685 and verify OE, sensor pins, module revision and signal levels. Do not silently reuse earlier assignments.
4. Qualify battery polarity, converter voltage/current limit, transient capacity, distribution, fusing and independent disconnect against measured loads before attaching servos.
5. Reproduce relevant software checks and compile selected firmware with pinned dependencies. Keep upload and physical commissioning separate from closure.
6. With a supported robot and reviewed supply, identify each servo, establish conservative endpoints and record individual tests before coordinated movement.
7. Measure range/timeout behavior and stop response before obstacle-aware movement. Record failures as well as passes.
8. Review later branches individually for reuse. Change status to “Submitted” only after explicit confirmation.

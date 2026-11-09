# HARDWARE_VERIFICATION — sole physical qualification checklist

All items below are **PENDING / NOT VERIFIED**. No photos, labels, electrical measurements or hardware tests were collected during Phase 0/0.1. This is the authoritative register of unresolved module-specific questions; other documents define requirements and test methods.

For each item record specimen/assembly ID, exact manufacturer document/revision, date, setup, instruments, conditions, evidence path, result and reviewer. Do not mark passed from a simulator or seller title.

- [ ] **HV01 Batteries P1/P2/P3:** exact cell chemistry/configuration and age; pack/BMS continuous/transient/disconnect limits; polarity/connectors; charge and per-cell cutoff rules; cell balance, damage, safe resistance/sag and delivered-Wh tests.
- [ ] **HV02 Power bank and cable:** output profiles at 5 V, actual sustained/transient rating, cable resistance, Pi 4 boot/CV/camera/USB load voltage, low-load shutdown, multi-port renegotiation, pass-through behavior and remaining energy/OS shutdown indication.
- [ ] **HV03 Servos:** exact MG996R/MG995 variant for each joint, supply/temperature/pulse ratings, direction/ID, connector/lead current, unloaded/holding/gait/transient current and condition; ninth servo separate.
- [ ] **HV04 Converter:** exact SKU/topology, safe input window and dropout, fixed/adjusted accuracy, start/stop overshoot, load-step response, true continuous thermal capacity, peak duration, quiescent loss, current limit/hiccup, UV/OV/thermal protection and regeneration handling.
- [ ] **HV05 Distribution/protection:** PCA breakout schematic/copper/terminal ratings; external harness loop resistance, conductor/contact ratings, fuse time-current/I²t and interrupt coordination, DC disconnect rating, reverse protection, grounding and no branch-positive bridging.
- [ ] **HV06 OE and partial power:** actual pull-up/pull-down network, logic-only/servo-only states, boot/reset/high-impedance behavior, no phantom powering through PWM/I2C/USB, independent rail power-good/UV/OV latch and explicit restart.
- [ ] **HV07 Uno safety:** bootloader version and watchdog-reset compatibility, actual fuses/BOD configuration and 16 MHz voltage envelope, early reset/OE behavior, 1 s watchdog candidate tolerance/progress servicing, I2C fault propagation, stopped CPU and lost-Pi tests.
- [ ] **HV08 Physical stop:** accessible independently rated servo-power interrupt covering every branch, latched restart behavior and mechanical support; D12 is proposed status only, not a working circuit.
- [ ] **HV09 Calibration/mechanics:** fixture and first-movement procedure, safe neutral/endpoints/rates and evidence for each joint, software-profile/table compatibility, clearances, mount/cooling/cable strain, stable supported and unsupported gait acceptance.
- [ ] **HV10 Range modules:** URM37 revision/pin labels/mode/voltage and pulse conversion; HC-SR04 revision/echo level; blind zones, timeout, placement, acoustics/crosstalk and selected-source validity.
- [ ] **HV11 Touch modules:** model, supply/output topology/active polarity, placement, safety-versus-interaction classification, debounce/stuck-state behavior and cable noise.
- [ ] **HV12 Optional OLED/pan:** OLED controller/panel/address/3.3 V interface and pull-ups on Pi bus; measured display load; pan servo range/mount/profile/load and separate current-envelope approval.
- [ ] **HV13 Monitoring:** battery/servo-rail sense and power-good circuit, divider/max input/transient rating, ADC reference/error/filtering and unpowered leakage; thresholds must derive from HV01/HV03/HV04.
- [ ] **HV14 CSI/Pi measurements:** camera model/ribbon, correct colour/orientation, capture SensorTimestamp clock domain and metadata age, actual frame backlog/latency, resource load and recovery while driving/streaming.
- [ ] **HV15 Integrated evidence:** measured STOP→OE and STOP→torque response, browser/USB/Pi failure recovery, no automatic movement after rail restoration, temperatures, usable runtime and reproducible demonstration course limits.

Use [power test methods](../hardware/Power/TEST_PLAN.md), [calibration contract](CALIBRATION.md), [safety design](SAFETY.md), and [validation evidence](VALIDATION.md). Electrical approval remains blocked until the applicable items pass. Supported isolated-joint commissioning can begin only with a qualified limited-energy source, independently working disconnect and a reviewed fixture procedure.

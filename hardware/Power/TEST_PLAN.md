# Power qualification test plan

**Status: not performed.** Use the single [HARDWARE_VERIFICATION](../../docs/HARDWARE_VERIFICATION.md) checklist to record specimen IDs, instrument setup, conditions, evidence and approval. This page defines methods and pass/fail criteria, not results.

| Stage | Procedure | Acceptance evidence |
| --- | --- | --- |
| Identify | Photograph P1/P2/P3 labels/connectors, protection and cell details; match datasheets/charger | Exact chemistry, charge/cutoff/current/thermal ratings documented; no damage |
| Logic bank | Inspect output modes/cable; log Pi input during boot, camera + CV + USB Uno load | Official Pi 4 supply baseline met; design target ≥4.9 V at Pi under test, no undervoltage flags or USB resets |
| Bench converter | Use a current-limited safe source and controlled electronic load before servos | Correct polarity/setpoint and no unsafe startup/overshoot; input/output scope captures and thermal data |
| Dynamic load | Start small; step toward approved normal envelope and documented fault test using rated equipment | Normal step droop ≤0.25 V target; no unstable hiccup; fault response inhibits until explicit recovery |
| Thermal | Operate at approved high-load profile until thermal equilibrium | All components/connectors below their datasheet limits with documented ambient/airflow; no guessed surface-temperature threshold |
| Harness | Measure loop resistance, voltage at branch ends, contact rise and polarity | Drop and current ratings meet selected envelope; protection coordinates with weakest wire/contact |
| Pack characterization | Individually measure loaded sag, energy and temperature within approved limits | Pack/BMS/connector continuous and transient capability established; cell limits observed |
| Protection | Validate disconnect, polarity protection, current limit, branch fusing and rail supervision with safe simulated faults | No exposed uncontrolled fault path; no automatic torque after rail restoration |
| Partial power | Logic only, servo only, USB removal, Uno reset, converter failure simulation, low bank | No phantom powering or active PWM with unsafe state; physical stop independent |
| Supported robot | Commission one joint, then poses/gaits with logging and spotter/power disconnect | Approved calibration, no overloads/collisions; measured stop response, no replay |
| Runtime | Record average loads/usable Wh, camera/CV mode and battery conditions | Calculator updated from evidence; measured duration and safe cutoff published |

Do not short a battery or deliberately stall the assembled robot to prove a paper number. Use rated controlled loads and manufacturer-approved test procedures; destructive fault testing needs suitable equipment and protection. If a pack's identity/rating cannot be established, mark it unsuitable for multi-servo testing and use a qualified source instead.

Required traces include Vpack, Vconverter input/output, branch current, OE, reset and serial fault timestamps where available. Average handheld-meter current misses fast transients. Converter datasheets must authorize additional capacitance and wiring topology. Qualify soft-start, abrupt disconnect and any regeneration path.

A/B/D power-bank auto-shutoff at low load, multi-port renegotiation, boot surge and charger pass-through behavior require direct tests. Do not assume a bank supports simultaneous charging and robot operation.

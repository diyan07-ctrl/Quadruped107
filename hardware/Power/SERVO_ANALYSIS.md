# Servo current and concurrency

## Variant evidence

The current TowerPro MG996R page lists 4.8–6.6 V, 10 mA idle, 170 mA no-load movement and 1.4 A stall. A legacy TowerPro-labelled sheet reports 0.5–0.9 A running and 2.5 A stall at 6 V, with different voltage/travel claims. These are distinct planning cases, not interchangeable guaranteed specifications. See S7/S8 in [SOURCES](SOURCES.md). The provenance of the legacy sheet does not identify the installed motors.

Soldered's MG995 sheet states 4.8–6.6 V but gives no idle, running or stall current. Do not relabel MG996R values as MG995 measurements. Until identification and load characterization, the same conservative planning cases test distribution sensitivity but do not certify an upper bound for unknown MG995-family units.

`P = V × I`; `I_total = Σ(count × current_per_servo × duty_fraction)`. Groups explicitly identify support/moving/stalled servos; this avoids hiding every load behind one concurrency factor. A group duty of 1 means its already-assumed average current applies continuously during that scenario.

<!-- POWER_TABLE_START -->
| Scenario at 6V distribution output | A | W |
| --- | --- | --- |
| powered idle / PWM disabled allowance | 0.08 | 0.48 |
| no-load MG996R reference | 1.36 | 8.16 |
| standing assumption | 2.80 | 16.80 |
| walking mixed support | 4.20 | 25.20 |
| turning mixed support | 5.60 | 33.60 |
| high-load assumption | 7.20 | 43.20 |
| simultaneous acceleration allowance | 11.20 | 67.20 |
| three stalls lower / five moving | 7.70 | 46.20 |
| three stalls upper / five moving | 11.00 | 66.00 |
| eight stall lower bound scenario | 11.20 | 67.20 |
| eight stall upper bound scenario | 20.00 | 120.00 |
| nine stall upper bound scenario | 22.50 | 135.00 |
<!-- POWER_TABLE_END -->

## Engineering interpretation

Standing uses 0.35 A per joint as a torque-dependent assumption, not a measured holding current. Walking assigns four at 0.7 A and four at 0.35 A; turning uses four at 0.9 A and four at 0.5 A. Actual contact timing, mass, leverage, friction and acceleration are unknown. No-load 0.17 A does not size a standing robot.

The simultaneous-acceleration row is an 11.2 A stress allowance, not a claim that startup equals stall. Three joints near the upper stall case plus five moving joints require 11 A / 66 W. The eight-stall rows span 11.2–20 A / 67.2–120 W. These are theoretical simultaneous-stall cases under the stated per-servo assumptions; an unknown installed variant may exceed them.

The 9 A continuous target derives from 7.2 A high load × 1.25. It is a planning allowance, not a certified safety factor. Choose at least 10 A verified continuous converter capability for the eight-servo candidate. Its pulse, current-limit and shutdown behavior must be documented and tested separately from its continuous thermal rating. A 20 A load step need not be sustained indefinitely; overload should inhibit and require a new enable after investigation.

Servo leads, contacts and the distribution trunk experience load pulses even if the average is modest. Use separate positive branch protection, external distribution and short returns. Do not route all motor current through an unqualified PCA9685 terminal/PCB. Check individual servo connector and lead heating under the relevant stall case; a large trunk fuse alone cannot protect thin individual leads.

Optional pan adds a new joint, mass and branch load. A 2.5 A pan fault makes the 9-servo planning case 22.5 A / 135 W; it is outside the baseline power freeze.

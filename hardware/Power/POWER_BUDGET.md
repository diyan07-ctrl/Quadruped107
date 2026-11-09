# Power budget

Assumptions: 6 V converter/distribution output; eight powered leg servos; proposed full sensor inventory; one camera; variable bare-Pi allocation by workload. Logic includes Uno, PCA9685 and sensors once. Servo energy is drawn from its battery, logic from its independent power bank in A/B/D. See the calculator's COMPONENTS, SCENARIOS and BOUNDS definitions.

<!-- POWER_TABLE_START -->
| Scenario | Servo A | Servo W | Logic W | Total output W | Servo input W at 90% | Servo input A at 6V / 85% |
| --- | --- | --- | --- | --- | --- | --- |
| disabled_streaming | 0.08 | 0.48 | 6.055 | 6.535 | 0.633 | 0.111 |
| standing | 2.80 | 16.80 | 6.055 | 22.855 | 18.767 | 3.311 |
| slow_walking | 4.20 | 25.20 | 6.565 | 31.765 | 28.100 | 4.958 |
| turning | 5.60 | 33.60 | 7.075 | 40.675 | 37.433 | 6.605 |
| exploration | 4.90 | 29.40 | 8.095 | 37.495 | 32.767 | 5.781 |
| vision_standing | 2.80 | 16.80 | 8.095 | 24.895 | 18.767 | 3.311 |
| pan_oled_exploration | 5.10 | 30.60 | 8.194 | 38.794 | 34.100 | 6.017 |
| high_load | 7.20 | 43.20 | 8.095 | 51.295 | 48.100 | 8.487 |
<!-- POWER_TABLE_END -->

“Total output” combines energy domains for comparison; it is not current through one connector. Servo input columns include the converter's extra 0.1 W input reserve, not Pi power. Optional pan/OLED adds 0.2 A at 6 V and 30 mA at 3.3 V. Continuous exploration includes computer vision at a 1.2 A bare-Pi allowance; it is an engineering scenario, not implemented autonomous software.

The eight-servo fault case is 120 W at the 6 V source. At 85% conversion it demands 141.28 W input including reserve. The model peak logic allocations sum to 13.475 W, so the simultaneous budget envelope is 133.475 W output, across independent domains. This is not observed consumption. The optional ninth-servo case alone adds 15 W at its 2.5 A planning fault current.

High-load converter heat at 85% is 7.72 W including reserve. A 10 A continuous candidate has 38.9% current headroom over the modeled 7.2 A high-load average, not necessarily over real gait transients or changed geometry. Enclosure cooling must dissipate measured heat while maintaining component limits; no generic current label is accepted.

Input current increases as a constant-power converter sees lower battery voltage. Evaluate the full loaded battery range, BMS limits and connector loss; evaluating only 7.4 V nominal conceals the worst input demand. An inability to supply stall current is acceptable only with controlled current limiting/inhibition and protected wiring, not uncontrolled oscillatory brownouts.

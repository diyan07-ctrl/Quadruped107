# Component load inventory

The table separates **model allocations** from established specifications. Idle/active are powered-load planning values; the “peak allowance” column is not a measured or manufacturer-certified maximum. Actual peaks are unknown for every installed part. Confidence and source are listed per row, with links in [SOURCES](SOURCES.md). A1 means an explicit analyst assumption.

<!-- POWER_TABLE_START -->
| Component | Qty | Model V | Idle A/each | Active A/each | Peak allowance A/each | Active W total | Supply / range caveat | Source | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pi 4 bare board | 1 | 5.1 | 0.600 | 1.200 | 2.000 | 6.120 | 5V USB-C; qualify at connector | S1 | active/peak allowances; no measured peak |
| Uno R3 | 1 | 5.0 | 0.050 | 0.070 | 0.100 | 0.350 | USB 5V; not VIN | S2 | estimated board load |
| PCA9685 breakout logic | 1 | 5.0 | 0.010 | 0.015 | 0.025 | 0.075 | IC 2.3–5.5V; breakout verify | S3 | board allowance incl. LEDs |
| CSI camera incremental | 1 | 5.0 | 0.000 | 0.250 | 0.350 | 1.250 | Pi CSI; 5V-equivalent load, not direct feed | S1 | reference allowance; actual model unknown |
| URM37 | 1 | 5.0 | 0.020 | 0.020 | 0.050 | 0.100 | V5 reference 3.3–5.5V; verify revision | S4 | published active; peak unknown |
| HC-SR04 | 1 | 5.0 | 0.015 | 0.015 | 0.030 | 0.075 | 5V reference; module verify | S5 | published active; peak unknown |
| Touch module | 5 | 5.0 | 0.005 | 0.005 | 0.020 | 0.125 | unknown until module identified | A1 | low-confidence allocation only |
| Optional SSD1306 module | 1 | 3.3 | 0.005 | 0.030 | 0.050 | 0.099 | Pi 3.3V-compatible breakout only | S6/A1 | display-pattern dependent allocation |
| Eight leg servos | 8 | 6.0 | 0.010 | 0.700 | 2.500 | 33.600 | MG996R S7 4.8–6.6V; MG995 S9 4.8–6.6V | S7/S8/S9 | variant-dependent; scenario values |
| Optional pan servo | 1 | 6.0 | 0.010 | 0.200 | 2.500 | 1.200 | assume same family until identified | A1 | allocation, not actual pan specification |
<!-- POWER_TABLE_END -->

## Interpretation and duty assumptions

All quantities are per the inventory, not proof of a particular module revision. Logic supplies remain on continuously; URM37, HC-SR04 and five touch modules are included as continuous active allocations even though their drivers are future work. This is a future-complete allowance, not current software consumption. The camera uses a 5 V-equivalent incremental load drawn through CSI/internal Pi regulation; never wire a camera directly to 5 V.

Pi 4's 1.2 A active allowance is a design scenario, distinct from official typical bare-board current and the 3 A recommended supply capacity. Streaming/vision changes the selected Pi current in the scenario table. The main Pi supply must cover camera, USB Uno subtree, and other peripherals without double counting them. A fan/extra USB device must be added before approval.

Uno's board load excludes the separately listed PCA9685 and sensors. Its estimated subtree is 145 mA active and 305 mA peak allocation at 5 V, before the Pi/USB connector losses. Neither number overrides the Uno USB polyfuse, port current limit, or cable tests. The touch allocation is deliberately provisional; actual modules could exceed it.

Powered servos with PWM disabled may still consume current. Their 10 mA idle allowance is not a guaranteed disabled-current specification. Standing and walking do not use no-load current: they use separate torque/duty assumptions in [SERVO_ANALYSIS](SERVO_ANALYSIS.md).

Optional OLED ownership is on Pi's electrically compatible 3.3 V I2C interface, not Uno. Optional pan assumes a full-size servo until identified; its active model is 0.2 A and peak allocation 2.5 A, not a specification for an unknown ninth servo. OLED duty depends on pixels and contrast; 30 mA is an allowance.

Converter loss is output/efficiency minus output, plus an explicit 0.1 W per-converter input reserve. That reserve covers unknown low-load/quiescent/auxiliary costs and is not a datasheet current. Cable dissipation is already within power measured at the distribution output: do not add I²R to 6I unless modeling a higher regulated source setpoint. Separate voltage drop and heat are shown in [DISTRIBUTION](DISTRIBUTION.md).

## Optional Pi 5

Official guidance recommends a 27 W / 5 V 5 A supply; a 3 A supply restricts USB peripherals to 600 mA. Typical bare-board current is not a system peak. Treat Pi 5 as a separate requalification, including cable, camera connector, cooling and power-bank negotiation. No Pi 5 load is added to the primary Pi 4 model.

## USB power-bank decision

The existing bank is NOT YET QUALIFIED: its actual 5 V output rating, usable delivered energy and cable are unknown. Official Pi 4 guidance uses a 5/5.1 V, 3 A USB-C supply baseline. A bank advertised as 18 W at 9 V does not thereby supply 3 A at 5 V; never apply 9 V to Pi. Confirm USB-C current advertisement/compatibility and voltage at the Pi during boot and camera/CV load.

The peak planning allocations total 13.475 W, about 2.64 A at a 5.1 V source, including Uno/sensors/camera once; this is an allowance, not a measured peak or proof that every 3 A bank is sufficient. Pi 4 supports a 1.2 A total USB-peripheral budget; the modeled Uno subtree is 0.145 A active and 0.305 A peak allowance, so reserve USB current for any additional devices and stay within the main supply budget. CSI camera load is not a USB port load.

Use one USB path from bank to Pi and Pi to Uno. Do not simultaneously feed Uno 5V/VIN from another source, and do not rely on unknown charger pass-through or multi-port behavior. Cable droop, startup negotiation, automatic bank shutoff and Pi undervoltage/throttling must be logged during HV02 testing. Keep enough qualified bank reserve for an orderly OS shutdown; no bank runtime is asserted without delivered Wh.

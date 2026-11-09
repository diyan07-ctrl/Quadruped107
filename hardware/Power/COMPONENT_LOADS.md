# Component load inventory

The table separates **model allocations** from established specifications. Idle/active are powered-load planning values; the “peak allowance” column is not a measured or manufacturer-certified maximum. Actual peaks are unknown for every installed part. Confidence and source are listed per row, with links in [SOURCES](SOURCES.md). A1 means an explicit analyst assumption.

<!-- POWER_TABLE_START -->
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

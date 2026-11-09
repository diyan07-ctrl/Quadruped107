# Sources and confidence register

Reviewed 2026-11-09. Published specifications apply to the named reference product, not automatically to the installed module. No local load, battery, voltage or temperature measurements exist.

| ID | Primary or manufacturer-labelled reference | Used facts / limits |
| --- | --- | --- |
| S1 | [Raspberry Pi power guidance](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html) and [Pi 4 product brief](https://datasheets.raspberrypi.com/rpi4/raspberry-pi-4-product-brief.pdf) | Pi 4 recommended 5/5.1 V 3 A supply; USB peripheral budget; typical bare-board values and camera incremental allowance; these are not measured installed system peaks |
| S2 | [Arduino Uno R3](https://docs.arduino.cc/hardware/uno-rev3/) and [Uno USB protection description](https://docs.arduino.cc/retired/boards/arduino-uno-rev3-with-long-pins/) | USB logic power and 500 mA polyfuse behavior; board consumption remains estimated |
| S3 | [NXP PCA9685 datasheet](https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf) | IC supply 2.3–5.5 V; signal output, OE and power behavior; breakout trace/current capacity not specified by this IC document |
| S4 | [DFRobot URM37 V5 product](https://www.dfrobot.com/product-53.html) | Reference module 3.3–5.5 V / 20 mA; installed revision unverified |
| S5 | [ElecFreaks HC-SR04 sheet hosted by SparkFun](https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf) | Reference module 5 V / 15 mA; no installed idle/transient certification |
| S6 | [Solomon Systech SSD1306 sheet hosted by Adafruit](https://cdn-shop.adafruit.com/datasheets/SSD1306.pdf) | Controller/display architecture; board power depends on panel, charge pump and pixels; use explicit module allowance |
| S7 | [TowerPro MG996R current product page](https://towerpro.com.tw/product/mg996R/) | Reference current/voltage values; installed origin and variant unknown |
| S8 | [Legacy TowerPro-labelled MG996R datasheet mirror](https://components101.com/sites/default/files/component_datasheet/MG996R%20Datasheet.pdf) | 2.5 A stall / 0.5–0.9 A running at 6 V; provenance/revision differs from S7, not proof of installed identity |
| S9 | [Soldered MG995 manufacturer-labelled sheet via Mouser](https://www.mouser.com/catalog/specsheets/Soldered_109042.pdf) | Voltage/travel/torque specification; no usable current specification, and its weight fields differ internally |
| S10 | [Microchip lithium-ion charging application note](https://www.microchip.com/en-us/application-notes/an947) | Chemistry-specific charging principles; does not identify the user's packs or approve a cutoff |
| S11 | [Pololu D24V150F6](https://www.pololu.com/product/2882) | Real converter example with dropout, accuracy, efficiency and load/thermal limitations; not installation approval |
| S12 | [Gens ace 3S 2200 mAh 25C manufacturer listing](https://www.genstattu.com/gens-ace-2200mah-3s-25c-11-1v-lipo-battery-xt60-ec3-deans-air-classic/) | Available replacement class; capacity/current label is not measured qualification; no purchase or price claim |
| S13 | [Adafruit PCA9685 pinouts](https://learn.adafruit.com/16-channel-pwm-servo-driver/pinouts) | Separation of VCC/V+, OE and I2C logic; does not certify an unknown clone's terminal or copper |
| A1 | Analyst assumptions in power_budget.py | Standing/gait currents, touch/OLED/pan allocations, efficiency/usable-energy brackets, 20 mΩ path, 0.1 W reserve and headroom; all estimates |

Use component manufacturer documents and measurements over seller-title current claims. Inconsistencies are preserved as uncertainty rather than averaged into a fabricated rating. Runtime and design-envelope calculations are original engineering estimates derived from the named assumptions.

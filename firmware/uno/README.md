# Arduino Uno R3 firmware

[sketch/sketch.ino](sketch/sketch.ino) executes the inherited [motion tables](sketch/motion.h), owns PCA9685, and services USB commands during cooperative gait delays. No sensor drivers, physical stop input, or MCU hardware watchdog are implemented.

Disconnect servo power before flashing. With Arduino CLI installed:

```bash
arduino-cli core update-index
arduino-cli compile --profile uno firmware/uno/sketch
arduino-cli board list
arduino-cli upload --profile uno --port /dev/ttyACM0 firmware/uno/sketch
```

Run from repository root and replace the port. The profile pins AVR core 1.8.8, Adafruit PWM Servo Driver Library 3.0.2 and Adafruit BusIO 1.17.4. Arduino IDE users open sketch/sketch.ino, select Arduino Uno, and install the same library versions. Close Serial Monitor before the Pi application starts.

[Protocol](../../docs/PROTOCOL.md) · [Proposed wiring](../../docs/WIRING.md) · [Safe tests](../../docs/SAFETY.md). PWM is 50 Hz at address 0x40; D8 OE HIGH disables signals. A communication timeout is not a hardware watchdog. Do not flash archived UNO Q sketches to Uno R3.

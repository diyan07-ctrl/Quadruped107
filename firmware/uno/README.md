# Preserved Arduino firmware

**Academic development concluded; further development on hold.** See [project status](../../PROJECT_STATUS.md). The final ENR107 demonstration sketch is **not identified**. No program was selected, moved or rewritten simply because it has the newest commit.

## Inventory and purpose

| Location | Purpose and evidence |
| --- | --- |
| [sketch/sketch.ino](sketch/sketch.ino) | Maintained main-branch Uno R3 Pi/USB-command firmware: PCA9685 setup, individual SERVO commands and named movement routines. Compile/software evidence exists; final academic identity unconfirmed |
| [sketch/motion.h](sketch/motion.h) | Eight-channel targets and initial, stand, greeting, tail-wag, forward/backward and turn sequences; inherited values, not verified calibration |
| [Archived servo calibrator](../../archive/uno-q/servo-calibrator/sketch/sketch.ino) | Historical UNO Q Bridge application exposing set_servo_pulse for individual PCA9685 channels; incompatible with Uno R3 |
| [Archived control station](../../archive/uno-q/control-station/sketch/sketch.ino) | Historical UNO Q Bridge control/movement program; retained as experiment source |
| [Later sensor-only sketch](https://github.com/diyan07-ctrl/Quadruped107/blob/beddc8b/firmware/uno/sensor_only/sensor_only.ino) | Separate release-branch non-actuating range/touch telemetry experiment; profile-dependent acquisition, with mock/compile evidence and unresolved physical gates |
| [Later direct calibration sketch](https://github.com/diyan07-ctrl/Quadruped107/blob/beddc8b/firmware/uno/direct_calibration/direct_calibration.ino) | Separate release-branch gated one-servo commissioning experiment using direct D12 signal; not PCA9685 channel testing or a walking demo |

No separate Uno R3 PCA9685 channel-sweep test or final D5/D3 URM37 academic sketch was located in fetched history. Channel control is preserved in main's SERVO command and the archived calibrator. No hardware success is inferred from those implementations. Recovered bench-test/final sketches should retain their original versions and test provenance.

See the [closure audit](../../docs/ENR107_CLOSURE_AUDIT.md) for refs and evidence gaps. Later sensor and safety changes remain on their existing branches.

## Build and install the maintained Uno R3 program

Disconnect servo power before flashing. Arduino IDE: open sketch/sketch.ino, select **Arduino Uno**, install Adafruit PWM Servo Driver Library **3.0.2** and Adafruit BusIO **1.17.4**. Wire comes with AVR core **1.8.8**. The pinned [profile](sketch/sketch.yaml) supports Arduino CLI, from the repository root:

```bash
arduino-cli core update-index
arduino-cli compile --profile uno firmware/uno/sketch
arduino-cli board list
```

Only after verifying the intended board, wiring and port, a future upload uses:

```bash
arduino-cli upload --profile uno --port <verified-port> firmware/uno/sketch
```

Replace `<verified-port>` with the actual port. No upload or hardware test is part of closure. Archived UNO Q programs require Arduino_RouterBridge, Bridge and Monitor; do not flash them to Uno R3.

## Behavior and configuration conflicts

The maintained sketch starts disarmed at **115200 baud**. The [protocol](../../docs/PROTOCOL.md) provides HELLO, PING, ARM, STOP, SERVO and named MOVE commands. Heartbeats maintain a 1500 ms communication timeout; cooperative gait delays service input. A host is required, so it is not a self-starting academic demo. This main-branch version has no URM37 acquisition, physical stop input or MCU hardware watchdog. A cooperative timeout does not replace a hardware disconnect.

PCA address is **0x40**, requested PWM frequency **50 Hz**, channels **0–7**. Source names FL shoulder/leg 0/1, FR 2/3, BL 4/5 and BR 6/7. **Actual final wiring remains unknown.** The 50–600 count bounds are not an approved sweep range or joint calibration.

This sketch uses **D8 → OE** with an external 10 kΩ pull-up; HIGH disables outputs. The academic brief's **OE → GND** applies only to an appropriate different always-enabled setup. Do not ground OE while D8 drives it. [Historical wiring](../../docs/WIRING.md) assigns URM37 D4/D2 and optional HC-SR04 D5/D3, whereas the academic brief assigns URM37 D5/D3. No pins changed. Match the program to verified wiring before use.

[Academic wiring](../../README.md#wiring-and-pin-connections) · [Historical safety](../../docs/SAFETY.md) · [Historical validation](../../docs/VALIDATION.md).

# Sensor and accessory extension contracts

Physical sensor drivers and TEL1 remain unimplemented. Phase 2 implements only [virtual sensing and behaviors](PHASE2.md); its [UDP observation schema](SENSORS.md) is separate from this reserved physical contract. Uno owns range/touch acquisition and local safety policy; Pi owns display, tracking, telemetry presentation and high-level scheduling. All future motion requests use the same controller; local inhibition outranks them.

| Extension | Proposed ownership / wiring | Rate / freshness | Invalid/failure behavior |
| --- | --- | --- | --- |
| URM37 primary | Uno D4 trigger / D2 pulse input; verify mode/revision | 5 Hz; host age ≤300 ms | Invalid/expired range inhibits exploration locally; never treat no echo as clear |
| HC-SR04 optional fallback | Uno D5 trigger / D3 echo | 5 Hz when selected; stagger acoustic measurements | No seamless fallback until calibrated validity is established; no concurrent pings |
| Touch 3–5 | Uno D6/D7/D9/D10/D11 | 100 Hz scan, initial 20 ms debounce target; publish 5 Hz | Stuck/invalid input blocks dependent behavior; classify safety vs interaction contacts before enabling |
| Pack and servo-rail monitor | Uno A0 / A1 after qualified divider/supervision; hardware latch independent | 10 Hz scan, 5 Hz reports, ≤300 ms age | Missing/unsafe power-good inhibits motion; thresholds are pack/servo specific |
| OLED expression | Pi I2C1, physical 3 SDA / 5 SCL, 3.3 V-compatible module | 5 Hz max animation target | Missing display never delays control or stops telemetry |
| Pan servo | Uno/PCA channel 8, separate profile/power qualification | PWM 50 Hz; requested targets ≤10 Hz | Default off, bounded speed/limits, no automatic startup sweep |
| Person/object tracking | Pi camera/vision worker; inference publishes fresh bounded intent only | Design ≥10 fresh frames/s; intent TTL 500 ms | Drop stale inference; camera age fault inhibits that mode |

## TEL1, an additive protocol-v1 extension

Future firmware must continue the exact READY Quadruped107 1 handshake and all v1 commands. After HELLO, an upgraded host can optionally request CAPS <id>. An upgraded Uno accepts this while disarmed and replies DONE <id> caps_tel1. An old Uno can reply ERR (including disarmed/unknown_command); the host then disables telemetry features, does not arm, and does not retry motion or disconnect solely for missing capability.

An upgraded host may then request TELEM <id> <rate_hz>, with rate 0 to disable or 1–10. Uno replies DONE <id> telemetry. Default is disabled after boot/HELLO. This negotiation and these verbs are reserved contracts; current SerialLink/firmware do not send or accept them.

Unsolicited LF-terminated ASCII record:

```text
TEL 1 seq uptime_ms range_mm source flags touch_mask pack_mv servo_mv
TEL 1 42 123456 380 1 15 3 7600 5980
```

seq is uint16 with wrap; uptime_ms is uint32 milliseconds with wrap. range_mm is -1 when invalid, otherwise 0–9999; source 0=none, 1=URM37, 2=HC-SR04. flags is decimal uint16: bit0 range valid, bit1 touch valid, bit2 pack valid, bit3 servo-rail valid, bit4 local inhibit, bit5 overload latch, bit6 watchdog reset seen, bit7 calibrated profile active; other bits reserved zero. touch_mask uses only bits 0–4 and represents contacts held or debounced-asserted during the current scheduled reporting interval. Coalesce short touch assertions between reports; reset interval history after each scheduled report (including a dropped telemetry frame) and on HELLO/stream reconfiguration, so old touches never replay after reconnect. Local safety uses the live 100 Hz debounced state independently; telemetry is best-effort and does not guarantee delivery of every individual tap. Voltage fields are -1 if invalid, otherwise integer 0–65535 mV. “Valid” requires a fresh bounded local acquisition and conversion; example values are illustrative, not measurements.

Worst-case defined fields fit within 63 characters before LF. At 5 Hz and about 60 bytes/line, telemetry is roughly 300 bytes/s, small relative to 115200 8N1 capacity (11,520 bytes/s). Use a bounded fixed buffer and transmit only if UART space is available; drop telemetry instead of blocking STOP/gait service. Critical faults still emit the existing FAULT line and latch locally, even when telemetry is disabled.

Host timestamps complete records with monotonic receive time, rejects malformed/out-of-range fields and duplicates, handles unsigned wrap deltas, and expires range/power/touch status after 300 ms. A new session resets sequence history. Local policy uses acquisition age, not host receive age; link latency must not turn an old reading into fresh motion evidence. Current v1 hosts ignore unrelated lines, so TEL1 cannot complete a motion acknowledgment.

## Uno resource gate

Baseline compile: 10,198 bytes flash and 998 bytes global SRAM; 1,050 bytes remain for stack/locals. Proposed additions: compact eight-joint limits/rates about 80 bytes, sensor/telemetry state about 32 bytes, reused output scratch up to 64 bytes. That yields about 1,174 bytes globals before library growth, not a compile result.

Targets: ≤1,300 bytes globals, ≥400 bytes measured worst-case stack margin, ≤28 KiB application flash. Recompile and measure stack high-water after every added driver, including nested gait/parser/fault paths. Do not enable all optional features simply because they have reserved pins. No dynamic String, large JSON object or 1,024-byte OLED framebuffer belongs on Uno.

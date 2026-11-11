# Sensor and accessory extension contracts

Phase 5 implements a separate non-actuating Uno sensor target, optional TEL1/TEL2 negotiation and physical monitoring through the existing SensorManager. The original production target remains separate and rejects physical ARM pending commissioning. Phase 2 [virtual sensing and behaviors](PHASE2.md) and its [UDP observation schema](SENSORS.md) remain intact. Uno owns range/touch acquisition; Pi owns display, tracking and scheduling. Physical monitoring never qualifies actuator control. See [software-readiness qualification](SOFTWARE_READINESS.md) for tests and hardware procedures.

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

The sensor target preserves the exact `READY Quadruped107 1` handshake, HELLO, PING and STOP; ARM/MOVE/SERVO always return `sensor_only`. After HELLO, the host requests `CAPS 0`. This target replies `DONE 0 caps_sensor2_tN`, where N is 0, 3, 4 or 5 configured touch inputs. Gated production replies `caps_actuator_gated`. Old firmware may reply ERR (including disarmed/unknown_command); the host disables telemetry negotiation without arming, retrying motion or disconnecting solely for missing capability. Unknown capability tokens grant nothing. Request ID 0 is reserved for negotiation during normal operation; exhaustion STOP 0 still completes normally.

`TELEM <id> <rate_hz>` enables diagnostic TEL1 emission (0 disables; 1–10 selects maximum reports/s). `TELEM <id> <rate_hz> 2` selects poll-bounded TEL2. The response is `DONE <id> telemetry`. Boot/HELLO disables both. Current SerialLink selects TEL2 at 5 Hz only after the exact sensor capability token. The sensor target emits both versions; production does not emit sensor telemetry. The host never sends ARM during negotiation.

Unsolicited LF-terminated ASCII record:

```text
TEL 1 seq uptime_ms range_mm source flags touch_mask pack_mv servo_mv
TEL 1 42 123456 380 1 15 3 7600 5980
```

seq is uint16 with wrap; uptime_ms is uint32 milliseconds with wrap. range_mm is -1 when invalid, otherwise 0–9999; source 0=none, 1=URM37, 2=HC-SR04. flags is decimal uint16: bit0 range valid, bit1 touch valid, bit2 pack valid, bit3 servo-rail valid, bit4 local inhibit, bit5 overload latch, bit6 watchdog reset seen, bit7 calibrated profile active; other bits reserved zero. touch_mask uses only bits 0–4 and represents contacts held or debounced-asserted during the current scheduled reporting interval. Coalesce short touch assertions between reports; reset interval history after each scheduled report (including a dropped telemetry frame) and on HELLO/stream reconfiguration, so old touches never replay after reconnect. Local safety uses the live 100 Hz debounced state independently; telemetry is best-effort and does not guarantee delivery of every individual tap. Voltage fields are -1 if invalid, otherwise integer 0–65535 mV. “Valid” requires a fresh bounded local acquisition and conversion; example values are illustrative, not measurements.

Worst-case defined fields fit within 63 characters before LF. At 5 Hz and about 60 bytes/line, telemetry is roughly 300 bytes/s, small relative to 115200 8N1 capacity (11,520 bytes/s). Use a bounded fixed buffer and transmit only if UART space is available; drop telemetry instead of blocking STOP/gait service. Critical faults still emit the existing FAULT line and latch locally, even when telemetry is disabled.

Host timestamps complete records with monotonic receive time, rejects malformed/out-of-range fields and duplicates, handles unsigned wrap deltas, and expires range/power/touch status after 300 ms. A new session resets sequence history. Local policy uses acquisition age, not host receive age; link latency must not turn an old reading into fresh motion evidence. Current v1 hosts ignore unrelated lines, so TEL1 cannot complete a motion acknowledgment.

## TEL2 acquisition-age monitoring extension

After exact `caps_sensor2_tN` negotiation and `TELEM 0 5 2`, the Pi sends `POLL 0 <token>` at 5 Hz. Tokens are uint16, scoped to the HELLO/connection session; only outstanding polls no older than 300 ms can validate a record. The firmware responds at no more than the negotiated rate, uses the latest pending token, and never blocks to wait for UART space:

```text
TEL 2 seq uptime_ms range_mm source flags touch_mask range_age_ms touch_age_ms token faults
TEL 2 0 640 400 1 19 0 37 0 42 0
```

TEL2 keeps sequence/uptime/range/source/flags/touch definitions above, omits unavailable voltages, and adds ages (0–999 ms, saturating at 999), echoed token (0–65535) and fault byte. Flag bit4 is always set: this target is permanently locally inhibited. Fault bits: 0 unconfigured URM37, 1 timeout/invalid/out-of-range acquisition, 2 stuck touch, 3 latched heartbeat watchdog. AVR watchdog reset indication retains flag bit6 where bootloader/reset-cause retention allows it. Unconfigured range is source 0, value -1, validity false. No pack, rail or calibrated-profile validity is asserted. Touch capability N prevents an absent fourth/fifth configured input from being invented by the host.

Range age is measured from captured echo completion, including foreground service delay. Touch age is measured from the oldest coalesced assertion in the report interval, or the latest scan for an empty mask. Interval history clears on every scheduled report including drop, HELLO and TELEM reconfiguration. Pressed-at-boot inputs require debounced release before touch validity; held inputs become invalid at two seconds. POLL replacement is bounded; telemetry remains best effort and does not guarantee every tap.

The host bounds total age by `firmware_age + full_poll_round_trip + elapsed_since_receive`. It does not assume clock synchronization or halve the round trip. Duplicate/reused/expired tokens, duplicate/backward sequence, uptime resets outside a new session, malformed/reserved values and version changes in a stream are rejected. Sequence gaps count dropped frames. Poll tokens are freshness correlation, not authentication; the serial peer and ordered USB session are trusted and must be reset/drained on reconnect. Every reconnect clears observations/polls and stays disarmed. Unknown capabilities cannot authorize telemetry features or motion. Rates above 5 Hz do not increase the 5 Hz range acquisition cadence, and the 300 ms limit is unchanged.

TEL1 reception still exposes receive freshness only and remains diagnostic-only. TEL2 exposes acquisition bounds but **always** reports `controlQualified=false`: missing swept-clearance/fallback and electrical safety evidence prevent physical navigation. Passive TEL1 records cannot qualify the physical SensorManager source. Telemetry and capability records cannot complete motion ACKs or authorize ARM.

## Uno resource gate

Baseline compile: 10,198 bytes flash and 998 bytes global SRAM; 1,050 bytes remain for stack/locals. Proposed additions: compact eight-joint limits/rates about 80 bytes, sensor/telemetry state about 32 bytes, reused output scratch up to 64 bytes. That yields about 1,174 bytes globals before library growth, not a compile result.

Targets: ≤1,300 bytes globals, ≥400 bytes measured worst-case stack margin, ≤28 KiB application flash. Recompile and measure stack high-water after every added driver, including nested gait/parser/fault paths. Do not enable all optional features simply because they have reserved pins. No dynamic String, large JSON object or 1,024-byte OLED framebuffer belongs on Uno.

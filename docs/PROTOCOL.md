# Protocol v1 and reserved telemetry extension

## Phase 2 additive sensor telemetry

See [SENSORS](SENSORS.md) for the complete bounded schema. Correlated v1 simulation ACKs may contain sensors={schema:1,seq,observations:[...]}; range unit is metres and source age is preserved plus a conservative round-trip allowance. Duplicate/out-of-order or stale telemetry cannot renew sensing. activeMotion and behavior are bounded additive trace metadata for diagnostics and the explicit proxy.

A host virtual-Uno stopEpoch prevents stale ready flags from permitting ARM after STOP. The bridge must acknowledge a fresh disarmed trace for the current stop epoch. This is host simulation metadata, not a change to serial v1 or physical firmware. Reserved TEL1 remains unimplemented; future adapters must convert millimetres explicitly. All physical protocols and fail-closed production behavior remain unchanged.


## Explicit virtual execution and trace extension

Production serial v1 syntax/baud/ACK semantics below are retained. The host [VirtualUno](../software/pi/quadruped/virtual_uno.py) is an in-memory emulator behind the actual SerialLink worker, selected only with --actuator-backend virtual. It models safe startup, ARM without pose replay, original gait target ticks, ACCEPT/DONE, busy/invalid errors, priority STOP, 1.5 s communication watchdog and reset/reconnect disarming. Eight targets are commanded estimates; activeMask identifies channels actually driven in the model.

[Generated virtual firmware](../tools/generate-virtual-firmware.py) copies production sources into ignored build/virtual/sketch, substitutes a no-I2C/no-GPIO PCA output stub, emits bounded TRACE lines and identifies as Quadruped107Virtual. The production host intentionally rejects that distinct hardware identity. This build is compiled in CI; it is not uploaded or exercised on a board. Production firmware remains unchanged and fails closed without its PCA.

The [UDP trace extension](../simulation/README.md) is a separate laptop visualization protocol, not a replacement for serial v1. Packets are JSON objects: v=1, type hello/challenge/trace/ack/stop, random client/server sessions, one-use nonce and monotonically increasing seq. A trace additionally includes virtual=true, armed boolean, eight integer targets 50..600 and activeMask 0..255. Maximum packet size 2048 bytes; receiver processes ≤8 per poll. Challenges expire at 150 ms receiver-local age, accepted traces lease forces for 300 ms. Invalid/duplicate/out-of-order frames do not renew the lease.

A new receiver epoch, receive timeout or explicit STOP inhibits output. STOP invalidates outstanding challenges; a disarmed frame must precede any new ARM. The Pi guard also disarms on missing acknowledgments; application re-enable is explicit. Trace snapshots may skip intermediate ticks and never replay old motion commands. Trusted private LAN only; random sessions reject accidental replay, not a hostile authenticated peer.


USB serial is unchanged: ASCII lines, LF terminated, CR ignored, 115200 baud / 8N1, no flow control. Uno accepts at most 63 characters before LF; overflow discards through LF and returns ERR 0 line_too_long. Binary/NUL input is unsupported.

## Implemented commands

```text
HELLO                    -> READY Quadruped107 1
PING                     -> PONG
ARM 1                    -> DONE 1 armed
MOVE 2 forward           -> ACCEPT 2 forward
                            DONE 2 forward
STOP 3                   -> DONE 3 stopped
SERVO 4 0 278            -> DONE 4 servo
```

HELLO and boot leave outputs disabled. ARM enables signals without selecting a pose. MOVE runs exactly one named routine: initial, stand, greeting, tail_wag, forward, backward, turn_left, turn_right. SERVO accepts channels 0–7, ticks 50–600; these are broad guards, not qualified joint limits. Optional channel 8 remains rejected by current firmware.

IDs are decimal. Pi limits normal IDs to 11 digits so MOVE's saved buffer is not exceeded. ID 0 is reserved for parser/best-effort stop; if normal IDs exhaust, new ordinary work is rejected and STOP can still use 0. Restart disarmed to reset the sequence. Firmware does not deduplicate requests; only matching DONE/ERR completes a host request, never ACCEPT/PONG or an unrelated ID.

Errors include invalid_id, pca9685_missing, busy, disarmed, invalid_motion, argument_too_long, unknown_motion, invalid_servo, servo_out_of_range, unknown_command, stopped and line_too_long. Validation order depends on driver/arming/busy state. Unknown MOVE may receive ACCEPT then ERR unknown_motion. MOVE/SERVO reject trailing tokens; HELLO/PING/ARM/STOP currently tolerate them. Send only strict forms.

## Phase 0.1 host transaction policy

The worker has up to four ordinary pending requests, including sent work, and a separate single urgent STOP slot. Repeated STOP calls coalesce until completion. STOP immediately marks the host disarmed, cancels ordinary pending requests with stopped, clears the ordinary queue and increments a cancellation barrier. Late ARM/DONE replies from older requests cannot set armed state.

Submission is nonblocking with respect to queue space; excess ordinary work rejects immediately. An ordinary request older than 250 ms at dispatch or past its completion deadline faults the link instead of being sent. New ARM/MOVE/SERVO reject while STOP is unacknowledged. ARM rejects while other ordinary requests are pending. Capacity and barrier checks also apply to direct transport callers.

The worker sends urgent work before ordinary work and heartbeat servicing. A request already in an OS write cannot be retracted; the transaction lock can wait for the configured 500 ms write timeout. Bytes already buffered at Uno may be parsed before STOP. This priority policy is not a guaranteed physical stop time.

Controller state locks are released during acknowledgment waits. ARM/SERVO/MOVE reserve one active controller ticket; STOP does not wait for that ticket's acknowledgment. Generations reject old HTTP arm/mode/calibration/heartbeat requests and prevent late completion from reviving stopped intent. Unsent poses/directions expire after 500 ms, with matching owner heartbeats renewing a held direction; stand is retained as the safe release request.

## Timeouts, faults and recovery

Host waits 2 s after opening USB, clears input, then sends HELLO and verifies exact identity within 3 s. PING cadence is 300 ms; missing PONG for 1.2 s fails the link. ARM/SERVO completion timeout is 3 s, STOP 2 s, MOVE 20 s. Read timeout is 50 ms and write timeout 500 ms. Partial command writes and malformed/truncated responses fault the session.

Uno's existing >1500 ms PING timeout is software serviced during cooperative waits. It emits FAULT watchdog after disabling outputs; driver initialization failure emits FAULT pca9685_missing. Unexpected READY or any FAULT during a session fails pending commands and discards queues. Runtime I2C failures are not comprehensively detected.

On timeout, disconnect or reset, no motion replays. Reconnection repeats HELLO, stays disarmed and requires explicit enable. Controller fault reason remains latched until a fresh ARM completes in the same generation/session. The independent MCU watchdog/physical-stop/rail circuits are designed but not yet implemented/qualified.

## HTTP ownership compatibility

JSON bodies, URLs and browser assets remain unchanged. POST /api/arm now sets an HttpOnly SameSite=Strict quadruped_control cookie. Non-browser clients must retain it for mode, calibration and heartbeat calls; first ARM claims ownership. Non-owners receive HTTP 409; STOP is available regardless of owner. Cookie values are not telemetry and must not be logged or committed. This is a deliberate safety tightening, not authentication or a new wire protocol.

## Telemetry

Current v1 supplies identity, heartbeat, completion and fault status only; there are no range, touch, voltage or measured-position values. The optional negotiated CAPS/TELEM/TEL1 contract is specified in [EXTENSIONS](EXTENSIONS.md), including framing/ranges, sequence wrap, validity and expiry. It is not activated in Phase 0.1. Old peers retain existing behavior and must not arm or repeatedly retry because telemetry capability is absent.

## Phase 3 passive telemetry preparation

The host now passively recognizes the reserved [TEL1 record](EXTENSIONS.md). It bounds ASCII records to 63 characters, validates fields/flags, handles sequence and uptime wrap, rejects duplicates/backward records and expires receive freshness after 300 ms. A new serial session resets history. TEL lines cannot complete pending ARM/MOVE/STOP acknowledgments. No CAPS/TELEM command is sent and firmware remains unchanged.

Diagnostics explicitly report controlQualified=false and acquisitionFreshnessKnown=false. TEL1 lacks an output-enable field, so servoOutputsEnabled is null, never inferred from voltage or armed intent. Distance, touch, voltage, inhibit, overload and watchdog flags are exposed only according to validity/freshness. A future negotiated revision must carry acquisition age and actual OE state before safety use; no reserved bit is assigned silently.

# USB serial protocol v1

This specifies the inspected implementation, including its limitations. Keep existing commands compatible during the repository refactor. Historical UNO Q Bridge RPC is a different interface and is archived.

## Framing and identity

USB serial uses 115200 baud, 8 data bits, no parity, one stop bit, no flow control. ASCII lines end with LF; Uno ignores CR. The Uno buffer accepts 63 characters before LF; longer lines are discarded through LF and yield ERR 0 line_too_long. Spaces separate tokens. Only known ASCII tokens should be sent; binary/NUL input is unsupported.

Pi waits 2 s after opening the port for Uno reset, clears input, sends HELLO and expects exactly READY Quadruped107 1 within 3 s. Firmware also emits READY at boot. HELLO disarms. Unexpected READY during normal operation is treated as reset and drops the link.

## Commands and replies

```text
HELLO                    -> READY Quadruped107 1
PING                     -> PONG
ARM 1                    -> DONE 1 armed
MOVE 2 forward           -> ACCEPT 2 forward
                            DONE 2 forward
STOP 3                   -> DONE 3 stopped
SERVO 4 0 278            -> DONE 4 servo
```

ARM enables OE only if the PWM driver initialized and no motion is active; it does not choose a pose. MOVE requires arming and runs one complete named routine. Valid names: initial, stand, greeting, tail_wag, forward, backward, turn_left, turn_right. Directional repetition is a Pi scheduling decision, not a latched Uno command.

SERVO takes channel 0–7 and integer PCA9685 ticks 50–600; it writes immediately, without joint-specific limits or a ramp. Current pan channel 8 is reserved and rejected. STOP inhibits outputs even when disarmed or driver initialization failed. A stopped MOVE eventually returns ERR with its original ID.

## IDs and parsing details

Pi assigns monotonically increasing decimal IDs per process. Only DONE/ERR with a matching pending ID completes a request. ACCEPT does not complete it, PONG is independent, and unrelated IDs are ignored. ID 0 is reserved by convention for parser errors and best-effort shutdown STOP. Firmware does not deduplicate requests or replay cached results.

The MOVE parser copies IDs into a 12-byte buffer, so use at most 11 digits (Pi currently has no rollover policy). Firmware validates IDs as decimal strings; it does not require uniqueness. MOVE names fit a 20-byte buffer. Extra arguments are rejected for MOVE/SERVO; HELLO/PING/ARM/STOP currently tolerate trailing tokens. Clients must emit the strict forms above rather than relying on this tolerance.

Typical errors: invalid_id, pca9685_missing, busy, disarmed, invalid_motion, argument_too_long, unknown_motion, invalid_servo, servo_out_of_range, unknown_command, stopped, line_too_long. Error checking order depends on driver, arming and busy state. An unknown named MOVE can receive ACCEPT followed by ERR unknown_motion. Recover from validation errors by fixing the request; never automatically resend motion after link failure.

## Heartbeats, faults and recovery

Pi sends PING every 300 ms, including while MOVE is pending. No PONG for 1.2 s drops the link. Uno checks for more than 1500 ms without PING while armed and emits FAULT watchdog after disabling outputs. ARM initializes this timeout. The watchdog is a loop-serviced communication timeout, not an AVR hardware watchdog.

Boot driver failure reports FAULT pca9685_missing. Runtime I2C failures are not fully surfaced. Any FAULT received by Pi drops the session, fails pending commands and clears the queue. Read timeout is 50 ms; write timeout is 500 ms. ARM and SERVO calls use 3 s command timeouts, STOP uses 2 s, and MOVE defaults to 20 s. A command timeout forces reconnection.

One worker owns serial reads and writes. STOP is serviced during cooperative gait delays but currently shares the outgoing FIFO; it has no separate hardware or queue-priority channel. Unplug, reset, handshake failure, command timeout or unexpected READY causes pending requests to fail; no queued motion is replayed. Reconnection repeats HELLO and leaves outputs disabled until explicit ARM. Opening USB may reset Uno; use a stable by-id path where possible.

## Telemetry and compatibility

v1 provides identity, completion, heartbeat and fault lines only. Pi exposes these plus camera/mode state through GET /api/state. It does not receive distance, touch, battery, or joint-position telemetry.

A later sensor phase must define a versioned unsolicited sensor record with freshness/validity before implementation. Do not emit unversioned sensor text into this channel or describe unsupported telemetry as available. Existing v1 lines remain stable unless a reviewed engineering change includes host/firmware compatibility tests. Protocol v1 framing and baud are unchanged by Phase 0.

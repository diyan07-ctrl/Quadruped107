# Unified virtual sensor contract

[Sensor implementation](../software/pi/quadruped/sensors.py) contains SensorBackend, SensorConfig, SensorObservation and SensorManager. No physical driver is implemented. Internal distance unit is **metres**; dashboard displays metres. Future TEL1 millimetres must be converted explicitly by a qualified adapter.

## Observation and health

Each observation has stable identity/type, monotonic acquisition estimate, measurement/unit, validity, freshness, health and error. Snapshot health is OK, INVALID, STALE or STUCK; missing records are absent and critical policy reports a fault. No missing/invalid value means infinite clearance.

Defaults in [sensors.example.json](../deploy/sensors.example.json): valid range 0.02–4.0 m, acquisition/update target 10 Hz, reported acquisition timeout 0.3 s, expiration 0.3 s, debounce 30 ms, stuck threshold 2 s, conflicting front ranges differing by >0.2 m, five touches. Three/four touches are supported with matching sender/receiver configuration. Unknown hardware limits are not inferred from these defaults.

Two front range IDs are urm37 and hcsr04. Both are required by this virtual profile; disagreement or missing either inhibits motion. This is conservative virtual redundancy, not automatic hardware failover. Touch IDs are touch_head/back/left/right/body, truncated to the configured count. Head/back are interaction candidates; side/body are safety contacts. Placement and roles are provisional.

sweep_forward/left/right/reverse are **additional simulator geometry evidence**, not ultrasonic readings or capabilities attributed to a real module. They must be valid and fresh to authorize their associated movements.

Touch transitions are debounced using local monotonic time. Press and release events have increasing IDs and freshness. Boot/reconnect while already pressed creates no new interaction. Events expire, logs cap at 64, a held press does not retrigger, and a stuck or invalid input inhibits. All released input is required before explicit enable.

## Additive UDP telemetry schema 1

The existing trace transport stays v1, bounded to 2048 bytes. Correlated acknowledgments may add:

```json
{
  "sensors": {
    "schema": 1,
    "seq": 42,
    "observations": [
      {"id":"urm37","kind":"range","value":0.8,"valid":true,"age":0.02,"error":null}
    ]
  }
}
```

This shortened example omits other required profile records; it would inhibit navigation. At most 16 observations are accepted; the default complete profile has 11. Kinds: range, touch, clearance. Distances must be finite numbers in configured limits; touch/clearance values must be exact booleans. Invalid records carry null value and bounded error text. Duplicate identities, unknown types, malformed payloads and invalid sequence numbers are rejected atomically.

Sequence numbers are nonnegative integers below 2^31, increasing within one receiver epoch. Duplicates/out-of-order batches do not refresh evidence. New sessions clear observations/debounce/events; this never arms. An absent record replaces old evidence rather than retaining it.

age is sender-local monotonic age since acquisition, including simulated latency/polling. The client adds the correlated trace round-trip interval as a conservative transport-age allowance. No synchronized clocks are assumed. Source age is preserved when a telemetry cache is reused; a new packet cannot relabel an old acquisition as fresh. Expiration uses the resulting acquisition estimate.

Only an ACK for the outstanding nonce/sequence/current server is delivered to the sensor manager. Unexpected senders, oversized/nested malformed packets, expired challenges, delayed/duplicate ACKs and old epochs cannot renew control. Missing sensor fields leave prior evidence aging toward inhibition. Simulator reset or missing ACK lease separately stops the controller. STOP epochs additionally require acknowledgment of a **fresh disarmed trace** before re-arm; stale ready flags cannot satisfy that barrier.

Original serial v1 and the reserved [TEL1 contract](EXTENSIONS.md) are unchanged. This UDP extension does not implement CAPS/TELEM/TEL on physical Uno firmware. Phase 1 receivers can ignore additive metadata; Phase 2 sensing refuses to arm without its complete valid profile.

## Resource and fault boundaries

One atomic latest batch; 64 touch events; 128 navigation transitions; bounded virtual-Uno history/queues and eight datagrams per receiver poll. Sensor callback STOP never waits for an acknowledgment. Controller dispatch and an independent 50 ms guard check sensing again. CPU timing targets are policies, not measured Pi guarantees. A blocked native camera cannot stall this independent path.

Malformed telemetry does not acquire control; no networking is authenticated. Use loopback/trusted private LAN only. Tests use explicit fixtures; no physical missing-device fallback exists.

## Future hardware verification

URM37 revision, mode, pin labels, supply, trigger/echo or serial interface and voltage levels must be identified from the actual module before wiring. HC-SR04 revision, supply, echo levels, timing, acoustic crosstalk and safe voltage interfacing also require verification. Proposed Uno assignments remain in [WIRING](WIRING.md). Stagger actual ultrasonic acquisitions; simultaneous virtual rays do not validate real acoustic behavior.

Physical touch polarity, pull-ups, placement, stuck behavior and safe roles require tests. Independent local Uno inhibition, telemetry adapter negotiation, power qualification and stop-distance measurements remain unimplemented hardware work. See [verification](HARDWARE_VERIFICATION.md) and [safety](SAFETY.md).

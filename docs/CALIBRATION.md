# Calibration architecture v1

## Digital-twin conversion

No physical calibration changed. [Model parameters](../simulation/model/parameters.json) provide a separate provisional mapping: channels 0–7, inherited stand tick as zero, tick bounds 50..600, direction +1 and piecewise ±1.2 rad. These are simulation-only assumptions, not measured servo endpoints or valid physical limits. ARM leaves activeMask zero until an explicit command; the starting numeric tick estimate does not assert position feedback.

The [motion generator](../tools/generate-motion-data.py) checks the original firmware table hash/values and reviewed routine order. Original spreadsheets and gait arrays remain unchanged. See [model provenance](../simulation/README.md).


The existing gait table is preserved byte-for-byte. The new [profile template](../hardware/calibration/profile.example.json) is deliberately unqualified with null endpoints. [calibration.py](../software/pi/quadruped/calibration.py) validates profiles and calculations offline; it is **not connected to the live scheduler or firmware**, and does not make current calibration commands joint-safe.

## Data contract

Profile fields: schema_version=1, positive revision, assembly-specific robot_id, pwm_hz=50, and eight joint records (optional ninth camera_pan). Each record contains stable id, channel, min_tick, neutral_tick, max_tick, direction (+1/-1), max_ticks_per_second, qualified boolean and evidence reference. Leg IDs/channel 0–7 are fixed to the existing map; optional pan is channel 8.

Template direction=+1 and 50 ticks/s are placeholders, not measured settings. The strict validator rejects unqualified profiles, duplicate/missing channels, unsupported versions, invalid rates and out-of-order limits. Qualified endpoints must fit current 50–600 firmware guards. A future profile activation path must also check immutable assembly ID, table/profile compatibility, firmware capabilities and checksum.

Direction describes increasing logical joint motion versus pulse direction; it does not turn ticks into measured angles. Use a per-joint mechanical calibration curve if angles become necessary. Tick-to-pulse conversion is `microseconds = ticks × 1,000,000 / (4096 × actual_PWM_Hz)`; use measured frequency/oscillator calibration for accuracy. At nominal 50 Hz, 300 ticks is 1464.84375 µs.

## Limits, speed and storage

Reject targets outside a qualified joint interval rather than silently clamping a multi-joint gait into a different pose. Rate-limit changes by max_ticks_per_second × elapsed_seconds, cap ramp update age at 100 ms, and drop stale ramp updates rather than jumping ahead. The pure ramp helper refuses an unknown starting position. These helpers do not alter the current firmware's fixed step ramps.

Keep reviewed profiles in version-controlled JSON with a revision and evidence files. Pi validates and retains the human-readable record; the later Uno representation uses compact fixed-width integers, schema/revision/CRC and an atomic dual-slot EEPROM update with wear budgeting. No repeated EEPROM writes during walking. After upload, read back identity/CRC before allowing motion. Initial leg data requires about 80 bytes before header/CRC; store text labels/target tables in flash where appropriate. Optional pan must be capability-gated: today's SERVO rejects channel 8.

## Controlled first movement

A commanded tick is an estimate, not measured position. Neither ARM/OE nor a software ramp from 300 identifies the physical shaft position. A per-joint neutral is not a guarantee that an attached leg starts there. An encoder would supply feedback but is not a required purchase for this course robot.

Phase 1 must use a supported fixture and a reviewed one-joint commissioning procedure: verify safe orientation/clearance, establish a physically safe reference with unloaded/disconnected linkage as appropriate, use a qualified limited-energy supply, then attach/align linkage without forcing gears. Document the method for this assembled mechanism. Do not infer position by commanding a blind full-range sweep.

Future firmware states are DISABLED → COMMISSION_REQUIRED → REFERENCE_COMMANDED → READY, with fault/power loss returning to DISABLED/unknown reference. “Reference commanded” records that a supervised command was issued; it still is not feedback. Restoring servo power while Pi remains logically armed must be prevented by the independent rail latch. Walking stays blocked until a valid profile and supervised initialization procedure have passed physical acceptance.

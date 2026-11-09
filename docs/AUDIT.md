# Phase 0 audit

Audit baseline: fb5bacc011ee3c99ed0cc3078a8081b49bfce029, the main branch at inspection. Working tree was clean before Phase 0. The local bundle includes two other source folders and a profile repository; they are not part of Quadruped107 and were not modified.

## Disposition

| Area inspected | Findings and action |
| --- | --- |
| Root README / two existing docs | Useful port detail but mixed implementation, proposal and validation claims; replace with concise navigation and nine focused technical documents |
| Active Uno sketch / motion.h | Reusable cooperative gait sequences, fixed parser, OE inhibit and communication timeout; retain code and targets unchanged |
| Pi camera, control, serial, vision, gestures | Reusable single owners, generation-based intent, explicit arm and synthetic simulation; package with relative imports, preserve behavior |
| Browser HTML/CSS/JS and pose images | Keep existing interface, HTTP API, same-port video, keyboard/touch controls and heartbeats; no framework migration |
| Tests / CI / deployment | Existing serial/controller/API/vision and HTTP subprocess tests; repair module launch and paths, add repository/install checks |
| Fusion / STEP / 24 STL / ZIP | Preserve all blobs under hardware; no mechanical redesign |
| Images / animation | Preserve all original blobs; electrical diagram remains historical |
| Two spreadsheets | Preserve original data and filenames; values unverified for current assembly |
| UNO Q calibration / deprecated station | Archive source, metadata and READMEs; useful JSON-export workflow and historical calibration differences, incompatible Bridge dependencies and incomplete board profiles |
| License / notices | Preserve GPL license and source notices; no evidenced additional named upstream author found |

No active implementation is duplicated. Archive implementations are explicitly historical. Original empty tools directory gains a repository validator. The workbooks contain one sheet each with joint calibration/orientation references and controller bindings. The F3Z archive contains 12 entries; the supplied STL ZIP contains 25. STEP metadata identifies the exporting software but has blank author/organization fields. The retained electrical image shows a historical 12 V battery/regulator arrangement and no OE stop connection, so it must not guide the new wiring. No existing generated calibration JSON, sensor driver, or telemetry stream was found in tracked source.

## Risks requiring later work

- Source comments previously called inherited values calibrated, but no physical verification evidence is supplied.
- Communication watchdog depends on a running cooperative loop; no AVR hardware watchdog, physical stop input, or comprehensive I2C write-fault handling.
- SafePulseMin/Max are broad guards; no per-joint endpoints, position feedback or first-motion position certainty.
- STOP shares a serial FIFO and controller operation lock; calibration/arming contention and concurrent mode changes need measured/failure-path qualification.
- Publication timestamps do not prove camera exposure freshness; capture backlog and actual latency need measurement.
- Browser control is single-operator by procedure, without an ownership token or authentication; threaded streams have no viewer cap.
- Legacy station README and source contain differing shoulder values; preserve as history rather than silently adopting either.
- Pi dependencies intentionally exclude App Lab/Bridge/Edge Impulse. Optional gesture package/model availability is unqualified.
- Equal STL blobs are legitimate named assembly parts and are retained. The original ZIP is retained even though it overlaps unpacked parts.

## Safety and cleanup review

Repository-path moves use Git renames. Preservation is checked against baseline Git blobs for CAD, meshes, ZIP, spreadsheets, images, animation and firmware targets. Link checks include archive documents, with absent placeholder screenshots removed rather than invented.

Secret-pattern and tracked-generated-file checks cover current tracked text; they are not an exhaustive historical secret audit. No credentials should be printed in reports. Known design limits are documented rather than addressed with out-of-scope sensing, new autonomous behavior or unverified firmware safety changes.

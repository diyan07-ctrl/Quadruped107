# Converter qualification and requirements

## Eight-servo specification

| Item | Conditional design requirement |
| --- | --- |
| Setpoint | 6.0 V nominal only after every servo rating permits it; verify startup/overshoot and joint-terminal voltage |
| Sustained load | At least 10 A demonstrated at lowest loaded input voltage, mounting and enclosure temperature |
| Transient/fault case | Characterize 20 A load demand; documented pulse capacity OR current-limit/shutdown plus independent OE/power inhibit |
| Input | A/B: pack-approved range; a 6 V buck-boost candidate must cover assumed 6.0–8.4 V including sag. D: approved 3S range; reference 9.0–12.6 V |
| Efficiency | Calculate at 85/90/95%; obtain actual curves, including light load and dropout |
| Regulation | Design target ≤0.25 V rail droop for accepted normal load steps, no overshoot above minimum installed servo rating |
| Fault behavior | Short-circuit and thermal protection, reverse-input precautions, defined enable/default-off and recovery behavior |
| Thermal | High-load planning loss 7.72 W at 85%; enclosure thermal test required |
| Capacity proof | Vendor load/temperature curves and transient limits plus measured acceptance tests; not advertised “maximum amps” |

Normal movement should not repeatedly trigger current limiting. A fault response can remove torque and cause collapse; qualification uses a supported chassis. Independent rail monitor / stop latch must prevent automatic motion resumption after a converter hiccup; current firmware cannot sense that rail.

## Buck versus buck-boost

A buck requires input above output by its load-dependent dropout margin. Even a conventional 2S pack can approach or fall below the required input while useful charge remains. A low battery may also sag on a step and repeatedly enter dropout. Use a buck-boost with verified current/thermal capability, or deliberately stop earlier at a measured input threshold and recalculate usable energy. Lowering the output to 5.5 V is a possible later qualified variant, not an automatic cure: torque, speed and current assumptions then require remeasurement.

Pololu's D24V150F6 is a documented 6 V / nominal 15 A class comparator (S11). Its minimum input is output plus load-dependent dropout, its fixed setpoint accuracy is ±4%, and achievable continuous current depends on dissipation/input voltage. It must **not** be approved from its “15 A” title, nor assumed suitable across a 2S discharge. Its 20 A pulse behavior and installation cooling remain unqualified. It is an evidence-backed comparison, not a required purchase.

A single qualified converter is simplest. Option B's two four-servo branches each model 3.6 A high load, 4.5 A with 25% allowance, and 10 A simultaneous upper-stall demand. A documented ≥5 A continuous branch converter (prefer ≥6 A if thermally justified) still needs transient/fault qualification. Do not parallel converter outputs or connect them together through PCA V+.

No converter SKU is electrically approved by this paper study. [TEST_PLAN](TEST_PLAN.md) defines the evidence required to change NOT YET QUALIFIED status.

# Distribution, ground and decoupling

Use an external distribution point rather than assuming the installed PCA9685 breakout can carry the full motor current. Its terminal manufacturer, PCB copper weight, trace cross-section, header contacts and safe temperature rise are unknown. The IC's output-current specification describes PWM signals, not servo V+ capacity (S3/S13).

Feed each servo positive and motor return from the rated external harness; connect only required PWM/reference signals to PCA. Do not unintentionally send motor current through the Pi, Uno, breadboard or a thin signal return. Logic ground and motor-domain reference meet at a controlled distribution point with a low-impedance reference path. Keep high-current loops short and away from camera/USB. Inspect alternative paths through cable shields and USB equipment before connecting test instruments.

Option B uses two independent positive rails. The PCA board normally joins its servo V+ headers, so those positive pins must not bridge branches. Use signal-only breakout leads and external positive/negative servo distribution, or physically separate qualified PWM/distribution hardware. Do not cut unknown PCB traces as an undocumented fix.

## Calculations

`R_round_trip = ρ × (outgoing length + return length) / conductor area + contact resistance`.

`ΔV = I × R`; `P_wire = I² × R`. The calculator assumes **20 mΩ round-trip**, not a specified cable. At 4.2 A: 0.084 V drop and 0.353 W dissipation. At 20 A: 0.4 V and 8 W. A 6 V source would supply about 5.6 V at the joint under that assumed peak path, before servo-lead losses. Cable heating worsens resistance.

For a 0.25 V drop target at 20 A, total path resistance must be ≤12.5 mΩ. Choose conductor area, route, contact and fuse resistance from that requirement and manufacturer ampacity data for the installation. Do not assign an AWG without length, insulation, bundling, ambient and flex-cycle information. Contacts must handle normal and fault pulses as well as the selected fuse rating.

Decoupling follows `C ≥ ΔI × Δt / ΔV` and `ΔV_ESR = ΔI × ESR`. A 10 A / 2 ms load edge with 0.25 V allowance needs **0.08 F (80,000 µF)** ideally, before ESR and inductance. This demonstrates why a small capacitor cannot compensate for an undersized battery or converter. Size any bulk capacitance from measured response, regulator stability limits and inrush; use local ceramic decoupling per board instructions.

Choose output capacitor voltage rating above actual rail transients (at least a 10 V class for the 6 V candidate); input capacitors need margin above fully charged pack voltage and measured ringing. Verify polarity, low-ESR compatibility, discharge time and safe service access. Large capacitors increase short-circuit energy and switch stress. Motor energy/regeneration can raise a rail if the converter cannot sink current; check sink/clamp requirements from measured waveforms, not an assumed capacitor value.

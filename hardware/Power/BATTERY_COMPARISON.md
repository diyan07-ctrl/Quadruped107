# Existing batteries and architecture options

Known inventory: three separate nominal 7.4 V, 1800 mAh packs described as Li-ion. Cell chemistry, series configuration, protection, BMS behavior, age, resistance, connector and current rating are unknown. **Each pack is NOT YET QUALIFIED.** Label them P1, P2, P3 and test individually; do not assume matching performance.

For an assumed conventional 2S / 4.2 V-per-cell lithium-ion chemistry, full charge is 8.4 V. A 6.0 V pack discharge endpoint is used only as a calculator stress point (3.0 V per cell), not an approved cutoff. Chemistry, manufacturer limits and cell imbalance may require an earlier cutoff. Never infer a charge program from “7.4 V” alone. See S10 in [SOURCES](SOURCES.md).

Nominal energy per pack is 7.4 × 1.8 = **13.32 Wh**. Three disconnected packs represent 39.96 Wh nominal inventory, not a safe combined battery or guaranteed delivered energy. Usable energy fractions of 60%, 75%, 85% are illustrative; age, discharge rate, cutoff/dropout and temperature can reduce them further.

| Option | Architecture and suitability | Principal limitation / decision |
| --- | --- | --- |
| A | P1 → servo converter; independent power bank → Pi/USB Uno. P2/P3 are disconnected replacements. Minimum-cost first candidate | Requires one pack to support the full current envelope and converter dropout window; presently unqualified |
| B | P1/P2 each feed a converter and four-servo positive branch; P3 is a spare. One control-ground reference, no positive interconnection | Separate positives are mandatory; the PCA common V+ rail must not bridge branches. Branch imbalance limits runtime to the first exhausted pack. More converters/protection/wiring; not the default |
| C | One documented higher-capacity battery feeds separately protected servo and logic regulators | Can reduce inventory but a shared input fault or sag can reset Pi. Requires logic hold-up/shutdown and cross-domain protection; not minimum-cost or default |
| D | A documented 3S servo pack and qualified 6 V buck, with existing independent Pi power bank | Better dropout margin and lower servo input current; requires a matched charger, mount, protection and verified current/thermal behavior. Robust fallback if existing packs fail |

## Current, sag and protection evidence

At 6 V input / 85% conversion, 43.2 W high load plus 0.1 W reserve draws 8.49 A; the 120 W fault case draws 23.55 A. Those imply approximately 4.72C and 13.08C from 1.8 Ah solely as a calculation, not as available ratings. A purchasing/qualification envelope with 25% allowance is about 10.61 A continuous and 29.43 A transient, including all input-path limits.

Option B halves a balanced servo load: about 4.25 A high-load and 11.78 A fault per 2S pack (including each converter reserve); the weaker/loaded branch sets completion time. Branches are not galvanically isolated because control ground is shared. Motor returns must not circulate through logic/reference conductors. P3 cannot provide a second complete two-pack session without another compatible source or a carefully managed off-line replacement.

Use `V_loaded = V_open − I × R_pack_and_path`. For illustration only, 0.1 Ω causes 1 V sag and 10 W internal/path loss at 10 A; it can invalidate the nominal operating window. The actual resistance must be measured with a suitable safe load test. BMS trip thresholds/delay, wire/connector current, voltage recovery, and prospective short-circuit current remain unknown.

A replacement example is the manufacturer-listed Gens ace 3S / 2200 mAh / 25C class (S12). A label implies 55 A arithmetically but is not our measured approval of a specimen, connector or installation. A 3S reference window 12.6–9.0 V is likewise conditional on that pack's instructions. No direct series or parallel combination of the existing packs is approved.

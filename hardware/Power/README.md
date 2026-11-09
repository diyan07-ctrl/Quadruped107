# Power engineering design freeze

**All installed batteries, converters, power-bank outputs and distribution hardware are NOT YET QUALIFIED. No electrical measurements were performed.** This study selects conditional architectures, not approved wiring or a shopping mandate.

## Decision

**Minimum-cost starting candidate: Option A.** One of the existing 7.4 V / 1800 mAh packs supplies a regulated servo domain; the existing power bank supplies Pi 4 and, through USB, Uno and sensors. Keep packs 2 and 3 disconnected as individually qualified replacements. Use available components only if their documented ratings and supported-load tests pass.

At a 6 V distribution setpoint, the planning envelope is 7.2 A sustained high load, with a 9 A continuous requirement after 25% engineering allowance. Specify **at least 10 A thermally demonstrated continuous output** in the actual enclosure, plus a documented response to a 20 A eight-servo fault/load step. Either support a qualified transient or inhibit/disconnect safely under overload; indefinite stall operation is forbidden. A raw “20 A module” advertisement is not evidence.

A 2S-to-6 V design needs a qualified buck-boost converter over the approved battery window, or a buck with an earlier cutoff above its measured dropout threshold. Do not assume a full 2S discharge can support a 6 V buck. Pack input demand can reach **23.55 A** in the 120 W planning fault at 6 V input / 85% conversion, before additional margin; these packs have no established rating for that demand.

**Recommended robust candidate if existing packs fail qualification: Option D.** A documented high-discharge 3S servo battery, separately regulated to 6 V, retains the independent Pi power bank. This increases buck headroom and reduces input current. An example commercial 3S / 2.2 Ah class is linked in [SOURCES](SOURCES.md); nominal energy is 24.42 Wh. It requires a correct balance charger, pack-specific cutoff/protection, mechanical fit and qualification. It is not automatically safer merely because it has a C-rating.

Do not purchase a replacement battery until the existing packs are identified and tested. A current-limited bench supply is the preferred first supported commissioning source if already available. The optional ninth servo changes the upper case to 22.5 A / 135 W; it is excluded from the eight-servo approval and requires a new review.

## Study navigation

[Component loads](COMPONENT_LOADS.md) · [Servos](SERVO_ANALYSIS.md) · [Battery options](BATTERY_COMPARISON.md) · [Budget](POWER_BUDGET.md) · [Converters](REGULATOR_SELECTION.md) · [Distribution](DISTRIBUTION.md) · [Protection](PROTECTION.md) · [Runtime](RUNTIME_ESTIMATES.md) · [Tests](TEST_PLAN.md) · [Sources](SOURCES.md)

Run from repository root:

```bash
python hardware/Power/power_budget.py
python hardware/Power/power_budget.py --json
python hardware/Power/power_budget.py --check
python -m unittest discover -s tests -v
```

The calculator is standard-library-only. Editable assumptions are at its top. Four marked Markdown tables are generated from those assumptions; --write-tables updates them and --check rejects drift. Calculated limits do not substitute for [physical verification](../../docs/HARDWARE_VERIFICATION.md).

## Cost, mass and responsiveness tradeoff

A keeps one existing pack and one converter/harness, so it is the least-parts starting candidate if ratings pass. B can extend balanced runtime but carries two packs, duplicated conversion/protection and more return-path complexity; added mass can increase servo load and invalidate that gain. C can consolidate sources but couples motor faults to logic survival. D keeps independent logic power and gains buck headroom with one documented servo pack, avoiding the duplicated B converter path. Its new-part cost, actual mass and mount must be compared before purchase; no installed mass or price has been assumed. Current capability and stable dynamic voltage take priority over nominal Ah.

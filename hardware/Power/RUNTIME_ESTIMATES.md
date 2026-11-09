# Runtime estimates

`Runtime_hours = nominal_energy_Wh × usable_fraction / average_input_power_W`.

Conversion input is `P_output / η + 0.1 W` per converter; 0.1 W is a separate allowance. If measured total efficiency already includes all quiescent costs, set that reserve to zero rather than double counting it. Pack energy: existing 13.32 Wh each; illustrative replacement 3S/2.2 Ah 24.42 Wh.

| Bound | Usable energy | Conversion efficiency | Average-load multiplier |
| --- | --- | --- | --- |
| Optimistic | 85% | 95% | 0.80 |
| Nominal | 75% | 90% | 1.00 |
| Conservative | 60% | 85% | 1.25 |

These are sensitivity scenarios, not confidence intervals or warranties. Every cell can perform worse. No continuous-walking estimate uses stall current as its normal average.

The first table is **Option A servo-battery runtime only**. The second table compares B balanced independent branches, C shared new 3S battery, D new 3S servo battery, and the independent bank's normalized requirement. All second-table values use nominal assumptions.

<!-- POWER_TABLE_START -->
<!-- POWER_TABLE_END -->

## Architecture limits

A/B/D complete-system runtime is the **minimum** of servo-source runtime and logic-bank runtime. Bank delivered usable Wh is unknown, so complete robot runtime cannot yet be approved. The last column means “minutes per usable Wh delivered at the bank's output”; multiply by measured delivered Wh. A bank's advertised cell mAh is not 5 V output mAh. If using nameplate cell Wh, include bank conversion/cutoff loss separately.

B assumes equal branch loads and equal qualified pack energies. In reality calculate each branch separately and take the minimum; two packs do not become one parallel source. One spare does not imply double runtime for a two-pack architecture.

C's estimates include logic and servo conversion from one 24.42 Wh illustrative battery. D's servo-only runtime excludes its independent power bank. The extra battery energy and better buck headroom trade against mass, charger and enclosure requirements; neither is a verified retrofit.

Disabled streaming still powers servo electronics in this model; a physical servo disconnect makes servo demand zero, and logic-bank energy then determines useful idle time. The runtime function deliberately rejects zero average power rather than returning a misleading infinity.

The legacy 2S pack may provide much less usable energy with a dropout-limited 6 V buck. Recalculate with measured cutoff and discharged Wh. Publish measured standby/standing/gait currents and load profiles in Phase 1 before presenting a demonstration runtime.

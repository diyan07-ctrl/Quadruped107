# Digital-twin engineering investigation

Original CAD, URDF target mapping, production gait tables and physical calibration remain unchanged. Axes, pivots, masses/inertia, friction and PWM-angle conversion remain provisional.

## Identified issues and corrections

The Phase 1 maximum 0.51–0.65 rad metric included channels with no output enabled. Numeric target estimates for those channels were not measured positions, so that maximum alone was not a useful motor-tracking measure. It remains for historical comparison; diagnostics now separately report active-channel maximum/RMS error, actual joints, targets and applied torque.

A networked navigation test also showed substantial base drift despite the nominal fixed-base flag after link dynamics changes. This invalidated a fixture assumption and let sensor rays move away from the expected obstacle. The repair adds an explicit world constraint for the **externally supported articulation fixture**, reports its position error and keeps free-base operation separate. The navigation proxy commands that constraint deliberately; it never presents its planar motion as gait-derived walking.

The 0.5 Nm modeled servo cap, collisions, original targets and canonical masses were not increased/disabled/retuned to make tests pass. Fixture support is external and explicitly labeled. Strict joint-excursion, fall and finite-value checks remain.

## Controlled study

[model_study.py](../simulation/model_study.py) runs stand, forward and turn_left with position gains 0.05/0.1/0.2, retaining collisions and torque. It additionally scales all provisional masses/inertias by 0.5/2 for forward as sensitivity experiments only. No such scale is adopted in the canonical model. Each routine receives a 0.5-second settling interval; reports separate completion error, settled error, active RMS, maximum applied torque, contacts and fixture drift.

These experiments investigate controller lag, transient targets, torque saturation and inertial sensitivity. They cannot identify correct axes/transforms or actual motor properties. No gain is adopted merely because it lowers a scalar error in an unqualified model. Model geometry and self-contact require actual CAD constraint recovery and mechanical evidence.

Measured CI results and source commit references are added to [validation](VALIDATION.md) after execution. Results are SIMULATED and AUTOMATED TESTED, never PHYSICAL HARDWARE TESTED.

## Measured sensitivity checkpoint

[Push CI 42682345230](https://github.com/diyan07-ctrl/Quadruped107/actions/runs/42682345230), source 9e44cff, passed 120 tests and the controlled study. Its [machine-readable measurements](evidence/PHASE2_MODEL_STUDY.json) preserve all twelve experiments, including an explicitly segmented stand/settle warm start.

| Routine / setting | Active RMS error (rad) | Settled max error (rad) | Max applied torque (Nm) | Max self-contact count |
| --- | ---: | ---: | ---: | ---: |
| stand / gain 0.1 | 0.059680 | 1.69e-13 | 0.117588 | 0 |
| forward / gain 0.1 | 0.057844 | 6.56e-6 | 0.500000 | 4 |
| forward / gain 0.2 | 0.057051 | 3.28e-6 | 0.500000 | 4 |
| turn_left / gain 0.1 | 0.056975 | 7.35e-6 | 0.500000 | 2 |
| forward / half inertia scale | 0.057846 | 6.85e-6 | 0.500000 | 4 |
| forward / double inertia scale | 0.057843 | 6.30e-6 | 0.500000 | 4 |

The active transient maximum stayed near 0.5075 rad for forward/turns. Low settled error and almost unchanged inertia sensitivity do not establish correct physical dynamics; they point toward startup target/pose disagreement and rapid command transitions as important contributors. The emulator begins with an unmeasured 300-tick estimate while simulated joints begin at neutral. Filtering inactive channels alone therefore cannot remove the activation transient.

A higher gain slightly reduces gait RMS but worsens stand RMS; default 0.1 is retained. Gaits reach the provisional torque cap and retain self-contact, so their transient saturation/contact effects remain unresolved. The anchored fixture position error was below 5.2e-8 m in these experiments. This confirms support behavior in the numerical fixture, not physical robot stability. Unknown axes, transforms, masses, friction and calibration cannot be corrected by scalar gain fitting.

## Startup-coherence experiment

Using the original stand command and a 0.5-second settling interval before forward, then starting a separately labeled measurement segment, reduced forward active maximum from **0.507500 to 0.171078 rad** and active RMS from **0.057844 to 0.027441 rad**. Torque still reached 0.5 Nm and maximum self-contact remained four. The warm-up results are preserved in the report instead of being discarded. No servo target or mass changed.

This supports using an **explicit virtual Stand followed by settling** for reproducible digital-twin demonstrations. ARM still commands no pose. It does not make a blind physical initialization safe, and no physical startup/calibration procedure is approved. Residual error, saturation and contacts remain visible rather than tuned away.

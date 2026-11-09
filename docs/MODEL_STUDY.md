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

# CAD-visual articulated simulator

This is a **provisional eight-joint test fixture**, using original CAD mesh surfaces. It exercises the real Python controller, v1 serial worker, host virtual Uno, original gait target sequences and network transport. Fixed-base articulation is the default. No physical walking, mass identification or servo calibration is claimed.

## Laptop setup

From the repository root (Python 3.11 recommended):

```powershell
py -3.11 -m venv .venv-sim
.venv-sim/Scripts/python.exe -m pip install -r software/pi/requirements-dev.txt -r simulation/requirements.txt -e software/pi
.venv-sim/Scripts/python.exe simulation/build_model.py --check
.venv-sim/Scripts/python.exe -m simulation.twin --host 0.0.0.0
```

Use the machine's trusted private IPv4 address in the Pi launcher. Restrict UDP 7002 to that private network if a firewall rule is necessary; no automatic firewall changes occur. GUI simulation runs on the laptop, not the 2 GB Pi.

A fully synthetic local demonstration uses a second shell:

```powershell
.venv-sim/Scripts/python.exe -m quadruped.main --simulate --host 127.0.0.1 --simulator 127.0.0.1
```

Open http://127.0.0.1:7000, explicitly enable **virtual** actuators and select OpenCV. The synthetic scene is clearly marked. To use the real webcam on the Pi, follow [deploy](../deploy/README.md). Simulation is explicitly configured and never substitutes itself for missing physical hardware.

Offline, explicitly armed articulation only:

```powershell
.venv-sim/Scripts/python.exe -m simulation.twin --headless --demo stand --arm-demo --steps 480 --report build/simulation/stand.json --capture build/simulation/stand.png
.venv-sim/Scripts/python.exe -m unittest discover -s tests -v
```

No automatic ARM occurs on network startup/reconnect. STOP disables virtual forces. A collapsed virtual limb after STOP represents loss of holding torque, not a commanded pose.

## Model provenance and limits

[CAD manifest](model/cad_manifest.json) records original mesh hashes, binary STL bounds and the STEP hash. [Generator](build_model.py) preserves the original files and deterministically creates [URDF](model/robot.urdf) and [parameters](model/parameters.json). Fourteen original mesh surfaces are reused. STL is unitless: millimetre scaling is inferred from STEP context and plausible part spans, not physically measured.

Exported leg parts have independent frames. Joint pivots, axis directions, assembled transforms and link lengths have **not** been recovered from Fusion constraints. Bounds supply provisional span proxies; the Y axes, origins, box collisions, mass/COM/inertia, friction, motor torque and tick-to-angle mapping are engineering placeholders. The fixed chassis does not demonstrate balance. Free-base mode (`--free-base`) is exploratory and terminates with a diagnostic on a fall, excessive tilt, joint excursion or numerical divergence.

Firmware channels are 0/1 FL, 2/3 FR, 4/5 BL, 6/7 BR. Ticks are explicitly mapped piecewise around inherited stand values to provisional ±1.2 rad; they are never treated as degrees or measured angles. Edit a copy of parameters and pass `--parameters FILE` for experiments. Values cannot qualify physical limits.

All eight inherited routines are supported, including stand, initial, forward, backward and turns. Identical target traces do not prove that the inherited gait is mechanically feasible. Diagnostics report joint error, contacts/self-contact and finite-state limits; a visually moving fixture is not locomotion evidence.

## Bridge contract

UDP v1 carries bounded eight-channel target snapshots (maximum 2048 bytes). One client/session owns a receiver. Random receiver epochs and one-use challenges expire after 150 ms on the receiver's monotonic clock; sequence numbers reject duplicate/out-of-order frames. No clock synchronization is assumed. A 300 ms receive lease removes forces. The Pi independently stops and disarms on loss of fresh acknowledgments or simulator reset. STOP invalidates an outstanding challenge; a fresh disarmed handshake and explicit browser re-enable are required.

The receiver handles at most eight datagrams per poll, retaining only the latest target state. It does not replay queued gaits. The reliable serial/virtual-Uno layer owns command acknowledgment; UDP visualizes its current output and may skip intermediate ticks. There is no authenticated security boundary: use a trusted local network. Simulator failure cannot open physical serial hardware.

## Acceptance procedure

1. Start simulator, then application. Verify both identify virtual actuators and remain disarmed.
2. Enable in one browser, select OpenCV, show a blue target left/right/center. Verify corresponding virtual turns/stand and eight commanded ticks.
3. Remove target: STOP/disarm after the configured loss deadline. Re-enable explicitly.
4. Unplug camera or stop its publication: stale observations inhibit motion. A frozen-pixel heuristic may also inhibit a genuinely static scene; it is conservative, not proof of camera freeze.
5. Manual STOP preempts motion. Stop the simulator or interrupt the network: the Pi disarms and the receiver lease removes forces. Restart must remain disarmed.
6. Record actual Pi CPU/RSS, camera FPS/frame age and observed host response times from `/api/state`. No numbers from CI qualify Pi or electrical performance.

Automated synthetic integration, UDP contracts and DIRECT model checks live in [tests](../tests/test_simulation.py). Physical webcam/Pi validation is blocked by SSH access in this development environment; see [validation](../docs/VALIDATION.md).

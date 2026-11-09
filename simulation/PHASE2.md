# Phase 2 simulation guide

All commands run on the development laptop from this branch's repository root. No Pi access, GPIO, upload or actuator power is required.

## Install and launch

```powershell
py -3.11 -m venv .venv-sim
.venv-sim/Scripts/python.exe -m pip install -r software/pi/requirements-dev.txt -r simulation/requirements.txt -e software/pi
.venv-sim/Scripts/python.exe -m simulation.twin --scenario single_obstacle --navigation-proxy --show-rays --host 127.0.0.1 --sensor-config deploy/sensors.example.json
```

In a second shell:

```powershell
.venv-sim/Scripts/python.exe -m quadruped.main --simulate --virtual-sensors --simulator 127.0.0.1 --host 127.0.0.1 --sensor-config deploy/sensors.example.json --navigation-config deploy/navigation.example.json
```

Open http://127.0.0.1:7000. Wait for valid sensors and simulator health, explicitly enable virtual actuators, then choose Virtual exploration or Virtual sensor test. Manual takeover and Idle disarm; re-enable explicitly afterward. All inputs must be released. Closing either process stops movement through the existing leases. Start/restart remains disarmed.

## Scenarios

| Name | Environment / purpose |
| --- | --- |
| empty | Flat bounded arena; clear initial range |
| single_obstacle | Box ahead; approach and conservative stop |
| multiple_obstacles | Several known boxes |
| narrow_passage | Side walls too close for the configured footprint |
| dead_end | Enclosure; no assumed escape direction |
| target | Blue sphere; visible obstacle geometry |
| sensor_failure | Disconnected virtual URM37 |
| touch | One head press 1.0–1.2 seconds after each explicit virtual enable |

Select --scenario NAME. Restart both processes for a deterministic new scene/session. Seeded noise defaults to zero; --sensor-noise and --sensor-latency change assumptions. --ultrasonic-profiles FILE accepts a JSON object keyed by urm37/hcsr04, overriding origin (three metres), yaw (radians), min_m/max_m, rate_hz, latency and noise_m. Settings are simulation-only and do not claim hardware equivalence. Programmatic sensors expose normal, missing, invalid, disconnected, no_echo, timeout and out_of_range failure modes. Touch fixtures support arbitrary simultaneous/held/disconnected inputs.

The scheduled touch scenario starts its clock when the receiver first observes explicit virtual enable. It emits one bounded head press per enable session; startup/reconnect cannot replay a press. Select exploration soon after enabling to observe its priority over locomotion. Sensor-test mode remains observation-only. Automated interaction tests also inject events after explicit enable.

## Navigation proxy and physics limits

--navigation-proxy is an explicit **kinematic planar proxy**, not computed walking locomotion. It repositions the externally fixed chassis at provisional 0.06 m/s forward, 0.04 m/s reverse and 0.35 rad/s turn, only while the virtual Uno reports the corresponding active routine and active channels. Actual original gait ticks still drive all articulated joints. It cannot move from a desired command that never reached the virtual Uno.

A separate known-geometry footprint guard rejects proxy collisions. Swept-clearance uses conservative circular regions around the provisional footprint and short path samples against scenario obstacle bounds, including the target. It is extra simulated evidence; one front ray is never interpreted as side/reverse clearance. It is not a general dynamic-world or real sensor safety guarantee. Recovery is a bounded turn fragment ending in disarm, not guaranteed passage/dead-end escape.

The model uses an explicit world fixture constraint because changing link dynamics allowed the nominal useFixedBase chassis to drift in earlier tests. Fixture force belongs to the external test support, not the servo torque model. Collisions, provisional masses, original ticks and the 0.5 Nm servo force cap remain. Free-base runs have no fixture; proxy and free-base cannot be combined. See [model investigation](../docs/MODEL_STUDY.md).

## Blue-target demonstration without a camera

The PyBullet sphere does not stream rendered video through the UDP sensor packets. To exercise the existing detector with a repeatable labeled video:

```powershell
.venv-sim/Scripts/python.exe tools/generate-blue-video.py
.venv-sim/Scripts/python.exe -m quadruped.main --camera-backend file --camera-device build/simulation/blue-target.avi --actuator-backend virtual --virtual-sensors --simulator 127.0.0.1 --host 127.0.0.1
```

Use a clear scenario, then select Blue target tracking. The prerecorded target moves left/center/right and disappears; target loss disarms. The video is synthetic and separate from the PyBullet camera. Tracking never requests forward motion; obstacle/sensor faults still outrank it. EOF/recovery never auto-arms.

## Reproducible checks and logs

```powershell
.venv-sim/Scripts/python.exe -m unittest discover -s tests -v
.venv-sim/Scripts/python.exe -m simulation.proxy_probe
.venv-sim/Scripts/python.exe -m simulation.model_study
.venv-sim/Scripts/python.exe -m simulation.twin --headless --scenario empty --steps 480 --report build/simulation/empty.json
```

The fixture runs at 240 Hz with four substeps and 100 solver iterations. CLI wall-clock pacing does not enlarge dt after a slow frame. Reports include pose, actual/target joints, active errors, contacts, range/touch observations, behavior labels and actual virtual motion. Scene history is capped at 256 records; state/transition logs are bounded. No Pi resource or physical performance claim follows from these checks.

In GUI network scenarios, press **R** to reset geometry, seed, touches, joint state and the fixture pose. It creates a new receiver epoch and disables output; the application must observe the reset and be explicitly re-enabled. Programmatic Scene.reset(receiver) uses the same path. No reset automatically arms or replays a gait.

For repeatable articulation comparisons, explicitly select **Stand**, wait for completion plus 0.5 seconds of virtual settling, then choose exploration. This uses an existing command after enable; ARM itself never sends a pose. The measured improvement is documented in MODEL_STUDY and does not qualify physical initialization.

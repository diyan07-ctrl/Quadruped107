# Phase 4 safety and fault injection

## Remediation safety result

The [remediation report](../evidence/phase4/2026-11-10-remediation/reports/REMEDIATION.md) records deterministic repairs to atomic sensor/time evaluation and STOP-before-recovery ordering. Freshness validation, 150 ms challenge TTL, 300 ms bridge lease, 300 ms sensor expiry, genuine stale-intent inhibition and explicit re-enable remain intact.

Actual reproduced stale range at 60.943 s disarmed movement. Later fresh input/reconnect stayed disarmed. A separate headless run then completed 905.094 s without automatic re-arm or unexpected stop. It logged one source rejected datagram and 1,920 rejected duplicate/out-of-order sensor batches; these counters are disclosed rather than hidden.

The complete new-head active fault sequence remains unverified after operator Escape stopped GUI work. [Final STOP](../evidence/phase4/2026-11-10-remediation/safety/final-before-shutdown.json) showed disabled/disarmed/mask zero; [shutdown](../evidence/phase4/2026-11-10-remediation/safety/shutdown.log) released the webcam and reconfirmed preserved Pi patch hashes. No physical actuator API/upload was used. No independent electrical inactivity measurement is claimed.

### Historical safety tests

**Virtual outputs only.** No GPIO, PCA9685 access, physical serial ARM, servo
power operation or firmware upload was performed. Physical power/OE voltage was
not electrically measured; software inhibition is not proof of an electrical stop.

| Injection | Observed result | Evidence |
| --- | --- | --- |
| Operator STOP during six manual virtual routines | Pi output mask zero; request/observation 125–235 ms | [Manual LAN probe](../evidence/phase4/2026-11-10/autonomy/manual-lan.json) |
| Real capture worker stopped during blue tracking | Nonzero mask before; `Stale vision result`, disarm/mask zero after; fresh acquisition did not re-arm | [Camera fault log](../evidence/phase4/2026-11-10/safety/camera-fault.log) |
| UDP polling interrupted | Pi disarmed; receiver lease removed outputs; restored transport stayed disarmed | [LAN faults](../evidence/phase4/2026-11-10/safety/lan-faults.json) |
| Receiver epoch reset | Old session inhibited; new disarmed handshake; explicit enable required | [LAN faults](../evidence/phase4/2026-11-10/safety/lan-faults.json) |
| Virtual sensor ages increased by 2 s | Sensor fault and disarm | [LAN faults](../evidence/phase4/2026-11-10/safety/lan-faults.json) |
| PyBullet obstacle inserted during forward | Obstacle/safety precedence stopped movement | [LAN faults](../evidence/phase4/2026-11-10/safety/lan-faults.json) |
| Virtual head touch / greeting | Bounded touch state and explicit personality command observed | [LAN faults](../evidence/phase4/2026-11-10/safety/lan-faults.json) |
| Invalid mode | HTTP 400, unknown mode rejected | [Manual LAN probe](../evidence/phase4/2026-11-10/autonomy/manual-lan.json) |
| Application restart | Startup disarmed, mask zero, new handshake ready | [Restart state](../evidence/phase4/2026-11-10/safety/restart-state.json) |
| Old guard fault crosses explicit recovery | Reproduced before repair; newer generation survives after repair; current fault still disarms | [Before](../evidence/phase4/2026-11-10/safety/guard-before.log), [after](../evidence/phase4/2026-11-10/safety/guard-after.log) |

Injection-to-observation times for network/control-file cases include up to one
second of instrument polling. They are not standalone software STOP deadlines.
The capture test closed the acquisition owner while retaining aging observations;
it did not physically unplug USB or claim verification of every native-driver hang.

The first touch/personality probe was interrupted by an HTTP timeout and its
partial fault results were preserved separately. The full headless retest passed
those short cases. Later endurance still encountered stale virtual front range,
so isolated short-case passes do not establish sustained reliability.

Real blue/yellow detection tests, synthetic regression images, PyBullet ray
distances and simulated touches are separate evidence classes. No physical
ultrasonic or touch driver was exercised. Actual target-loss motion response and
controlled multiple-candidate selection remain incomplete; automated synthetic
coverage must not be used to mark those physical-target cases passed.

After every successful short fault test the source was restored, outputs remained
off, and a deliberate test ARM preceded the next movement. The endurance runner
does not re-enable after its first unexpected stop. Freshness, the 300 ms receive
lease, disarmed handshake, STOP priority and explicit enable were retained.

Follow [hardware qualification](HARDWARE_VERIFICATION.md) and the existing power
test plan before any future powered electronics work. Phase 4 is not permission
to energize the suspected damaged PCA9685 or servos.

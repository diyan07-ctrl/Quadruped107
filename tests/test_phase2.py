"""Phase 2 deterministic sensor, policy, transport and real-application scenarios."""
import copy
import json
from pathlib import Path
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"software/pi"))
from quadruped.sensors import SensorManager, SensorConfig, fixture_batch
from quadruped.navigation import Navigation, NavigationSettings, motion_inhibition
from quadruped.bridge import TraceReceiver, TraceServer, TraceClient, encode, decode
from quadruped.main import Runtime, create_app
from test_runtime import wait_for


class SensorTests(unittest.TestCase):
    def setUp(self):
        self.now=0.
        self.seq=0
        self.manager=SensorManager(clock=lambda:self.now)
        self.send()

    def send(self,**kwargs):
        self.seq+=1
        self.assertTrue(self.manager.ingest(fixture_batch(self.seq,**kwargs)))
        return self.manager.snapshot()

    def test_units_freshness_and_health(self):
        state=self.manager.snapshot()
        self.assertIsNone(state["fault"])
        self.assertEqual(state["observations"]["urm37"]["unit"],"m")
        self.assertTrue(state["observations"]["urm37"]["fresh"])

    def test_range_zero_negative_out_of_range_and_nan(self):
        for value in (0,-1,5,float("nan"),True):
            state=self.send(distance=value)
            self.assertIsNotNone(state["fault"])

    def test_missing_sensor_is_not_clear(self):
        batch=fixture_batch(2)
        batch["observations"]=[r for r in batch["observations"] if r["id"]!="urm37"]
        self.manager.ingest(batch)
        self.assertIsNotNone(self.manager.snapshot()["fault"])
        self.assertIsNone(self.manager.snapshot()["front_m"])

    def test_missing_touch_is_a_fault(self):
        batch=fixture_batch(2)
        batch["observations"]=[r for r in batch["observations"] if r["id"]!="touch_body"]
        self.manager.ingest(batch)
        self.assertIsNotNone(self.manager.snapshot()["fault"])

    def test_timeout_and_expiration(self):
        self.assertIsNotNone(self.send(age=.5)["fault"])
        self.send()
        self.now=.31
        self.assertIsNotNone(self.manager.snapshot()["fault"])

    def test_conflicting_ranges(self):
        batch=fixture_batch(2)
        batch["observations"][1]["value"]=.5
        self.manager.ingest(batch)
        self.assertIn("Conflicting",self.manager.snapshot()["fault"])

    def test_button_bounce_press_and_release(self):
        self.now=.01
        self.send(touches={"head":True})
        self.now=.02
        self.send(touches={"head":False})
        self.now=.03
        self.send(touches={"head":True})
        self.assertFalse(self.manager.snapshot()["events"])
        self.now=.07
        state=self.send(touches={"head":True})
        self.assertEqual([e["pressed"] for e in state["events"]],[True])
        self.now=.08
        self.send()
        self.now=.12
        state=self.send()
        self.assertEqual([e["pressed"] for e in state["events"]],[True,False])

    def test_stuck_touch(self):
        self.now=.01
        self.send(touches={"head":True})
        self.now=.05
        self.send(touches={"head":True})
        self.now=2.1
        state=self.send(touches={"head":True})
        self.assertTrue(state["touches"]["touch_head"]["stuck"])
        self.assertIsNotNone(state["fault"])

    def test_simultaneous_touch_priority(self):
        self.now=.01
        self.send(touches={"head":True,"back":True})
        self.now=.05
        state=self.send(touches={"head":True,"back":True})
        self.assertIn("Simultaneous",motion_inhibition(state,"stand",NavigationSettings()))

    def test_reconnect_held_press_does_not_replay(self):
        self.manager.reset("new")
        self.manager.ingest(fixture_batch(0,touches={"head":True}),session="new")
        self.assertFalse(self.manager.snapshot()["events"])

    def test_duplicate_and_out_of_order_do_not_refresh(self):
        self.now=.2
        self.assertFalse(self.manager.ingest(fixture_batch(1)))
        self.assertFalse(self.manager.ingest(fixture_batch(0)))
        self.now=.31
        self.assertIsNotNone(self.manager.snapshot()["fault"])

    def test_delayed_telemetry_includes_transport_age(self):
        self.assertTrue(self.manager.ingest(fixture_batch(2,age=.15),transport_age=.2))
        self.assertIsNotNone(self.manager.snapshot()["fault"])

    def test_invalid_contracts_are_bounded(self):
        for batch in ({},dict(schema=2,seq=2,observations=[]),dict(schema=1,seq=True,observations=[]),
                      dict(schema=1,seq=2,observations=[{}]*17)):
            self.assertFalse(self.manager.ingest(batch))
        with self.assertRaises(ValueError): SensorConfig(min_m=0)
        with self.assertRaises(ValueError): SensorConfig(touch_count=8)
        with self.assertRaises(ValueError): NavigationSettings(caution_m=.1)

    def test_telemetry_fits_existing_packet_limit(self):
        packet=dict(v=1,type="ack",server="ab"*16,nonce="cd"*16,seq=200,ready=True,fault=None,sensors=fixture_batch())
        self.assertLess(len(encode(packet)),2048)


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.now=0.
        self.seq=0
        self.manager=SensorManager(clock=lambda:self.now)
        self.nav=Navigation()

    def sensors(self,distance=2.,clearance=True,touches=None):
        self.seq+=1
        self.manager.ingest(fixture_batch(self.seq,distance=distance,clearance=clearance,touches=touches))
        return self.manager.snapshot()

    def step(self,mode="explore",enabled=True,session=1,observation=None,**kwargs):
        sensors=kwargs.pop("sensors",None) or self.sensors()
        return self.nav.step(mode,enabled,session,sensors,observation,self.now,**kwargs)

    def test_empty_environment_explores_one_request(self):
        decision=self.step()
        self.assertEqual((decision.state,decision.motion),("EXPLORING","forward"))
        self.nav.accepted(decision.motion,self.now)
        self.now=.1
        self.assertIsNone(self.step().motion)

    def test_obstacle_ahead_preempts_busy(self):
        decision=self.step(sensors=self.sensors(.2),busy=True)
        self.assertTrue(decision.stop)
        self.assertEqual(decision.state,"OBSTACLE_BLOCKED")

    def test_exact_threshold_and_caution_hysteresis(self):
        decision=self.step(sensors=self.sensors(.35,False))
        self.assertTrue(decision.stop)
        self.now=.1
        self.assertEqual(self.step(sensors=self.sensors(.6)).state,"OBSTACLE_CAUTION")
        self.now=.2
        self.assertEqual(self.step(sensors=self.sensors(.62)).state,"OBSTACLE_CAUTION")
        self.now=.3
        self.assertEqual(self.step(sensors=self.sensors(.66)).state,"EXPLORING")

    def test_single_front_sensor_never_infers_turn_clearance(self):
        state=self.sensors(.2)
        for k in tuple(state["observations"]):
            if k.startswith("sweep_"): del state["observations"][k]
        self.assertTrue(self.step(sensors=state).stop)

    def test_narrow_path_missing_footprint_evidence(self):
        self.assertTrue(self.step(sensors=self.sensors(2.,False)).stop)

    def test_recovery_is_bounded_and_stop_wins(self):
        decision=self.step(sensors=self.sensors(.2))
        self.assertEqual(decision.state,"RECOVERY")
        self.nav.accepted(decision.motion,self.now)
        self.now=.2
        self.assertIsNone(self.step(enabled=False).motion)
        self.now=.3
        self.step(session=2,sensors=self.sensors(.2))
        self.now=1.
        self.assertTrue(self.step(session=2,sensors=self.sensors(.2)).stop)

    def test_recovery_attempt_limit_survives_rearm(self):
        for session in (1,2):
            self.assertEqual(self.step(session=session,sensors=self.sensors(.2)).state,"RECOVERY")
        self.assertTrue(self.step(session=3,sensors=self.sensors(.2)).stop)
        self.assertEqual(self.nav.attempts,2)

    def test_sensor_fault_inhibits(self):
        self.assertEqual(self.step(sensors=self.sensors(-1)).state,"SENSOR_FAULT")

    def test_communication_fault_inhibits(self):
        self.assertTrue(self.step(communication_ok=False).stop)

    def test_manual_takeover_has_no_autonomous_motion(self):
        self.step()
        self.assertEqual(self.step(mode="manual").state,"MANUAL_OVERRIDE")
        self.assertIsNone(self.step(mode="manual").motion)

    def test_tracking_yields_to_obstacle(self):
        target=dict(detected=True,offset=-.8,observed_at=0.)
        self.assertTrue(self.step(mode="opencv",observation=target,sensors=self.sensors(.2)).stop)

    def test_blue_target_center_left_and_loss(self):
        target=dict(detected=True,offset=-.8,observed_at=0.)
        self.step(mode="opencv",observation=target)
        self.now=.1
        target["observed_at"]=.1
        decision=self.step(mode="opencv",observation=target)
        self.assertEqual(decision.motion,"turn_left")
        self.now=.6
        self.assertTrue(self.step(mode="opencv",observation=dict(detected=False,observed_at=.6)).stop)

    def test_stale_camera_inhibits_only_tracking(self):
        self.assertEqual(self.step(mode="opencv",observation=dict(detected=True,offset=0,observed_at=-1)).state,"CAMERA_FAULT")
        self.assertEqual(self.step(mode="explore").state,"EXPLORING")

    def test_touch_reaction_is_one_bounded_command(self):
        self.step()
        self.now=.01
        self.step(sensors=self.sensors(touches={"head":True}))
        self.now=.05
        decision=self.step(sensors=self.sensors(touches={"head":True}))
        self.assertEqual((decision.state,decision.motion),("TOUCH_REACTION","greeting"))
        self.nav.accepted(decision.motion,self.now)
        self.now=.1
        self.assertIsNone(self.step(sensors=self.sensors(touches={"head":True})).motion)
        self.now=2.1
        self.assertTrue(self.step(sensors=self.sensors()).stop)

    def test_repeated_mode_switches_cancel_old_action(self):
        for _ in range(10):
            self.assertEqual(self.step(mode="sensor_test").state,"READY")
            self.assertEqual(self.step(mode="manual").state,"MANUAL_OVERRIDE")
            self.assertIsNone(self.step(mode="idle").motion)

    def test_exploration_budget(self):
        self.step()
        self.now=30.1
        self.assertTrue(self.step().stop)


class ExplicitBackend:
    def __init__(self):
        self.seq=0
        self.distance=2.
        self.disconnected=False

    def sample(self,now):
        self.seq+=1
        return fixture_batch(self.seq,distance=-1 if self.disconnected else self.distance)


class RuntimeNavigationTests(unittest.TestCase):
    def setUp(self):
        self.backend=ExplicitBackend()
        self.runtime=Runtime(camera_backend="synthetic",actuator_backend="virtual",virtual_sensors=True,sensor_backend=self.backend)
        self.runtime.start()
        self.api=create_app(self.runtime).test_client()
        wait_for(lambda:self.runtime.link.snapshot()["connected"],4)
        wait_for(lambda:self.runtime.sensors.snapshot()["fault"] is None)

    def tearDown(self): self.runtime.close()

    def pump(self,predicate,timeout=3):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            self.api.post("/api/heartbeat",json={})
            if predicate(): return
            time.sleep(.03)
        self.fail(str(self.runtime.state()))

    def test_actual_controller_explore_obstacle_stop_and_reconnect_latch(self):
        self.assertEqual(self.api.post("/api/arm",json={}).status_code,200)
        self.assertEqual(self.api.post("/api/mode",json={"mode":"explore"}).status_code,200)
        self.pump(lambda:self.runtime.link.engine.snapshot()["activeMotion"]=="forward")
        self.backend.distance=.2
        self.pump(lambda:not self.runtime.motion.snapshot()["enabled"])
        self.pump(lambda:not self.runtime.link.engine.snapshot()["armed"])
        history=len(self.runtime.link.engine.snapshot()["history"])
        self.backend.distance=2.
        time.sleep(.1)
        self.assertFalse(self.runtime.motion.snapshot()["enabled"])
        self.assertFalse(self.runtime.link.engine.snapshot()["activeMask"])
        self.assertEqual(self.api.post("/api/mode",json={"mode":"explore"}).status_code,409)

    def test_manual_takeover_cancels_pending_autonomy_and_idle(self):
        self.assertEqual(self.api.post("/api/arm",json={}).status_code,200)
        self.api.post("/api/mode",json={"mode":"explore"})
        self.pump(lambda:self.runtime.motion.snapshot()["busy"])
        self.assertEqual(self.api.post("/api/mode",json={"mode":"manual"}).status_code,200)
        self.assertFalse(self.runtime.motion.snapshot()["enabled"])
        self.assertFalse(self.runtime.link.engine.snapshot()["activeMask"])
        self.pump(lambda:not self.runtime.motion.snapshot()["busy"])
        self.assertEqual(self.api.post("/api/arm",json={}).status_code,200)
        self.assertEqual(self.api.post("/api/mode",json={"mode":"idle"}).status_code,200)
        self.assertFalse(self.runtime.motion.snapshot()["enabled"])

    def test_sensor_disconnect_preempts_without_camera_dependency(self):
        self.api.post("/api/arm",json={})
        self.api.post("/api/mode",json={"mode":"explore"})
        self.pump(lambda:self.runtime.link.engine.snapshot()["activeMotion"]=="forward")
        self.backend.disconnected=True
        self.pump(lambda:not self.runtime.motion.snapshot()["enabled"])
        self.assertEqual(self.api.post("/api/arm",json={}).status_code,409)


class EnvironmentTests(unittest.TestCase):
    def test_scenario_geometry_and_ray_distance(self):
        from simulation.twin import World
        from simulation.environment import Scene, SCENARIOS
        for scenario in SCENARIOS:
            clock=[0.]
            world=World()
            try:
                scene=Scene(world,scenario,clock=lambda:clock[0],latency=0)
                batch=scene.telemetry()
                self.assertTrue(batch["observations"])
                if scenario=="single_obstacle":
                    reading=next(r for r in batch["observations"] if r["id"]=="urm37")
                    self.assertAlmostEqual(reading["value"],.65,places=4)
                if scenario=="narrow_passage": self.assertFalse(scene.clearance()["sweep_forward"])
                if scenario=="sensor_failure":
                    self.assertFalse(next(r for r in batch["observations"] if r["id"]=="urm37")["valid"])
            finally: world.close()

    def test_noise_latency_failure_and_bounded_proxy(self):
        from simulation.twin import World
        from simulation.environment import Scene, UltrasonicSettings
        clock=[0.]
        world=World()
        try:
            scene=Scene(world,"empty",clock=lambda:clock[0],latency=.1,proxy=True)
            self.assertFalse(any(r["kind"]=="range" for r in scene.telemetry()["observations"]))
            clock[0]=.15
            self.assertTrue(any(r["kind"]=="range" for r in scene.telemetry()["observations"]))
            scene.ultrasonic["urm37"].mode="out_of_range"
            clock[0]=.4
            scene.telemetry()
            clock[0]=.55
            manager=SensorManager(clock=lambda:clock[0])
            manager.ingest(scene.telemetry())
            self.assertIsNotNone(manager.snapshot()["fault"])
            with self.assertRaises(ValueError): scene.advance(dict(armed=False),dt=1)
            with self.assertRaises(ValueError): UltrasonicSettings(noise_m=-1)
        finally: world.close()

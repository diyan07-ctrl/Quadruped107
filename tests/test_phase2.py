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
        target=dict(detected=True,offset=-.8,observed_at=0.)
        self.step(mode="opencv",observation=target)
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
        self.touches={}

    def sample(self,now):
        self.seq+=1
        return fixture_batch(self.seq,distance=-1 if self.disconnected else self.distance,touches=self.touches)


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
        response=self.api.post("/api/mode",json={"mode":"explore"})
        self.assertEqual(response.status_code,200,response.get_json())
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

    def test_stop_during_recovery_cancels_queued_turn(self):
        self.backend.distance=.2
        self.pump(lambda:self.runtime.sensors.snapshot()["front_m"]==.2)
        self.assertEqual(self.api.post("/api/arm",json={}).status_code,200)
        self.assertEqual(self.api.post("/api/mode",json={"mode":"explore"}).status_code,200)
        self.pump(lambda:self.runtime.link.engine.snapshot()["activeMotion"]=="turn_left")
        self.assertEqual(self.api.post("/api/stop",json={}).status_code,200)
        self.assertFalse(self.runtime.link.engine.snapshot()["armed"])
        time.sleep(.1)
        self.assertFalse(self.runtime.link.engine.snapshot()["activeMask"])

    def test_touch_executes_existing_greeting_and_expires(self):
        self.api.post("/api/arm",json={})
        self.api.post("/api/mode",json={"mode":"explore"})
        self.pump(lambda:self.runtime.link.engine.snapshot()["activeMotion"]=="forward")
        self.backend.touches={"head":True}
        self.pump(lambda:self.runtime.link.engine.snapshot()["activeMotion"]=="greeting")
        deadline=self.runtime.navigation_state()["deadline"]
        self.backend.touches={}
        self.pump(lambda:not self.runtime.motion.snapshot()["enabled"],timeout=3)
        self.pump(lambda:not self.runtime.link.engine.snapshot()["armed"])
        self.assertLessEqual(deadline,time.monotonic(),self.runtime.motion.snapshot())

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

    def test_touch_scenario_waits_for_explicit_enable(self):
        from simulation.twin import World
        from simulation.environment import Scene
        clock=[0.]
        world=World()
        try:
            scene=Scene(world,"touch",clock=lambda:clock[0],latency=0)
            clock[0]=10.
            scene.telemetry()
            self.assertFalse(scene.touches["head"].pressed)
            scene.advance(dict(armed=True,activeMask=0,targets=[300]*8))
            clock[0]=11.05
            scene.telemetry()
            self.assertTrue(scene.touches["head"].pressed)
            scene.advance(dict(armed=False,activeMask=0,targets=[300]*8))
            clock[0]=11.21
            scene.telemetry()
            self.assertFalse(scene.touches["head"].pressed)
        finally: world.close()

    def test_scene_reset_is_seeded_disarmed_and_changes_epoch(self):
        from simulation.twin import World
        from simulation.environment import Scene
        world=World()
        receiver=TraceReceiver()
        try:
            scene=Scene(world,"single_obstacle",latency=0,noise=.001)
            first=scene.telemetry()["observations"][0]["value"]
            old=receiver.session
            scene.add_box(.5,0,.05,.1)
            scene.touches["head"].pressed=True
            scene.reset(receiver)
            self.assertNotEqual(receiver.session,old)
            self.assertFalse(receiver.state["armed"])
            self.assertFalse(world.active_mask)
            self.assertFalse(scene.touches["head"].pressed)
            self.assertEqual(scene.telemetry()["observations"][0]["value"],first)
            self.assertEqual(world.diagnostics()["fixturePositionErrorM"],0)
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


class NetworkNavigationTests(unittest.TestCase):
    def test_pybullet_rays_udp_controller_proxy_obstacle_stop(self):
        from simulation.twin import World
        from simulation.environment import Scene
        world=World()
        scene=Scene(world,"single_obstacle",latency=0,proxy=True)
        server=TraceServer(port=0,sensors=scene.telemetry)
        runtime=Runtime(camera_backend="synthetic",actuator_backend="virtual",virtual_sensors=True,
                        simulator_host=server.address[0],simulator_port=server.address[1])
        runtime.start()
        api=create_app(runtime).test_client()
        def pump(predicate,timeout=5):
            deadline=time.monotonic()+timeout
            heartbeat=0
            while time.monotonic()<deadline:
                frame=server.poll()
                self.assertTrue(scene.advance(frame))
                world.apply(frame)
                world.step()
                if time.monotonic()-heartbeat>.15:
                    api.post("/api/heartbeat",json={})
                    heartbeat=time.monotonic()
                if predicate(): return
                time.sleep(.003)
            self.fail(json.dumps(dict(runtime=runtime.state(),world=world.diagnostics(),clearance=scene.clearance(),rays=[(a,b,h[:4]) for a,b,h in scene.ultrasonic["urm37"].last_rays])))
        try:
            pump(lambda:runtime.link.snapshot()["connected"] and runtime.bridge.snapshot()["readyToArm"] and runtime.sensors.snapshot()["fault"] is None)
            self.assertEqual(api.post("/api/arm",json={}).status_code,200)
            self.assertEqual(api.post("/api/mode",json={"mode":"explore"}).status_code,200)
            pump(lambda:runtime.link.engine.snapshot()["activeMotion"]=="forward")
            pump(lambda:not runtime.motion.snapshot()["enabled"],timeout=6)
            pump(lambda:not server.receiver.state["armed"],timeout=1)
            self.assertEqual(scene.proxy_contacts,0)
            self.assertGreater(world.diagnostics()["basePosition"][0],0)
            self.assertLessEqual(runtime.sensors.snapshot()["front_m"],.6)
            self.assertFalse(world.active_mask)
            self.assertFalse(runtime.motion.snapshot()["enabled"])
            print("NAVIGATION_SCENARIO_JSON="+json.dumps(dict(classification="SIMULATED UDP INTEGRATION",
                scenario="single_obstacle",physicalValidation=False,
                proxyPose=world.diagnostics()["basePosition"],frontM=runtime.sensors.snapshot()["front_m"],
                proxyContacts=scene.proxy_contacts,activeMask=world.active_mask,
                fault=runtime.motion.snapshot()["fault"],steps=world.frames)))
        finally:
            runtime.close()
            server.close()
            world.close()

    def test_stale_duplicate_and_unexpected_sender_telemetry(self):
        receiver=TraceReceiver()
        peer=("127.0.0.1",10000)
        client="ab"*16
        challenge=decode(receiver.handle(encode(dict(v=1,type="hello",client=client)),peer))
        frame=dict(v=1,type="trace",client=client,server=challenge["server"],nonce=challenge["nonce"],
                   seq=1,virtual=True,armed=False,activeMask=0,targets=[300]*8)
        self.assertIsNone(receiver.handle(encode(frame),("127.0.0.1",10001)))
        self.assertIsNotNone(receiver.handle(encode(frame),peer))
        self.assertIsNone(receiver.handle(encode(frame),peer))
        self.assertIsNone(receiver.handle(b"["*1000+b"]"*1000,peer))
        self.assertIsNone(receiver.handle(b"x"*2049,peer))

    def test_three_touch_configuration(self):
        manager=SensorManager(SensorConfig(touch_count=3))
        self.assertTrue(manager.ingest(fixture_batch(touch_count=3)))
        self.assertIsNone(manager.snapshot()["fault"])
        self.assertEqual(len(manager.snapshot()["touches"]),3)

    def test_noise_is_seeded_and_no_echo_is_invalid(self):
        from simulation.twin import World
        from simulation.environment import SimulatedUltrasonicSensor, UltrasonicSettings
        world=World()
        try:
            left=SimulatedUltrasonicSensor("urm37",world,UltrasonicSettings(noise_m=.01,latency=0),seed=7)
            right=SimulatedUltrasonicSensor("urm37",world,UltrasonicSettings(noise_m=.01,latency=0),seed=7)
            self.assertEqual(left.sample(0)["value"],right.sample(0)["value"])
            left.mode="no_echo"
            self.assertFalse(left.sample(1)["valid"])
        finally: world.close()


class TrackingIntegrationTests(unittest.TestCase):
    def test_blue_camera_tracking_obstacle_and_manual_takeover(self):
        import cv2
        import numpy as np
        from quadruped.camera import Camera
        class BlueCamera(Camera):
            def _run(self):
                while not self.stop_event.wait(.1):
                    frame=np.zeros((480,640,3),dtype=np.uint8)
                    cv2.circle(frame,(90,240),35,(255,0,0),-1)
                    _,jpeg=cv2.imencode(".jpg",frame)
                    with self.lock:
                        self.frame,self.jpeg=frame,jpeg.tobytes()
                        self.timestamp=time.monotonic()
                        self.sequence+=1
                        self.status="Synthetic blue-target integration fixture"
        backend=ExplicitBackend()
        runtime=Runtime(camera_backend="synthetic",actuator_backend="virtual",virtual_sensors=True,sensor_backend=backend)
        runtime.camera=BlueCamera(simulate=True)
        runtime.start()
        api=create_app(runtime).test_client()
        def pump(predicate,timeout=4):
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                api.post("/api/heartbeat",json={})
                if predicate(): return
                time.sleep(.03)
            self.fail(json.dumps(runtime.state()))
        try:
            pump(lambda:runtime.link.snapshot()["connected"] and runtime.camera.latest()[0] is not None and not runtime.sensors.snapshot()["fault"])
            self.assertEqual(api.post("/api/arm",json={}).status_code,200)
            self.assertEqual(api.post("/api/mode",json={"mode":"opencv"}).status_code,200)
            pump(lambda:runtime.link.engine.snapshot()["activeMotion"]=="turn_left")
            self.assertEqual(api.post("/api/mode",json={"mode":"manual"}).status_code,200)
            self.assertFalse(runtime.link.engine.snapshot()["armed"])
            pump(lambda:not runtime.motion.snapshot()["busy"] and not runtime.motion.snapshot()["stopping"])
            self.assertEqual(api.post("/api/arm",json={}).status_code,200)
            self.assertEqual(api.post("/api/mode",json={"mode":"opencv"}).status_code,200)
            pump(lambda:runtime.link.engine.snapshot()["activeMotion"]=="turn_left")
            backend.distance=.2
            pump(lambda:not runtime.motion.snapshot()["enabled"])
            pump(lambda:not runtime.link.engine.snapshot()["activeMask"])
            self.assertFalse(any(line.startswith("MOVE") and line.endswith("forward") for line in runtime.link.engine.snapshot()["history"]))
        finally: runtime.close()


class LifecycleRegressionTests(unittest.TestCase):
    def test_idle_rejects_stale_generation_without_overwriting_mode(self):
        from quadruped.controller import MotionController
        from quadruped.serial_link import SimulatedLink
        controller=MotionController(SimulatedLink())
        controller.arm()
        old=controller.snapshot()["generation"]
        controller.set_mode("explore")
        with self.assertRaises(RuntimeError): controller.set_mode("idle",expected_generation=old)
        self.assertEqual(controller.snapshot()["appMode"],"explore")
        controller.close()

    def test_prerecorded_blue_fixture_through_file_camera(self):
        import runpy
        import tempfile
        from quadruped.camera import Camera
        from quadruped.vision import detect_blue_ball
        with tempfile.TemporaryDirectory() as directory:
            video=runpy.run_path(str(ROOT/"tools/generate-blue-video.py"))["generate"](Path(directory)/"blue.avi")
            camera=Camera(backend="file",device=str(video))
            camera.start()
            try:
                wait_for(lambda:camera.latest()[0] is not None)
                observation=detect_blue_ball(camera.latest()[0])
                self.assertTrue(observation["detected"])
                self.assertLess(observation["offset"],-.5)
            finally: camera.close()

    def test_reset_disconnect_and_reconnect_never_rearm(self):
        import threading
        sequence=[0]
        def provider():
            sequence[0]+=1
            return fixture_batch(sequence[0])
        server=TraceServer(port=0,sensors=provider)
        address=server.address
        quit_server=threading.Event()
        def serve():
            while not quit_server.wait(.005): server.poll()
        thread=threading.Thread(target=serve)
        thread.start()
        runtime=Runtime(camera_backend="synthetic",actuator_backend="virtual",virtual_sensors=True,
                        simulator_host=address[0],simulator_port=address[1])
        runtime.start()
        api=create_app(runtime).test_client()
        def pump(predicate,timeout=4):
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                api.post("/api/heartbeat",json={})
                if predicate(): return
                time.sleep(.02)
            self.fail(json.dumps(runtime.state()))
        try:
            pump(lambda:runtime.link.snapshot()["connected"] and runtime.bridge.snapshot()["readyToArm"] and not runtime.sensors.snapshot()["fault"])
            self.assertEqual(api.post("/api/arm",json={}).status_code,200)
            api.post("/api/mode",json={"mode":"explore"})
            pump(lambda:runtime.link.engine.snapshot()["activeMotion"]=="forward")
            server.receiver.reset()
            pump(lambda:not runtime.motion.snapshot()["enabled"])
            pump(lambda:not runtime.motion.snapshot()["stopping"] and
                 not runtime.link.engine.snapshot()["armed"] and runtime.bridge.snapshot()["readyToArm"])
            self.assertFalse(runtime.motion.snapshot()["enabled"])
            self.assertEqual(api.post("/api/arm",json={}).status_code,200)
            api.post("/api/mode",json={"mode":"explore"})
            pump(lambda:runtime.link.engine.snapshot()["activeMotion"]=="forward")
            quit_server.set()
            thread.join(1)
            server.close()
            pump(lambda:not runtime.motion.snapshot()["enabled"])
            pump(lambda:not runtime.link.engine.snapshot()["armed"])
            server=TraceServer(*address,sensors=provider)
            quit_server.clear()
            thread=threading.Thread(target=serve)
            thread.start()
            pump(lambda:runtime.bridge.snapshot()["readyToArm"])
            self.assertFalse(runtime.motion.snapshot()["enabled"])
            self.assertFalse(runtime.link.engine.snapshot()["activeMask"])
        finally:
            runtime.close()
            quit_server.set()
            thread.join(1)
            if server.socket.fileno()!=-1: server.close()

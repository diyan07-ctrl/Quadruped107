"""Synthetic BGR camera -> real app/controller -> virtual serial -> UDP -> PyBullet."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
import cv2
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"software/pi"))
from quadruped.camera import Camera
from quadruped.main import Runtime,create_app
from quadruped.navigation import Navigation
from quadruped.sensors import SensorManager,fixture_batch
from quadruped.virtual_uno import VirtualUno

class PersonalityTests(unittest.TestCase):
    def test_overlapping_requests_and_stop_cancellation(self):
        clock=[0.]
        sensors=SensorManager(clock=lambda:clock[0])
        sensors.ingest(fixture_batch())
        nav=Navigation()
        nav.request_interaction("greeting",1,10)
        with self.assertRaises(RuntimeError): nav.request_interaction("tail_wag",1,10)
        decision=nav.step("interaction",True,1,sensors.snapshot(),None,0,generation=10)
        self.assertEqual((decision.state,decision.motion),("PERSONALITY","greeting"))
        self.assertIsNone(nav.step("manual",False,1,sensors.snapshot(),None,.1,generation=11).motion)
        self.assertIsNone(nav.pending_interaction)

    def test_interaction_needs_clearance_and_matching_generation(self):
        manager=SensorManager(clock=lambda:0)
        manager.ingest(fixture_batch(distance=.2))
        nav=Navigation()
        nav.request_interaction("attention",1,1)
        self.assertTrue(nav.step("interaction",True,1,manager.snapshot(),None,0,generation=1).stop)
        nav=Navigation()
        nav.request_interaction("attention",1,1)
        manager.ingest(fixture_batch(1))
        decision=nav.step("interaction",True,1,manager.snapshot(),None,0,generation=2)
        self.assertIsNone(decision.motion)
        with self.assertRaises(ValueError): nav.request_interaction({},1,1)

class SmoothingTests(unittest.TestCase):
    def test_stop_discards_smoothing_residual_and_does_not_delay_output_off(self):
        from simulation.twin import World
        world=World(target_rate=2)
        try:
            world.apply(dict(virtual=True,armed=True,activeMask=255,targets=[400]*8))
            for _ in range(10): world.step()
            self.assertLessEqual(world.max_motor_jump,2/240+1e-12)
            world.apply(dict(virtual=True,armed=False,activeMask=0,targets=[400]*8))
            target=list(world.motor_targets)
            for _ in range(30): world.step()
            self.assertFalse(world.active_mask)
            self.assertEqual(target,world.motor_targets)
            self.assertFalse(world.diagnostics()["physicalLocomotionValidated"])
        finally: world.close()

    def test_invalid_smoothing_configuration(self):
        from simulation.twin import World
        for value in (-1,4,float("nan"),True):
            with self.assertRaises(ValueError): World(target_rate=value)

class IntegratedDemonstrationTests(unittest.TestCase):
    def test_both_colors_motion_obstacle_camera_reset_and_stop(self):
        from simulation.twin import World
        from simulation.environment import Scene
        from quadruped.bridge import TraceServer
        source=dict(x=100,color=(255,0,0),available=True)
        class DemoCamera(Camera):
            def _run(self):
                while not self.stop_event.wait(.1):
                    if not source["available"]:
                        with self.lock:
                            self.frame=self.jpeg=None
                            self.timestamp=0
                        continue
                    frame=np.zeros((480,640,3),dtype=np.uint8)
                    if source["x"] is not None: cv2.circle(frame,(source["x"],240),35,source["color"],-1)
                    _,jpeg=cv2.imencode(".jpg",frame)
                    with self.lock:
                        self.frame,self.jpeg=frame,jpeg.tobytes()
                        self.timestamp=time.monotonic()
                        self.sequence+=1
                        self.status="SYNTHETIC integrated demonstration"
        world=World()
        scene=Scene(world,"empty",latency=0)
        server=TraceServer(port=0,sensors=scene.telemetry)
        with tempfile.TemporaryDirectory() as folder:
            runtime=Runtime(camera_backend="synthetic",actuator_backend="virtual",virtual_sensors=True,
                simulator_host=server.address[0],simulator_port=server.address[1],vision_state=Path(folder)/"vision.json")
            runtime.camera=DemoCamera(simulate=True)
            runtime.start()
            api=create_app(runtime).test_client()
            traces=set()
            evidence=[]
            def pump(predicate,timeout=5):
                deadline=time.monotonic()+timeout
                heartbeat=0
                while time.monotonic()<deadline:
                    frame=server.poll()
                    traces.add(tuple(frame["targets"]))
                    world.apply(frame); world.step()
                    if time.monotonic()-heartbeat>.15:
                        api.post("/api/heartbeat",json={})
                        heartbeat=time.monotonic()
                    if predicate(): return
                    time.sleep(.004)
                self.fail(json.dumps(runtime.state()))
            def ready():
                pump(lambda:runtime.link.snapshot()["connected"] and runtime.bridge.snapshot()["readyToArm"] and
                    not runtime.motion.snapshot()["busy"] and not runtime.motion.snapshot()["stopping"] and
                    not runtime.sensors.snapshot()["fault"] and runtime.camera.latest()[0] is not None and
                    runtime.state()["vision"]["targetFresh"] and runtime.vision.get("blueBall",{}).get("detected"))
            def enable():
                ready()
                result=api.post("/api/arm",json={})
                self.assertEqual(result.status_code,200,result.json)
                response=api.post("/api/mode",json={"mode":"opencv"})
                self.assertEqual(response.status_code,200,response.json)
            try:
                for color,bgr in (("blue",(255,0,0)),("yellow",(0,255,180))):
                    source.update(x=100,color=bgr,available=True)
                    if color=="yellow":
                        result=api.post("/api/vision",json={"revision":1,"target_color":"yellow"})
                        self.assertEqual(result.status_code,200,result.json)
                        self.assertFalse(runtime.motion.snapshot()["enabled"])
                    enable()
                    pump(lambda:runtime.link.engine.snapshot()["activeMotion"]=="turn_left")
                    pump(lambda:server.receiver.state.get("activeMotion")=="turn_left")
                    self.assertTrue(world.active_mask)
                    for x in (180,260,320):
                        source["x"]=x
                        pump(lambda:runtime.vision.get("blueBall",{}).get("x")==x)
                    pump(lambda:runtime.navigation.tracker.state=="TARGET_CENTER")
                    for x in (400,480,560):
                        source["x"]=x
                        pump(lambda:runtime.vision.get("blueBall",{}).get("x")==x)
                    pump(lambda:runtime.link.engine.snapshot()["activeMotion"]=="turn_right")
                    evidence.append(dict(target=color,acceptedLeft=True,acceptedRight=True,centered=True))
                    if color=="blue":
                        source["x"]=None
                        pump(lambda:not runtime.motion.snapshot()["enabled"],2)
                        pump(lambda:not runtime.link.engine.snapshot()["armed"])
                    else:
                        scene.add_box(.45,0,.05,.4)
                        pump(lambda:not runtime.motion.snapshot()["enabled"],2)
                        pump(lambda:not server.receiver.state["armed"])
                        self.assertFalse(world.active_mask)
                scene.reset(server.receiver)
                source["x"]=100
                ready()
                self.assertFalse(runtime.motion.snapshot()["enabled"])
                enable()
                pump(lambda:runtime.link.engine.snapshot()["activeMotion"]=="turn_left")
                source["available"]=False
                pump(lambda:not runtime.motion.snapshot()["enabled"],1.5)
                source["available"]=True
                ready()
                self.assertFalse(runtime.motion.snapshot()["enabled"])
                enable()
                pump(lambda:runtime.link.engine.snapshot()["activeMotion"]=="turn_left")
                server.receiver.reset()
                pump(lambda:not runtime.motion.snapshot()["enabled"],1.5)
                ready()
                self.assertFalse(runtime.motion.snapshot()["enabled"])
                enable()
                pump(lambda:runtime.link.engine.snapshot()["activeMotion"]=="turn_left")
                self.assertEqual(api.post("/api/stop",json={}).status_code,200)
                self.assertFalse(runtime.link.engine.snapshot()["activeMask"])
                self.assertGreater(len(traces),5)
                statuses={item["status"] for item in runtime.motion.events.snapshot()}
                self.assertIn("acknowledged_complete",statuses)
                print("DEMONSTRATION_JSON="+json.dumps(dict(source="synthetic BGR camera fixture",physicalValidation=False,
                    targets=evidence,virtualJoints=8,distinctTargetVectors=len(traces),stop=True,
                    obstacleOverride=True,cameraFault=True,simulatorReset=True,automaticRearm=False)))
            finally:
                runtime.close(); server.close(); world.close()


class InteractionRuntimeTests(unittest.TestCase):
    def test_explicit_personality_uses_virtual_uno_and_stop_cancels(self):
        from test_phase2 import ExplicitBackend
        from test_runtime import wait_for
        runtime=Runtime(camera_backend="synthetic",actuator_backend="virtual",virtual_sensors=True,sensor_backend=ExplicitBackend())
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
            pump(lambda:runtime.link.snapshot()["connected"] and not runtime.sensors.snapshot()["fault"])
            self.assertEqual(api.post("/api/arm",json={}).status_code,200)
            self.assertEqual(api.post("/api/mode",json={"mode":"interaction"}).status_code,200)
            self.assertEqual(api.post("/api/interaction",json={"name":"greeting"}).status_code,200)
            self.assertEqual(api.post("/api/interaction",json={"name":"tail_wag"}).status_code,409)
            pump(lambda:runtime.link.engine.snapshot()["activeMotion"]=="greeting")
            self.assertEqual(api.post("/api/stop",json={}).status_code,200)
            self.assertFalse(runtime.link.engine.snapshot()["activeMask"])
            self.assertEqual(api.post("/api/interaction",json={"name":"attention"}).status_code,409)
            self.assertEqual(sum(line.startswith("MOVE") and line.endswith("greeting") for line in runtime.link.engine.snapshot()["history"]),1)
        finally: runtime.close()

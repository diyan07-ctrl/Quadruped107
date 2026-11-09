"""Freshness/order/lease tests for simulator transport and CAD PyBullet fixtures."""
import importlib.util
import json
from pathlib import Path
import sys
import threading
import time
import unittest
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"software/pi"))
from quadruped.bridge import TraceReceiver, TraceServer, TraceClient, encode, decode, LEASE
from quadruped.main import Runtime, create_app
from quadruped.camera import Camera
from test_runtime import wait_for


class BridgeContractTests(unittest.TestCase):
    def setUp(self):
        self.now=0.0
        self.receiver=TraceReceiver(clock=lambda:self.now)
        self.peer=("127.0.0.1",40000)
        self.client="ab"*16
        self.seq=0

    def challenge(self,client=None,peer=None):
        return decode(self.receiver.handle(encode(dict(v=1,type="hello",client=client or self.client)),peer or self.peer))

    def frame(self,armed=False,challenge=None,**changes):
        challenge=challenge or self.challenge()
        self.seq+=1
        data=dict(v=1,type="trace",client=self.client,server=challenge["server"],nonce=challenge["nonce"],seq=self.seq,
                  virtual=True,armed=armed,activeMask=255 if armed else 0,targets=[300]*8)
        data.update(changes)
        return data

    def send(self,data): return self.receiver.handle(encode(data),self.peer)

    def test_disarmed_handshake_required_before_arm(self):
        self.send(self.frame(True))
        self.assertFalse(self.receiver.state["armed"])
        self.send(self.frame(False))
        self.send(self.frame(True))
        self.assertTrue(self.receiver.state["armed"])

    def test_duplicate_and_stale_challenge_do_not_renew_lease(self):
        self.send(self.frame(False))
        data=self.frame(True)
        self.send(data)
        self.now=.2
        self.assertIsNone(self.send(data))
        self.now=.31
        self.assertFalse(self.receiver.snapshot()["armed"])
        old=self.challenge()
        self.now+=.16
        self.assertIsNone(self.send(self.frame(True,challenge=old)))
        self.assertFalse(self.receiver.snapshot()["armed"])

    def test_stop_invalidates_older_armed_frame(self):
        self.send(self.frame(False))
        self.send(self.frame(True))
        delayed=self.frame(True)
        self.send(dict(v=1,type="stop",client=self.client,server=self.receiver.session,seq=delayed["seq"]+1))
        self.assertIsNone(self.send(delayed))
        self.assertFalse(self.receiver.snapshot()["activeMask"])

    def test_reset_and_new_process_cannot_replay_arm(self):
        self.send(self.frame(False))
        old=self.frame(True)
        self.receiver.reset()
        self.assertIsNone(self.send(old))
        self.send(self.frame(False))
        self.now+=LEASE+.01
        reply=self.challenge(client="cd"*16,peer=("127.0.0.1",40001))
        self.assertNotEqual(reply["server"],old["server"])
        self.assertFalse(self.receiver.snapshot()["armed"])

    def test_invalid_payloads_are_rejected(self):
        for changes in ({"targets":[True]*8},{"targets":[601]*8},{"targets":[300]*7},{"activeMask":256},
                        {"virtual":False},{"seq":-1},{"armed":"true"}):
            self.assertIsNone(self.send(self.frame(**changes)))
        self.assertIsNone(self.receiver.handle(b"x"*3000,self.peer))
        self.assertIsNone(self.receiver.handle(b"not json",self.peer))
        self.assertFalse(self.receiver.snapshot()["armed"])

    def test_real_udp_loopback_and_priority_stop(self):
        server=TraceServer(port=0)
        state=dict(virtual=True,armed=False,targets=[300]*8,activeMask=0)
        stop=threading.Event()
        def serve():
            while not stop.wait(.005): server.poll()
        thread=threading.Thread(target=serve)
        thread.start()
        client=TraceClient(*server.address,lambda:dict(state))
        client.start()
        try:
            wait_for(lambda:client.snapshot()["connected"] and client.snapshot()["readyToArm"])
            client.prepare_arm()
            state.update(armed=True,activeMask=255)
            wait_for(lambda:server.receiver.state["armed"])
            state.update(armed=False,activeMask=0)
            wait_for(lambda:not server.receiver.state["armed"])
        finally:
            client.close()
            stop.set()
            thread.join(1)
            server.close()

    def test_runtime_stops_when_simulator_disappears(self):
        server=TraceServer(port=0)
        stop=threading.Event()
        def serve():
            while not stop.wait(.005): server.poll()
        thread=threading.Thread(target=serve)
        thread.start()
        runtime=Runtime(camera_backend="synthetic",actuator_backend="virtual",
                        simulator_host=server.address[0],simulator_port=server.address[1])
        runtime.start()
        try:
            wait_for(lambda:runtime.link.snapshot()["connected"],4)
            wait_for(lambda:runtime.bridge.snapshot()["readyToArm"])
            api=create_app(runtime).test_client()
            self.assertEqual(api.post("/api/arm",json={}).status_code,200)
            self.assertEqual(api.post("/api/mode",json={"mode":"forward"}).status_code,200)
            stop.set()
            thread.join(1)
            server.close()
            wait_for(lambda:not runtime.motion.snapshot()["enabled"],1.2)
            wait_for(lambda:not runtime.link.engine.snapshot()["activeMask"],1.0)
            self.assertFalse(runtime.link.engine.snapshot()["armed"])
        finally:
            runtime.close()
            stop.set()
            thread.join(1)
            if server.socket.fileno()!=-1: server.close()


@unittest.skipUnless(importlib.util.find_spec("pybullet"),"NOT TESTED: install simulation/requirements.txt")
class DigitalTwinTests(unittest.TestCase):
    def test_cad_dimensions_joint_mapping_and_headless_motion(self):
        from simulation.build_model import mesh_info
        from simulation.twin import World
        info=mesh_info(ROOT/"hardware/stl/Base.stl")
        self.assertEqual(info["size"],[140.0,155.0,29.0])
        world=World()
        try:
            self.assertEqual(len(world.joints),8)
            self.assertAlmostEqual(world.angle(0,278),0)
            world.apply(dict(virtual=True,armed=True,activeMask=255,targets=[300]*8))
            for _ in range(240): values=world.step()
            self.assertTrue(all(np.isfinite(values)))
            with self.assertRaises(ValueError): world.apply(dict(virtual=False,armed=True,targets=[300]*8,activeMask=255))
            with self.assertRaises(ValueError): world.angle(0,1000)
        finally: world.close()

    def test_camera_perception_controller_protocol_udp_and_pybullet(self):
        from simulation.twin import World
        target={"x":80}
        class TargetCamera(Camera):
            def _run(self):
                while not self.stop_event.wait(.1):
                    frame=np.zeros((480,640,3),dtype=np.uint8)
                    if target["x"] is not None: cv2.circle(frame,(target["x"],240),35,(255,0,0),-1)
                    _,jpeg=cv2.imencode(".jpg",frame)
                    with self.lock:
                        self.frame,self.jpeg=frame,jpeg.tobytes()
                        self.timestamp=time.monotonic()
                        self.sequence+=1
                        self.status="Synthetic target test fixture"
        world=World()
        server=TraceServer(port=0)
        runtime=Runtime(camera_backend="synthetic",actuator_backend="virtual",
                        simulator_host=server.address[0],simulator_port=server.address[1])
        runtime.camera=TargetCamera(simulate=True)
        runtime.start()
        api=create_app(runtime).test_client()
        signatures=set()
        def pump(predicate,timeout=5,heartbeat=True):
            deadline=time.monotonic()+timeout
            last_heartbeat=0
            while time.monotonic()<deadline:
                frame=server.poll()
                signatures.add(tuple(frame["targets"]))
                world.apply(frame)
                world.step()
                if heartbeat and time.monotonic()-last_heartbeat>.15:
                    api.post("/api/heartbeat",json={"motion":None})
                    last_heartbeat=time.monotonic()
                if predicate(): return
                time.sleep(.005)
            self.fail("Integrated pipeline condition timed out")
        try:
            pump(lambda:runtime.link.snapshot()["connected"] and runtime.bridge.snapshot()["readyToArm"])
            self.assertEqual(api.post("/api/arm",json={}).status_code,200)
            self.assertEqual(api.post("/api/mode",json={"mode":"opencv"}).status_code,200)
            pump(lambda:any(line.endswith("turn_left") and line.startswith("MOVE") for line in runtime.link.engine.snapshot()["history"]))
            target["x"]=320
            pump(lambda:runtime.vision.get("behavior")=="TARGET_CENTER")
            target["x"]=None
            pump(lambda:not runtime.motion.snapshot()["enabled"],timeout=2)
            pump(lambda:not server.receiver.state["armed"],timeout=1)
            self.assertGreater(len(signatures),3)
            self.assertFalse(world.diagnostics()["physicalLocomotionValidated"])
            self.assertEqual(world.diagnostics()["jointCount"],8)
        finally:
            runtime.close()
            server.close()
            world.close()

"""USB backend fixtures, perception/FSM decisions and the explicit virtual Uno."""
import math
import sys
import time
import unittest
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"software/pi"))
from quadruped.camera import Camera
from quadruped.autonomy import Behavior, VisionSettings
from quadruped.virtual_uno import VirtualUno, VirtualSerial, DATA
from quadruped.main import Runtime, create_app
from quadruped.vision import detect_blue_ball


class CameraBackendTests(unittest.TestCase):
    def test_usb_yuyv_configuration_and_release(self):
        resources=[]
        camera=None
        class Capture:
            def __init__(self,*args): self.args=args; self.settings=[]; self.released=False; resources.append(self)
            def isOpened(self): return True
            def set(self,*args): self.settings.append(args); return True
            def read(self):
                camera.stop_event.set()
                return True,np.zeros((240,320,3),dtype=np.uint8)
            def release(self): self.released=True
        camera=Camera(backend="usb",device="/dev/video0",width=320,height=240,fps=8,factory=Capture)
        camera._run()
        self.assertEqual(resources[0].args,("/dev/video0",cv2.CAP_V4L2))
        self.assertIn((cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc(*"YUYV")),resources[0].settings)
        self.assertTrue(resources[0].released)
        self.assertEqual(camera.latest()[0].shape,(240,320,3))

    def test_missing_device_releases_failed_resource(self):
        class Missing:
            released=False
            def isOpened(self): return False
            def release(self): self.released=True
        resource=Missing()
        camera=Camera(backend="usb",factory=lambda *args:resource)
        with self.assertRaises(RuntimeError): camera._open()
        self.assertTrue(resource.released)

    def test_capture_failure_reopens_without_stale_frame(self):
        resources=[]
        camera=None
        class Capture:
            def __init__(self,*args): self.number=len(resources);self.released=False;resources.append(self)
            def isOpened(self): return True
            def set(self,*args): return True
            def read(self):
                if self.number==0: return False,None
                camera.stop_event.set()
                return True,np.zeros((480,640,3),dtype=np.uint8)
            def release(self): self.released=True
        camera=Camera(backend="usb",factory=Capture)
        camera._run()
        self.assertEqual(camera.errors,1)
        self.assertEqual(len(resources),2)
        self.assertTrue(all(r.released for r in resources))
        self.assertIsNotNone(camera.latest()[1])

    def test_frozen_capture_invalidates_image(self):
        camera=None
        class Frozen:
            def isOpened(self): return True
            def set(self,*args): return True
            def read(self):
                time.sleep(.015)
                return True,np.zeros((100,100,3),dtype=np.uint8)
            def release(self): camera.stop_event.set()
        camera=Camera(backend="usb",freeze_seconds=.02,factory=lambda *args:Frozen())
        camera._run()
        self.assertIsNone(camera.latest()[0])
        self.assertIn("Unchanged",camera.last_error)

    def test_bad_configurations(self):
        for kwargs in ({"backend":"missing"},{"fps":0},{"fps":math.nan},{"width":0},{"height":True}):
            with self.assertRaises(ValueError): Camera(**kwargs)


class DecisionTests(unittest.TestCase):
    def obs(self,x=0,at=0,detected=True):
        return dict(detected=detected,offset=x,observed_at=at)

    def test_left_right_center_and_hysteresis(self):
        behavior=Behavior(VisionSettings(min_frames=1))
        self.assertEqual(behavior.step(self.obs(-.8),0).state,"TARGET_LEFT")
        self.assertEqual(behavior.step(self.obs(-.25,.1),.1).state,"TARGET_LEFT")
        self.assertEqual(behavior.step(self.obs(.25,.2),.2).state,"TARGET_CENTER")
        self.assertEqual(behavior.step(self.obs(.8,.3),.3).motion,"turn_right")

    def test_persistence_and_frequency_bound(self):
        behavior=Behavior()
        self.assertEqual(behavior.step(self.obs(-.8),0).state,"IDLE")
        decision=behavior.step(self.obs(-.8,.1),.1)
        self.assertEqual(decision.motion,"turn_left")
        behavior.accepted(decision.motion,.1)
        self.assertIsNone(behavior.step(self.obs(-.8,.2),.2).motion)

    def test_stale_missing_future_and_invalid_observations(self):
        for observation,now in ((None,0),(self.obs(0,0),1),(self.obs(0,1),0),(self.obs(math.nan),0)):
            self.assertTrue(Behavior().step(observation,now).inhibit)

    def test_loss_stops_and_search_is_explicit_and_bounded(self):
        self.assertTrue(Behavior().step(self.obs(at=1,detected=False),1).inhibit)
        behavior=Behavior(VisionSettings(search_enabled=True))
        self.assertEqual(behavior.step(self.obs(at=.4,detected=False),.4).state,"SEARCHING")
        self.assertTrue(behavior.step(self.obs(at=3,detected=False),3).inhibit)

    def test_stop_manual_and_virtual_obstacle_priority(self):
        self.assertEqual(Behavior().step(None,0,stopped=True).state,"STOPPED")
        self.assertEqual(Behavior().step(None,0,manual=True).state,"MANUAL_OVERRIDE")
        self.assertTrue(Behavior().step(self.obs(),0,obstacle=True).inhibit)

    def test_invalid_settings_and_hsv_configuration(self):
        for kwargs in ({"enter_error":0},{"min_frames":True},{"hsv_lower":(300,0,0)},{"command_period":math.inf}):
            with self.assertRaises(ValueError): VisionSettings(**kwargs)
        frame=np.zeros((480,640,3),dtype=np.uint8)
        cv2.circle(frame,(320,240),35,(0,0,255),-1)
        result=detect_blue_ball(frame,lower=(0,100,100),upper=(10,255,255))
        self.assertTrue(result["detected"])
        self.assertEqual(len(result["bbox"]),4)
        self.assertGreater(result["area"],0)


class VirtualProtocolTests(unittest.TestCase):
    def setUp(self):
        self.now=0.0
        self.engine=VirtualUno(clock=lambda:self.now)
        self.lines=[]
        self.engine.emit=self.lines.append

    def send(self,text): self.engine.feed((text+"\n").encode("ascii"))

    def test_handshake_safe_arm_and_reset(self):
        self.send("HELLO")
        self.assertEqual(self.lines[-1],"READY Quadruped107 1")
        self.send("ARM 1")
        self.assertTrue(self.engine.armed)
        self.assertEqual(self.engine.active_mask,0)
        self.engine.reset()
        self.assertFalse(self.engine.armed)

    def test_every_real_routine_produces_bounded_eight_joint_trace(self):
        for name in DATA["routines"]:
            self.engine.reset()
            self.send("ARM 1")
            self.send("MOVE 2 "+name)
            for _ in range(2000):
                self.now+=.02
                self.send("PING")
                self.engine.advance()
                if self.engine.active is None: break
            self.assertIsNone(self.engine.active,name)
            self.assertIn("DONE 2 "+name,self.lines)
            self.assertTrue(self.engine.trace)
            self.assertTrue(all(len(ticks)==8 and all(50<=tick<=600 for tick in ticks)
                                for at,ticks,mask in self.engine.trace))

    def test_stop_preempts_active_move_and_hello_never_replays(self):
        self.send("ARM 1")
        self.send("MOVE 2 greeting")
        self.send("STOP 3")
        self.assertIn("ERR 2 stopped",self.lines)
        self.assertEqual(self.lines[-1],"DONE 3 stopped")
        self.assertFalse(self.engine.active_mask)
        self.send("HELLO")
        self.now+=1
        self.engine.advance()
        self.assertFalse(self.engine.armed)
        self.assertIsNone(self.engine.active)

    def test_watchdog_loss_faults_and_requires_arm(self):
        self.send("ARM 1")
        self.now=1.51
        self.engine.advance()
        self.assertEqual(self.lines[-1],"FAULT watchdog")
        self.send("MOVE 2 forward")
        self.assertEqual(self.lines[-1],"ERR 2 disarmed")

    def test_invalid_commands_overflow_and_busy(self):
        self.send("MOVE 1 forward")
        self.assertEqual(self.lines[-1],"ERR 1 disarmed")
        self.send("ARM 2")
        self.send("SERVO 3 8 300")
        self.assertEqual(self.lines[-1],"ERR 3 servo_out_of_range")
        self.send("MOVE 4 unknown")
        self.assertEqual(self.lines[-1],"ERR 4 unknown_motion")
        self.send("MOVE 5 forward")
        self.send("ARM 6")
        self.assertEqual(self.lines[-1],"ERR 6 busy")
        self.engine.feed(b"x"*80+b"\nSTOP 7\n")
        self.assertIn("ERR 0 line_too_long",self.lines)
        self.assertEqual(self.lines[-1],"DONE 7 stopped")

    def test_virtual_output_overflow_disarms_and_disconnects(self):
        device=VirtualSerial()
        try:
            device.engine.feed(b"ARM 1\n")
            for _ in range(300): device.engine.feed(b"PING\n")
            deadline=time.monotonic()+1
            while not device.closed.is_set() and time.monotonic()<deadline: time.sleep(.01)
            self.assertTrue(device.closed.is_set())
            self.assertFalse(device.engine.snapshot()["armed"])
            with self.assertRaises(OSError): device.write(b"ARM 2\n")
            with self.assertRaises(OSError): device.readline()
        finally: device.close()

    def test_virtual_serial_disconnect_is_explicit(self):
        device=VirtualSerial()
        device.close()
        with self.assertRaises(OSError): device.write(b"ARM 1\n")


class OperatingModeTests(unittest.TestCase):
    def test_physical_monitor_cannot_arm(self):
        runtime=Runtime()
        client=create_app(runtime).test_client()
        self.assertEqual(client.post("/api/arm",json={}).status_code,409)
        self.assertFalse(runtime.state()["physicalActuationAllowed"])
        self.assertFalse(runtime.actuators_simulated)

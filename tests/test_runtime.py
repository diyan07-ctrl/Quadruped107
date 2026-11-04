"""Hardware-free behavior checks for the Pi/Uno port."""
import base64
import queue
import sys
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Dev/Quadruped107-connect/python"))
from camera import Camera
from controller import MotionController
from main import Runtime, create_app
from serial_link import Pending, SerialLink, SimulatedLink
from vision import choose_blue_ball_motion, detect_blue_ball


def wait_for(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate(): return
        time.sleep(0.01)
    raise AssertionError("Timed out waiting for state")


class FakeSerial:
    def __init__(self, **kwargs):
        self.incoming = queue.Queue()
        self.sent = []
        self.active = None
        self.closed = False

    def reset_input_buffer(self): pass

    def write(self, data):
        self.sent.append(data)
        parts = data.decode().split()
        if parts[0] == "HELLO": self.incoming.put(b"READY Quadruped107 1\n")
        if parts[0] == "PING": self.incoming.put(b"PONG\n")
        if parts[0] == "ARM": self.incoming.put(f"DONE {parts[1]} armed\n".encode())
        if parts[0] == "MOVE":
            self.active = parts[1]
            self.incoming.put(f"ACCEPT {parts[1]} {parts[2]}\n".encode())
        if parts[0] == "STOP":
            self.incoming.put(f"DONE {parts[1]} stopped\n".encode())
            if self.active:
                self.incoming.put(f"ERR {self.active} stopped\n".encode())
                self.active = None
        return len(data)

    def readline(self, *args):
        try: return self.incoming.get(timeout=0.02)
        except queue.Empty: return b""

    def close(self): self.closed = True


class SerialTests(unittest.TestCase):
    def test_ambiguous_port_is_rejected(self):
        ports = [SimpleNamespace(device=p, vid=0x2341, description="Uno") for p in ["A", "B"]]
        with self.assertRaisesRegex(RuntimeError, "2 serial candidates"):
            SerialLink(discover=lambda: ports)._find_port()

    def test_acknowledgement_does_not_complete_command(self):
        link = SerialLink()
        pending = Pending("MOVE")
        link.pending[7] = pending
        link._receive("ACCEPT 7 forward")
        link._receive("DONE 6 forward")
        self.assertFalse(pending.event.is_set())
        link._receive("ERR 7 stopped")
        self.assertTrue(pending.event.is_set())
        self.assertEqual(pending.error, "stopped")

    def test_reconnect_fails_pending_and_discards_queue(self):
        link = SerialLink()
        pending = Pending("MOVE")
        link.pending[1] = pending
        link.outgoing.put((1, "MOVE 1 forward\n"))
        link.armed = True
        link._fail("USB unplugged")
        self.assertFalse(link.armed)
        self.assertTrue(link.outgoing.empty())
        self.assertTrue(pending.event.is_set())
        self.assertEqual(pending.error, "USB unplugged")

    def test_heartbeats_and_stop_work_during_pending_move(self):
        device = FakeSerial()
        link = SerialLink("fake", factory=lambda **kwargs: device)
        link.start()
        try:
            wait_for(lambda: link.snapshot()["connected"], 4)
            link.command("ARM")
            errors = []
            def move():
                try: link.command("MOVE", "forward")
                except RuntimeError as error: errors.append(str(error))
            worker = threading.Thread(target=move)
            worker.start()
            wait_for(lambda: device.active is not None)
            pings = device.sent.count(b"PING\n")
            wait_for(lambda: device.sent.count(b"PING\n") > pings)
            link.command("STOP", timeout=1)
            worker.join(1)
            self.assertFalse(worker.is_alive())
            self.assertEqual(errors, ["stopped"])
            self.assertFalse(link.snapshot()["armed"])
        finally: link.close()
        self.assertTrue(device.closed)


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.link = SimulatedLink()
        self.controller = MotionController(self.link)
        self.controller.start()

    def tearDown(self): self.controller.close()

    def test_startup_and_arm_do_not_move(self):
        with self.assertRaises(RuntimeError): self.controller.set_mode("forward")
        self.controller.arm()
        time.sleep(0.08)
        self.assertEqual(self.link.history, [("ARM",)])

    def test_browser_lease_stops_and_disarms(self):
        self.controller.arm()
        self.controller.set_mode("forward")
        wait_for(lambda: ("MOVE", "forward") in self.link.history)
        wait_for(lambda: not self.controller.snapshot()["enabled"], 2)
        self.assertEqual(self.link.history[-1], ("STOP",))

    def test_autonomous_gait_is_one_step_per_request(self):
        self.controller.arm()
        self.controller.set_mode("opencv")
        wait_for(lambda: self.controller.snapshot()["executedGeneration"] == self.controller.snapshot()["generation"])
        self.controller.autonomous("opencv", "forward")
        wait_for(lambda: ("MOVE", "forward") in self.link.history)
        time.sleep(0.12)
        self.assertEqual(self.link.history.count(("MOVE", "forward")), 1)

    def test_invalid_servo_does_not_reach_uno(self):
        self.controller.arm()
        for channel, pulse in [(8, 300), (0, 601), (True, 300), (0, -1)]:
            with self.assertRaises(ValueError): self.controller.servo(channel, pulse)
        self.assertEqual(self.link.history, [("ARM",)])

    def test_reset_does_not_resume_old_motion(self):
        self.controller.arm()
        self.controller.set_mode("forward")
        wait_for(lambda: ("MOVE", "forward") in self.link.history)
        self.link.epoch += 1
        wait_for(lambda: not self.controller.snapshot()["enabled"])
        count = self.link.history.count(("MOVE", "forward"))
        time.sleep(0.1)
        self.assertEqual(count, self.link.history.count(("MOVE", "forward")))


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime(simulate=True)
        self.runtime.start()
        self.client = create_app(self.runtime).test_client()

    def tearDown(self): self.runtime.close()

    def post(self, path, data=None): return self.client.post(path, json=data or {})

    def test_static_assets_and_simulated_jpeg(self):
        for path in ["/", "/app.js", "/styles.css", "/poses/stand.webp"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            response.close()
        wait_for(lambda: self.runtime.camera.latest()[1] is not None)
        data = self.client.get("/api/camera-frame").get_json()
        jpeg = cv2.imdecode(np.frombuffer(base64.b64decode(data["data"]), dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(jpeg.shape, (480, 640, 3))
        stream = self.client.get("/video-feed", buffered=False)
        self.assertIn(b"Content-Type: image/jpeg", next(iter(stream.response)))
        stream.close()

    def test_commands_require_arm_and_post(self):
        self.assertEqual(self.post("/api/mode", {"mode": "stand"}).status_code, 409)
        self.assertEqual(self.client.get("/api/mode/forward").status_code, 404)
        self.assertEqual(self.post("/api/arm").status_code, 200)
        self.assertEqual(self.post("/api/mode", {"mode": "stand"}).status_code, 200)
        self.assertEqual(self.post("/api/stop").status_code, 200)
        self.assertFalse(self.runtime.motion.snapshot()["enabled"])

    def test_heartbeat_corrects_lost_key_release(self):
        self.post("/api/arm")
        self.post("/api/mode", {"mode": "forward"})
        self.post("/api/heartbeat", {"motion": None})
        self.assertEqual(self.runtime.motion.snapshot()["desiredMotion"], "stand")

    def test_missing_model_and_malformed_requests(self):
        self.assertEqual(self.post("/api/mode", {"mode": "hand_gesture"}).status_code, 409)
        self.assertEqual(self.post("/api/mode", {"mode": 1}).status_code, 400)
        self.assertEqual(self.client.post("/api/arm", json=[]).status_code, 400)
        self.assertEqual(self.client.post("/api/arm", data="{}").status_code, 415)
        self.assertEqual(self.client.post("/api/arm", json={}, headers={"Origin": "http://other-host"}).status_code, 403)


class VisionTests(unittest.TestCase):
    def test_bgr_blue_ball_drives_correct_direction(self):
        for x, expected in [(80, "turn_left"), (320, "forward"), (560, "turn_right")]:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.circle(frame, (x, 240), 35, (255, 0, 0), -1)
            detection = detect_blue_ball(frame)
            self.assertTrue(detection["detected"])
            self.assertEqual(choose_blue_ball_motion(detection)[1], expected)

    def test_close_ball_stops(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.circle(frame, (320, 240), 130, (255, 0, 0), -1)
        self.assertEqual(choose_blue_ball_motion(detect_blue_ball(frame))[1], "hold")

    def test_red_ball_is_not_blue(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.circle(frame, (320, 240), 35, (0, 0, 255), -1)
        self.assertFalse(detect_blue_ball(frame)["detected"])

    def test_stale_camera_frames_are_not_returned(self):
        camera = Camera(simulate=True)
        camera.frame = np.zeros((10, 10, 3), dtype=np.uint8)
        camera.jpeg = b"old frame"
        camera.timestamp = time.monotonic() - 1.0
        frame, jpeg, _, _ = camera.latest()
        self.assertIsNone(frame)
        self.assertIsNone(jpeg)


if __name__ == "__main__": unittest.main()

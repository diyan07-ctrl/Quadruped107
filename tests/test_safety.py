"""Failure-path tests for priority STOP, cancellation and operator ownership."""
import math
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "software/pi"))
from quadruped.serial_link import SerialLink, MAX_ID, QUEUE_TTL
from quadruped.controller import MotionController, INTENT_TTL
from quadruped.main import Runtime, create_app
from test_runtime import FakeSerial, wait_for


class GateLink(SerialLink):
    def __init__(self, block=None):
        super().__init__("fake")
        self.connected = True
        self.block = block
        self.device = FakeSerial()

    def submit(self, *args, **kwargs):
        ticket = super().submit(*args, **kwargs)
        self._send_next(self.device)
        return ticket

    def wait(self, ticket):
        if ticket.verb != self.block and not ticket.event.is_set():
            self._receive(f"DONE {ticket.identifier} {'armed' if ticket.verb == 'ARM' else 'stopped'}")
        return super().wait(ticket)


class PriorityTests(unittest.TestCase):
    def setUp(self):
        self.link = SerialLink()
        self.link.connected = self.link.armed = True
        self.device = FakeSerial()

    def test_stop_cancels_full_queue_and_has_reserved_capacity(self):
        tickets = [self.link.submit("MOVE", "forward") for _ in range(4)]
        with self.assertRaisesRegex(RuntimeError, "capacity"):
            self.link.submit("SERVO", 0, 300)
        stop = self.link.submit("STOP")
        self.assertTrue(all(t.event.is_set() and t.error == "stopped" for t in tickets))
        self.assertTrue(self.link.outgoing.empty())
        self.assertIs(stop, self.link.submit("STOP"))
        with self.assertRaises(RuntimeError): self.link.submit("ARM")
        self.link._send_next(self.device)
        self.assertEqual(self.device.sent, [f"STOP {stop.identifier}\n".encode()])
        self.link._receive(f"DONE {stop.identifier} stopped")
        self.assertFalse(self.link.armed)
        self.assertFalse(self.link.snapshot()["stopping"])

    def test_late_arm_ack_cannot_cross_stop_barrier(self):
        self.link.armed = False
        arm = self.link.submit("ARM")
        stop = self.link.submit("STOP")
        self.link._receive(f"DONE {arm.identifier} armed")
        self.assertFalse(self.link.armed)
        self.link._receive(f"DONE {stop.identifier} stopped")
        self.assertFalse(self.link.armed)
        fresh = self.link.submit("ARM")
        self.link._receive(f"DONE {fresh.identifier} armed")
        self.assertTrue(self.link.armed)

    def test_stale_queued_request_is_not_written(self):
        ticket = self.link.submit("MOVE", "forward")
        ticket.created -= QUEUE_TTL + .01
        with self.assertRaisesRegex(TimeoutError, "Stale"):
            self.link._send_next(self.device)
        self.assertEqual(self.device.sent, [])

    def test_command_timeout_faults_and_clears_pending(self):
        with self.assertRaises(TimeoutError):
            self.link.command("MOVE", "forward", timeout=.01)
        self.assertFalse(self.link.connected)
        self.assertFalse(self.link.armed)
        self.assertFalse(self.link.pending)
        self.assertTrue(self.link.outgoing.empty())
        with self.assertRaises(RuntimeError): self.link.submit("ARM")

    def test_disconnect_ignores_old_ack_and_requires_fresh_arm(self):
        arm = self.link.submit("ARM")
        self.link._fail("USB gone")
        self.link._receive(f"DONE {arm.identifier} armed")
        self.assertFalse(self.link.armed)
        self.link.connected = True
        self.link.reset_event.clear()
        with self.assertRaisesRegex(RuntimeError, "disarmed"):
            self.link.submit("MOVE", "forward")
        fresh = self.link.submit("ARM")
        self.link._receive(f"DONE {fresh.identifier} armed")
        self.assertTrue(self.link.armed)

    def test_invalid_timeout_line_and_identifier_exhaustion(self):
        for timeout in (0, -1, math.nan, math.inf, True, "3"):
            with self.assertRaises(ValueError):
                self.link.submit("MOVE", "forward", timeout=timeout)
        for arg in ("x" * 70, "é"):
            with self.assertRaises(ValueError): self.link.submit("MOVE", arg)
        self.link.sequence = MAX_ID
        with self.assertRaises(RuntimeError): self.link.submit("ARM")
        self.assertEqual(self.link.submit("STOP").identifier, 0)

    def test_stop_after_current_write_precedes_remaining_motion(self):
        entered, release = threading.Event(), threading.Event()
        class BlockingDevice:
            def __init__(self): self.sent = []
            def write(self, data):
                if not self.sent:
                    entered.set()
                    if not release.wait(1): raise AssertionError("Test write not released")
                self.sent.append(data)
                return len(data)
        device = BlockingDevice()
        self.link.submit("MOVE", "forward")
        self.link.submit("MOVE", "backward")
        sender = threading.Thread(target=self.link._send_next, args=(device,))
        sender.start()
        self.assertTrue(entered.wait(1))
        stopped = []
        stopper = threading.Thread(target=lambda: stopped.append(self.link.submit("STOP")))
        stopper.start()
        release.set()
        sender.join(1)
        stopper.join(1)
        self.assertFalse(sender.is_alive() or stopper.is_alive())
        self.link._send_next(device)
        self.link._send_next(device)
        self.assertEqual([d.split()[0] for d in device.sent], [b"MOVE", b"STOP"])


class ControllerRaceTests(unittest.TestCase):
    def interrupted_operation(self, verb):
        link = GateLink(block=verb)
        controller = MotionController(link)
        if verb != "ARM": controller.arm()
        errors = []
        def work():
            try:
                if verb == "ARM": controller.arm()
                else: controller.servo(0, 300)
            except RuntimeError as error: errors.append(str(error))
        thread = threading.Thread(target=work)
        thread.start()
        wait_for(lambda: controller.snapshot()["busy"])
        if verb == "SERVO":
            with self.assertRaises(RuntimeError): controller.set_mode("stand")
        controller.stop()
        thread.join(1)
        self.assertFalse(thread.is_alive())
        self.assertTrue(errors)
        self.assertFalse(controller.snapshot()["enabled"])
        self.assertFalse(controller.snapshot()["busy"])
        self.assertIsNotNone(controller.snapshot()["fault"])

    def test_stop_during_pending_arm(self):
        self.interrupted_operation("ARM")

    def test_stop_during_pending_servo(self):
        self.interrupted_operation("SERVO")

    def test_old_request_generation_cannot_rearm_or_move(self):
        controller = MotionController(GateLink())
        old = controller.snapshot()["generation"]
        controller.stop()
        with self.assertRaisesRegex(RuntimeError, "Stale"):
            controller.arm(expected_generation=old)
        controller.arm()
        with self.assertRaisesRegex(RuntimeError, "Stale"):
            controller.set_mode("forward", expected_generation=old)

    def test_stale_desired_pose_is_never_submitted(self):
        link = GateLink()
        controller = MotionController(link)
        controller.arm()
        controller.set_mode("greeting")
        controller.desired_at -= INTENT_TTL + .1
        controller.start()
        try:
            wait_for(lambda: not controller.snapshot()["enabled"])
            self.assertNotIn(b"MOVE", [d.split()[0] for d in link.device.sent])
        finally: controller.close()

    def test_mode_change_is_rejected_during_active_step(self):
        link = GateLink(block="MOVE")
        controller = MotionController(link)
        controller.arm()
        controller.set_mode("forward")
        controller.start()
        try:
            wait_for(lambda: controller.snapshot()["busy"])
            with self.assertRaises(RuntimeError): controller.set_mode("opencv")
            controller.set_mode("stand")  # release intent remains permitted
        finally: controller.close()


class OwnerTests(unittest.TestCase):
    def test_one_browser_owns_movement_but_any_browser_can_stop(self):
        runtime = Runtime(simulate=True)
        runtime.start()
        try:
            app = create_app(runtime)
            first, second = app.test_client(), app.test_client()
            self.assertEqual(first.post("/api/arm", json={}).status_code, 200)
            self.assertEqual(second.post("/api/mode", json={"mode":"forward"}).status_code, 409)
            self.assertEqual(second.post("/api/heartbeat", json={}).status_code, 409)
            self.assertEqual(second.post("/api/arm", json={}).status_code, 409)
            self.assertEqual(second.post("/api/stop", json={}).status_code, 200)
            self.assertFalse(runtime.motion.snapshot()["enabled"])
            self.assertEqual(second.post("/api/arm", json={}).status_code, 200)
            self.assertEqual(first.post("/api/mode", json={"mode":"forward"}).status_code, 409)
        finally: runtime.close()

    def test_old_release_cannot_clear_new_claim(self):
        runtime = Runtime(simulate=True)
        token, epoch = runtime.claim_control(None)
        runtime.release_control(token, epoch)
        newer, generation = runtime.claim_control(None)
        runtime.release_control(token, epoch)
        self.assertEqual(runtime.owner_token, newer)
        runtime.finish_claim(generation)


if __name__ == "__main__": unittest.main()

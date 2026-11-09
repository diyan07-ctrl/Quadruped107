"""One motion owner; state changes never hold locks across serial acknowledgments."""
from __future__ import annotations
import threading
import time

MOTIONS = {"initial", "stand", "greeting", "tail_wag", "forward", "backward", "turn_left", "turn_right"}
CONTINUOUS = {"forward", "backward", "turn_left", "turn_right"}
MODES = {"manual", "opencv", "hand_gesture", "explore", "sensor_test", "idle"}
LEASE_SECONDS = 1.0
INTENT_TTL = 0.5


class MotionController:
    def __init__(self, link):
        from .explain import DecisionHistory
        self.events=DecisionHistory()
        self.last_request=None
        self.link = link
        self.safety_check = None
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.wake = threading.Event()
        self.generation = self.executed = 0
        self.session = 0
        self.app_mode = "manual"
        self.desired = self.current = "none"
        self.busy = self.enabled = False
        self.active = self.stop_ticket = None
        self.last_heartbeat = self.desired_at = 0.0
        self.vision_seen = 0.0
        self.result = "Connect the Uno, then enable servos"
        self.error = None
        self.fault = "Startup; explicit enable required"
        self.epoch = link.snapshot()["epoch"]
        self.thread = threading.Thread(target=self._run, name="motion", daemon=True)
        self.guard = threading.Thread(target=self._guard, name="control-lease", daemon=True)

    def start(self):
        self.thread.start()
        self.guard.start()

    def snapshot(self):
        with self.lock:
            return dict(appMode=self.app_mode, desiredMotion=self.desired,
                        currentMotion=self.current, generation=self.generation,
                        executedGeneration=self.executed, busy=self.busy,
                        session=self.session,
                        enabled=self.enabled, stopping=self.stop_ticket is not None,
                        fault=self.fault, lastResult=self.result, lastError=self.error,lastRequest=self.last_request)

    def heartbeat(self, held_motion=None, expected_generation=None):
        with self.lock:
            if expected_generation is not None and expected_generation != self.generation:
                raise RuntimeError("Stale heartbeat")
            self.last_heartbeat = time.monotonic()
            if held_motion == self.desired and held_motion in CONTINUOUS:
                self.desired_at = self.last_heartbeat

    def _retire(self, ticket):
        with self.lock:
            if self.active is ticket:
                self.active = None
                self.busy = False

    def vision_heartbeat(self, owner, generation, published_at):
        with self.lock:
            if not self.enabled or self.app_mode != owner or self.generation != generation:
                return False
            self.vision_seen = published_at
            return True

    def arm(self, expected_generation=None):
        with self.lock:
            if self.stop_event.is_set(): raise RuntimeError("Application shutting down")
            if expected_generation is not None and expected_generation != self.generation:
                raise RuntimeError("Stale arm request")
            if self.busy or self.stop_ticket is not None: raise RuntimeError("Wait for pending operation/STOP")
            if self.enabled: raise RuntimeError("Already enabled")
            epoch = self.link.snapshot()["epoch"]
            self.generation += 1
            generation = self.generation
            ticket = self.link.submit("ARM", timeout=3)
            self.active, self.busy = ticket, True
        try:
            self.link.wait(ticket)
            with self.lock:
                link = self.link.snapshot()
                if generation != self.generation or self.stop_ticket is not None or not link["armed"] or link["epoch"] != epoch:
                    raise RuntimeError("Arming cancelled by stop or link change")
                self.enabled = True
                self.session += 1
                self.epoch = epoch
                self.executed = generation
                self.app_mode = "manual"
                self.desired = self.current = "none"
                self.result, self.error, self.fault = "Enabled; select a pose", None, None
                self.last_heartbeat = time.monotonic()
        except Exception:
            with self.lock: still_current = generation == self.generation
            if still_current: self.stop("Arming failed; explicit enable required")
            raise
        finally:
            self._retire(ticket)

    def stop(self, reason="Stopped; servos disabled", expected_generation=None, *, wait=True):
        # Invalidate first, submit while holding only the state/transaction locks,
        # then release those locks before waiting. ARM/SERVO cannot delay STOP by
        # holding a lock for their acknowledgment timeout.
        with self.lock:
            if expected_generation is not None and expected_generation != self.generation:
                return
            self.enabled = False
            self.generation += 1
            self.executed = self.generation
            self.app_mode = "manual"
            self.desired = self.current = "none"
            self.events.record("stop",status="locally_inhibited",reason=reason,generation=self.generation)
            self.result = reason
            if self.fault is None: self.fault = reason
            ticket = None
            if self.link.snapshot()["connected"]:
                try:
                    ticket = self.link.submit("STOP", timeout=2)
                    self.stop_ticket = ticket
                except Exception as error:
                    self.error = str(error)
        self.wake.set()
        if ticket is not None and wait:
            try:
                self.link.wait(ticket)
                self.events.record("stop_ack",status="acknowledged",generation=self.generation,request_id=ticket.identifier)
            except Exception as error:
                with self.lock: self.error = str(error)
            finally:
                with self.lock:
                    if self.stop_ticket is ticket: self.stop_ticket = None

    def set_mode(self, mode, expected_generation=None):
        mode = mode.strip().lower().replace("-", "_")
        if mode not in MOTIONS | MODES: raise ValueError("Unknown mode")
        with self.lock:
            takeover = mode in MOTIONS | {"manual"} and self.app_mode not in {"manual","idle"}
            if mode == "idle" or takeover:
                if expected_generation is not None and expected_generation != self.generation:
                    raise RuntimeError("Stale mode request")
                self.stop("Idle selected" if mode=="idle" else "Manual takeover; explicit enable required",
                          expected_generation=expected_generation,wait=False)
                if mode=="idle": self.app_mode="idle"
                stopped_generation,ticket=self.generation,self.stop_ticket
            else: stopped_generation,ticket=None,None
        if stopped_generation is not None:
            if ticket is not None:
                try: self.link.wait(ticket)
                finally:
                    with self.lock:
                        if self.stop_ticket is ticket: self.stop_ticket=None
            return stopped_generation
        with self.lock:
            if expected_generation is not None and expected_generation != self.generation:
                raise RuntimeError("Stale mode request")
            if not self.enabled or not self.link.snapshot()["armed"]:
                raise RuntimeError("Enable servos before selecting a motion or vision mode")
            if self.busy and self.active is not None and self.active.verb != "MOVE":
                raise RuntimeError("Wait for calibration/arming to finish")
            if mode in MODES and self.busy:
                raise RuntimeError("Wait for the current step before changing control mode; STOP inhibits immediately")
            self.generation += 1
            if mode in MODES:
                self.app_mode, self.desired = mode, "none" if mode in {"explore", "sensor_test"} or mode=="opencv" and self.safety_check else "stand"
                self.vision_seen = time.monotonic()
            else:
                self.app_mode, self.desired = "manual", mode
            if self.desired == "none": self.executed = self.generation
            self.last_heartbeat = self.desired_at = time.monotonic()
            self.result, self.error = f"Selected {mode}", None
            generation = self.generation
        self.wake.set()
        return generation

    def autonomous(self, owner, motion, expected_generation=None):
        if owner not in {"opencv", "hand_gesture", "explore"} or motion not in MOTIONS:
            raise ValueError("Invalid autonomous owner or motion")
        with self.lock:
            self.events.record("motion_request",motion=motion,status="requested",generation=expected_generation)
            reason=None
            if expected_generation is not None and expected_generation != self.generation: reason="Stale generation"
            elif not self.enabled or self.app_mode != owner: reason="Disarmed or different control owner"
            elif self.busy and not (motion=="stand" and self.active is not None and self.active.verb=="MOVE"): reason="Motion already active"
            elif motion=="stand" and self.desired=="stand": reason="Stand intent already selected"
            elif self.generation != self.executed and motion!="stand": reason="Intent pending"
            if reason:
                self.last_request=dict(motion=motion,status="rejected",reason=reason,generation=self.generation)
                self.events.record("motion_rejected",motion=motion,status="rejected",reason=reason,generation=self.generation)
                return False
            self.generation += 1
            self.desired, self.desired_at = motion, time.monotonic()
            self.last_request=dict(motion=motion,status="intent_accepted",reason="Awaiting serial dispatch",generation=self.generation)
            self.events.record("motion_intent",motion=motion,status="intent_accepted",generation=self.generation)
        self.wake.set()
        return True

    def servo(self, channel, pulse, expected_generation=None):
        if type(channel) is not int or type(pulse) is not int or not 0 <= channel <= 7 or not 50 <= pulse <= 600:
            raise ValueError("Servo channel must be 0..7 and pulse 50..600")
        with self.lock:
            if expected_generation is not None and expected_generation != self.generation:
                raise RuntimeError("Stale calibration request")
            if not self.enabled: raise RuntimeError("Enable servos first")
            if self.busy or self.desired in CONTINUOUS or self.generation != self.executed:
                raise RuntimeError("Wait for motion to finish before calibrating")
            if self.safety_check:
                reason = self.safety_check("servo")
                if reason: raise RuntimeError(reason)
            self.app_mode = "manual"
            generation = self.generation
            ticket = self.link.submit("SERVO", channel, pulse, timeout=3)
            self.active, self.busy = ticket, True
        try:
            self.link.wait(ticket)
        except Exception:
            with self.lock: still_current = generation == self.generation and self.enabled
            if still_current: self.stop("Calibration command failed")
            raise
        finally:
            self._retire(ticket)

    def _guard(self):
        while not self.stop_event.wait(0.05):
            with self.lock:
                if self.stop_ticket is not None and self.stop_ticket.event.is_set():
                    if self.stop_ticket.error: self.error = str(self.stop_ticket.error)
                    self.stop_ticket = None
                link = self.link.snapshot()
                safety_reason = self.safety_check(self.current if self.busy else self.desired) if self.enabled and self.safety_check else None
                stale = self.enabled and time.monotonic() - self.last_heartbeat > LEASE_SECONDS
                reset = self.enabled and (not link["connected"] or not link["armed"] or link["epoch"] != self.epoch)
                vision_stale = self.enabled and self.app_mode in {"opencv", "hand_gesture"} and time.monotonic() - self.vision_seen > .8
                generation = self.generation
            if stale or reset or vision_stale or safety_reason:
                reason = (safety_reason if safety_reason else "Control heartbeat expired" if stale else
                          "Arduino disconnected or reset; enable again" if reset else "Vision observation expired")
                self.stop(reason,
                          expected_generation=generation)

    def _run(self):
        while not self.stop_event.is_set():
            ticket = None
            stale = False
            with self.lock:
                repeat = self.app_mode == "manual" and self.desired in CONTINUOUS
                run = self.enabled and not self.busy and (repeat or self.generation != self.executed)
                if run:
                    motion, generation = self.desired, self.generation
                    # Stand is a safe release intent; a queued action/held direction
                    # expires unless a matching current heartbeat renews it.
                    safety_reason = self.safety_check(motion) if self.safety_check else None
                    stale = bool(safety_reason) or motion != "stand" and time.monotonic() - self.desired_at > INTENT_TTL
                    if not stale:
                        try:
                            ticket = self.link.submit("MOVE", motion)
                            self.active, self.busy, self.current = ticket, True, motion
                            self.events.record("motion_dispatch",motion=motion,status="submitted_to_serial",generation=generation,request_id=ticket.identifier)
                        except Exception as error:
                            self.error = str(error)
            if stale:
                self.stop(safety_reason or "Stale motion intent", expected_generation=generation)
                continue
            if not run:
                self.wake.wait(0.05)
                self.wake.clear()
                continue
            if ticket is None:
                self.stop("Motion submission failed")
                continue
            try:
                self.link.wait(ticket)
                with self.lock:
                    if generation == self.generation:
                        self.result, self.error = f"Completed {motion}", None
                        self.events.record("motion_complete",motion=motion,status="acknowledged_complete",generation=generation,request_id=ticket.identifier)
            except Exception as error:
                with self.lock:
                    still_current = self.enabled
                    if still_current: self.error = str(error)
                if still_current: self.stop(f"Motion failed: {error}")
            finally:
                with self.lock: self.executed = max(self.executed, generation)
                self._retire(ticket)
            self.stop_event.wait(0.02)

    def close(self):
        self.stop_event.set()
        self.stop("Application shutdown")
        self.wake.set()
        for thread in (self.thread, self.guard):
            if thread.is_alive(): thread.join(3)

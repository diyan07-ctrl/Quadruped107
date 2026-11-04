"""Motion scheduler with a browser lease, generation cancellation and explicit arming."""
from __future__ import annotations
import threading
import time

MOTIONS = {"initial", "stand", "greeting", "tail_wag", "forward", "backward", "turn_left", "turn_right"}
CONTINUOUS = {"forward", "backward", "turn_left", "turn_right"}
MODES = {"manual", "opencv", "hand_gesture"}
LEASE_SECONDS = 1.0


class MotionController:
    def __init__(self, link):
        self.link = link
        self.lock = threading.RLock()
        self.operation_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.wake = threading.Event()
        self.generation = 0
        self.executed = 0
        self.app_mode = "manual"
        self.desired = self.current = "none"
        self.busy = False
        self.enabled = False
        self.last_heartbeat = 0.0
        self.result = "Connect the Uno, then enable servos"
        self.error = None
        self.epoch = link.snapshot()["epoch"]
        self.thread = threading.Thread(target=self._run, name="motion", daemon=True)
        self.guard = threading.Thread(target=self._guard, name="control-lease", daemon=True)

    def start(self):
        self.thread.start(); self.guard.start()

    def snapshot(self):
        with self.lock:
            return dict(appMode=self.app_mode, desiredMotion=self.desired,
                        currentMotion=self.current, generation=self.generation,
                        executedGeneration=self.executed, busy=self.busy,
                        enabled=self.enabled, lastResult=self.result, lastError=self.error)

    def heartbeat(self):
        with self.lock: self.last_heartbeat = time.monotonic()

    def arm(self):
        with self.operation_lock:
            self.link.command("ARM", timeout=3)
            with self.lock:
                self.enabled = True
                self.epoch = self.link.snapshot()["epoch"]
                self.generation += 1
                self.executed = self.generation
                self.app_mode = "manual"
                self.desired = self.current = "none"
                self.result, self.error = "Enabled; select a pose", None
                self.last_heartbeat = time.monotonic()

    def stop(self, reason="Stopped; servos disabled"):
        with self.operation_lock:
            with self.lock:
                self.enabled = False
                self.generation += 1
                self.executed = self.generation
                self.app_mode = "manual"
                self.desired = self.current = "none"
                self.result = reason
            # STOP is sent by the independent serial worker even during MOVE.
            if self.link.snapshot()["connected"]:
                try: self.link.command("STOP", timeout=2)
                except Exception as error:
                    with self.lock: self.error = str(error)
            self.wake.set()

    def set_mode(self, mode):
        mode = mode.strip().lower().replace("-", "_")
        if mode not in MOTIONS | MODES: raise ValueError("Unknown mode")
        with self.lock:
            if not self.enabled or not self.link.snapshot()["armed"]:
                raise RuntimeError("Enable servos before selecting a motion or vision mode")
            self.generation += 1
            if mode in MODES:
                self.app_mode = mode
                self.desired = "stand"  # clear any previous continuous command
            else:
                self.app_mode = "manual"
                self.desired = mode
            self.last_heartbeat = time.monotonic()
            self.result, self.error = f"Selected {mode}", None
            generation = self.generation
        self.wake.set()
        return generation

    def autonomous(self, owner, motion):
        with self.lock:
            if not self.enabled or self.app_mode != owner or self.busy: return
            if self.generation != self.executed: return  # do not replace mode-entry stand
            self.generation += 1
            self.desired = motion
        self.wake.set()

    def servo(self, channel, pulse):
        if type(channel) is not int or type(pulse) is not int or not 0 <= channel <= 7 or not 50 <= pulse <= 600:
            raise ValueError("Servo channel must be 0..7 and pulse 50..600")
        with self.operation_lock:
            with self.lock:
                if not self.enabled: raise RuntimeError("Enable servos first")
                if self.busy or self.desired in CONTINUOUS or self.generation != self.executed:
                    raise RuntimeError("Wait for motion to finish before calibrating")
                self.app_mode = "manual"
                self.busy = True
            try: self.link.command("SERVO", channel, pulse, timeout=3)
            finally:
                with self.lock: self.busy = False

    def _guard(self):
        while not self.stop_event.wait(0.05):
            link = self.link.snapshot()
            with self.lock:
                stale = self.enabled and time.monotonic() - self.last_heartbeat > LEASE_SECONDS
                reset = self.enabled and (not link["connected"] or not link["armed"] or link["epoch"] != self.epoch)
            if stale or reset:
                self.stop("Control heartbeat expired" if stale else "Arduino disconnected or reset; enable again")

    def _run(self):
        while not self.stop_event.is_set():
            with self.lock:
                repeat = self.app_mode == "manual" and self.desired in CONTINUOUS
                run = self.enabled and not self.busy and (repeat or self.generation != self.executed)
                if run:
                    motion, generation = self.desired, self.generation
                    self.busy = True
                    self.current = motion
            if not run:
                self.wake.wait(0.05); self.wake.clear(); continue
            try:
                self.link.command("MOVE", motion)
                with self.lock:
                    if generation == self.generation:
                        self.result, self.error = f"Completed {motion}", None
            except Exception as error:
                with self.lock: self.error = str(error)
                self.stop(f"Motion failed: {error}")
            finally:
                with self.lock:
                    self.executed = max(self.executed, generation)
                    self.busy = False
            self.stop_event.wait(0.02)

    def close(self):
        self.stop_event.set()
        self.stop("Application shutdown")
        self.wake.set()
        for thread in (self.thread, self.guard):
            if thread.is_alive(): thread.join(3)

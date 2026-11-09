"""Explicit host-side Uno emulator; no GPIO, I2C or physical serial device is opened."""
from __future__ import annotations
from collections import deque
import json
import math
import queue
import threading
import time
from importlib.resources import files
from .serial_link import SerialLink

DATA = json.loads(files("quadruped").joinpath("data/motions.json").read_text())


class VirtualUno:
    def __init__(self, *, clock=time.monotonic, speed=1.0):
        if not math.isfinite(speed) or not .1 <= speed <= 10: raise ValueError("Virtual speed must be .1..10")
        self.clock, self.speed = clock, speed
        self.lock = threading.RLock()
        self.emit = lambda line: None
        self.history = deque(maxlen=128)
        self.trace = deque(maxlen=128)
        self.reset()

    def reset(self):
        with self.lock:
            self.armed = False
            self.targets = [300]*8  # commanded estimate, NEVER measured shaft position
            self.active_mask = 0
            self.active = None
            self.frames = deque()
            self.last_ping = self.clock()
            self.line = bytearray()
            self.overflow = False
            self.fault = None

    def snapshot(self):
        with self.lock:
            return dict(virtual=True, armed=self.armed, targets=list(self.targets),
                        activeMask=self.active_mask, activeMotion=self.active[1] if self.active else None,
                        fault=self.fault, samples=len(self.trace), history=list(self.history))

    def disarm(self, silent=False):
        self.armed = False
        self.active_mask = 0
        self.frames.clear()
        if self.active and not silent: self.emit(f"ERR {self.active[0]} stopped")
        self.active = None

    def feed(self, data):
        with self.lock:
            for character in data:
                if character == 13: continue
                if character == 10:
                    if self.overflow: self.emit("ERR 0 line_too_long")
                    else:
                        try: self.handle(self.line.decode("ascii"))
                        except UnicodeError: self.emit("ERR 0 invalid_ascii")
                    self.line.clear()
                    self.overflow = False
                elif not self.overflow:
                    if len(self.line) >= 63:
                        self.line.clear()
                        self.overflow = True
                    else: self.line.append(character)

    def handle(self, line):
        fields = line.split()
        if not fields: return
        verb = fields[0]
        self.history.append(line)
        if verb == "HELLO":
            self.disarm()
            self.emit("READY Quadruped107 1")
            return
        if verb == "PING":
            self.last_ping = self.clock()
            self.emit("PONG")
            return
        if len(fields)<2 or not fields[1].isascii() or not fields[1].isdigit():
            self.emit("ERR 0 invalid_id")
            return
        identifier = fields[1]
        def reply(kind, detail): self.emit(f"{kind} {identifier} {detail}")
        if verb == "STOP":
            self.disarm()
            reply("DONE","stopped")
            return
        if verb == "ARM":
            if self.active: reply("ERR","busy"); return
            self.armed = True
            self.last_ping = self.clock()
            self.fault = None
            reply("DONE","armed")
            return
        if not self.armed: reply("ERR","disarmed"); return
        if self.active: reply("ERR","busy"); return
        if verb == "SERVO":
            if len(fields)!=4 or len(fields[2])!=1 or len(fields[3])>3 or not all(x.isascii() and x.isdigit() for x in fields[2:]):
                reply("ERR","invalid_servo"); return
            channel,tick=map(int,fields[2:])
            if not 0<=channel<=7 or not 50<=tick<=600:
                reply("ERR","servo_out_of_range"); return
            self.targets[channel]=tick
            self.active_mask |= 1<<channel
            self.trace.append((self.clock(),list(self.targets),self.active_mask))
            reply("DONE","servo")
        elif verb == "MOVE":
            if len(fields)!=3: reply("ERR","invalid_motion"); return
            name=fields[2]
            if len(identifier)>11 or len(name)>=20: reply("ERR","argument_too_long"); return
            reply("ACCEPT",name)
            if name not in DATA["routines"]: reply("ERR","unknown_motion"); return
            cursor=list(self.targets)
            mask=self.active_mask
            elapsed=0.0
            frames=[]
            for stage in DATA["routines"][name]:
                if "pause_ms" in stage:
                    elapsed += stage["pause_ms"]/1000
                    continue
                targets=DATA["tables"][stage["table"]]
                while any(cursor[ch]!=target for ch,target in targets):
                    for ch,target in targets:
                        step=DATA["constants"]["SmoothStepPulse"]
                        cursor[ch] += max(-step,min(step,target-cursor[ch]))
                        mask |= 1<<ch
                    frames.append((elapsed,list(cursor),mask))
                    elapsed += stage["delay_ms"]/1000
                    if len(frames)>4096: raise RuntimeError("Virtual trajectory capacity exceeded")
            self.frames=deque(frames)
            self.started=self.clock()
            self.duration=elapsed
            self.active=(identifier,name)
        else: reply("ERR","unknown_command")

    def advance(self):
        with self.lock:
            now=self.clock()
            if self.armed and now-self.last_ping>1.5:
                self.disarm()
                self.fault="watchdog"
                self.emit("FAULT watchdog")
            if not self.active: return
            elapsed=(now-self.started)*self.speed
            budget=512
            while self.frames and self.frames[0][0]<=elapsed and budget:
                _,self.targets,self.active_mask=self.frames.popleft()
                self.trace.append((now,list(self.targets),self.active_mask))
                budget-=1
            if not self.frames and elapsed>=self.duration:
                identifier,name=self.active
                self.active=None
                self.emit(f"DONE {identifier} {name}")


class VirtualSerial:
    def __init__(self, *, engine=None, **options):
        self.engine=engine or VirtualUno()
        self.incoming=queue.Queue(maxsize=256)
        self.closed=threading.Event()
        self.overflow=False
        self.engine.reset()
        self.engine.emit=self._emit
        self._emit("READY Quadruped107 1")
        self.thread=threading.Thread(target=self._run,name="virtual-uno",daemon=True)
        self.thread.start()

    def _emit(self,line):
        try: self.incoming.put_nowait((line+"\n").encode("ascii"))
        except queue.Full: self.overflow=True

    def _run(self):
        while not self.closed.wait(.01):
            if self.overflow:
                with self.engine.lock: self.engine.disarm(silent=True)
                break
            self.engine.advance()

    def write(self,data):
        if self.closed.is_set(): raise OSError("Virtual serial disconnected")
        self.engine.feed(data)
        return len(data)

    def readline(self,*args):
        try: return self.incoming.get(timeout=.02)
        except queue.Empty: return b""

    def reset_input_buffer(self):
        while True:
            try: self.incoming.get_nowait()
            except queue.Empty: return

    def close(self):
        self.closed.set()
        if self.thread.is_alive(): self.thread.join(1)
        with self.engine.lock: self.engine.disarm(silent=True)


class VirtualLink(SerialLink):
    def __init__(self, *, speed=1.0):
        self.engine=VirtualUno(speed=speed)
        super().__init__("virtual://uno",factory=lambda **options: VirtualSerial(engine=self.engine,**options))

    def snapshot(self):
        state=super().snapshot()
        virtual=self.engine.snapshot()
        state.update(kind="virtual-uno",virtual=True,targets=virtual["targets"],
                     activeMask=virtual["activeMask"],activeMotion=virtual["activeMotion"],
                     virtualFault=virtual["fault"],samples=virtual["samples"])
        return state

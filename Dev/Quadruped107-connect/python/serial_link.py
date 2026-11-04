"""Single-reader USB serial transport. Never replay commands after reconnect."""
from __future__ import annotations
import os
import queue
import threading
import time
from dataclasses import dataclass, field
import serial
from serial.tools import list_ports


@dataclass
class Pending:
    verb: str
    event: threading.Event = field(default_factory=threading.Event)
    result: str = ""
    error: str | None = None


class SerialLink:
    def __init__(self, port="auto", *, factory=serial.Serial, discover=None):
        self.port = port
        self.factory = factory
        self.discover = discover or list_ports.comports
        self.lock = threading.RLock()
        self.pending = {}
        self.outgoing = queue.Queue()
        self.sequence = 0
        self.connected = False
        self.armed = False
        self.error = "Arduino not connected"
        self.epoch = 0
        self.selected_port = None
        self.stop_event = threading.Event()
        self.reset_event = threading.Event()
        self.thread = threading.Thread(target=self._run, name="uno-serial", daemon=True)

    def start(self):
        self.thread.start()

    def snapshot(self):
        with self.lock:
            return dict(connected=self.connected, armed=self.armed, error=self.error,
                        epoch=self.epoch, port=self.selected_port)

    def _find_port(self):
        if self.port != "auto":
            return self.port
        candidates = [p.device for p in self.discover() if
                      p.vid in {0x2341, 0x2A03, 0x1A86, 0x10C4} or
                      "arduino" in (p.description or "").lower()]
        if len(candidates) != 1:
            raise RuntimeError(f"Found {len(candidates)} serial candidates; set QUADRUPED_SERIAL_PORT explicitly")
        return candidates[0]

    def command(self, verb, *arguments, timeout=20.0):
        if verb not in {"MOVE", "ARM", "STOP", "SERVO"}:
            raise ValueError("Invalid serial command")
        tokens = [str(a) for a in arguments]
        if any(not t or not all(c.isalnum() or c == "_" for c in t) for t in tokens):
            raise ValueError("Invalid serial argument")
        with self.lock:
            if not self.connected:
                raise RuntimeError(self.error or "Arduino disconnected")
            self.sequence += 1
            identifier = self.sequence
            pending = Pending(verb)
            self.pending[identifier] = pending
            self.outgoing.put((identifier, f"{verb} {identifier} {' '.join(tokens)}".rstrip() + "\n"))
        if not pending.event.wait(timeout):
            self.reset_event.set()
            self._fail("Serial command timed out")
            raise TimeoutError("Arduino response timed out; re-arm after reconnection")
        if pending.error:
            raise RuntimeError(pending.error)
        return pending.result

    def _fail(self, error):
        with self.lock:
            self.connected = False
            self.armed = False
            self.error = error
            self.epoch += 1
            for pending in self.pending.values():
                pending.error = error
                pending.event.set()
            self.pending.clear()
            while not self.outgoing.empty():
                try:
                    self.outgoing.get_nowait()
                except queue.Empty:
                    break

    def _receive(self, line):
        fields = line.split(maxsplit=2)
        if line.startswith("FAULT ") or line.startswith("READY "):
            raise RuntimeError(line)
        if len(fields) < 2 or fields[0] not in {"DONE", "ERR"}:
            return
        try:
            identifier = int(fields[1])
        except ValueError:
            return
        with self.lock:
            pending = self.pending.pop(identifier, None)
            if pending:
                pending.result = fields[2] if len(fields) > 2 else ""
                if fields[0] == "ERR":
                    pending.error = pending.result
                elif pending.verb == "ARM":
                    self.armed = True
                elif pending.verb == "STOP":
                    self.armed = False
                pending.event.set()

    def _run(self):
        while not self.stop_event.is_set():
            connection = None
            try:
                selected = self._find_port()
                options = dict(port=selected, baudrate=115200, timeout=0.05, write_timeout=0.5)
                if os.name != "nt": options["exclusive"] = True
                connection = self.factory(**options)
                if self.stop_event.wait(2.0): break  # Uno resets when USB serial opens
                connection.reset_input_buffer()
                connection.write(b"HELLO\n")
                deadline = time.monotonic() + 3.0
                while connection.readline().strip() != b"READY Quadruped107 1":
                    if time.monotonic() > deadline or self.stop_event.is_set():
                        raise RuntimeError("Quadruped107 firmware handshake failed")
                with self.lock:
                    self.selected_port = selected
                    self.connected = True
                    self.armed = False
                    self.error = None
                    self.epoch += 1
                    self.reset_event.clear()
                last_ping = 0.0
                last_pong = time.monotonic()
                while not self.stop_event.is_set() and not self.reset_event.is_set():
                    now = time.monotonic()
                    if now - last_ping >= 0.3:
                        connection.write(b"PING\n"); last_ping = now
                    try:
                        identifier, message = self.outgoing.get_nowait()
                    except queue.Empty:
                        pass
                    else:
                        with self.lock:
                            if identifier in self.pending:
                                connection.write(message.encode("ascii"))
                    raw = connection.readline(128)
                    if raw:
                        if not raw.endswith(b"\n"): raise RuntimeError("Truncated serial response")
                        line = raw.decode("ascii", errors="strict").strip()
                        if line == "PONG": last_pong = now
                        else: self._receive(line)
                    if now - last_pong > 1.2: raise RuntimeError("Arduino heartbeat lost")
            except Exception as error:
                self._fail(str(error))
            finally:
                if connection:
                    try: connection.write(b"STOP 0\n")
                    except Exception: pass
                    connection.close()
                self._fail("Serial disconnected" if self.stop_event.is_set() else self.error or "Reconnecting")
            self.stop_event.wait(2.0)

    def close(self):
        self.stop_event.set()
        if self.thread.is_alive(): self.thread.join(4)


class SimulatedLink:
    """Explicit development mode: never opens a serial port."""
    def __init__(self):
        self.armed = False
        self.epoch = 1
        self.history = []

    def start(self): pass

    def snapshot(self):
        return dict(connected=True, armed=self.armed, epoch=self.epoch, port="simulation", error=None)

    def command(self, verb, *arguments, **kwargs):
        if verb == "ARM": self.armed = True
        elif verb == "STOP": self.armed = False
        elif not self.armed: raise RuntimeError("disarmed")
        self.history.append((verb, *arguments))
        time.sleep(0.01)
        return "simulated"

    def close(self): self.armed = False

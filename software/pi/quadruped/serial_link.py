"""Single-owner USB serial transport with an independent, coalesced STOP slot."""
from __future__ import annotations
import math
import os
import queue
import threading
import time
from dataclasses import dataclass, field
import serial
from serial.tools import list_ports

QUEUE_TTL = 0.25
MAX_ORDINARY = 4
MAX_ID = 99_999_999_999


@dataclass
class Pending:
    verb: str
    event: threading.Event = field(default_factory=threading.Event)
    result: str = ""
    error: str | None = None
    identifier: int = 0
    barrier: int = 0
    created: float = field(default_factory=time.monotonic)
    deadline: float = 0.0
    sent: bool = False


class SerialLink:
    def __init__(self, port="auto", *, factory=serial.Serial, discover=None):
        from .telemetry import TelemetryStream
        self.telemetry=TelemetryStream()
        self.port = port
        self.factory = factory
        self.discover = discover or list_ports.comports
        self.lock = threading.RLock()
        self.pending = {}
        self.outgoing = queue.Queue(maxsize=MAX_ORDINARY)
        self.urgent = None
        self.stop_pending = None
        self.barrier = 0
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
                        stopping=self.stop_pending is not None, epoch=self.epoch,
                        queued=self.outgoing.qsize(), port=self.selected_port,telemetry=self.telemetry.snapshot())

    def _find_port(self):
        if self.port != "auto":
            return self.port
        candidates = [p.device for p in self.discover() if
                      p.vid in {0x2341, 0x2A03, 0x1A86, 0x10C4} or
                      "arduino" in (p.description or "").lower()]
        if len(candidates) != 1:
            raise RuntimeError(f"Found {len(candidates)} serial candidates; set QUADRUPED_SERIAL_PORT explicitly")
        return candidates[0]

    def _clear_queue(self):
        while True:
            try: self.outgoing.get_nowait()
            except queue.Empty: break

    def submit(self, verb, *arguments, timeout=20.0):
        """Enqueue without waiting for acknowledgment; never waits for queue space."""
        if verb not in {"MOVE", "ARM", "STOP", "SERVO"}:
            raise ValueError("Invalid serial command")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        tokens = [str(a) for a in arguments]
        if any(not t or not t.isascii() or not all(c.isalnum() or c == "_" for c in t) for t in tokens):
            raise ValueError("Invalid serial argument")
        with self.lock:
            if not self.connected or self.reset_event.is_set():
                raise RuntimeError(self.error or "Arduino disconnected")
            if verb == "STOP" and self.stop_pending is not None:
                return self.stop_pending
            if verb != "STOP":
                if self.stop_pending is not None:
                    raise RuntimeError("STOP pending; explicit arm required afterward")
                if verb != "ARM" and not self.armed:
                    raise RuntimeError("disarmed")
                if verb == "ARM" and any(p.verb != "STOP" for p in self.pending.values()):
                    raise RuntimeError("busy")
                if len(self.pending) >= MAX_ORDINARY or self.outgoing.full():
                    raise RuntimeError("Serial command capacity reached")
            if self.sequence >= MAX_ID and verb != "STOP":
                raise RuntimeError("Request IDs exhausted; restart application disarmed")
            identifier = self.sequence + 1 if self.sequence < MAX_ID else 0
            message = f"{verb} {identifier} {' '.join(tokens)}".rstrip() + "\n"
            if len(message) > 64:
                raise ValueError("Serial command exceeds firmware line limit")
            if identifier: self.sequence = identifier
            if verb == "STOP":
                self.barrier += 1
                self.armed = False
                for old in self.pending.values():
                    old.error = "stopped"
                    old.event.set()
                self.pending.clear()
                self._clear_queue()
            pending = Pending(verb, identifier=identifier, barrier=self.barrier,
                              deadline=time.monotonic() + timeout)
            self.pending[identifier] = pending
            if verb == "STOP":
                self.stop_pending = pending
                self.urgent = (identifier, message)
            else:
                self.outgoing.put_nowait((identifier, message))
            return pending

    def wait(self, pending):
        if not pending.event.wait(max(0.0, pending.deadline - time.monotonic())):
            self._fail("Serial command timed out")
            raise TimeoutError("Arduino response timed out; re-arm after reconnection")
        if pending.error:
            raise RuntimeError(pending.error)
        return pending.result

    def command(self, verb, *arguments, timeout=20.0):
        return self.wait(self.submit(verb, *arguments, timeout=timeout))

    def _fail(self, error):
        with self.lock:
            self.reset_event.set()
            self.connected = self.armed = False
            self.error = error
            self.epoch += 1
            self.barrier += 1
            for pending in self.pending.values():
                pending.error = error
                pending.event.set()
            self.pending.clear()
            self._clear_queue()
            self.urgent = self.stop_pending = None

    def _receive(self, line):
        if line.startswith("TEL "):
            self.telemetry.ingest(line)
            return
        fields = line.split(maxsplit=2)
        if line.startswith("FAULT ") or line.startswith("READY "):
            raise RuntimeError(line)
        if len(fields) < 2 or fields[0] not in {"DONE", "ERR"}:
            return
        try: identifier = int(fields[1])
        except ValueError: return
        with self.lock:
            pending = self.pending.pop(identifier, None)
            if pending:
                pending.result = fields[2] if len(fields) > 2 else ""
                if fields[0] == "ERR":
                    pending.error = pending.result
                elif pending.verb == "ARM" and pending.barrier == self.barrier:
                    self.armed = True
                elif pending.verb == "STOP":
                    self.armed = False
                if pending is self.stop_pending:
                    self.stop_pending = None
                pending.event.set()

    def _send_next(self, connection):
        # Check and write under the same short transaction lock: STOP cannot be
        # overtaken by an already dequeued ordinary request. A current OS write
        # can still take up to write_timeout; this is not a physical stop bound.
        with self.lock:
            if not self.connected or self.reset_event.is_set():
                return
            if self.urgent is not None:
                identifier, message = self.urgent
                self.urgent = None
            else:
                try: identifier, message = self.outgoing.get_nowait()
                except queue.Empty: return
            pending = self.pending.get(identifier)
            if pending is None or pending.barrier != self.barrier:
                return
            if pending.verb != "STOP" and time.monotonic() - pending.created > QUEUE_TTL:
                raise TimeoutError("Stale queued serial command")
            if time.monotonic() >= pending.deadline:
                raise TimeoutError("Expired serial command")
            written = connection.write(message.encode("ascii"))
            if written != len(message):
                raise RuntimeError("Partial serial write")
            pending.sent = True

    def _run(self):
        while not self.stop_event.is_set():
            connection = None
            try:
                selected = self._find_port()
                options = dict(port=selected, baudrate=115200, timeout=0.05, write_timeout=0.5)
                if os.name != "nt": options["exclusive"] = True
                connection = self.factory(**options)
                if self.stop_event.wait(2.0): break
                connection.reset_input_buffer()
                connection.write(b"HELLO\n")
                deadline = time.monotonic() + 3.0
                while connection.readline().strip() != b"READY Quadruped107 1":
                    if time.monotonic() > deadline or self.stop_event.is_set():
                        raise RuntimeError("Quadruped107 firmware handshake failed")
                self.telemetry.reset()
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
                    self._send_next(connection)  # urgent STOP precedes heartbeat/ordinary work
                    now = time.monotonic()
                    if now - last_ping >= 0.3:
                        connection.write(b"PING\n")
                        last_ping = now
                    raw = connection.readline(128)
                    if raw:
                        if not raw.endswith(b"\n"): raise RuntimeError("Truncated serial response")
                        line = raw.decode("ascii", errors="strict").strip()
                        if line == "PONG": last_pong = time.monotonic()
                        else: self._receive(line)
                    if time.monotonic() - last_pong > 1.2:
                        raise RuntimeError("Arduino heartbeat lost")
            except Exception as error:
                self._fail(str(error))
            finally:
                if connection:
                    try: connection.write(b"\nSTOP 0\n")
                    except Exception: pass
                    try: connection.close()
                    except Exception: pass  # failure state/queue cleanup below must still run
                self._fail("Serial disconnected" if self.stop_event.is_set() else self.error or "Reconnecting")
            self.stop_event.wait(2.0)

    def close(self):
        self.stop_event.set()
        if self.thread.is_alive(): self.thread.join(4)


class SimulatedLink:
    """Explicit development mode; same submission contract, no real hardware."""
    def __init__(self):
        self.armed = False
        self.epoch = 1
        self.history = []
        self.lock = threading.RLock()

    def start(self): pass

    def snapshot(self):
        with self.lock:
            return dict(connected=True, armed=self.armed, epoch=self.epoch,
                        stopping=False, queued=0, port="simulation", error=None)

    def submit(self, verb, *arguments, timeout=20.0):
        with self.lock:
            if verb == "ARM": self.armed = True
            elif verb == "STOP": self.armed = False
            elif not self.armed: raise RuntimeError("disarmed")
            self.history.append((verb, *arguments))
            pending = Pending(verb, result="simulated")
            pending.event.set()
            return pending

    def wait(self, pending):
        if pending.error: raise RuntimeError(pending.error)
        return pending.result

    def command(self, verb, *arguments, **kwargs):
        return self.wait(self.submit(verb, *arguments, **kwargs))

    def close(self):
        with self.lock: self.armed = False

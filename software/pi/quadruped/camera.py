"""Single capture owner publishing the latest BGR frame; never controls actuators."""
from __future__ import annotations
import logging
import math
import threading
import time
import zlib
import cv2
import numpy as np


class Camera:
    def __init__(self, simulate=False, index=0, *, backend=None, device=None,
                 width=640, height=480, fps=8, freeze_seconds=5.0, factory=None):
        self.backend = backend or ("synthetic" if simulate else "picamera2")
        if self.backend not in {"synthetic", "usb", "picamera2", "file"}:
            raise ValueError("Unknown camera backend")
        if any(type(v) is not int or not 32 <= v <= 1920 for v in (width, height)):
            raise ValueError("Camera dimensions must be integers 32..1920")
        if isinstance(fps, bool) or not isinstance(fps, (int, float)) or not math.isfinite(fps) or not 1 <= fps <= 60:
            raise ValueError("Requested FPS must be 1..60")
        if not math.isfinite(freeze_seconds) or not 0 <= freeze_seconds <= 120:
            raise ValueError("freeze_seconds must be 0..120")
        self.simulate = self.backend == "synthetic"
        self.index = index
        self.device = index if device is None else device
        self.width, self.height, self.requested_fps = width, height, fps
        self.freeze_seconds = freeze_seconds
        self.factory = factory or cv2.VideoCapture
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.frame = self.jpeg = None
        self.timestamp = 0.0
        self.status = "Starting camera"
        self.sequence = self.errors = self.reconnects = 0
        self.actual_fps = self.capture_ms = 0.0
        self.last_error = None
        self.last_changed = 0.0
        self.thread = threading.Thread(target=self._run, name="camera-owner", daemon=True)

    def start(self): self.thread.start()

    def latest(self, *, with_timestamp=False):
        with self.lock:
            fresh = time.monotonic() - self.timestamp < .8
            result = (self.frame.copy() if fresh and self.frame is not None else None,
                      self.jpeg if fresh else None, self.sequence, self.status)
            return result + (self.timestamp,) if with_timestamp else result

    def diagnostics(self):
        with self.lock:
            age = time.monotonic() - self.timestamp if self.timestamp else None
            return dict(backend=self.backend, device=str(self.device), available=age is not None and age < .8,
                        actualFps=round(self.actual_fps, 2), requestedFps=self.requested_fps,
                        width=self.width, height=self.height, frameAge=age,
                        captureMs=round(self.capture_ms, 2), errors=self.errors,
                        reconnects=self.reconnects, lastError=self.last_error, status=self.status,
                        ownerAlive=self.thread.is_alive(), unchangedFor=(time.monotonic()-self.last_changed
                            if self.last_changed else None))

    def _open(self):
        if self.backend == "picamera2":
            from picamera2 import Picamera2
            resource = Picamera2(self.index)
            try:
                resource.configure(resource.create_video_configuration(
                    main={"size": (self.width, self.height), "format": "RGB888"},
                    controls={"FrameRate": self.requested_fps}, buffer_count=4, queue=False))
                resource.start()
            except Exception:
                resource.close()
                raise
            return resource
        api = cv2.CAP_V4L2 if self.backend == "usb" else cv2.CAP_ANY
        resource = self.factory(self.device, api)
        try:
            if not resource.isOpened(): raise RuntimeError("VideoCapture did not open")
            if self.backend == "usb":
                # This camera advertises YUYV, not MJPEG. Settings are requests;
                # actual achieved FPS is measured independently.
                resource.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
                resource.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                resource.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                resource.set(cv2.CAP_PROP_FPS, self.requested_fps)
                resource.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return resource
        except Exception:
            resource.release()
            raise

    def _run(self):
        while not self.stop_event.is_set():
            resource = None
            previous_hash = None
            previous_capture = None
            try:
                if not self.simulate: resource = self._open()
                with self.lock: self.reconnects += 1
                while not self.stop_event.is_set():
                    started = time.monotonic()
                    if self.simulate:
                        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                        cv2.putText(frame, "SIMULATION - no hardware", (10, self.height//2),
                                    cv2.FONT_HERSHEY_SIMPLEX, .6, (255, 255, 255), 1)
                    elif self.backend == "picamera2":
                        frame = resource.capture_array("main")  # RGB888 bytes are BGR on Pi
                    else:
                        success, frame = resource.read()
                        if not success or frame is None: raise RuntimeError("Capture failed or video ended")
                    captured = time.monotonic()
                    if captured - started >= .8: raise RuntimeError("Capture returned too late")
                    if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
                        raise RuntimeError("Camera did not return a BGR image")
                    if not self.simulate:
                        fingerprint = zlib.crc32(frame.tobytes())
                        if fingerprint != previous_hash:
                            self.last_changed = captured
                            previous_hash = fingerprint
                        elif self.freeze_seconds and captured-self.last_changed >= self.freeze_seconds:
                            raise RuntimeError("Unchanged image watchdog: possible frozen capture")
                    success, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if not success: raise RuntimeError("JPEG encoding failed")
                    with self.lock:
                        # Use capture-call start, not publication, so slow reads
                        # cannot relabel their old result as a fresh observation.
                        self.timestamp = started
                        self.frame, self.jpeg = frame, jpeg.tobytes()
                        self.width, self.height = frame.shape[1], frame.shape[0]
                        if previous_capture is not None:
                            instantaneous = 1 / max(.000001, captured-previous_capture)
                            self.actual_fps = instantaneous if not self.actual_fps else .8*self.actual_fps+.2*instantaneous
                        previous_capture = captured
                        self.capture_ms = (captured-started)*1000
                        self.sequence += 1
                        self.last_error = None
                        self.status = "Simulated camera" if self.simulate else f"{self.backend} camera connected"
                    if self.backend in {"synthetic", "file"}:
                        self.stop_event.wait(max(0, 1/self.requested_fps-(time.monotonic()-started)))
            except Exception as error:
                logging.warning("Camera: %s", error)
                with self.lock:
                    self.frame = self.jpeg = None
                    self.timestamp = self.actual_fps = 0.0
                    self.errors += 1
                    self.last_error = str(error)
                    self.status = f"Camera unavailable: {error}"
                self.stop_event.wait(.5)
            finally:
                if resource is not None:
                    try:
                        if self.backend == "picamera2":
                            try: resource.stop()
                            finally: resource.close()
                        else: resource.release()
                    except Exception: logging.exception("Camera resource release failed")

    def close(self):
        self.stop_event.set()
        if self.thread.is_alive(): self.thread.join(3)
        if self.thread.is_alive():
            logging.warning("Capture remains blocked in native driver; restart process to reclaim device")

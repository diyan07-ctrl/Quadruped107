"""CSI camera owner. Frames use OpenCV BGR order and expire after capture failure."""
from __future__ import annotations
import logging
import threading
import time
import cv2
import numpy as np


class Camera:
    def __init__(self, simulate=False, index=0):
        self.simulate, self.index = simulate, index
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.frame = self.jpeg = None
        self.timestamp = 0.0
        self.status = "Starting Pi camera"
        self.sequence = 0
        self.thread = threading.Thread(target=self._run, name="pi-camera", daemon=True)

    def start(self): self.thread.start()

    def latest(self, *, with_timestamp=False):
        with self.lock:
            fresh = time.monotonic() - self.timestamp < 0.8
            snapshot = (self.frame.copy() if fresh and self.frame is not None else None,
                        self.jpeg if fresh else None, self.sequence, self.status)
            return snapshot + (self.timestamp,) if with_timestamp else snapshot

    def _run(self):
        while not self.stop_event.is_set():
            camera = None
            try:
                if not self.simulate:
                    from picamera2 import Picamera2
                    camera = Picamera2(self.index)
                    config = camera.create_video_configuration(
                        main={"size": (640, 480), "format": "RGB888"},
                        controls={"FrameRate": 20}, buffer_count=4, queue=False)
                    camera.configure(config)
                    camera.start()
                while not self.stop_event.is_set():
                    if self.simulate:
                        frame = np.zeros((480, 640, 3), dtype=np.uint8)
                        cv2.putText(frame, "SIMULATION - no hardware", (35, 240),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    else:
                        # Picamera2 RGB888 is [B,G,R] on the Pi's little-endian CPU.
                        frame = camera.capture_array("main")
                    success, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if not success: raise RuntimeError("JPEG encoding failed")
                    with self.lock:
                        self.frame, self.jpeg = frame, jpeg.tobytes()
                        self.timestamp = time.monotonic()
                        self.sequence += 1
                        self.status = "Simulated camera" if self.simulate else "Pi CSI camera connected"
                    if self.simulate: self.stop_event.wait(0.05)
            except Exception as error:
                logging.warning("Pi camera: %s", error)
                with self.lock:
                    self.frame = self.jpeg = None
                    self.timestamp = 0.0
                    self.status = f"Pi camera unavailable: {error}"
                self.stop_event.wait(2)
            finally:
                if camera:
                    try: camera.stop()
                    finally: camera.close()

    def close(self):
        self.stop_event.set()
        if self.thread.is_alive(): self.thread.join(3)

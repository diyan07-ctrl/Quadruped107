"""Quadruped107 Raspberry Pi 4 service, 2026-11-04. GPL-3.0."""
from __future__ import annotations
import argparse
import base64
import logging
import os
import signal
import secrets
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, Response, jsonify, request, send_from_directory
from werkzeug.serving import make_server

from .camera import Camera
from .controller import CONTINUOUS, MODES, MOTIONS, MotionController
from .serial_link import SerialLink, SimulatedLink
from .vision import choose_blue_ball_motion, detect_blue_ball, encode_vision_frame

APP_DIR = Path(__file__).resolve().parent


class Runtime:
    def __init__(self, *, simulate=False, port="auto", camera_index=0, gesture_model="", link=None):
        self.simulate = simulate
        self.link = link or (SimulatedLink() if simulate else SerialLink(port))
        self.camera = Camera(simulate, camera_index)
        self.motion = MotionController(self.link)
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.owner_lock = threading.Lock()
        self.owner_token = None
        self.owner_seen = 0.0
        self.owner_generation = 0
        self.arming_claim = False
        self.vision = dict(opencv="Idle", handGesture="Not configured",
                           blueBall={}, hand={})
        self.preview = None
        self.preview_at = 0.0
        self.detector = None
        if gesture_model:
            try:
                from .gestures import GestureDetector
                self.detector = GestureDetector(gesture_model)
                self.vision["handGesture"] = "Ready"
            except Exception as error:
                self.vision["handGesture"] = f"Unavailable: {error}"
                logging.warning("Hand gestures: %s", error)
        self.worker = threading.Thread(target=self._vision_loop, name="vision", daemon=True)

    def start(self):
        self.link.start(); self.camera.start(); self.motion.start(); self.worker.start()

    def claim_control(self, token):
        with self.owner_lock:
            state = self.motion.snapshot()
            if self.arming_claim or state["busy"] or state["stopping"] or state["enabled"]:
                raise RuntimeError("Control is enabled or an operation is pending; STOP before takeover")
            if self.owner_token is not None and token != self.owner_token and (
                    state["enabled"] or state["busy"] or state["stopping"] or
                    time.monotonic() - self.owner_seen < 1.0):
                raise RuntimeError("Another browser holds control; STOP is available to everyone")
            token = token if isinstance(token, str) and 20 <= len(token) <= 128 else secrets.token_urlsafe(24)
            self.owner_token, self.owner_seen = token, time.monotonic()
            self.owner_generation += 1
            self.arming_claim = True
            return token, self.owner_generation

    def require_control(self, token):
        with self.owner_lock:
            if self.owner_token is None or token != self.owner_token:
                raise RuntimeError("Enable servos in this browser to acquire control")
            self.owner_seen = time.monotonic()
            return self.motion.snapshot()["generation"]

    def release_control(self, token, generation):
        with self.owner_lock:
            if token == self.owner_token and generation == self.owner_generation:
                self.owner_token = None
                self.arming_claim = False

    def finish_claim(self, generation):
        with self.owner_lock:
            if generation == self.owner_generation: self.arming_claim = False

    def frame(self):
        _, jpeg, _, _ = self.camera.latest()
        with self.lock:
            if (self.motion.snapshot()["appMode"] != "manual" and
                    time.monotonic() - self.preview_at < 0.8 and jpeg):
                return self.preview or jpeg
        return jpeg

    def state(self):
        _, jpeg, _, status = self.camera.latest()
        with self.lock:
            vision = {**self.vision}
        return dict(ok=True, simulation=self.simulate, motion=self.motion.snapshot(),
                    link=self.link.snapshot(), controlModes=sorted(MODES), motionModes=sorted(MOTIONS),
                    features=dict(handGesture=self.detector is not None), vision=vision,
                    camera=dict(available=jpeg is not None, status=status,
                                snapshotEndpoint="/api/camera-frame", mjpegEndpoint="/video-feed"))

    def _vision_loop(self):
        last_sequence = 0
        last_action_at = 0.0
        candidate = None
        stable = 0
        previous_mode = "manual"
        issued_gesture = None
        while not self.stop_event.wait(0.06):
            state = self.motion.snapshot()
            mode = state["appMode"]
            if mode != previous_mode:
                candidate, stable, issued_gesture = None, 0, None
                previous_mode = mode
            if mode == "manual" or not state["enabled"]: continue
            frame, _, sequence, _ = self.camera.latest()
            if frame is None:
                self.motion.stop("Camera frame expired during vision control")
                continue
            if sequence == last_sequence: continue
            last_sequence = sequence
            try:
                if mode == "opencv":
                    detection = detect_blue_ball(frame)
                    action, motion = choose_blue_ball_motion(detection)
                    motion = "stand" if motion == "hold" else motion
                    key = action
                    preview = encode_vision_frame(frame, detection, action, motion)
                    with self.lock:
                        self.preview, self.preview_at = preview, time.monotonic()
                        self.vision["opencv"] = f"{action}: {motion}"
                        self.vision["blueBall"] = {k: v for k, v in detection.items() if k != "mask"}
                        self.vision["blueBall"].update(action=action, motion=motion)
                else:
                    if self.detector is None: raise RuntimeError("Hand gesture model unavailable")
                    gesture = self.detector.detect(frame)
                    with self.lock:
                        self.vision["hand"] = ({"detected": True, **gesture} if gesture else
                                               dict(detected=False, gesture="none", motion="hold"))
                    if not gesture:
                        candidate, stable, issued_gesture = None, 0, None
                        continue
                    key, motion = gesture["gesture"], gesture["motion"]
                stable = stable + 1 if key == candidate else 1
                candidate = key
                if (stable >= 2 and time.monotonic() - last_action_at >= 1.5 and
                        (mode != "hand_gesture" or key != issued_gesture)):
                    before = self.motion.snapshot()["generation"]
                    self.motion.autonomous(mode, motion)
                    if self.motion.snapshot()["generation"] != before:
                        last_action_at = time.monotonic()
                        issued_gesture = key
            except Exception as error:
                logging.exception("Vision failed")
                self.motion.stop(f"Vision failed: {error}")

    def close(self):
        self.stop_event.set()
        self.motion.close()
        self.link.close()
        self.camera.close()
        if self.worker.is_alive(): self.worker.join(3)
        if self.detector and not self.worker.is_alive(): self.detector.close()
        elif self.worker.is_alive(): logging.warning("Vision worker still running after shutdown deadline")


def create_app(runtime):
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 4096

    @app.before_request
    def same_origin_control():
        if request.method == "POST":
            origin = request.headers.get("Origin")
            if origin and urlsplit(origin).netloc != request.host:
                return jsonify(ok=False, error="Cross-origin control rejected"), 403
            if not request.is_json:
                return jsonify(ok=False, error="Use application/json"), 415

    @app.errorhandler(ValueError)
    def invalid(error): return jsonify(ok=False, error=str(error)), 400

    @app.errorhandler(RuntimeError)
    @app.errorhandler(TimeoutError)
    def unavailable(error): return jsonify(ok=False, error=str(error)), 409

    @app.get("/")
    def index(): return send_from_directory(APP_DIR / "web", "index.html")

    @app.get("/<path:name>")
    def asset(name): return send_from_directory(APP_DIR / "web", name)

    @app.get("/api/state")
    def state(): return jsonify(runtime.state())

    @app.get("/api/mode")
    def mode(): return jsonify(ok=True, state=runtime.motion.snapshot())

    @app.post("/api/mode")
    def set_mode():
        data = body()
        mode = data.get("mode")
        if not isinstance(mode, str): raise ValueError("mode must be a string")
        mode = mode.strip().lower().replace("-", "_")
        if mode == "hand_gesture" and runtime.detector is None:
            raise RuntimeError(runtime.vision["handGesture"])
        if mode in {"opencv", "hand_gesture"} and runtime.camera.latest()[0] is None:
            raise RuntimeError("A fresh Pi camera frame is required for vision control")
        generation = runtime.require_control(request.cookies.get("quadruped_control"))
        generation = runtime.motion.set_mode(mode, expected_generation=generation)
        return jsonify(ok=True, acceptedMode=mode, generation=generation, state=runtime.motion.snapshot())

    @app.post("/api/heartbeat")
    def heartbeat():
        data = body()
        motion = data.get("motion")
        if motion is not None and (not isinstance(motion, str) or motion not in CONTINUOUS):
            raise ValueError("Invalid held motion")
        with runtime.owner_lock:
            unclaimed = runtime.owner_token is None
        if unclaimed: return jsonify(ok=True)
        generation = runtime.require_control(request.cookies.get("quadruped_control"))
        runtime.motion.heartbeat(motion, expected_generation=generation)
        state = runtime.motion.snapshot()
        if (state["enabled"] and state["appMode"] == "manual" and
                state["desiredMotion"] in CONTINUOUS and motion != state["desiredMotion"]):
            runtime.motion.set_mode("stand", expected_generation=generation)
        return jsonify(ok=True)

    @app.post("/api/arm")
    def arm():
        body()
        generation = runtime.motion.snapshot()["generation"]
        token, claim = runtime.claim_control(request.cookies.get("quadruped_control"))
        try: runtime.motion.arm(expected_generation=generation)
        except Exception:
            runtime.release_control(token, claim)
            raise
        finally: runtime.finish_claim(claim)
        response = jsonify(ok=True, state=runtime.motion.snapshot())
        response.set_cookie("quadruped_control", token, httponly=True, samesite="Strict")
        return response

    @app.post("/api/stop")
    def stop():
        with runtime.owner_lock:
            token, claim = runtime.owner_token, runtime.owner_generation
        body(); runtime.motion.stop()
        runtime.release_control(token, claim)
        return jsonify(ok=True, state=runtime.motion.snapshot())

    @app.post("/api/servo")
    def servo():
        generation = runtime.require_control(request.cookies.get("quadruped_control"))
        data = body()
        runtime.motion.servo(data.get("channel"), data.get("pulse"), expected_generation=generation)
        return jsonify(ok=True)

    @app.get("/api/camera-frame")
    def camera_frame():
        frame = runtime.frame()
        return jsonify(ok=frame is not None, available=frame is not None,
                       status=runtime.camera.latest()[3], mimeType="image/jpeg",
                       data=base64.b64encode(frame).decode("ascii") if frame else None)

    @app.get("/video-feed")
    def video_feed():
        def frames():
            while not runtime.stop_event.is_set():
                frame = runtime.frame()
                if frame:
                    yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " +
                           str(len(frame)).encode() + b"\r\n\r\n" + frame + b"\r\n")
                runtime.stop_event.wait(0.05)
        return Response(frames(), mimetype="multipart/x-mixed-replace; boundary=frame",
                        headers={"Cache-Control": "no-store"})

    return app


def body():
    data = request.get_json()
    if not isinstance(data, dict): raise ValueError("JSON body must be an object")
    return data


def main():
    parser = argparse.ArgumentParser(description="Pi 4 camera and Uno robot controller")
    parser.add_argument("--simulate", action="store_true", help="Synthetic camera and serial; no hardware")
    parser.add_argument("--host", default=os.getenv("QUADRUPED_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("QUADRUPED_PORT", "7000")))
    parser.add_argument("--serial-port", default=os.getenv("QUADRUPED_SERIAL_PORT", "auto"))
    parser.add_argument("--camera-index", type=int, default=int(os.getenv("QUADRUPED_CAMERA_INDEX", "0")))
    parser.add_argument("--gesture-model", default=os.getenv("QUADRUPED_GESTURE_MODEL", ""))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    def terminate(_signal, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, terminate)
    runtime = Runtime(simulate=args.simulate, port=args.serial_port,
                      camera_index=args.camera_index, gesture_model=args.gesture_model)
    server = None
    try:
        server = make_server(args.host, args.port, create_app(runtime), threaded=True)
        runtime.start()
        logging.info("Quadruped107%s: http://%s:%s", " SIMULATION" if args.simulate else "", args.host, args.port)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        runtime.close()
        if server is not None: server.server_close()


if __name__ == "__main__": main()

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
from .autonomy import Behavior, VisionSettings, Decision
from .diagnostics import ProcessStats
from .controller import CONTINUOUS, MODES, MOTIONS, MotionController
from .serial_link import SerialLink, SimulatedLink
from .vision import choose_blue_ball_motion, detect_blue_ball, encode_vision_frame

APP_DIR = Path(__file__).resolve().parent


class Runtime:
    def __init__(self, *, simulate=False, port="auto", camera_index=0, gesture_model="", link=None,
                 camera_backend=None, camera_device=None, width=640, height=480, fps=8,
                 actuator_backend=None, vision_config=None, virtual_speed=1.0,
                 simulator_host=None, simulator_port=7002):
        self.simulate = simulate
        self.actuators_simulated = simulate or actuator_backend == "virtual"
        if link is not None: self.link = link
        elif actuator_backend == "virtual":
            from .virtual_uno import VirtualLink
            self.link = VirtualLink(speed=virtual_speed)
        else: self.link = SimulatedLink() if simulate else SerialLink(port)
        self.camera = Camera(simulate, camera_index, backend=camera_backend, device=camera_device,
                             width=width, height=height, fps=fps)
        self.vision_settings = VisionSettings.load(vision_config)
        self.behavior = Behavior(self.vision_settings)
        self.obstacle_blocked = False
        self.stats = ProcessStats()
        self.motion = MotionController(self.link)
        self.bridge = None
        if simulator_host:
            if not self.actuators_simulated or not hasattr(self.link, "engine"):
                raise ValueError("Network bridge requires explicitly selected protocol virtual actuators")
            from .bridge import TraceClient
            self.bridge = TraceClient(simulator_host, simulator_port, self.link.engine.snapshot)
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
        self.bridge_guard = threading.Thread(target=self._bridge_guard, name="bridge-safety", daemon=True)

    def start(self):
        self.link.start(); self.camera.start(); self.motion.start(); self.worker.start()
        if self.bridge: self.bridge.start(); self.bridge_guard.start()

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
            if (time.monotonic() - self.preview_at < 0.8 and jpeg):
                return self.preview or jpeg
        return jpeg

    def state(self):
        _, jpeg, _, status = self.camera.latest()
        with self.lock:
            vision = {**self.vision}
        return dict(ok=True, simulation=self.actuators_simulated, physicalActuationAllowed=False,
                    system=self.stats.snapshot(), obstacleVirtual=self.obstacle_blocked,
                    bridge=self.bridge.snapshot() if self.bridge else None, motion=self.motion.snapshot(),
                    link=self.link.snapshot(), controlModes=sorted(MODES), motionModes=sorted(MOTIONS),
                    features=dict(handGesture=self.detector is not None), vision=vision,
                    camera=dict(**self.camera.diagnostics(),
                                snapshotEndpoint="/api/camera-frame", mjpegEndpoint="/video-feed"))

    def _vision_loop(self):
        last_sequence=0
        context=None
        count=0
        measured_at=time.monotonic()
        held_gesture=None
        gesture_count=0
        gesture_last_request=0.0
        last_gesture_sent=None
        while not self.stop_event.wait(.02):
            state=self.motion.snapshot()
            mode=state["appMode"]
            new_context=(mode,state["session"])
            if new_context!=context:
                self.behavior.reset(time.monotonic())
                context=new_context
                held_gesture=None
                gesture_count=0
                gesture_last_request=0.0
                last_gesture_sent=None
            frame,_,sequence,_,published_at=self.camera.latest(with_timestamp=True)
            autonomous=state["enabled"] and mode!="manual"
            if frame is None:
                decision=self.behavior.step(None,time.monotonic(),enabled=autonomous,
                    manual=state["enabled"] and mode=="manual",stopped=not state["enabled"] and state["session"]>0)
                with self.lock:
                    self.vision["behavior"]=decision.state
                    self.preview=None
                if autonomous:
                    self.motion.stop("Camera frame expired during vision control",expected_generation=state["generation"])
                continue
            if sequence==last_sequence: continue
            last_sequence=sequence
            started=time.monotonic()
            try:
                settings=self.vision_settings
                if settings.hsv_lower==(95,70,30) and settings.hsv_upper==(140,255,255):
                    detection=detect_blue_ball(frame)
                else:
                    detection=detect_blue_ball(frame,lower=settings.hsv_lower,upper=settings.hsv_upper)
                now=time.monotonic()
                observation={k:v for k,v in detection.items() if k!="mask"}
                observation.update(observed_at=published_at,frameAge=now-published_at)
                if autonomous and not self._fresh_observation(state,published_at): continue
                if now-published_at>settings.max_age: continue
                decision=self.behavior.step(observation,now,enabled=autonomous,
                    manual=state["enabled"] and mode=="manual",stopped=not state["enabled"] and state["session"]>0,
                    obstacle=self.obstacle_blocked)
                if mode=="hand_gesture" and autonomous:
                    if self.detector is None: raise RuntimeError("Hand gesture model unavailable")
                    gesture=self.detector.detect(frame)
                    label=gesture.get("motion") if gesture else None
                    gesture_count=gesture_count+1 if label==held_gesture else 1
                    held_gesture=label
                    if label is None: last_gesture_sent=None
                    action=label if label and label!=last_gesture_sent and gesture_count>=settings.min_frames and now-gesture_last_request>=settings.command_period else None
                    decision=Decision("MANUAL_OVERRIDE" if not autonomous else "GESTURE_CONTROL",
                                      action if label else "stand",False,"Optional gesture control")
                    with self.lock: self.vision["hand"]=gesture or {}
                preview=encode_vision_frame(frame,detection,decision.state,decision.motion or "hold")
                if autonomous and not self._fresh_observation(state,published_at): continue
                count+=1
                elapsed=time.monotonic()-measured_at
                with self.lock:
                    if elapsed>=.5:
                        self.vision["processingFps"]=round(count/elapsed,2)
                        count,measured_at=0,time.monotonic()
                    self.preview,self.preview_at=preview,published_at
                    self.vision["blueBall"]=observation
                    self.vision["behavior"]=decision.state
                    self.vision["opencv"]=decision.reason or decision.state
                    self.vision["processingMs"]=round((time.monotonic()-started)*1000,2)
                    self.vision["transitions"]=list(self.behavior.transitions)
                if not autonomous: continue
                if not self.actuators_simulated:
                    self.motion.stop("Physical autonomous motion is inhibited",expected_generation=state["generation"])
                    continue
                if decision.inhibit:
                    self.motion.stop(decision.reason,expected_generation=state["generation"])
                    continue
                motion=decision.motion
                if motion and self.motion.autonomous(mode,motion,expected_generation=state["generation"]):
                    self.behavior.accepted(motion,time.monotonic())
                    if mode=="hand_gesture":
                        gesture_last_request=time.monotonic()
                        last_gesture_sent=motion if held_gesture else None
            except Exception as error:
                logging.exception("Vision failed")
                with self.lock: self.vision["opencv"]=str(error)
                if autonomous:
                    self.motion.stop(f"Vision failed: {error}",expected_generation=state["generation"])

    def _bridge_guard(self):
        while not self.stop_event.wait(.05):
            health=self.bridge.snapshot()
            if self.motion.snapshot()["enabled"] and (not health["connected"] or health["fault"]):
                self.motion.stop(health["fault"] or "Simulator disconnected; explicit enable required")

    def _fresh_observation(self, state, published_at):
        if time.monotonic() - published_at > .5:
            self.motion.stop("Stale vision result", expected_generation=state["generation"])
            return False
        return self.motion.vision_heartbeat(state["appMode"], state["generation"], published_at)

    def close(self):
        self.stop_event.set()
        self.motion.close()
        if self.bridge: self.bridge.close()
        if self.bridge_guard.is_alive(): self.bridge_guard.join(1)
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
            raise RuntimeError("A fresh camera frame is required for vision control")
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
        if not runtime.actuators_simulated:
            raise RuntimeError("Physical actuation is prohibited; explicitly select virtual actuators")
        if runtime.obstacle_blocked: raise RuntimeError("Clear the virtual obstacle before enabling")
        generation = runtime.motion.snapshot()["generation"]
        token, claim = runtime.claim_control(request.cookies.get("quadruped_control"))
        bridge_epoch = None
        try:
            if runtime.bridge: bridge_epoch = runtime.bridge.prepare_arm()
            runtime.motion.arm(expected_generation=generation)
            if runtime.bridge and (runtime.bridge.snapshot()["epoch"] != bridge_epoch or not runtime.bridge.snapshot()["connected"]):
                runtime.motion.stop("Simulator changed during enable")
                raise RuntimeError("Simulator changed during enable")
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

    @app.post("/api/simulation/obstacle")
    def obstacle():
        if not runtime.actuators_simulated: raise RuntimeError("Virtual sensor endpoint only")
        data = body()
        if type(data.get("blocked")) is not bool: raise ValueError("blocked must be boolean")
        runtime.obstacle_blocked = data["blocked"]
        if runtime.obstacle_blocked: runtime.motion.stop("Virtual obstacle blocked")
        return jsonify(ok=True, virtual=True, blocked=runtime.obstacle_blocked)

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
    parser.add_argument("--camera-backend", choices=("usb", "picamera2", "synthetic", "file"))
    parser.add_argument("--camera-device", default=os.getenv("QUADRUPED_CAMERA_DEVICE", "0"))
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=float, default=8)
    parser.add_argument("--actuator-backend", choices=("virtual", "serial-monitor"), default=None)
    parser.add_argument("--virtual-speed", type=float, default=1.0)
    parser.add_argument("--vision-config")
    parser.add_argument("--simulator", help="Trusted simulator host; enables mandatory network lease")
    parser.add_argument("--simulator-port", type=int, default=7002)
    args = parser.parse_args()
    if args.simulate and args.camera_backend not in (None, "synthetic"):
        parser.error("--simulate means synthetic camera; use --camera-backend usb --actuator-backend virtual for mixed mode")
    if args.simulate and args.actuator_backend not in (None, "virtual"):
        parser.error("--simulate cannot select a physical serial backend")
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    def terminate(_signal, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, terminate)
    runtime = Runtime(simulate=args.simulate, port=args.serial_port,
                      camera_index=args.camera_index, gesture_model=args.gesture_model,
                      camera_backend=args.camera_backend or ("synthetic" if args.simulate else "usb"),
                      camera_device=int(args.camera_device) if args.camera_device.isdecimal() else args.camera_device,
                      width=args.width, height=args.height, fps=args.fps,
                      actuator_backend=args.actuator_backend or ("virtual" if args.simulate else "serial-monitor"),
                      vision_config=args.vision_config, virtual_speed=args.virtual_speed,
                      simulator_host=args.simulator, simulator_port=args.simulator_port)
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

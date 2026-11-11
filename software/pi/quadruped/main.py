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
from .display import make_display_backend
from .vision import choose_blue_ball_motion, detect_blue_ball, encode_vision_frame, TargetLock

APP_DIR = Path(__file__).resolve().parent


class Runtime:
    def __init__(self, *, simulate=False, port="auto", camera_index=0, gesture_model="", link=None,
                 camera_backend=None, camera_device=None, width=640, height=480, fps=8,
                 actuator_backend=None, vision_config=None, virtual_speed=1.0,
                 simulator_host=None, simulator_port=7002, virtual_sensors=False, sensor_backend=None, navigation_config=None, sensor_config=None, vision_state=None,
                 sensor_source=None, sensor_port=None, sensor_link=None, display_backend=None):
        self.simulate = simulate
        self.actuators_simulated = simulate or actuator_backend == "virtual"
        if link is not None:
            if self.actuators_simulated and not isinstance(link, SimulatedLink):
                from .virtual_uno import VirtualLink
                if not isinstance(link, VirtualLink):
                    raise ValueError("Simulation configuration cannot wrap a physical or unknown actuator link")
            self.link = link
        elif actuator_backend == "virtual":
            from .virtual_uno import VirtualLink
            self.link = VirtualLink(speed=virtual_speed)
        else: self.link = SimulatedLink() if simulate else SerialLink(port)
        self.camera = Camera(simulate, camera_index, backend=camera_backend, device=camera_device,
                             width=width, height=height, fps=fps)
        from .vision_config import load_state
        self.settings_lock=threading.RLock()
        self.vision_state_path=Path(vision_state) if vision_state else None
        if vision_config and self.vision_state_path and Path(vision_config).resolve()==self.vision_state_path.resolve():
            raise ValueError("Vision preferences must be separate from the supplied configuration")
        self.vision_revision=1
        if not vision_config and self.vision_state_path and self.vision_state_path.exists():
            self.vision_settings,self.vision_revision=load_state(self.vision_state_path)
        else: self.vision_settings = VisionSettings.load(vision_config)
        self.behavior = Behavior(self.vision_settings)
        self.obstacle_blocked = False
        self.stats = ProcessStats()
        self.motion = MotionController(self.link)
        self.sensors = None
        self.navigation = None
        self.nav_lock = threading.RLock()
        self.nav_wake = threading.Event()
        self.sensor_backend = sensor_backend
        self.sensor_source=sensor_source or ('test' if virtual_sensors and sensor_backend else 'virtual' if virtual_sensors else 'none')
        if self.sensor_source not in {'none','virtual','test','physical_uno'}:
            raise ValueError('Unknown sensor source')
        if virtual_sensors and self.sensor_source=='physical_uno':
            raise ValueError('Select one authoritative sensor source')
        self.sensor_link=None
        self.physical_provider=None
        if self.sensor_source!='none':
            if not self.actuators_simulated or not hasattr(self.link, "engine"):
                raise ValueError("Sensor readiness requires explicit protocol virtual actuators")
            if self.sensor_source=='virtual' and not simulator_host and sensor_backend is None:
                raise ValueError("Virtual sensing requires simulator telemetry or an explicit test backend")
            if self.sensor_source=='test' and sensor_backend is None:
                raise ValueError('Test sensors require an explicit deterministic backend')
            if self.sensor_source=='physical_uno' and sensor_backend is not None:
                raise ValueError('Physical sensing cannot also use a test backend')
            from .sensors import SensorManager, SensorConfig
            from .navigation import Navigation, NavigationSettings, motion_inhibition
            self.sensors = SensorManager(SensorConfig.load(sensor_config),source=self.sensor_source)
            if self.sensor_source=='physical_uno':
                from .physical_sensors import PhysicalSensorProvider
                if sensor_link is None and not sensor_port: raise ValueError('Physical sensor port must be explicit')
                if sensor_link is not None and not getattr(sensor_link,'sensor_only',False):
                    raise ValueError('Physical sensor link must prohibit actuation')
                self.sensor_link=sensor_link or SerialLink(sensor_port,sensor_only=True)
                self.physical_provider=PhysicalSensorProvider(self.sensor_link,self.sensors)
            self.navigation = Navigation(NavigationSettings.load(navigation_config),self.vision_settings)
            self.motion.safety_check = self._sensor_inhibition
        self.bridge = None
        if simulator_host:
            if not self.actuators_simulated or not hasattr(self.link, "engine"):
                raise ValueError("Network bridge requires explicitly selected protocol virtual actuators")
            from .bridge import TraceClient
            self.bridge = TraceClient(simulator_host, simulator_port, self._trace_state,
                                      on_sensors=self._sensor_update if self.sensors and self.sensor_source!='physical_uno' else None)
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.owner_lock = threading.Lock()
        self.owner_token = None
        self.owner_seen = 0.0
        self.owner_generation = 0
        self.arming_claim = False
        self.vision = dict(opencv="Idle", targetColor=self.vision_settings.target_color, handGesture="Not configured",
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
        self.nav_worker = threading.Thread(target=self._navigation_loop, name="virtual-autonomy", daemon=True)
        self.bridge_guard = threading.Thread(target=self._bridge_guard, name="bridge-safety", daemon=True)
        from .display import DisplayService
        self.display=DisplayService(display_backend,self.state)

    def start(self):
        self.link.start(); self.camera.start(); self.motion.start(); self.worker.start()
        if self.bridge: self.bridge.start(); self.bridge_guard.start()
        if self.sensors: self.nav_worker.start()
        if self.sensor_link: self.sensor_link.start()
        self.display.start()

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
        with self.settings_lock,self.lock:
            vision = {**self.vision}
            config=self.vision_configuration()
            vision["targetColor"]=self.vision_settings.target_color
            observed=vision.get("blueBall",{}).get("observed_at")
            vision["observationAge"]=time.monotonic()-observed if observed is not None else None
            vision["targetFresh"]=observed is not None and 0<=vision["observationAge"]<=self.vision_settings.max_age
        return dict(ok=True, simulation=self.actuators_simulated, physicalActuationAllowed=False,
                    system=self.stats.snapshot(), obstacleVirtual=self.obstacle_blocked,
                    bridge=self.bridge.snapshot() if self.bridge else None, motion=self.motion.snapshot(),
                    link=self.link.snapshot(), controlModes=sorted({'manual','idle','sensor_test'} if self.sensor_source=='physical_uno' else MODES-{"hand_gesture"} if self.sensors else MODES-{"explore","sensor_test","interaction"}-(set() if self.detector else {"hand_gesture"})), motionModes=sorted(MOTIONS),
                    sensors=self.sensors.snapshot() if self.sensors else None,
                    sensorSource=self.sensor_source,sensorLink=self.sensor_link.snapshot() if self.sensor_link else None,
                    oled=self.display.snapshot(),
                    autonomy=self.navigation_state(),visionConfig=config,
                    decisionHistory=self.motion.events.snapshot(),
                    features=dict(handGesture=self.detector is not None and self.sensors is None,virtualSensors=self.sensors is not None and self.sensor_source!='physical_uno'), vision=vision,
                    camera=dict(**self.camera.diagnostics(),
                                snapshotEndpoint="/api/camera-frame", mjpegEndpoint="/video-feed"))

    def _vision_loop(self):
        last_sequence=0
        target_tracker=TargetLock(self.vision_settings)
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
            with self.settings_lock: settings,revision=self.vision_settings,self.vision_revision
            new_context=(mode,state["session"],revision)
            if new_context!=context:
                self.behavior=Behavior(settings)
                self.behavior.reset(time.monotonic())
                target_tracker=TargetLock(settings)
                context=new_context
                held_gesture=None
                gesture_count=0
                gesture_last_request=0.0
                last_gesture_sent=None
            frame,_,sequence,_,published_at=self.camera.latest(with_timestamp=True)
            autonomous=state["enabled"] and mode in {"opencv","hand_gesture"} and self.sensors is None
            if frame is None:
                decision=self.behavior.step(None,time.monotonic(),enabled=autonomous,
                    manual=state["enabled"] and mode=="manual",stopped=not state["enabled"] and state["session"]>0)
                with self.lock:
                    if not self.sensors: self.vision["behavior"]=decision.state
                    self.preview=None
                if autonomous:
                    self.motion.stop("Camera frame expired during vision control",expected_generation=state["generation"])
                continue
            if sequence==last_sequence: continue
            last_sequence=sequence
            started=time.monotonic()
            try:
                if (settings.hsv_lower==(95,70,30) and settings.hsv_upper==(140,255,255) and
                    (settings.min_area,settings.min_radius,settings.max_radius_ratio,settings.min_circularity)==(150,8,.38,.55)):
                    detection=detect_blue_ball(frame)
                else:
                    detection=detect_blue_ball(frame,lower=settings.hsv_lower,upper=settings.hsv_upper,
                        min_area=settings.min_area,min_radius=settings.min_radius,
                        max_radius_ratio=settings.max_radius_ratio,min_circularity=settings.min_circularity)
                with self.settings_lock:
                    if revision!=self.vision_revision: continue
                detection=target_tracker.process(detection,published_at,allow_new=not state["enabled"])
                now=time.monotonic()
                observation={k:v for k,v in detection.items() if k!="mask"}
                observation.update(observed_at=published_at,frameAge=now-published_at,revision=revision,targetColor=settings.target_color)
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
                preview=encode_vision_frame(frame,detection,self.navigation_state()["state"] if self.sensors else decision.state,decision.motion or "hold",target_name=settings.target_color)
                if autonomous and not self._fresh_observation(state,published_at): continue
                with self.settings_lock:
                    if revision!=self.vision_revision: continue
                count+=1
                elapsed=time.monotonic()-measured_at
                with self.settings_lock,self.lock:
                    if revision!=self.vision_revision: continue
                    if elapsed>=.5:
                        self.vision["processingFps"]=round(count/elapsed,2)
                        count,measured_at=0,time.monotonic()
                    self.preview,self.preview_at=preview,published_at
                    self.vision["blueBall"]=observation
                    self.vision["targetColor"]=settings.target_color
                    if not self.sensors: self.vision["behavior"]=decision.state
                    if not self.sensors: self.vision["opencv"]=decision.reason or decision.state
                    self.vision["processingMs"]=round((time.monotonic()-started)*1000,2)
                    self.vision["transitions"]=list(self.behavior.transitions)
                self.motion.events.record("perception",status=detection.get("lockState","unknown"),
                    reason=settings.target_color+" target "+("detected" if observation.get("detected") else "missing"),generation=revision)
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
                current=self.motion.snapshot()
                with self.lock: self.vision["blueBall"]={}
                if current["enabled"] and current["appMode"] in {"opencv","hand_gesture"}:
                    self.motion.stop(f"Vision failed: {error}",expected_generation=current["generation"])

    def vision_configuration(self):
        with self.settings_lock:
            return dict(revision=self.vision_revision,settings=self.vision_settings.to_dict(),
                        persisted=self.vision_state_path is not None)

    def update_vision(self,data,token):
        if not self.actuators_simulated: raise RuntimeError("Target selection requires explicitly virtual actuators")
        with self.owner_lock:
            if self.arming_claim: raise RuntimeError("Enable operation in progress")
            if self.owner_token is not None and token!=self.owner_token and (
                self.motion.snapshot()["enabled"] or time.monotonic()-self.owner_seen<1):
                raise RuntimeError("Another browser owns control")
            with self.settings_lock:
                if type(data.get("revision")) is not int or data["revision"]!=self.vision_revision:
                    raise RuntimeError("Stale vision configuration revision")
                changes={k:v for k,v in data.items() if k!="revision"}
                merged=self.vision_settings.to_dict()
                if changes.get("target_color",merged["target_color"])!=merged["target_color"]:
                    merged.pop("hsv_lower"); merged.pop("hsv_upper")
                merged.update(changes)
                settings=VisionSettings.from_dict(merged)
                self.motion.stop("Vision configuration changed; explicit enable required",wait=False)
                revision=self.vision_revision+1
                if self.vision_state_path:
                    from .vision_config import save_state
                    try: save_state(self.vision_state_path,settings,revision)
                    except OSError as error: raise RuntimeError("Preference write failed; actuators remain disarmed") from error
                self.vision_settings,self.vision_revision=settings,revision
                if self.navigation:
                    with self.nav_lock: self.navigation.tracker=Behavior(settings)
                with self.lock:
                    self.preview=None
                    self.vision["blueBall"]={}
                    self.vision["targetColor"]=settings.target_color
                self.motion.events.record("configuration",status="applied_disarmed",
                    reason=settings.target_color+" target selected",generation=revision)
                return self.vision_configuration()

    def _trace_state(self):
        state=self.link.engine.snapshot()
        if self.navigation:
            state["behavior"]=self.navigation_state()["state"]
        else:
            with self.lock: state["behavior"]=self.vision.get("behavior","IDLE")
        return state

    def navigation_state(self):
        with self.nav_lock:
            return self.navigation.snapshot() if self.navigation else None

    def _sensor_inhibition(self,motion):
        from .navigation import motion_inhibition
        sensors=self.sensors.snapshot()
        reason=motion_inhibition(sensors,motion,self.navigation.settings)
        if reason: return reason
        state=self.motion.snapshot()
        if (state["appMode"] in {"opencv","explore"} and motion in CONTINUOUS
            and sensors["front_m"]<=self.navigation.settings.caution_m
            and self.navigation_state()["state"]!="RECOVERY"):
            return "Obstacle override preempts autonomous motion"
        return None

    def _sensor_update(self,batch,*,notify=True,**metadata):
        if not self.sensors: return
        self.sensors.ingest(batch,**metadata)
        if notify: self.nav_wake.set()
        state=self.motion.snapshot()
        reason=self.motion.safety_check(state["currentMotion"] if state["busy"] else state["desiredMotion"])
        if state["enabled"] and reason:
            self.motion.stop(reason,expected_generation=state["generation"],wait=False)

    def _navigation_loop(self):
        while not self.stop_event.is_set():
            self.nav_wake.wait(.02)
            self.nav_wake.clear()
            try:
                if self.physical_provider: self.physical_provider.update()
                if self.sensor_backend:
                    batch=self.sensor_backend.sample(time.monotonic())
                    if batch is not None: self._sensor_update(batch,session="explicit-test-backend",notify=False)
                state=self.motion.snapshot()
                with self.lock: observation=dict(self.vision.get("blueBall",{}))
                with self.settings_lock:
                    if observation.get("revision")!=self.vision_revision: observation={}
                if state["enabled"] and state["appMode"]=="opencv" and observation.get("observed_at") is not None:
                    self._fresh_observation(state,observation["observed_at"])
                health=self.bridge.snapshot() if self.bridge else None
                with self.nav_lock:
                    decision=self.navigation.step(state["appMode"],state["enabled"],state["session"],
                        self.sensors.snapshot(),observation,time.monotonic(),busy=state["busy"],
                        communication_ok=not health or health["connected"] and not health["fault"],generation=state["generation"])
                with self.lock:
                    self.vision["behavior"]=decision.state
                    self.vision["opencv"]=decision.reason or decision.state
                self.motion.events.record("autonomy",status=decision.state,reason=decision.reason)
                if state["enabled"] and decision.stop:
                    self.motion.stop(decision.reason,expected_generation=state["generation"],wait=False)
                elif decision.motion and self.motion.autonomous(state["appMode"],decision.motion,expected_generation=state["generation"]):
                    with self.nav_lock: self.navigation.accepted(decision.motion,time.monotonic())
            except Exception:
                logging.exception("Virtual autonomy failed")
                state=self.motion.snapshot()
                if state["enabled"]: self.motion.stop("Virtual autonomy worker fault",expected_generation=state["generation"],wait=False)

    def _bridge_guard(self):
        while not self.stop_event.wait(.05):
            state=self.motion.snapshot()
            health=self.bridge.snapshot()
            if state["enabled"] and (not health["connected"] or health["fault"]):
                self.motion.stop(health["fault"] or "Simulator disconnected; explicit enable required",
                                 expected_generation=state["generation"])

    def _fresh_observation(self, state, published_at):
        if time.monotonic() - published_at > .5:
            self.motion.stop("Stale vision result", expected_generation=state["generation"])
            return False
        return self.motion.vision_heartbeat(state["appMode"], state["generation"], published_at)

    def close(self):
        self.stop_event.set()
        self.nav_wake.set()
        if self.nav_worker.is_alive(): self.nav_worker.join(1)
        self.motion.close()
        self.display.close()
        if self.sensor_link: self.sensor_link.close()
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
    def invalid(error):
        runtime.motion.events.record("api_rejection",status="rejected",reason=request.path+": "+str(error))
        return jsonify(ok=False, error=str(error)), 400

    @app.errorhandler(RuntimeError)
    @app.errorhandler(TimeoutError)
    def unavailable(error):
        runtime.motion.events.record("api_rejection",status="rejected",reason=request.path+": "+str(error))
        return jsonify(ok=False, error=str(error)), 409

    @app.get("/")
    def index(): return send_from_directory(APP_DIR / "web", "index.html")

    @app.get("/<path:name>")
    def asset(name): return send_from_directory(APP_DIR / "web", name)

    @app.get("/api/state")
    def state(): return jsonify(runtime.state())

    @app.get("/api/vision")
    def vision_config(): return jsonify(ok=True,**runtime.vision_configuration())

    @app.post("/api/vision")
    def set_vision():
        return jsonify(ok=True,**runtime.update_vision(body(),request.cookies.get("quadruped_control")))

    @app.get("/api/mode")
    def mode(): return jsonify(ok=True, state=runtime.motion.snapshot())

    @app.post("/api/mode")
    def set_mode():
        data = body()
        mode = data.get("mode")
        if not isinstance(mode, str): raise ValueError("mode must be a string")
        mode = mode.strip().lower().replace("-", "_")
        if runtime.sensor_source=='physical_uno' and mode not in {'manual','idle','sensor_test'}:
            raise RuntimeError('Physical monitoring only; navigation clearance unavailable')
        if mode in {"explore","sensor_test","interaction"} and runtime.sensors is None:
            raise RuntimeError("Explicit virtual sensors are required")
        if mode == "hand_gesture" and runtime.sensors:
            raise RuntimeError("Phase 2 supports blue tracking; optional gesture control remains Phase 1 only")
        if runtime.sensors and mode not in {"manual","idle","sensor_test"} and runtime.sensors.snapshot()["fault"]:
            raise RuntimeError(runtime.sensors.snapshot()["fault"])
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
        if runtime.sensors and runtime.sensors.snapshot()["fault"]: raise RuntimeError(runtime.sensors.snapshot()["fault"])
        if runtime.sensors and any(t["pressed"] for t in runtime.sensors.snapshot()["touches"].values()):
            raise RuntimeError("Release virtual touch inputs before explicit enable")
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

    @app.post("/api/interaction")
    def interaction():
        data=body()
        generation=runtime.require_control(request.cookies.get("quadruped_control"))
        state=runtime.motion.snapshot()
        if not runtime.sensors or not runtime.actuators_simulated or state["appMode"]!="interaction" or not state["enabled"]:
            raise RuntimeError("Select virtual Interactions after explicit enable")
        if state["busy"] or state["stopping"]: raise RuntimeError("Motion or STOP pending")
        sensor=runtime.sensors.snapshot()
        if sensor["fault"] or sensor["front_m"]<=runtime.navigation.settings.caution_m:
            raise RuntimeError(sensor["fault"] or "Interaction obstacle clearance insufficient")
        with runtime.nav_lock:
            runtime.navigation.request_interaction(data.get("name"),state["session"],generation)
        runtime.nav_wake.set()
        runtime.motion.events.record("interaction",status="requested",reason=str(data.get("name")),generation=generation)
        return jsonify(ok=True,status="queued_intent",physical=False)

    @app.post("/api/servo")
    def servo():
        generation = runtime.require_control(request.cookies.get("quadruped_control"))
        data = body()
        runtime.motion.servo(data.get("channel"), data.get("pulse"), expected_generation=generation)
        return jsonify(ok=True)

    @app.post("/api/simulation/target")
    def synthetic_target():
        data=body()
        if not runtime.actuators_simulated or not runtime.camera.simulate:
            raise RuntimeError("Explicit synthetic camera and virtual actuators required")
        with runtime.owner_lock:
            if runtime.motion.snapshot()["enabled"] and request.cookies.get("quadruped_control")!=runtime.owner_token:
                raise RuntimeError("Another browser owns control")
            runtime.camera.set_synthetic_target(visible=data.get("visible"),color=data.get("color"),x=data.get("x"))
        runtime.motion.events.record("synthetic_input",status="fixture_changed",
            reason=str(data.get("color"))+" "+("visible" if data.get("visible") else "hidden"))
        return jsonify(ok=True,synthetic=True,physical=False)

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
    parser.add_argument("--vision-state",default=os.getenv("QUADRUPED_VISION_STATE","build/state/vision.json"))
    parser.add_argument("--simulator", help="Trusted simulator host; enables mandatory network lease")
    parser.add_argument("--simulator-port", type=int, default=7002)
    parser.add_argument("--virtual-sensors", action="store_true", help="Explicit Phase 2 virtual autonomy; simulator telemetry required")
    parser.add_argument("--navigation-config")
    parser.add_argument("--sensor-config")
    parser.add_argument('--sensor-source',choices=('none','virtual','test','physical_uno'))
    parser.add_argument('--sensor-port',help='Separate non-actuating Uno USB port; explicit selection required')
    parser.add_argument('--oled',choices=('off','mock','ssd1306'),default='off')
    parser.add_argument('--oled-address',type=lambda v:int(v,0),default=0x3c)
    parser.add_argument('--oled-bus',type=int,default=1)
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
                      simulator_host=args.simulator, simulator_port=args.simulator_port,
                      virtual_sensors=args.virtual_sensors,navigation_config=args.navigation_config,sensor_config=args.sensor_config,vision_state=args.vision_state,
                      sensor_source=args.sensor_source,sensor_port=args.sensor_port,
                      display_backend=make_display_backend(args.oled,args.oled_bus,args.oled_address))
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

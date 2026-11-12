"""Eight-joint CAD-visual PyBullet fixture. No physical hardware API exists here."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import time
from quadruped.bridge import TraceServer
from quadruped.virtual_uno import VirtualUno

MODEL=Path(__file__).resolve().parent/"model"


class SimulationFault(RuntimeError): pass


class World:
    def __init__(self,*,gui=False,free_base=False,parameters=None,position_gain=.1,target_rate=0.0):
        try: import pybullet as p
        except ImportError as error: raise RuntimeError("Install simulation/requirements.txt on the laptop") from error
        if not isinstance(position_gain,(float,int)) or isinstance(position_gain,bool) or not math.isfinite(position_gain) or not .01<=position_gain<=1:
            raise ValueError("Position gain must be .01..1 (simulation only)")
        if type(target_rate) not in (int,float) or not math.isfinite(target_rate) or not 0<=target_rate<=3:
            raise ValueError("Simulation smoothing rate must be 0..3 rad/s")
        self.target_rate=target_rate
        self.position_gain=position_gain
        self.p=p
        self.client=p.connect(p.GUI if gui else p.DIRECT)
        if self.client < 0:
            raise SimulationFault('PyBullet GUI connection unavailable' if gui else 'PyBullet DIRECT connection unavailable')
        self.gui=gui
        self.render_status=dict(renderer='TinyRenderer',guiRequested=gui,frames=0,error=None)
        self.fixed=not free_base
        self.parameters=json.loads(Path(parameters or MODEL/"parameters.json").read_text())
        self.frames=0
        self.max_joint_error=0.0
        self.max_active_error=0.0
        self.active_error_squared=0.0
        self.active_error_samples=0
        self.max_torque=0.0
        self.max_raw_jump=self.max_motor_jump=0.0
        self.contact_pairs={}
        self.measurement_start_step=0
        self.contact_count=0
        self.self_contacts=0
        self.fault=None
        try:
            for key in ("force_nm","friction","initial_height_m","max_velocity_rad_s","base_mass_kg","upper_mass_kg","lower_and_foot_mass_kg"):
                value=self.parameters[key]
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:
                    raise ValueError("Invalid model parameter: "+key)
            p.resetSimulation(physicsClientId=self.client)
            p.setGravity(0,0,-9.81,physicsClientId=self.client)
            p.setTimeStep(1/240,physicsClientId=self.client)
            p.setPhysicsEngineParameter(numSolverIterations=100,numSubSteps=4,physicsClientId=self.client)
            plane=p.createCollisionShape(p.GEOM_PLANE,physicsClientId=self.client)
            p.createMultiBody(0,plane,physicsClientId=self.client)
            self.robot=p.loadURDF(str(MODEL/"robot.urdf"),[0,0,self.parameters["initial_height_m"]],
                useFixedBase=self.fixed,flags=p.URDF_USE_SELF_COLLISION|p.URDF_USE_SELF_COLLISION_EXCLUDE_PARENT|p.URDF_USE_INERTIA_FROM_FILE,
                physicsClientId=self.client)
            indices={p.getJointInfo(self.robot,i,physicsClientId=self.client)[1].decode():i
                     for i in range(p.getNumJoints(self.robot,physicsClientId=self.client))}
            channels=self.parameters["channels"]
            if [item["channel"] for item in channels]!=list(range(8)) or len(indices)!=8:
                raise ValueError("Expected the eight firmware channels/joints")
            self.joints=[indices[item["joint"]] for item in channels]
            for index in [-1]+self.joints:
                label="chassis" if index==-1 else p.getJointInfo(self.robot,index,physicsClientId=self.client)[1].decode()
                mass=self.parameters["base_mass_kg" if index==-1 else "upper_mass_kg" if label.startswith("shoulder") else "lower_and_foot_mass_kg"]
                old=p.getDynamicsInfo(self.robot,index,physicsClientId=self.client)
                inertia=[value*mass/old[0] for value in old[2]] if old[0]>0 else old[2]
                if index==-1 and self.fixed: mass=0
                p.changeDynamics(self.robot,index,mass=mass,localInertiaDiagonal=inertia,
                                 lateralFriction=self.parameters["friction"],
                                 maxJointVelocity=self.parameters["max_velocity_rad_s"],physicsClientId=self.client)
            self.fixture_constraint=None
            self.fixture_position=[0,0,self.parameters["initial_height_m"]]
            self.fixture_orientation=[0,0,0,1]
            if self.fixed:
                # Explicit external fixture: changing link dynamics must not let the
                # nominally fixed base drift. This is not additional servo torque.
                self.fixture_constraint=p.createConstraint(self.robot,-1,-1,-1,p.JOINT_FIXED,[0,0,0],
                    [0,0,0],self.fixture_position,physicsClientId=self.client)
                p.changeConstraint(self.fixture_constraint,self.fixture_position,
                    jointChildFrameOrientation=self.fixture_orientation,maxForce=500,physicsClientId=self.client)
            self.targets=[0.0]*8
            self.motor_targets=[0.0]*8
            self.active_mask=0
            self.apply(dict(virtual=True,armed=False,activeMask=0,targets=[300]*8))
            if gui:
                p.resetDebugVisualizerCamera(.65,45,-25,[0,0,.12],physicsClientId=self.client)
        except Exception:
            p.disconnect(self.client)
            raise

    def start_measurement(self):
        """Begin an explicitly labeled experiment segment; preserve pose and gait state."""
        self.max_joint_error=self.max_active_error=self.active_error_squared=0.0
        self.active_error_samples=0
        self.max_torque=0.0
        self.contact_count=self.self_contacts=0
        self.measurement_start_step=self.frames
        self.max_raw_jump=self.max_motor_jump=0.0
        self.contact_pairs={}

    def set_fixture_pose(self,position,orientation):
        if self.fixture_constraint is None: raise ValueError("Only an explicitly fixed fixture can be repositioned")
        self.fixture_position=list(position)
        self.fixture_orientation=list(orientation)
        self.p.changeConstraint(self.fixture_constraint,self.fixture_position,
            jointChildFrameOrientation=self.fixture_orientation,maxForce=500,physicsClientId=self.client)
        self.p.resetBasePositionAndOrientation(self.robot,position,orientation,physicsClientId=self.client)
        self.p.resetBaseVelocity(self.robot,[0,0,0],[0,0,0],physicsClientId=self.client)

    def angle(self,channel,tick):
        item=self.parameters["channels"][channel]
        if type(tick) is not int or not item["min_tick"]<=tick<=item["max_tick"]:
            raise ValueError("Tick outside provisional mapping")
        lo,neutral,hi=item["min_tick"],item["neutral_tick"],item["max_tick"]
        if (not lo<neutral<hi or type(item["direction"]) is not int or item["direction"] not in (-1,1)
                or not item["min_angle_rad"]<0<item["max_angle_rad"]): raise ValueError("Invalid provisional mapping")
        ratio=(tick-neutral)/(hi-neutral if tick>=neutral else neutral-lo)
        result=ratio*(item["max_angle_rad"] if ratio>=0 else -item["min_angle_rad"])*item["direction"]
        if not math.isfinite(result) or not -1.2<=result<=1.2: raise ValueError("Angle outside URDF limits")
        return result

    def apply(self,frame):
        if frame.get("virtual") is not True or type(frame.get("armed")) is not bool:
            raise ValueError("Only explicit virtual frames accepted")
        ticks=frame.get("targets")
        mask=frame.get("activeMask")
        if not isinstance(ticks,list) or len(ticks)!=8 or type(mask) is not int or not 0<=mask<=255:
            raise ValueError("Invalid eight-joint trace")
        incoming=[self.angle(i,tick) for i,tick in enumerate(ticks)]
        old_mask=self.active_mask
        for channel,index in enumerate(self.joints):
            actual=self.p.getJointState(self.robot,index,physicsClientId=self.client)[0]
            active=bool(frame["armed"] and mask&(1<<channel))
            if active:
                previous=self.targets[channel] if old_mask&(1<<channel) else actual
                self.max_raw_jump=max(self.max_raw_jump,abs(incoming[channel]-previous))
                if self.target_rate:
                    if not old_mask&(1<<channel): self.motor_targets[channel]=actual
                else:
                    previous_motor=self.motor_targets[channel] if old_mask&(1<<channel) else actual
                    self.max_motor_jump=max(self.max_motor_jump,abs(incoming[channel]-previous_motor))
                    self.motor_targets[channel]=incoming[channel]
            else:
                # STOP removes force immediately and discards the interpolation residual.
                self.motor_targets[channel]=actual
        self.targets=incoming
        self.active_mask=mask if frame["armed"] else 0
        self._drive()

    def _drive(self):
        for channel,index in enumerate(self.joints):
            self.p.setJointMotorControl2(self.robot,index,self.p.POSITION_CONTROL,
                targetPosition=self.motor_targets[channel],positionGain=self.position_gain,
                force=self.parameters["force_nm"] if self.active_mask&(1<<channel) else 0,
                maxVelocity=self.parameters["max_velocity_rad_s"],physicsClientId=self.client)

    def step(self):
        if self.target_rate and self.active_mask:
            limit=self.target_rate/240
            for channel in range(8):
                if self.active_mask&(1<<channel):
                    delta=max(-limit,min(limit,self.targets[channel]-self.motor_targets[channel]))
                    self.max_motor_jump=max(self.max_motor_jump,abs(delta))
                    self.motor_targets[channel]+=delta
            self._drive()
        self.p.stepSimulation(physicsClientId=self.client)
        self.frames+=1
        position,orientation=self.p.getBasePositionAndOrientation(self.robot,physicsClientId=self.client)
        joints=[self.p.getJointState(self.robot,i,physicsClientId=self.client)[0] for i in self.joints]
        if not all(math.isfinite(v) for v in (*position,*orientation,*joints)) or max(map(abs,position))>10:
            self.fault="Numerical divergence"
        elif not self.fixed and (position[2]<.025 or max(map(abs,self.p.getEulerFromQuaternion(orientation)[:2]))>1.2):
            self.fault="Provisional free-base model fell or exceeded tilt limit"
        elif any(abs(value)>1.3 for value in joints):
            self.fault="Joint limit excursion"
        contacts=self.p.getContactPoints(bodyA=self.robot,physicsClientId=self.client)
        self.contact_count=max(self.contact_count,len(contacts))
        self.self_contacts=max(self.self_contacts,sum(c[1]==self.robot and c[2]==self.robot for c in contacts))
        for contact in contacts:
            if contact[1]!=self.robot or contact[2]!=self.robot: continue
            links=[]
            for index in sorted((contact[3],contact[4])):
                links.append("chassis" if index==-1 else self.p.getJointInfo(self.robot,index,physicsClientId=self.client)[12].decode())
            key=" / ".join(links)
            item=self.contact_pairs.setdefault(key,dict(samples=0,maxPenetrationM=0.0))
            item["samples"]+=1
            item["maxPenetrationM"]=max(item["maxPenetrationM"],max(0,-contact[8]))
        self.max_joint_error=max(self.max_joint_error,max(abs(a-b) for a,b in zip(joints,self.targets)))
        for channel,index in enumerate(self.joints):
            if self.active_mask&(1<<channel):
                error=abs(joints[channel]-self.targets[channel])
                self.max_active_error=max(self.max_active_error,error)
                self.active_error_squared+=error*error
                self.active_error_samples+=1
                torque=abs(self.p.getJointState(self.robot,index,physicsClientId=self.client)[3])
                self.max_torque=max(self.max_torque,torque)
        if self.fault:
            for index in self.joints:
                self.p.setJointMotorControl2(self.robot,index,self.p.VELOCITY_CONTROL,force=0,physicsClientId=self.client)
            raise SimulationFault(self.fault)
        return joints

    def diagnostics(self):
        position,orientation=self.p.getBasePositionAndOrientation(self.robot,physicsClientId=self.client)
        return dict(provisional=True,fixedBase=self.fixed,steps=self.frames,basePosition=list(position),
                    baseEuler=list(self.p.getEulerFromQuaternion(orientation)),jointCount=len(self.joints),
                    jointNames=[item["joint"] for item in self.parameters["channels"]],
                    maxJointErrorRad=self.max_joint_error,maxContactCount=self.contact_count,
                    maxSelfCollisionContacts=self.self_contacts,fault=self.fault,
                    physicalLocomotionValidated=False,solverIterations=100,subSteps=4,
                    modeledVelocityLimitRadS=self.parameters["max_velocity_rad_s"],positionGain=self.position_gain,
                    maxActiveJointErrorRad=self.max_active_error,measurementStartStep=self.measurement_start_step,
                    activeJointRmsErrorRad=math.sqrt(self.active_error_squared/self.active_error_samples) if self.active_error_samples else None,
                    maxAppliedMotorTorqueNm=self.max_torque,
                    currentJointPositions=[self.p.getJointState(self.robot,i,physicsClientId=self.client)[0] for i in self.joints],
                    currentJointTargets=list(self.targets),activeMask=self.active_mask,
                    smoothingRateRadS=self.target_rate,motorTargets=list(self.motor_targets),
                    maxRawTargetJumpRad=self.max_raw_jump,maxMotorTargetJumpRad=self.max_motor_jump,
                    selfContactPairs=dict(self.contact_pairs),
                    baseMassKg=self.p.getDynamicsInfo(self.robot,-1,physicsClientId=self.client)[0],
                    fixtureConstraint=self.fixture_constraint is not None,
                    rendering=dict(self.render_status),
                    fixturePositionErrorM=math.dist(position,self.fixture_position) if self.fixed else None)

    def render_bgr(self):
        import cv2
        import numpy as np
        view=self.p.computeViewMatrixFromYawPitchRoll([0,0,.12],.65,45,-25,0,2)
        projection=self.p.computeProjectionMatrixFOV(50,4/3,.01,10)
        _,_,rgba,_,_=self.p.getCameraImage(640,480,view,projection,renderer=self.p.ER_TINY_RENDERER,physicsClientId=self.client)
        image=np.array(rgba,dtype=np.uint8).reshape(480,640,4)
        result=cv2.cvtColor(image,cv2.COLOR_RGBA2BGR)
        try:
            validate_render(result)
        except SimulationFault as error:
            self.render_status['error']=str(error)
            raise
        self.render_status.update(frames=self.render_status['frames']+1,error=None)
        return result

    def capture(self,path):
        import cv2
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        if not cv2.imwrite(str(path),self.render_bgr()): raise RuntimeError("Capture write failed")

    def close(self):
        if self.p.isConnected(self.client): self.p.disconnect(self.client)


def validate_render(frame):
    """Reject missing/black/flat capture; this does not qualify a visible GUI."""
    import numpy as np
    if (frame is None or frame.shape!=(480,640,3) or frame.dtype!=np.uint8 or
            float(frame.max())<8 or float(frame.std())<1):
        raise SimulationFault('Simulation capture unavailable, black or flat')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headless",action="store_true")
    parser.add_argument("--free-base",action="store_true")
    parser.add_argument("--host",default="127.0.0.1")
    parser.add_argument("--port",type=int,default=7002)
    parser.add_argument("--steps",type=int,default=0)
    parser.add_argument("--parameters")
    parser.add_argument("--smoothing-rate",type=float,default=0.0,help="Explicit simulation-only target rate; 0 disables")
    parser.add_argument("--scenario",choices=("empty","single_obstacle","multiple_obstacles","narrow_passage","dead_end","target","sensor_failure","touch"))
    parser.add_argument("--navigation-proxy",action="store_true",help="Explicit kinematic proxy; never inferred walking physics")
    parser.add_argument("--show-rays",action="store_true")
    parser.add_argument("--sensor-noise",type=float,default=0.0)
    parser.add_argument("--sensor-latency",type=float,default=.02)
    parser.add_argument("--sensor-config")
    parser.add_argument("--ultrasonic-profiles",help="JSON with per-sensor origin/yaw/range/rate/noise/latency")
    parser.add_argument("--report")
    parser.add_argument("--capture")
    parser.add_argument("--record",help="Bounded 640x480 30 FPS offline simulation AVI (requires --steps)")
    parser.add_argument("--demo",choices=("stand","initial","forward","backward","turn_left","turn_right","greeting","tail_wag"))
    parser.add_argument("--arm-demo",action="store_true",help="Explicitly arm only the offline virtual demo")
    args=parser.parse_args()
    if args.demo and not args.arm_demo: parser.error("Offline demo requires explicit --arm-demo")
    if args.steps<0: parser.error("steps must be nonnegative")
    if args.record and not 1<=args.steps<=7200: parser.error("--record requires --steps 1..7200 (max 30 simulated seconds)")
    if args.navigation_proxy and (not args.scenario or args.free_base): parser.error("Proxy requires an explicit scenario and fixed-base fixture")
    world=World(gui=not args.headless,free_base=args.free_base,parameters=args.parameters,target_rate=args.smoothing_rate)
    server=None
    scene=None
    engine=None
    failed=False
    writer=None
    joint_log=None
    recorded_frames=0
    try:
        if args.record:
            import cv2
            path=Path(args.record)
            if path.suffix.lower() != ".avi": raise ValueError("--record requires .avi output")
            path.parent.mkdir(parents=True,exist_ok=True)
            writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*"MJPG"),30,(640,480))
            if not writer.isOpened(): raise RuntimeError("Simulation video writer could not open")
            joint_log=path.with_suffix('.joints.jsonl').open('w',encoding='utf-8')
        if args.scenario:
            from .environment import Scene
            from quadruped.sensors import SensorConfig
            profiles=json.loads(Path(args.ultrasonic_profiles).read_text()) if args.ultrasonic_profiles else None
            scene=Scene(world,args.scenario,proxy=args.navigation_proxy,show_rays=args.show_rays,
                        noise=args.sensor_noise,latency=args.sensor_latency,sensor_config=SensorConfig.load(args.sensor_config),profiles=profiles)
        if args.demo:
            engine=VirtualUno()
            engine.feed(b"HELLO\nARM 1\n")
            engine.feed(("MOVE 2 "+args.demo+"\n").encode())
        else: server=TraceServer(args.host,args.port,sensors=scene.telemetry if scene else None)
        # QPC on Windows: monotonic, with enough resolution for the 240 Hz step.
        # Python 3.11's Windows monotonic clock can have a 15.625 ms tick.
        started=time.perf_counter()
        while not args.steps or world.frames<args.steps:
            if not args.headless and scene and server:
                events=world.p.getKeyboardEvents(physicsClientId=world.client)
                if events.get(ord("r"),0)&world.p.KEY_WAS_TRIGGERED: scene.reset(server.receiver)
            if engine:
                engine.feed(b"PING\n")
                engine.advance()
                frame=engine.snapshot()
            else: frame=server.poll()
            if scene and not scene.advance(frame): raise SimulationFault("Navigation proxy collision guard")
            world.apply(frame)
            measured=world.step()
            if writer and world.frames%8==0:
                writer.write(world.render_bgr())
                joint_log.write(json.dumps(dict(step=world.frames,simulationTimeS=world.frames/240,
                    measuredJointPositionsRad=measured,requestedTargetsRad=list(world.targets),
                    motorTargetsRad=list(world.motor_targets),activeMask=world.active_mask))+'\n')
                recorded_frames+=1
            if not args.headless and world.frames%24==0:
                for i,index in enumerate(world.joints):
                    point=world.p.getLinkState(world.robot,index,physicsClientId=world.client)[0]
                    world.p.addUserDebugText(str(i),point,lifeTime=.12,physicsClientId=world.client)
            time.sleep(max(0,started+world.frames/240-time.perf_counter()))
    except KeyboardInterrupt: pass
    except SimulationFault as error:
        world.fault=str(error)
        failed=True
    finally:
        if writer: writer.release()
        if joint_log: joint_log.close()
        if engine:
            engine.feed(b'STOP 0\n')
            world.apply(engine.snapshot())
        evidence=world.diagnostics()
        if args.record: evidence["recording"]={"file":str(args.record),"format":"AVI MJPEG","fps":30,"frames":recorded_frames,"source":"PyBullet TinyRenderer; simulated only","measuredJointLog":str(Path(args.record).with_suffix('.joints.jsonl'))}
        if scene: evidence["environment"]=scene.diagnostics()
        if server: evidence["bridge"]=server.receiver.snapshot(); server.close()
        if engine: evidence["virtualUno"]=engine.snapshot()
        try:
            if args.capture: world.capture(args.capture)
        except Exception as error:
            failed=True
            evidence['captureError']=str(error)
        finally:
            evidence['rendering']=dict(world.render_status)
            world.close()
        if args.report:
            Path(args.report).parent.mkdir(parents=True,exist_ok=True)
            Path(args.report).write_text(json.dumps(evidence,indent=2)+"\n")
        print(json.dumps(evidence,sort_keys=True))
    if failed: raise SystemExit(2)


if __name__=="__main__": main()

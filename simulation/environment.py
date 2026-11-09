"""Known-geometry virtual worlds, range rays and optional kinematic navigation proxy."""
from collections import deque
from dataclasses import dataclass
import math
import random
import time
from quadruped.sensors import RANGE_IDS, TOUCH_IDS, CLEARANCE_IDS, number, SensorConfig

SCENARIOS=("empty","single_obstacle","multiple_obstacles","narrow_passage","dead_end","target","sensor_failure","touch")
LAYOUTS={
    "empty":[],
    "single_obstacle":[(.9,0,.1,.4)],
    "multiple_obstacles":[(.9,0,.1,.3),(1.7,.65,.2,.2),(2.1,-.7,.15,.4)],
    "narrow_passage":[(1,.27,1,.04),(1,-.27,1,.04),(2.2,0,.1,.5)],
    "dead_end":[(.45,0,.08,.6),(.1,.45,.7,.08),(.1,-.45,.7,.08),(-.45,0,.08,.6)],
    "target":[],
    "sensor_failure":[],
    "touch":[],
}


@dataclass(frozen=True)
class UltrasonicSettings:
    min_m: float=.02
    max_m: float=4.0
    rate_hz: float=10.0
    latency: float=.02
    noise_m: float=0.0
    origin: tuple=(.15,0,.02)
    yaw: float=0.0

    def __post_init__(self):
        if (not number(self.min_m,.001,10) or not number(self.max_m,.01,10) or self.min_m>=self.max_m
            or not number(self.rate_hz,1,50) or not number(self.latency,0,1)
            or not number(self.noise_m,0,1) or len(self.origin)!=3
            or not all(number(v,-2,2) for v in self.origin) or not number(self.yaw,-math.pi,math.pi)):
            raise ValueError("Invalid virtual ultrasonic configuration")


class SimulatedUltrasonicSensor:
    def __init__(self,identity,world,settings=None,*,seed=0):
        if identity not in RANGE_IDS: raise ValueError("Unknown virtual ultrasonic")
        self.identity,self.world=identity,world
        self.settings=settings or UltrasonicSettings(rate_hz=5 if identity=="urm37" else 10)
        self.random=random.Random(seed)
        self.mode="normal"
        self.next_poll=0.0
        self.pending=deque(maxlen=8)
        self.current=None
        self.last_rays=[]

    def sample(self,now):
        if now>=self.next_poll:
            self.next_poll=now+1/self.settings.rate_hz
            position,orientation=self.world.p.getBasePositionAndOrientation(self.world.robot,physicsClientId=self.world.client)
            body_yaw=self.world.p.getEulerFromQuaternion(orientation)[2]
            x,y,z=self.settings.origin
            origin=(position[0]+x*math.cos(body_yaw)-y*math.sin(body_yaw),
                    position[1]+x*math.sin(body_yaw)+y*math.cos(body_yaw),position[2]+z)
            rays=[]
            for offset in (-.1,0,.1):
                yaw=body_yaw+self.settings.yaw+offset
                end=(origin[0]+self.settings.max_m*math.cos(yaw),origin[1]+self.settings.max_m*math.sin(yaw),origin[2])
                hit=self.world.p.rayTest(origin,end,physicsClientId=self.world.client)[0]
                rays.append((origin,end,hit))
            self.last_rays=rays
            blocked_self=any(hit[0]==self.world.robot for _,_,hit in rays)
            value=min(self.settings.max_m*hit[2] if hit[0]>=0 else self.settings.max_m for _,_,hit in rays)
            value+=self.random.uniform(-self.settings.noise_m,self.settings.noise_m)
            record=dict(id=self.identity,kind="range",value=value,valid=not blocked_self,error="Self obstruction" if blocked_self else None)
            if self.mode in ("invalid","disconnected","no_echo"): record.update(valid=False,value=None,error=self.mode)
            if self.mode=="out_of_range": record["value"]=self.settings.max_m+1
            capture=now-1 if self.mode=="timeout" else now
            if self.mode!="missing": self.pending.append((now+self.settings.latency,capture,record))
            else: self.current=None
        while self.pending and self.pending[0][0]<=now:
            _,capture,record=self.pending.popleft()
            self.current=(capture,record)
        if self.current is None: return None
        captured,record=self.current
        return dict(record,age=max(0,now-captured))


class SimulatedTouchSensor:
    def __init__(self,identity):
        if identity not in TOUCH_IDS: raise ValueError("Unknown touch")
        self.identity=identity
        self.pressed=False
        self.connected=True

    def sample(self,now):
        return dict(id="touch_"+self.identity,kind="touch",value=self.pressed if self.connected else None,
                    valid=self.connected,age=0.0,error=None if self.connected else "disconnected")


class Scene:
    """Sensor rays use PyBullet. Swept-clearance is extra simulator geometry evidence."""
    def __init__(self,world,scenario="empty",*,seed=0,clock=time.monotonic,latency=.02,noise=0.0,proxy=False,show_rays=False,sensor_config=None,profiles=None):
        if scenario not in SCENARIOS: raise ValueError("Unknown scenario")
        if proxy and not world.fixed: raise ValueError("Navigation proxy requires the fixed-base articulated fixture")
        config=sensor_config or SensorConfig()
        profiles=profiles or {}
        if not isinstance(profiles,dict) or set(profiles)-set(RANGE_IDS): raise ValueError("Invalid ultrasonic profiles")
        self.world,self.scenario,self.clock=world,scenario,clock
        self.reset_options=dict(seed=seed,clock=clock,latency=latency,noise=noise,proxy=proxy,show_rays=show_rays,sensor_config=config,profiles=profiles)
        self.proxy,self.show_rays=proxy,show_rays
        self.boxes=[]
        self.bodies=[]
        self.debug_lines=[]
        self.seq=0
        self.created=clock()
        self.last_batch=None
        self.next_batch=0.0
        self.proxy_contacts=0
        self.proxy_pose=[0.,0.,0.]
        self.trace=deque(maxlen=256)
        self.ultrasonic={k:SimulatedUltrasonicSensor(k,world,UltrasonicSettings(
            **dict(dict(rate_hz=config.rate_hz,min_m=config.min_m,max_m=config.max_m,latency=latency,noise_m=noise),**profiles.get(k,{}))),seed=seed+i) for i,k in enumerate(RANGE_IDS)}
        self.touches={k:SimulatedTouchSensor(k) for k in TOUCH_IDS[:config.touch_count]}
        # Walls are finite known static geometry; robot self-collision remains enabled.
        for box in [(3,0,.08,2),(0,2,3,.08),(0,-2,3,.08),(-1,0,.08,2)]+LAYOUTS[scenario]:
            self.add_box(*box)
        self.target=None
        if scenario=="target":
            p=world.p
            shape=p.createCollisionShape(p.GEOM_SPHERE,radius=.08,physicsClientId=world.client)
            visual=p.createVisualShape(p.GEOM_SPHERE,radius=.08,rgbaColor=[0,0,1,1],physicsClientId=world.client)
            self.target=p.createMultiBody(0,shape,visual,[1.5,0,.25],physicsClientId=world.client)
            self.bodies.append(self.target)
            self.boxes.append((1.5,0,.08,.08))
        if scenario=="sensor_failure": self.ultrasonic["urm37"].mode="disconnected"

    def reset(self,receiver):
        """Owner-thread reset: new transport epoch, disarmed output, identical seeded scene."""
        receiver.reset()
        world=self.world
        for body in self.bodies: world.p.removeBody(body,physicsClientId=world.client)
        position=[0,0,world.parameters["initial_height_m"]]
        if world.fixed: world.set_fixture_pose(position,[0,0,0,1])
        else:
            world.p.resetBasePositionAndOrientation(world.robot,position,[0,0,0,1],physicsClientId=world.client)
            world.p.resetBaseVelocity(world.robot,[0,0,0],[0,0,0],physicsClientId=world.client)
        for index in world.joints: world.p.resetJointState(world.robot,index,0,0,physicsClientId=world.client)
        world.apply(dict(virtual=True,armed=False,activeMask=0,targets=[300]*8))
        world.fault=None
        world.start_measurement()
        scenario,options=self.scenario,self.reset_options
        self.__init__(world,scenario,**options)

    def add_box(self,x,y,hx,hy):
        p=self.world.p
        collision=p.createCollisionShape(p.GEOM_BOX,halfExtents=[hx,hy,.3],physicsClientId=self.world.client)
        visual=p.createVisualShape(p.GEOM_BOX,halfExtents=[hx,hy,.3],rgbaColor=[.6,.3,.2,1],physicsClientId=self.world.client)
        body=p.createMultiBody(0,collision,visual,[x,y,.3],physicsClientId=self.world.client)
        self.boxes.append((x,y,hx,hy))
        self.bodies.append(body)
        return body

    def clear_circle(self,x,y,radius=.25):
        for bx,by,hx,hy in self.boxes:
            dx=max(abs(x-bx)-hx,0)
            dy=max(abs(y-by)-hy,0)
            if dx*dx+dy*dy<=radius*radius: return False
        return True

    def clearance(self):
        position,orientation=self.world.p.getBasePositionAndOrientation(self.world.robot,physicsClientId=self.world.client)
        x,y=position[:2]
        yaw=self.world.p.getEulerFromQuaternion(orientation)[2]
        turn=self.clear_circle(x,y,.27)
        forward=all(self.clear_circle(x+distance*math.cos(yaw),y+distance*math.sin(yaw),.25) for distance in (0,.08,.16))
        reverse=all(self.clear_circle(x-distance*math.cos(yaw),y-distance*math.sin(yaw),.25) for distance in (0,.08,.16))
        return dict(sweep_forward=forward,sweep_left=turn,sweep_right=turn,sweep_reverse=reverse)

    def telemetry(self):
        now=self.clock()
        if now>=self.next_batch:
            self.next_batch=now+.05
            self.seq+=1
            if self.scenario=="touch": self.touches["head"].pressed=1.0<=now-self.created<1.2
            records=[record for sensor in self.ultrasonic.values() if (record:=sensor.sample(now)) is not None]
            records += [sensor.sample(now) for sensor in self.touches.values()]
            records += [dict(id=k,kind="clearance",value=value,valid=True,age=0.0) for k,value in self.clearance().items()]
            self.last_batch=dict(schema=1,seq=self.seq,observations=records)
            self.batch_at=now
            if self.show_rays:
                for sensor in self.ultrasonic.values():
                    for start,end,hit in sensor.last_rays:
                        self.world.p.addUserDebugLine(start,hit[3] if hit[0]>=0 else end,[1,0,0],lifeTime=.12,physicsClientId=self.world.client)
        # Preserve acquisition age even if networking polls faster than sensors.
        return dict(self.last_batch,observations=[dict(r,age=r["age"]+max(0,now-self.batch_at)) for r in self.last_batch["observations"]])

    def advance(self,frame,dt=1/240):
        if not number(dt,.0001,.02): raise ValueError("Bounded simulation step required")
        if self.proxy and frame.get("armed") and frame.get("activeMask"):
            p=self.world.p
            position,orientation=p.getBasePositionAndOrientation(self.world.robot,physicsClientId=self.world.client)
            yaw=p.getEulerFromQuaternion(orientation)[2]
            motion=frame.get("activeMotion")
            velocity=.06 if motion=="forward" else -.04 if motion=="backward" else 0
            turn=.35 if motion=="turn_left" else -.35 if motion=="turn_right" else 0
            x=self.proxy_pose[0]+velocity*math.cos(self.proxy_pose[2])*dt
            y=self.proxy_pose[1]+velocity*math.sin(self.proxy_pose[2])*dt
            if not self.clear_circle(x,y):
                self.proxy_contacts+=1
                return False
            yaw=self.proxy_pose[2]+turn*dt
            self.proxy_pose=[x,y,yaw]
            self.world.set_fixture_pose([x,y,self.world.parameters["initial_height_m"]],p.getQuaternionFromEuler([0,0,yaw]))
        if self.world.frames%24==0:
            actual=[self.world.p.getJointState(self.world.robot,i,physicsClientId=self.world.client)[0] for i in self.world.joints]
            pose=self.world.p.getBasePositionAndOrientation(self.world.robot,physicsClientId=self.world.client)[0]
            self.trace.append(dict(step=self.world.frames,pose=list(pose),targets=list(frame["targets"]),
                                   actual=actual,errors=[a-b for a,b in zip(actual,self.world.targets)],
                                   motion=frame.get("activeMotion"),behavior=frame.get("behavior"),armed=frame["armed"]))
        return True

    def diagnostics(self):
        return dict(scenario=self.scenario,navigationProxy=self.proxy,proxySpeedMps=.06 if self.proxy else None,
                    proxyContacts=self.proxy_contacts,obstacles=len(self.boxes),sensors=self.telemetry(),trace=list(self.trace),
                    physicalLocomotionValidated=False)

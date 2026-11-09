"""Deterministic visual decisions; this module never sends actuator commands."""
from dataclasses import dataclass, field
from collections import deque
import json
import math


@dataclass(frozen=True)
class VisionSettings:
    hsv_lower: tuple = (95,70,30)
    hsv_upper: tuple = (140,255,255)
    enter_error: float = .32
    exit_error: float = .20
    min_frames: int = 2
    loss_seconds: float = .35
    max_age: float = .5
    command_period: float = .6
    search_enabled: bool = False
    search_seconds: float = 2.0

    def __post_init__(self):
        for triple in (self.hsv_lower,self.hsv_upper):
            if len(triple)!=3 or any(type(v) is not int or not 0<=v<=limit for v,limit in zip(triple,(179,255,255))):
                raise ValueError("Invalid HSV triple")
        if any(a>b for a,b in zip(self.hsv_lower,self.hsv_upper)): raise ValueError("HSV lower exceeds upper")
        for name in ("enter_error","exit_error","loss_seconds","max_age","command_period","search_seconds"):
            value=getattr(self,name)
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:
                raise ValueError(f"Invalid {name}")
        if not 0<self.exit_error<self.enter_error<1: raise ValueError("Require exit < enter < 1")
        if type(self.min_frames) is not int or not 1<=self.min_frames<=30: raise ValueError("Invalid persistence")
        if type(self.search_enabled) is not bool: raise ValueError("search_enabled must be boolean")

    @classmethod
    def load(cls,path):
        if not path: return cls()
        with open(path,encoding="utf-8") as stream: data=json.load(stream)
        for key in ("hsv_lower","hsv_upper"):
            if key in data: data[key]=tuple(data[key])
        return cls(**data)


@dataclass(frozen=True)
class Decision:
    state: str
    motion: str | None = None
    inhibit: bool = False
    reason: str = ""


class Behavior:
    def __init__(self,settings=None):
        self.settings=settings or VisionSettings()
        self.transitions=deque(maxlen=64)
        self.reset(0.0)

    def reset(self,now):
        self.state="IDLE"
        self.started=now
        self.last_seen=None
        self.candidate=None
        self.persistence=0
        self.last_request=-1e9
        self.last_motion=None

    def _result(self,state,now,motion=None,inhibit=False,reason=""):
        if state!=self.state:
            self.transitions.append(dict(at=now,previous=self.state,state=state,reason=reason))
            self.state=state
        if motion is not None and now-self.last_request<self.settings.command_period:
            motion=None
        if motion=="stand" and self.last_motion=="stand": motion=None
        return Decision(state,motion,inhibit,reason)

    def accepted(self,motion,now):
        self.last_motion=motion
        self.last_request=now

    def step(self,observation,now,*,enabled=True,manual=False,stopped=False,obstacle=False):
        if stopped: return self._result("STOPPED",now,reason="Explicit stop or latched fault")
        if obstacle: return self._result("OBSTACLE_BLOCKED",now,inhibit=True,reason="Virtual obstacle")
        if manual: return self._result("MANUAL_OVERRIDE",now)
        if not observation or not isinstance(observation.get("observed_at"),(float,int)):
            return self._result("CAMERA_FAULT",now,inhibit=enabled,reason="No valid observation")
        age=now-observation["observed_at"]
        if not math.isfinite(age) or not 0<=age<=self.settings.max_age:
            return self._result("CAMERA_FAULT",now,inhibit=enabled,reason="Stale observation")
        if not enabled: return self._result("IDLE",now)
        if not observation.get("detected"):
            self.persistence=0
            self.candidate=None
            lost=now-(self.last_seen if self.last_seen is not None else self.started)
            if lost<self.settings.loss_seconds:
                return self._result("TARGET_LOST",now,motion="stand",reason="Waiting for target-loss deadline")
            if self.settings.search_enabled and lost<self.settings.loss_seconds+self.settings.search_seconds:
                return self._result("SEARCHING",now,motion="turn_right",reason="Explicit bounded virtual search")
            return self._result("TARGET_LOST",now,inhibit=True,reason="Target lost; virtual motion inhibited")
        error=observation.get("offset")
        if isinstance(error,bool) or not isinstance(error,(int,float)) or not math.isfinite(error) or abs(error)>1:
            return self._result("CAMERA_FAULT",now,inhibit=True,reason="Invalid target error")
        self.last_seen=now
        if self.state=="TARGET_LEFT" and error < -self.settings.exit_error: target="TARGET_LEFT"
        elif self.state=="TARGET_RIGHT" and error > self.settings.exit_error: target="TARGET_RIGHT"
        else: target="TARGET_LEFT" if error < -self.settings.enter_error else "TARGET_RIGHT" if error > self.settings.enter_error else "TARGET_CENTER"
        self.persistence=self.persistence+1 if target==self.candidate else 1
        self.candidate=target
        if self.persistence<self.settings.min_frames:
            return self._result(self.state,now,motion="stand",reason="Detection persistence")
        return self._result(target,now,motion={"TARGET_LEFT":"turn_left","TARGET_RIGHT":"turn_right","TARGET_CENTER":"stand"}[target])

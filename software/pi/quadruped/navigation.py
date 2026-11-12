"""Deterministic virtual policy. Only the existing MotionController executes decisions."""
from collections import deque
from dataclasses import dataclass
import json
import logging
from .autonomy import Behavior, VisionSettings
from .sensors import number, TWO_TOUCH_PROFILE


@dataclass(frozen=True)
class NavigationSettings:
    blocked_m: float=.35
    caution_m: float=.60
    hysteresis_m: float=.05
    command_period: float=1.25
    recovery_seconds: float=.6
    max_recovery_attempts: int=2
    touch_seconds: float=2.0
    exploration_seconds: float=30.0

    def __post_init__(self):
        for key in ("blocked_m","caution_m","hysteresis_m","command_period","recovery_seconds","touch_seconds","exploration_seconds"):
            if not number(getattr(self,key),.001,120): raise ValueError("Invalid navigation "+key)
        if not self.blocked_m+self.hysteresis_m<self.caution_m: raise ValueError("Clearance ordering")
        if type(self.max_recovery_attempts) is not int or not 0<=self.max_recovery_attempts<=5:
            raise ValueError("Invalid recovery attempt count")

    @classmethod
    def load(cls,path):
        if not path: return cls()
        with open(path,encoding="utf-8") as stream: return cls(**json.load(stream))


@dataclass(frozen=True)
class NavigationDecision:
    state: str
    motion: str | None=None
    stop: bool=False
    reason: str=""


def clearance(snapshot,key):
    obs=snapshot["observations"].get(key)
    return bool(obs and obs["valid"] and obs["measurement"] is True)


def physical_gesture_profile(snapshot):
    return (snapshot.get('source')=='physical_uno' and snapshot.get('touchProfile')==TWO_TOUCH_PROFILE
            and snapshot.get('configuredTouchCount')==2)


def motion_inhibition(snapshot,motion,settings,*,virtual_touch_gesture=False):
    """Independent guard also used immediately before serial admission."""
    if snapshot["fault"]: return snapshot["fault"]
    touches=snapshot["touches"]
    pressed=[k for k,v in touches.items() if v["pressed"]]
    if len(pressed)>1: return "Simultaneous touch contacts"
    if any(k in pressed for k in ("touch_left","touch_right","touch_body")): return "Body safety contact"
    if 'touch_front_bottom' in pressed and not (virtual_touch_gesture and physical_gesture_profile(snapshot)
                                                and motion in (None,'none','stand')):
        return 'Front-bottom protective contact; only explicit virtual gesture placeholders permit this input'
    distance=snapshot["front_m"]
    if virtual_touch_gesture and physical_gesture_profile(snapshot) and distance<=settings.caution_m:
        return 'Virtual placeholder clearance inhibited'
    if motion=="forward" and distance<=settings.caution_m: return "Forward clearance below caution threshold"
    if motion=="forward" and not clearance(snapshot,"sweep_forward"): return "No fresh forward footprint clearance evidence"
    if motion in ("turn_left","turn_right"):
        if not clearance(snapshot,"sweep_"+motion.split("_")[1]): return "No fresh swept-turn clearance evidence"
    if motion=="backward" and not clearance(snapshot,"sweep_reverse"): return "No fresh reverse clearance evidence"
    if motion in ("greeting","tail_wag","servo") and distance<=settings.caution_m:
        return "Interaction clearance inhibited"
    return None


class Navigation:
    def __init__(self,settings=None,vision_settings=None):
        self.settings=settings or NavigationSettings()
        self.tracker=Behavior(vision_settings or VisionSettings())
        self.transitions=deque(maxlen=128)
        self.context=None
        self.attempts=0  # total process budget; STOP/re-arm cannot silently replenish it
        self.state="IDLE"
        self.obstacle="UNKNOWN"
        self.reason="Explicit virtual mode required"
        self.last_motion=None
        self.last_request=-1e9
        self.deadline=None
        self.action=None
        self.action_sent=False
        self.started=0.0
        self.last_event=0
        self.pending_interaction=None
        self.touch_gesture=None

    def request_interaction(self,name,session,generation):
        actions={"attention":"stand","greeting":"greeting","tail_wag":"tail_wag","neutral":"initial"}
        if not isinstance(name,str) or name not in actions: raise ValueError("Unsupported interaction")
        if self.pending_interaction is not None or self.deadline is not None:
            raise RuntimeError("Interaction already pending or active")
        self.pending_interaction=(session,generation,actions[name])

    def _result(self,state,now,motion=None,stop=False,reason=""):
        if stop and self.touch_gesture and self.touch_gesture['status'] in ('virtual_placeholder_requested','virtual_placeholder_dispatched'):
            self.touch_gesture={**self.touch_gesture,'status':'complete_disarmed_recovery_required' if 'action complete' in reason else 'cancelled_fault_or_stop'}
        if state!=self.state:
            logging.info("Virtual autonomy %s -> %s: %s",self.state,state,reason)
            self.transitions.append(dict(at=now,previous=self.state,state=state,reason=reason))
        self.state,self.reason=state,reason
        return NavigationDecision(state,motion,stop,reason)

    def accepted(self,motion,now):
        self.last_motion,self.last_request=motion,now
        self.tracker.accepted(motion,now)
        if motion==self.action: self.action_sent=True
        if self.touch_gesture and motion==self.action:
            self.touch_gesture={**self.touch_gesture,'status':'virtual_placeholder_dispatched'}

    def snapshot(self):
        return dict(virtual=True,state=self.state,obstacle=self.obstacle,reason=self.reason,
                    touchGesture=self.touch_gesture,
                    lastRequestedMotion=self.last_motion,recoveryAttempts=self.attempts,
                    deadline=self.deadline,transitions=list(self.transitions))

    def step(self,mode,enabled,session,sensors,observation,now,*,busy=False,communication_ok=True,generation=None):
        two_touch=physical_gesture_profile(sensors)
        context=(mode,session,sensors.get('session')) if two_touch else (mode,session)
        if context!=self.context:
            self.context=context
            self.deadline=self.action=None
            self.action_sent=False
            if self.touch_gesture and self.touch_gesture['status'] in ('virtual_placeholder_requested','virtual_placeholder_dispatched'):
                self.touch_gesture={**self.touch_gesture,'status':'cancelled_context_change'}
            self.started=now
            self.last_request=-1e9
            self.last_motion=None
            self.last_event=max((e["seq"] for e in sensors["events"]),default=self.last_event)
            self.tracker.reset(now)
        if self.pending_interaction and (mode!="interaction" or not enabled or self.pending_interaction[:2]!=(session,generation)):
            self.pending_interaction=None
        if not enabled:
            return self._result("IDLE" if mode=="idle" else "EMERGENCY_STOP",now,reason="Disarmed; explicit enable required")
        if not communication_ok: return self._result("EMERGENCY_STOP",now,stop=True,reason="Simulator communication fault")
        if sensors["fault"]: return self._result("SENSOR_FAULT",now,stop=True,reason=sensors["fault"])
        reason=motion_inhibition(sensors,"stand",self.settings,virtual_touch_gesture=two_touch and mode=='interaction')
        if reason:
            if two_touch and reason=='Simultaneous touch contacts':
                self.last_event=max((e['seq'] for e in sensors['events']),default=self.last_event)
                self.touch_gesture=dict(status='rejected_simultaneous',request=None,physicalCalibration='PENDING')
            return self._result("EMERGENCY_STOP",now,stop=True,reason=reason)
        if mode=="manual": return self._result("MANUAL_OVERRIDE",now)
        if mode in ("idle","sensor_test"): return self._result("IDLE" if mode=="idle" else "READY",now,reason="Observation only")
        distance=sensors["front_m"]
        if distance<=self.settings.blocked_m: self.obstacle="BLOCKED"
        elif distance<=self.settings.caution_m or (self.obstacle in ("CAUTION","BLOCKED") and distance<self.settings.caution_m+self.settings.hysteresis_m):
            self.obstacle="CAUTION"
        else: self.obstacle="CLEAR"
        if self.deadline is not None:
            reason=motion_inhibition(sensors,self.action,self.settings,virtual_touch_gesture=two_touch and mode=='interaction')
            if reason or self.obstacle!="CLEAR" and self.action in ("greeting","tail_wag"):
                return self._result("OBSTACLE_BLOCKED",now,stop=True,reason=reason or "Obstacle during interaction")
            if now>=self.deadline:
                return self._result(self.state,now,stop=True,reason="Bounded virtual action complete; explicit enable required")
            return self._result(self.state,now,self.action if not self.action_sent and not busy else None,reason="Bounded action active")
        if self.obstacle=="BLOCKED":
            # A blocked moving robot must STOP before a different maneuver.
            if busy: return self._result("OBSTACLE_BLOCKED",now,stop=True,reason="Obstacle preempts active movement")
            if mode=="explore" and self.attempts<self.settings.max_recovery_attempts:
                direction=next((d for d in ("left","right") if clearance(sensors,"sweep_"+d)),None)
                if direction:
                    self.attempts+=1
                    self.action="turn_"+direction
                    self.deadline=now+self.settings.recovery_seconds
                    return self._result("RECOVERY",now,self.action,reason="Additional swept-volume evidence permits one bounded virtual turn")
            return self._result("OBSTACLE_BLOCKED",now,stop=True,reason="Blocked; no qualified recovery evidence or budget")
        if self.obstacle=="CAUTION":
            return self._result("OBSTACLE_CAUTION",now,stop=True,reason="Conservative caution policy inhibits navigation")
        if mode=="interaction":
            if two_touch:
                # No physical pose angles are known. Only the existing virtual
                # stand routine is an explicit, bounded placeholder, never sit/bow qualification.
                for event in sensors['events']:
                    if event['seq']<=self.last_event: continue
                    self.last_event=event['seq']
                    if not event['pressed']: continue
                    if event['id'] not in ('touch_back','touch_front_bottom'): continue
                    request='REAR_LOWER' if event['id']=='touch_back' else 'FRONT_LOWER'
                    self.touch_gesture=dict(sensor=event['id'],request=request,eventSeq=event['seq'],
                        status='virtual_placeholder_requested',motion='stand',physicalCalibration='PENDING',
                        note='Neutral virtual stand placeholder; does not implement measured sit or bow geometry')
                    self.action='stand'
                    self.deadline=now+self.settings.touch_seconds
                    return self._result('TOUCH_GESTURE_PLACEHOLDER',now,'stand',
                        reason=request+' request: bounded virtual stand placeholder; calibration pending')
                return self._result('READY',now,reason='Two-touch virtual placeholders explicitly selected; no walking or physical output')
            if self.pending_interaction:
                _,_,self.action=self.pending_interaction
                self.pending_interaction=None
                self.deadline=now+self.settings.touch_seconds
                return self._result("PERSONALITY",now,self.action,reason="Explicit bounded virtual interaction")
            return self._result("READY",now,reason="Choose one explicit interaction")
        for event in sensors["events"]:
            if event["seq"]<=self.last_event: continue
            self.last_event=event["seq"]
            if event["pressed"] and event["id"] in ("touch_head","touch_back"):
                self.action="greeting" if event["id"]=="touch_head" else "tail_wag"
                self.deadline=now+self.settings.touch_seconds
                return self._result("TOUCH_REACTION",now,self.action,reason="One bounded cancellable virtual interaction")
        if mode=="opencv":
            decision=self.tracker.step(observation,now)
            if decision.inhibit:
                return self._result("CAMERA_FAULT" if decision.state=="CAMERA_FAULT" else "TARGET_LOST",now,stop=True,reason=decision.reason)
            motion=decision.motion
            reason=motion_inhibition(sensors,motion,self.settings) if motion else None
            if reason: return self._result("OBSTACLE_BLOCKED",now,stop=True,reason=reason)
            return self._result("TARGET_TRACKING" if decision.state.startswith("TARGET_") and decision.state!="TARGET_LOST" else decision.state,
                                now,motion,reason=decision.reason)
        if mode=="explore":
            reason=motion_inhibition(sensors,"forward",self.settings)
            if reason: return self._result("OBSTACLE_BLOCKED",now,stop=True,reason=reason)
            if now-self.started>=self.settings.exploration_seconds:
                return self._result("IDLE",now,stop=True,reason="Exploration session budget expired")
            return self._result("EXPLORING",now,"forward" if now-self.last_request>=self.settings.command_period and not busy else None,
                                reason="Fresh front clearance; one gait at a time")
        return self._result("IDLE",now,stop=True,reason="Unsupported virtual autonomy mode")

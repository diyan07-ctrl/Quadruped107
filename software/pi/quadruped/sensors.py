"""Unified bounded observations. No GPIO, I2C, serial telemetry or hardware drivers."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass, asdict
import math
import json
import threading
import time
from typing import Protocol

TOUCH_IDS=("head","back","left","right","body")
RANGE_IDS=("urm37","hcsr04")
CLEARANCE_IDS=("sweep_forward","sweep_left","sweep_right","sweep_reverse")


def number(value,low,high):
    return type(value) in (int,float) and math.isfinite(value) and low<=value<=high


@dataclass(frozen=True)
class SensorConfig:
    min_m: float=.02
    max_m: float=4.0
    rate_hz: float=10.0
    timeout: float=.3
    expiration: float=.3
    debounce: float=.03
    stuck_seconds: float=2.0
    conflict_m: float=.2
    touch_count: int=5

    def __post_init__(self):
        for key in ("min_m","max_m","rate_hz","timeout","expiration","debounce","stuck_seconds","conflict_m"):
            if not number(getattr(self,key),.001,120): raise ValueError("Invalid sensor "+key)
        if not self.min_m<self.max_m or not self.debounce<self.stuck_seconds:
            raise ValueError("Invalid sensor limits")
        if type(self.touch_count) is not int or not 3<=self.touch_count<=5:
            raise ValueError("Require three to five virtual touches")

    @classmethod
    def load(cls,path):
        if not path: return cls()
        with open(path,encoding="utf-8") as stream: return cls(**json.load(stream))


@dataclass(frozen=True)
class SensorObservation:
    sensor_id: str
    kind: str
    observed_at: float
    measurement: float | bool | None
    unit: str
    valid: bool
    error: str | None=None
    sender_age: float=0.0
    source_seq: int | None=None
    source_sampled_at: float | None=None

    def snapshot(self,now,expiration):
        age=now-self.observed_at
        fresh=0<=age<=expiration
        valid=self.valid and fresh
        return dict(id=self.sensor_id,kind=self.kind,measurement=self.measurement,unit=self.unit,
                    age=max(0,age),fresh=fresh,valid=valid,
                    health="OK" if valid else "STALE" if not fresh else "INVALID",
                    error=self.error if fresh else "Observation expired",virtual=True)


class SensorBackend(Protocol):
    def sample(self,now:float) -> dict: ...


class SensorManager:
    """One atomic latest batch; sender age + round-trip age bound, never receive-time relabeling."""
    def __init__(self,config=None,*,clock=time.monotonic,source='virtual'):
        if source not in {'virtual','physical_uno','test'}: raise ValueError('Unknown sensor source')
        self.source=source
        self.config=config or SensorConfig()
        self.clock=clock
        self.lock=threading.RLock()
        self.session=None
        self.seq=-1
        self.observations={}
        self.events=deque(maxlen=64)
        self.event_seq=0
        self.touch={}
        self.rejected=0
        self.last_received=None
        self.last_transport_age=0.0
        self.rejection_reasons={}
        self.recent_batches=deque(maxlen=32)
        self.last_fault=None
        self.fault_events=deque(maxlen=8)
        self.was_fault=False

    @property
    def registry(self):
        return {**{k:"range" for k in RANGE_IDS},**{"touch_"+k:"touch" for k in TOUCH_IDS[:self.config.touch_count]},
                **{k:"clearance" for k in CLEARANCE_IDS}}

    def reset(self,session=None):
        with self.lock:
            self.session=session
            self.seq=-1
            self.observations.clear()
            self.events.clear()
            self.touch.clear()
            self.last_received=None
            self.was_fault=False

    def ingest(self,batch,*,session="fixture",transport_age=0.0):
        now=self.clock()
        try:
            if not number(transport_age,0,self.config.expiration): raise ValueError("Old transport")
            if not isinstance(batch,dict) or type(batch.get("schema")) is not int or batch["schema"]!=1:
                raise ValueError("Sensor schema")
            seq=batch.get("seq")
            records=batch.get("observations")
            if type(seq) is not int or not 0<=seq<2**31 or not isinstance(records,list) or len(records)>16:
                raise ValueError("Sensor batch bounds")
            parsed={}
            for record in records:
                if not isinstance(record,dict): raise ValueError("Observation object")
                identity=record.get("id")
                kind=self.registry.get(identity)
                if kind is None or identity in parsed or record.get("kind")!=kind: raise ValueError("Sensor identity")
                age=record.get("age")
                if not number(age,0,120) or type(record.get("valid")) is not bool: raise ValueError("Sensor age/validity")
                value=record.get("value")
                valid=record["valid"]
                error=record.get("error")
                if error is not None and (not isinstance(error,str) or len(error)>80): raise ValueError("Sensor error")
                if valid:
                    valid=number(value,self.config.min_m,self.config.max_m) if kind=="range" else type(value) is bool
                    if not valid: error="Measurement outside configured type/range"
                elif value is not None and not isinstance(value,(float,int,bool)): raise ValueError("Invalid measurement type")
                if age>self.config.timeout:
                    valid=False
                    error="Acquisition timeout"
                if not valid: value=None
                source_seq=record.get('sampleSeq')
                sampled_at=record.get('sampledAtMonotonic')
                if source_seq is not None and (type(source_seq) is not int or source_seq<0): raise ValueError('Sensor sample sequence')
                if sampled_at is not None and not number(sampled_at,0,1e12): raise ValueError('Sensor source clock')
                parsed[identity]=SensorObservation(identity,kind,now-age-transport_age,value,
                    "m" if kind=="range" else "boolean",valid,error,age,source_seq,sampled_at)
            with self.lock:
                if session!=self.session: self.reset(session)
                if seq<=self.seq: raise ValueError("Duplicate/out-of-order telemetry")
                self.seq=seq
                self.last_received=now
                self.last_transport_age=transport_age
                # Missing records replace the batch and therefore cannot keep old evidence alive.
                self.observations=parsed
                self._update_touches(now)
                self.recent_batches.append(dict(session=session,seq=seq,receivedAtMonotonic=now,
                    transportAgeBoundS=transport_age,committedAtMonotonic=self.clock(),
                    ranges={k:dict(senderAgeS=v.sender_age,valid=v.valid,value=v.measurement,
                        sampleSeq=v.source_seq,sampledAtSenderMonotonic=v.source_sampled_at)
                        for k,v in parsed.items() if k in RANGE_IDS}))
            return True
        except (ValueError,TypeError,KeyError) as error:
            with self.lock:
                self.rejected+=1
                reason=str(error)[:80]
                self.rejection_reasons[reason]=self.rejection_reasons.get(reason,0)+1
            return False

    def _event(self,identity,pressed,now):
        self.event_seq+=1
        self.events.append(dict(seq=self.event_seq,id=identity,pressed=pressed,at=now))

    def _update_touches(self,now):
        for identity in ("touch_"+k for k in TOUCH_IDS[:self.config.touch_count]):
            obs=self.observations.get(identity)
            if not obs or not obs.valid or now-obs.observed_at>self.config.expiration:
                self.touch.pop(identity,None)
                continue
            value=obs.measurement
            state=self.touch.get(identity)
            if state is None:
                # Boot/reconnect while asserted is never a new interaction.
                self.touch[identity]=dict(raw=value,since=now,pressed=value,held_since=now if value else None)
                continue
            if state["raw"]!=value: state.update(raw=value,since=now)
            if value!=state["pressed"] and now-state["since"]>=self.config.debounce:
                state["pressed"]=value
                state["held_since"]=now if value else None
                self._event(identity,value,now)

    def snapshot(self):
        with self.lock:
            # Clock and observations must belong to the same locked snapshot.
            # Reading time first lets a concurrent newer sample appear future-dated,
            # or lets a reader delayed on this lock hide genuine expiration.
            now=self.clock()
            records={k:v.snapshot(now,self.config.expiration) for k,v in self.observations.items()}
            for record in records.values(): record['virtual']=self.source!='physical_uno'
            touches={}
            for identity in ("touch_"+k for k in TOUCH_IDS[:self.config.touch_count]):
                record=records.get(identity)
                state=self.touch.get(identity)
                pressed=bool(state and state["pressed"])
                stuck=bool(pressed and now-state["held_since"]>=self.config.stuck_seconds)
                if stuck and record: record.update(valid=False,health="STUCK",error="Touch held beyond limit")
                touches[identity]=dict(pressed=pressed,stuck=stuck,valid=bool(record and record["valid"]))
            ranges=[records.get(k) for k in RANGE_IDS]
            fault=None
            if not all(r and r["valid"] for r in ranges): fault="Missing, invalid or stale front range"
            elif abs(ranges[0]["measurement"]-ranges[1]["measurement"])>self.config.conflict_m:
                fault="Conflicting front range observations"
            if not all(t["valid"] for t in touches.values()): fault=fault or "Missing, stale or stuck touch input"
            if fault:
                self.last_fault=dict(atMonotonic=now,session=self.session,seq=self.seq,reason=fault,
                    receivedAgeS=None if self.last_received is None else now-self.last_received,
                    transportAgeBoundS=self.last_transport_age,
                    observations={k:dict(v) for k,v in records.items()})
                if not self.was_fault: self.fault_events.append(self.last_fault)
            self.was_fault=bool(fault)
            fresh_events=[dict(e,age=now-e["at"]) for e in self.events if 0<=now-e["at"]<=self.config.expiration]
            return dict(virtual=self.source!='physical_uno',source=self.source,
                        monitoringOnly=self.source=='physical_uno',
                        safetyInhibits=([fault] if fault else []) +
                            (['Physical monitoring: unmeasured HC-SR04 and swept clearance; navigation inhibited'] if self.source=='physical_uno' else []),
                        session=self.session,seq=self.seq,config=asdict(self.config),observations=records,touches=touches,
                        events=fresh_events,front_m=min(r["measurement"] for r in ranges) if not fault else None,
                        fault=fault,rejected=self.rejected,
                        receivedAge=None if self.last_received is None else now-self.last_received,
                        diagnostics=dict(clockDomain='receiver monotonic; source timestamps diagnostic only',
                            snapshotAtMonotonic=now,lastReceivedAtMonotonic=self.last_received,
                            lastTransportAgeBoundS=self.last_transport_age,rejectionReasons=dict(self.rejection_reasons),
                            lastFault=self.last_fault,faultEvents=list(self.fault_events),recentBatches=list(self.recent_batches)))


def fixture_batch(seq=0,*,distance=2.0,touches=None,clearance=True,age=0.0,touch_count=5):
    """Deterministic explicit virtual fixture; never selected as a missing-device fallback."""
    touches=touches or {}
    records=[dict(id=k,kind="range",value=distance,valid=True,age=age) for k in RANGE_IDS]
    records += [dict(id="touch_"+k,kind="touch",value=bool(touches.get(k,False)),valid=True,age=age) for k in TOUCH_IDS[:touch_count]]
    records += [dict(id=k,kind="clearance",value=clearance,valid=True,age=age) for k in CLEARANCE_IDS]
    return dict(schema=1,seq=seq,observations=records)

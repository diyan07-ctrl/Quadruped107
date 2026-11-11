"""TEL1 diagnostics and poll-bounded TEL2 monitoring; never authorizes actuation."""
from dataclasses import dataclass, asdict
import threading
import time

@dataclass(frozen=True)
class Telemetry:
    seq:int
    uptime_ms:int
    range_mm:int
    source:int
    flags:int
    touch_mask:int
    pack_mv:int
    servo_mv:int

@dataclass(frozen=True)
class SensorTelemetry:
    seq:int
    uptime_ms:int
    range_mm:int
    source:int
    flags:int
    touch_mask:int
    range_age_ms:int
    touch_age_ms:int
    token:int
    faults:int

def parse_tel2(line):
    if not isinstance(line,str) or not line.isascii() or len(line.rstrip('\r\n'))>63:
        raise ValueError('TEL2 line bound')
    fields=line.split()
    if len(fields)!=12 or fields[:2]!=['TEL','2']:
        raise ValueError('TEL2 format')
    if any(not t or t[0]=='+' or not t.lstrip('-').isdigit() for t in fields[2:]):
        raise ValueError('TEL2 integer')
    r=SensorTelemetry(*map(int,fields[2:]))
    if (not 0<=r.seq<=65535 or not 0<=r.uptime_ms<=0xffffffff or
        not -1<=r.range_mm<=4000 or not 0<=r.source<=1 or not 0<=r.flags<=127 or
        not 0<=r.touch_mask<=31 or not 0<=r.range_age_ms<=999 or
        not 0<=r.touch_age_ms<=999 or not 0<=r.token<=65535 or not 0<=r.faults<=255):
        raise ValueError('TEL2 bounds')
    if r.flags&1 and (r.range_mm<20 or r.source!=1 or r.range_age_ms>300):
        raise ValueError('TEL2 invalid range claim')
    if r.flags&2 and r.touch_age_ms>300: raise ValueError('TEL2 invalid touch claim')
    return r

def parse_tel1(line):
    if not isinstance(line,str) or not line.isascii() or len(line.rstrip("\r\n"))>63: raise ValueError("TEL1 line bound")
    fields=line.split()
    if len(fields)!=10 or fields[:2]!=["TEL","1"]: raise ValueError("TEL1 format")
    if any(not token or token[0]=="+" or not token.lstrip("-").isdigit() for token in fields[2:]): raise ValueError("TEL1 integer")
    record=Telemetry(*map(int,fields[2:]))
    if (not 0<=record.seq<=65535 or not 0<=record.uptime_ms<=0xffffffff or
        not -1<=record.range_mm<=9999 or not 0<=record.source<=2 or
        not 0<=record.flags<=255 or not 0<=record.touch_mask<=31 or
        not -1<=record.pack_mv<=65535 or not -1<=record.servo_mv<=65535):
        raise ValueError("TEL1 field bounds")
    if record.flags&1 and (record.range_mm<0 or record.source==0): raise ValueError("Valid range requires value/source")
    if record.flags&4 and record.pack_mv<0 or record.flags&8 and record.servo_mv<0: raise ValueError("Valid voltage missing")
    return record

class TelemetryStream:
    def __init__(self,*,clock=time.monotonic):
        self.clock=clock
        self.lock=threading.Lock()
        self.errors=0
        self.reset()

    def reset(self):
        with self.lock:
            self.record=None
            self.received=None
            self.polls={}
            self.poll_sequence=0
            self.age_bound=None
            self.dropped=0
            self.last_valid_acquisition=None

    def poll(self):
        with self.lock:
            self.poll_sequence=(self.poll_sequence+1)&65535
            token=self.poll_sequence
            now=self.clock()
            self.polls={k:v for k,v in self.polls.items() if now-v<=.3}
            self.polls[token]=now
            return token

    def ingest(self,line):
        try:
            record=parse_tel2(line) if line.startswith('TEL 2 ') else parse_tel1(line)
            with self.lock:
                now=self.clock()
                bound=None
                if isinstance(record,SensorTelemetry):
                    sent=self.polls.pop(record.token,None)
                    if sent is None or not 0<=now-sent<=.3:
                        raise ValueError('TEL2 missing/expired poll')
                    bound=now-sent
                if self.record:
                    if type(record) is not type(self.record): raise ValueError('Telemetry version changed in session')
                    delta=(record.seq-self.record.seq)&0xffff
                    elapsed=(record.uptime_ms-self.record.uptime_ms)&0xffffffff
                    if delta==0 or delta>32767 or elapsed>0x7fffffff: raise ValueError("TEL1 duplicate/out-of-order/reset")
                    self.dropped+=delta-1
                self.record=record
                self.received=now
                self.age_bound=bound
                if bound is not None and record.flags&1 and not record.faults&11 and bound+record.range_age_ms/1000+.002<=.3:
                    self.last_valid_acquisition=now-bound-record.range_age_ms/1000-.002
            return True
        except ValueError:
            with self.lock: self.errors+=1
            return False

    def snapshot(self):
        with self.lock:
            record=self.record
            age=None if self.received is None else self.clock()-self.received
            fresh=age is not None and 0<=age<=.3
            if record is None: return dict(supported=False,record=None,age=age,receiveFresh=False,errors=self.errors)
            if isinstance(record,SensorTelemetry):
                # Millisecond truncation and AVR micros() resolution get a
                # conservative 2 ms guard; never loosen the 300 ms policy.
                range_age=age+self.age_bound+record.range_age_ms/1000+.002
                touch_age=age+self.age_bound+record.touch_age_ms/1000+.002
                range_valid=bool(record.flags&1 and range_age<=.3 and not record.faults&11)
                touch_valid=bool(record.flags&2 and touch_age<=.3 and not record.faults&12)
                return dict(supported=True,record=asdict(record),version=2,age=age,receiveFresh=fresh,
                    rangeAge=range_age,touchAge=touch_age,rangeValid=range_valid,touchValid=touch_valid,
                    distanceM=record.range_mm/1000 if range_valid else None,errors=self.errors,
                    drops=self.dropped,transportAgeBound=self.age_bound,
                    lastValidAcquisitionMonotonic=self.last_valid_acquisition,
                    acquisitionFreshnessKnown=True,controlQualified=False,
                    servoOutputsEnabled=False,localInhibit=True,faults=record.faults)
            return dict(supported=True,record=asdict(record),age=age,receiveFresh=fresh,errors=self.errors,
                distanceM=record.range_mm/1000 if fresh and record.flags&1 else None,
                rangeValid=bool(fresh and record.flags&1),touchValid=bool(fresh and record.flags&2),
                watchdogResetSeen=bool(record.flags&64),localInhibit=bool(record.flags&16),
                overloadLatched=bool(record.flags&32),servoOutputsEnabled=None,
                acquisitionFreshnessKnown=False,controlQualified=False)

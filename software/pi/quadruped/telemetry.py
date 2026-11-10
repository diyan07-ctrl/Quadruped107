"""Passive TEL1 diagnostics. No capability negotiation or physical safety activation."""
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

    def ingest(self,line):
        try:
            record=parse_tel1(line)
            with self.lock:
                if self.record:
                    delta=(record.seq-self.record.seq)&0xffff
                    elapsed=(record.uptime_ms-self.record.uptime_ms)&0xffffffff
                    if delta==0 or delta>32767 or elapsed>0x7fffffff: raise ValueError("TEL1 duplicate/out-of-order/reset")
                self.record=record
                self.received=self.clock()
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
            return dict(supported=True,record=asdict(record),age=age,receiveFresh=fresh,errors=self.errors,
                distanceM=record.range_mm/1000 if fresh and record.flags&1 else None,
                rangeValid=bool(fresh and record.flags&1),touchValid=bool(fresh and record.flags&2),
                watchdogResetSeen=bool(record.flags&64),localInhibit=bool(record.flags&16),
                overloadLatched=bool(record.flags&32),servoOutputsEnabled=None,
                acquisitionFreshnessKnown=False,controlQualified=False)

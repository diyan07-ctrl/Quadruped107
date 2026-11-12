"""Finite, explicit virtual-test held intent, independent of telemetry reads.

This is qualification instrumentation, not an automatic recovery mechanism.
No ARM is sent here. Deadline, cancellation or any renewal failure ends it.
"""
from collections import deque
import threading
import time
import math

class HeldIntentLease:
    def __init__(self,renew,motion,deadline,*,period=.1,clock=time.monotonic):
        if motion not in ('forward','backward','turn_left','turn_right'): raise ValueError('Held direction required')
        if not 0<period<=.2: raise ValueError('Renewal period must be <= 200 ms')
        if not math.isfinite(deadline) or deadline<=clock(): raise ValueError('Finite future deadline required')
        self.renew,self.motion,self.deadline,self.period,self.clock=renew,motion,deadline,period,clock
        self.cancelled=threading.Event()
        self.records=deque(maxlen=20000)
        self.error=None
        self.thread=threading.Thread(target=self._run,name='qualification-held-intent',daemon=True)

    def tick(self):
        if self.cancelled.is_set() or self.clock()>=self.deadline:
            self.cancelled.set();return False
        started=self.clock()
        try:
            self.renew(self.motion)
            self.records.append(dict(startedMonotonic=started,durationS=self.clock()-started,ok=True))
            return True
        except Exception as error:
            self.error=type(error).__name__+': '+str(error)
            self.records.append(dict(startedMonotonic=started,durationS=self.clock()-started,ok=False,error=self.error))
            self.cancelled.set();return False

    def _run(self):
        while self.tick():
            if self.cancelled.wait(self.period): break

    def start(self): self.thread.start()

    def close(self):
        self.cancelled.set()
        if self.thread.is_alive(): self.thread.join(1)

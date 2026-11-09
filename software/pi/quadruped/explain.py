"""Bounded factual lifecycle events; requests are not execution acknowledgments."""
from collections import deque
import threading
import time

class DecisionHistory:
    def __init__(self,capacity=128):
        self.lock=threading.Lock()
        self.items=deque(maxlen=capacity)
        self.last={}
        self.sequence=0

    def record(self,kind,*,motion=None,status="",reason="",generation=None,request_id=None):
        signature=(motion,status,reason,generation,request_id)
        with self.lock:
            if self.last.get(kind)==signature: return
            self.last[kind]=signature
            self.sequence+=1
            self.items.append(dict(seq=self.sequence,at=time.monotonic(),time=time.strftime("%H:%M:%S"),
                kind=kind,motion=motion,status=status,reason=str(reason)[:240],generation=generation,requestId=request_id))

    def snapshot(self):
        with self.lock: return list(self.items)

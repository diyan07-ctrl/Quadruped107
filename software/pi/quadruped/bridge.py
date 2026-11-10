"""Bounded, challenge/lease-based UDP trace transport for trusted LAN simulation only."""
from __future__ import annotations
import ipaddress
import json
import secrets
import socket
import threading
import time

MAX_PACKET=2048
LEASE=.3
CHALLENGE_TTL=.15


def encode(data):
    raw=json.dumps(data,separators=(",",":"),allow_nan=False).encode()
    if len(raw)>MAX_PACKET: raise ValueError("Simulation packet too large")
    return raw


def decode(raw):
    if len(raw)>MAX_PACKET: raise ValueError("Simulation packet too large")
    try: data=json.loads(raw)
    except RecursionError as error: raise ValueError("Nested simulation packet exceeds parser budget") from error
    if not isinstance(data,dict) or type(data.get("v")) is not int or data["v"]!=1:
        raise ValueError("Invalid simulation protocol version")
    return data


class TraceReceiver:
    def __init__(self,*,clock=time.monotonic):
        self.clock=clock
        self.invalid=0
        self.reset()

    def reset(self):
        self.session=secrets.token_hex(16)
        self.peer=self.client=None
        self.challenge=None
        self.last_seq=-1
        self.last_frame=None
        self.peer_since=self.clock()
        self.requires_disarmed=True
        self.state=dict(virtual=True,armed=False,activeMask=0,targets=[300]*8,activeMotion=None)
        self.reason="Waiting for explicit virtual connection"

    def expire(self):
        if self.last_frame is not None and self.clock()-self.last_frame>LEASE:
            self.state["armed"]=False
            self.state["activeMask"]=0
            self.requires_disarmed=True
            self.state["activeMotion"]=None
            self.reason="Simulator receive lease expired"

    def handle(self,raw,address):
        self.expire()
        try:
            data=decode(raw)
            client=data.get("client")
            if not isinstance(client,str) or len(client)!=32 or any(c not in "0123456789abcdef" for c in client):
                raise ValueError("Invalid client session")
            if (self.peer is not None and (address!=self.peer or client!=self.client) and data.get("type")=="hello"
                    and self.clock()-(self.last_frame if self.last_frame is not None else self.peer_since)>LEASE):
                self.reset()  # old process is gone; new session still requires a disarmed frame
            if self.peer is not None and (address!=self.peer or client!=self.client):
                raise ValueError("Simulator already owned")
            kind=data.get("type")
            if kind=="hello":
                if self.peer is None: self.peer_since=self.clock()
                self.peer,self.client=address,client
                nonce=secrets.token_hex(16)
                self.challenge=(nonce,self.clock())
                return encode(dict(v=1,type="challenge",server=self.session,nonce=nonce))
            if self.peer is None or data.get("server")!=self.session: raise ValueError("Session mismatch")
            seq=data.get("seq")
            if type(seq) is not int or not 0<=seq<2**31 or seq<=self.last_seq:
                raise ValueError("Duplicate/out-of-order trace")
            if kind=="stop":
                self.last_seq=seq
                self.state["armed"]=False
                self.state["activeMask"]=0
                self.requires_disarmed=True
                self.challenge=None
                self.state["activeMotion"]=None
                self.reason="Priority virtual STOP"
                return None
            if kind!="trace" or self.challenge is None: raise ValueError("No outstanding challenge")
            nonce,born=self.challenge
            if data.get("nonce")!=nonce or self.clock()-born>CHALLENGE_TTL:
                raise ValueError("Stale challenge")
            self.challenge=None
            targets=data.get("targets")
            mask=data.get("activeMask")
            armed=data.get("armed")
            if (data.get("virtual") is not True or type(armed) is not bool or
                not isinstance(targets,list) or len(targets)!=8 or
                any(type(t) is not int or not 50<=t<=600 for t in targets) or
                type(mask) is not int or not 0<=mask<=255):
                raise ValueError("Invalid virtual actuator payload")
            active=data.get("activeMotion")
            if active is not None and active not in ("initial","stand","forward","backward","turn_left","turn_right","greeting","tail_wag"):
                raise ValueError("Invalid active motion")
            behavior=data.get("behavior")
            if behavior is not None and (not isinstance(behavior,str) or len(behavior)>40): raise ValueError("Invalid behavior label")
            self.last_seq=seq
            self.last_frame=self.clock()
            if not armed: self.requires_disarmed=False
            if armed and self.requires_disarmed:
                self.state["armed"]=False
                self.state["activeMask"]=0
                self.reason="Disarmed frame required before fresh ARM"
            else:
                self.state=dict(virtual=True,armed=armed,activeMask=mask if armed else 0,targets=targets,activeMotion=active if armed else None,behavior=behavior)
                self.reason=None
            return encode(dict(v=1,type="ack",server=self.session,nonce=nonce,seq=seq,
                               ready=not self.requires_disarmed,fault=self.reason))
        except (ValueError,TypeError,KeyError,UnicodeError):
            self.invalid+=1
            return None

    def snapshot(self):
        self.expire()
        return {**self.state,"server":self.session,"seq":self.last_seq,"invalid":self.invalid,
                "fault":self.reason,"ready":not self.requires_disarmed}


class TraceServer:
    def __init__(self,host="127.0.0.1",port=7002,*,sensors=None):
        self.sensors=sensors
        self.receiver=TraceReceiver()
        self.socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.socket.bind((host,port))
        self.socket.setblocking(False)
        self.address=self.socket.getsockname()

    def poll(self):
        for _ in range(8):
            try: raw,address=self.socket.recvfrom(MAX_PACKET+1)
            except BlockingIOError: break
            reply=self.receiver.handle(raw,address)
            if reply is not None:
                try:
                    if self.sensors:
                        message=decode(reply)
                        if message["type"]=="ack": message["sensors"]=self.sensors()
                        reply=encode(message)
                    self.socket.sendto(reply,address)
                except (OSError,ValueError): pass
        return self.receiver.snapshot()

    def close(self):
        self.receiver.state["armed"]=False
        self.receiver.state["activeMask"]=0
        self.socket.close()


class TraceClient:
    def __init__(self,host,port,snapshot,*,on_sensors=None):
        self.on_sensors=on_sensors
        if type(port) is not int or not 1<=port<=65535: raise ValueError("Invalid simulator port")
        address=socket.gethostbyname(host)
        if not (ipaddress.ip_address(address).is_private or ipaddress.ip_address(address).is_loopback):
            raise ValueError("Simulator must be on a trusted private/loopback network")
        self.address=(address,port)
        self.source=snapshot
        self.client=secrets.token_hex(16)
        self.lock=threading.Lock()
        self.stop_event=threading.Event()
        self.session=None
        self.seq=0
        self.last_ack=0.0
        self.pending=None
        self.epoch=0
        self.fault=None
        self.ready=False
        self.disarmed_stop_epoch=None
        self.errors=0
        self.thread=threading.Thread(target=self._run,name="simulation-bridge",daemon=True)

    def start(self): self.thread.start()

    def snapshot(self):
        source=self.source()
        with self.lock:
            age=time.monotonic()-self.last_ack if self.last_ack else None
            return dict(connected=age is not None and age<=LEASE,ackAge=age,
                        readyToArm=self.ready and not source["armed"] and source.get("stopEpoch")==self.disarmed_stop_epoch,fault=self.fault,epoch=self.epoch,errors=self.errors,
                        transport="UDP challenge/lease",physical=False)

    def prepare_arm(self):
        source=self.source()
        with self.lock:
            if (not self.last_ack or time.monotonic()-self.last_ack>LEASE or not self.ready
                or source["armed"] or source.get("stopEpoch")!=self.disarmed_stop_epoch):
                raise RuntimeError("Simulator unavailable or awaiting disarmed handshake")
            self.fault=None
            return self.epoch

    def _run(self):
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        sock.settimeout(.02)
        last_hello=0.0
        awaiting=False
        was_armed=False
        try:
            while not self.stop_event.is_set():
                now=time.monotonic()
                state=self.source()
                armed=bool(state["armed"])
                if was_armed and not armed and self.session:
                    with self.lock: self.ready=False
                    self.seq+=1
                    sock.sendto(encode(dict(v=1,type="stop",client=self.client,server=self.session,seq=self.seq)),self.address)
                was_armed=armed
                if now-last_hello>=.05 and (not awaiting or now-last_hello>CHALLENGE_TTL):
                    sock.sendto(encode(dict(v=1,type="hello",client=self.client)),self.address)
                    last_hello=now
                    awaiting=True
                try: raw,peer=sock.recvfrom(MAX_PACKET+1)
                except socket.timeout: continue
                if peer!=self.address: continue
                now=time.monotonic()  # receipt time, including time blocked in recvfrom
                try:
                    data=decode(raw)
                    if data.get("type")=="challenge":
                        server,nonce=data.get("server"),data.get("nonce")
                        if not isinstance(server,str) or len(server)!=32 or not isinstance(nonce,str) or len(nonce)!=32:
                            raise ValueError("Invalid challenge")
                        with self.lock:
                            if self.session is not None and self.session!=server:
                                self.fault="Simulator reset; explicit re-arm required"
                                self.ready=False
                                self.epoch+=1
                            self.session=server
                        self.seq+=1
                        if self.seq>=2**31: raise RuntimeError("Simulation sequence exhausted")
                        state=self.source()
                        message=dict(v=1,type="trace",client=self.client,server=server,nonce=nonce,seq=self.seq,
                                     virtual=True,armed=bool(state["armed"]),activeMask=state["activeMask"],targets=state["targets"],
                                     activeMotion=state.get("activeMotion"),behavior=state.get("behavior"))
                        self.pending=(nonce,self.seq,now,bool(state["armed"]),state.get("stopEpoch"))
                        sock.sendto(encode(message),self.address)
                    elif data.get("type")=="ack" and self.pending:
                        nonce,seq,born,sent_armed,sent_stop_epoch=self.pending
                        if data.get("server")!=self.session or data.get("nonce")!=nonce or data.get("seq")!=seq or now-born>LEASE:
                            raise ValueError("Stale acknowledgment")
                        if self.on_sensors and "sensors" in data:
                            self.on_sensors(data["sensors"],session=self.session,transport_age=max(0,now-born))
                        with self.lock:
                            self.last_ack=now
                            self.ready=data.get("ready") is True and not sent_armed
                            if self.ready: self.disarmed_stop_epoch=sent_stop_epoch
                            if data.get("fault"): self.fault=str(data["fault"])[:160]
                        self.pending=None
                        awaiting=False
                except (ValueError,TypeError,KeyError):
                    with self.lock: self.errors+=1
        except (OSError, RuntimeError):
            with self.lock: self.fault="Simulation network disconnected"
        finally:
            if self.session:
                try:
                    self.seq+=1
                    sock.sendto(encode(dict(v=1,type="stop",client=self.client,server=self.session,seq=self.seq)),self.address)
                except OSError: pass
            sock.close()

    def close(self):
        self.stop_event.set()
        if self.thread.is_alive(): self.thread.join(1)

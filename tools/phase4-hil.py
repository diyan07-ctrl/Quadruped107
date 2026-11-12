"""Phase 4 real-camera/virtual-actuator qualification instrumentation.

No physical actuator, GPIO or firmware-upload path. No automatic ARM/recovery.
Run only on the trusted LAN. All durations use a host-local monotonic clock.
"""
import argparse
import base64
from datetime import datetime,timezone
import json
import logging
from pathlib import Path
import queue
import threading
import time
import urllib.request
import urllib.error
import http.cookiejar
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'software/pi'),str(ROOT/'tools')]

def utc(): return datetime.now(timezone.utc).isoformat()

def atomic(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value),encoding='utf-8');temp.replace(path)

def optional_snapshot(path,value,journal):
    """A convenience preview cannot terminate the safety-supervised simulator."""
    try: atomic(path,value)
    except OSError as error:
        journal.put(dict(kind='artifact_error',path=str(path),error=repr(error)))
        return False
    return True

class Journal:
    """Bounded nonblocking producer; disk work belongs to a separate thread."""
    def __init__(self,path,clock=time.monotonic):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.clock=clock
        self.queue=queue.Queue(maxsize=4096);self.dropped=0
        self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start()
    def put(self,value):
        try: self.queue.put_nowait(dict(utc=utc(),localMonotonic=self.clock(),**value))
        except queue.Full: self.dropped+=1
    def _run(self):
        with self.path.open('w',encoding='utf-8') as file:
            while True:
                value=self.queue.get()
                if value is None: break
                file.write(json.dumps(value)+'\n');file.flush()
    def close(self):
        self.queue.put(None);self.thread.join(5)

def twin(args):
    from simulation.twin import World
    from simulation.environment import Scene
    from quadruped.bridge import TraceServer,decode
    clock=time.perf_counter
    world=World(gui=args.gui)
    scene=Scene(world,'empty',latency=.02,clock=clock)
    journal=Journal(args.output/'trace.jsonl',clock=clock)
    control={};last_action=None
    def sensors():
        batch=scene.telemetry()
        if control.get('stale_sensors'):
            batch={**batch,'observations':[{**r,'age':r['age']+2} for r in batch['observations']]}
        return batch
    server=TraceServer(args.host,args.port,sensors=sensors)
    original=server.receiver.handle
    def handle(raw,peer):
        started=clock();before=server.receiver.invalid
        reply=original(raw,peer)
        try: message=decode(raw)
        except ValueError: message={}
        journal.put(dict(kind='udp',peer=peer,messageType=message.get('type'),seq=message.get('seq'),
          sentArmed=message.get('armed'),accepted=reply is not None,rejected=server.receiver.invalid!=before,
          receiver=server.receiver.snapshot(),handleMs=1000*(clock()-started)))
        return reply
    server.receiver.handle=handle
    start=last_tick=clock();next_tick=start
    last_control=last_sample=last_image=0
    intervals=[]
    try:
        while clock()-start<args.seconds:
            now=clock();intervals.append(now-last_tick);last_tick=now
            if now-last_control>=.1:
                if args.control.exists():
                    try: control=json.loads(args.control.read_text())
                    except json.JSONDecodeError: pass
                action=control.get('action_id')
                if action!=last_action:
                    if control.get('reset'): scene.reset(server.receiver)
                    if control.get('obstacle'): scene.add_box(float(control['obstacle']),0,.05,.4)
                    for name,sensor in scene.touches.items(): sensor.pressed=name==control.get('touch')
                    last_action=action
                last_control=now
            if control.get('shutdown'): break
            frame=server.receiver.snapshot() if control.get('pause_udp') else server.poll()
            scene.advance(frame)
            world.apply(frame);positions=world.step()
            if now-last_sample>=.1:
                batch=scene.telemetry()
                journal.put(dict(kind='physics',elapsedS=now-start,frames=world.frames,
                    receiver=frame,actualJointRad=list(positions),requestedTicks=frame['targets'],
                    ranges=[r for r in batch['observations'] if r['kind']=='range'],
                    tickMaxS=max(intervals),tickMeanS=sum(intervals)/len(intervals),control=control))
                optional_snapshot(args.output/'latest.json',dict(utc=utc(),receiver=frame,actualJointRad=list(positions)),journal)
                intervals=[];last_sample=now
            if control.get('image') and now-last_image>=.5:
                # Optional slow preview, separately measured; endurance need not render it.
                world.capture(args.output/'preview.png');last_image=now
            next_tick+=1/240
            time.sleep(max(0,min(.01,next_tick-clock())))
    finally:
        server.close();world.apply(dict(virtual=True,armed=False,activeMask=0,targets=[300]*8))
        atomic(args.output/'result.json',dict(durationS=clock()-start,diagnostics=world.diagnostics(),journalDrops=journal.dropped,
            clock=vars(time.get_clock_info('perf_counter'))))
        world.close();journal.close()

def pi(args):
    import cv2
    from werkzeug.serving import make_server
    from flask import jsonify
    from quadruped.main import Runtime,create_app
    from quadruped.camera import Camera
    from quadruped.vision import detect_blue_ball,encode_vision_frame
    runtime=Runtime(camera_backend='usb',camera_device='/dev/video0',width=320,height=240,fps=30,
        actuator_backend='virtual',virtual_sensors=True,simulator_host=args.host,simulator_port=args.port,
        vision_state=args.output/'vision.json')
    runtime.start();app=create_app(runtime)
    @app.get('/qualification/frame')
    def diagnostic_frame():
        frame,_,seq,_,captured=runtime.camera.latest(with_timestamp=True)
        if frame is None: return jsonify(available=False)
        with runtime.settings_lock: settings=runtime.vision_settings
        detection=detect_blue_ball(frame,lower=settings.hsv_lower,upper=settings.hsv_upper,
            min_area=settings.min_area,min_radius=settings.min_radius,max_radius_ratio=settings.max_radius_ratio,min_circularity=settings.min_circularity)
        hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV)
        def encode(image,extension): return base64.b64encode(cv2.imencode(extension,image)[1]).decode()
        mask=detection.pop('mask')
        annotated=encode_vision_frame(frame,detection,runtime.navigation_state()['state'],
            runtime.link.engine.snapshot().get('activeMotion') or 'hold',target_name=settings.target_color)
        return jsonify(available=True,sequence=seq,capturedAtReceiverMonotonic=captured,
            frameAgeS=time.monotonic()-captured,targetColor=settings.target_color,settings=settings.to_dict(),
            rawJpeg=encode(frame,'.jpg'),maskPng=encode(mask,'.png'),annotatedJpeg=base64.b64encode(annotated).decode(),
            rawPng=encode(frame,'.png'),
            detection=detection,overexposedFraction=float((hsv[:,:,2]>=250).mean()))
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    server=make_server('127.0.0.1',7000,app,threaded=True)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    journal=Journal(args.output/'state.jsonl');start=time.monotonic();last_action=None
    try:
        while time.monotonic()-start<args.seconds:
            control={}
            if args.control.exists():
                try: control=json.loads(args.control.read_text())
                except json.JSONDecodeError: pass
            if control.get('action_id')!=last_action:
                if control.get('camera_stop'): runtime.camera.close()
                if control.get('camera_resume'):
                    runtime.camera.close();runtime.camera=Camera(backend='usb',device='/dev/video0',width=320,height=240,fps=30);runtime.camera.start()
                last_action=control.get('action_id')
            if control.get('shutdown'): break
            state=runtime.state();assert state['physicalActuationAllowed'] is False
            journal.put(dict(kind='state',elapsedS=time.monotonic()-start,state=state))
            time.sleep(.2)
    finally:
        runtime.motion.stop('Qualification shutdown')
        atomic(args.output/'final-state.json',runtime.state())
        server.shutdown();runtime.close();journal.close()

class Client:
    def __init__(self,url):
        self.url=url.rstrip('/')
        self.jar=http.cookiejar.CookieJar()
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(self.jar))
    def call(self,path,data=None,timeout=3):
        request=urllib.request.Request(self.url+'/'+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'})
        try:
            with self.opener.open(request,timeout=timeout) as reply: return json.load(reply)
        except urllib.error.HTTPError as error:
            detail=error.read(512).decode('utf-8',errors='replace')
            raise RuntimeError(f'HTTP {error.code} at {path}; server rejection: {detail}') from error
    def renewer(self):
        # Immutable cookie header; diagnostic reads and cookie disk I/O cannot block renewal.
        request=urllib.request.Request(self.url+'/api/heartbeat');self.jar.add_cookie_header(request)
        cookie=request.get_header('Cookie')
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        def renew(motion):
            req=urllib.request.Request(self.url+'/api/heartbeat',data=json.dumps(dict(motion=motion)).encode(),
                 headers={'Content-Type':'application/json','Cookie':cookie or ''})
            with opener.open(req,timeout=.3) as reply:
                if reply.status!=200: raise RuntimeError('Heartbeat rejected')
                reply.read()
        return renew
    def ready(self):
        for _ in range(100):
            state=self.call('api/state')
            if (state['bridge']['readyToArm'] and state['bridge']['connected'] and
                not state['motion']['busy'] and not state['motion']['stopping'] and not state['sensors']['fault']): return state
            time.sleep(.1)
        raise RuntimeError('Qualification readiness timeout')

def run(args):
    from hil_lease import HeldIntentLease
    client=Client(args.url);journal=Journal(args.output/'samples.jsonl')
    lease=None;start=None;failure=None;count=0;last_progress=-30
    try:
        client.call('api/stop',{});client.ready()
        client.call('api/arm',{});client.call('api/mode',dict(mode='forward'))
        lease=HeldIntentLease(client.renewer(),'forward',time.monotonic()+args.seconds+5)
        lease.start()
        for _ in range(50):
            state=client.call('api/state')
            if not state['motion']['enabled']: raise RuntimeError('Disarmed before active interval')
            if state['link']['activeMotion']=='forward' and state['link']['activeMask']: break
            time.sleep(.1)
        else: raise RuntimeError('No accepted active forward movement')
        start=time.monotonic();lease.deadline=start+args.seconds
        while time.monotonic()-start<args.seconds:
            state=client.call('api/state');elapsed=time.monotonic()-start
            journal.put(dict(kind='sample',elapsedS=elapsed,state=state));count+=1
            if (not state['motion']['enabled'] or not state['link']['armed'] or not state['link']['activeMask'] or not state['bridge']['connected'] or
                not state['camera']['available'] or state['sensors']['fault'] or lease.error):
                failure=dict(elapsedS=elapsed,state=state,renewalError=lease.error);break
            if elapsed-last_progress>=30:
                print(json.dumps(dict(elapsedS=elapsed,enabled=True,sensorSeq=state['sensors']['seq'],
                    front=state['sensors']['front_m'],intentAgeS=state['motion']['intentAgeS'])),flush=True);last_progress=elapsed
            time.sleep(.2)
    except Exception as error: failure=dict(error=type(error).__name__+': '+str(error))
    finally:
        if lease: lease.close()
        try: client.call('api/stop',{})
        except Exception as error:
            if failure is None: failure=dict(error='Final STOP: '+str(error))
        duration=0 if start is None else time.monotonic()-start
        result=dict(result='PASS' if failure is None and duration>=args.seconds else 'FAIL',
            requiredSeconds=args.seconds,durationS=duration,samples=count,failure=failure,
            automaticRearm=False,heartbeatRecords=list(lease.records) if lease else [],journalDrops=journal.dropped)
        atomic(args.output/'result.json',result);journal.close()
        print(json.dumps({k:v for k,v in result.items() if k!='heartbeatRecords'}),flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role',choices=('twin','pi','run'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--control',type=Path,default=Path('build/remediation-control.json'))
    parser.add_argument('--host',default='192.168.1.43')
    parser.add_argument('--port',type=int,default=7002)
    parser.add_argument('--gui',action='store_true')
    parser.add_argument('--seconds',type=float,default=3600)
    parser.add_argument('--url',default='http://127.0.0.1:7000')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    {'twin':twin,'pi':pi,'run':run}[args.role](args)
if __name__=='__main__': main()

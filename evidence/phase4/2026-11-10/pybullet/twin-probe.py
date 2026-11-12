"""Qualification instrumentation around the existing twin; virtual outputs only.

Control is a local file written by the test operator. Sensor faults and touch
are explicitly simulated. Real camera/application input arrives over LAN UDP.
"""
import argparse
import copy
from datetime import datetime,timezone
import json
from pathlib import Path
import time
import cv2
from simulation.twin import World
from simulation.environment import Scene
from quadruped.bridge import TraceServer,decode

parser=argparse.ArgumentParser()
parser.add_argument('--host',default='192.168.1.43')
parser.add_argument('--port',type=int,default=7002)
parser.add_argument('--gui',action='store_true')
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--control',type=Path,required=True)
args=parser.parse_args()
args.output.mkdir(parents=True,exist_ok=True)
world=World(gui=args.gui)
scene=Scene(world,'empty',latency=0)
control={}
def sensors():
    batch=copy.deepcopy(scene.telemetry())
    if control.get('stale_sensors'):
        for item in batch['observations']: item['age']+=2
    return batch
server=TraceServer(args.host,args.port,sensors=sensors)
events=(args.output/'packets.jsonl').open('w',encoding='utf-8')
samples=(args.output/'joints.jsonl').open('w',encoding='utf-8')
original=server.receiver.handle
last_vector=None
def observe(raw,address):
    global last_vector
    before=server.receiver.invalid
    reply=original(raw,address)
    frame=server.receiver.snapshot()
    vector=(frame['armed'],frame['activeMask'],tuple(frame['targets']),frame.get('activeMotion'))
    if server.receiver.invalid!=before or vector!=last_vector:
        try: msg=decode(raw)
        except ValueError: msg={'type':'invalid'}
        events.write(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),local_monotonic_s=time.monotonic(),
          peer=address,type=msg.get('type'),seq=msg.get('seq'),sent_armed=msg.get('armed'),
          accepted=reply is not None,rejected=server.receiver.invalid!=before,state=frame))+'\n')
        events.flush()
        last_vector=vector
    return reply
server.receiver.handle=observe
last_action=None
last_sample=last_render=0
writer=None
started=time.monotonic()
next_step=started
try:
    while True:
        now=time.monotonic()
        if now-last_sample>=1:
            if args.control.exists(): control=json.loads(args.control.read_text())
            action=control.get('action_id')
            if action!=last_action:
                if control.get('reset'): scene.reset(server.receiver)
                if control.get('obstacle'): scene.add_box(.45,0,.05,.4)
                if control.get('capture'): world.capture(control['capture'])
                for name,sensor in scene.touches.items(): sensor.pressed=name==control.get('touch')
                last_action=action
            if control.get('shutdown'): break
        frame=server.receiver.snapshot() if control.get('pause_udp') else server.poll()
        scene.advance(frame)
        world.apply(frame)
        values=world.step()
        if now-last_sample>=1:
            item=dict(utc=datetime.now(timezone.utc).isoformat(),elapsed_s=now-started,receiver=frame,
                      actual_joint_positions_rad=list(values),requested_targets_ticks=frame['targets'],
                      world_fault=world.fault,frames=world.frames,control=control)
            samples.write(json.dumps(item)+'\n'); samples.flush()
            (args.output/'latest.json').write_text(json.dumps(item,indent=2)+'\n')
            last_sample=now
        record=control.get('record')
        if record and now-last_render>=.2:
            if writer is None:
                writer=cv2.VideoWriter(str(args.output/'virtual-network.avi'),cv2.VideoWriter_fourcc(*'MJPG'),5,(640,480))
                if not writer.isOpened(): raise RuntimeError('Video writer failed')
            image=world.render_bgr()
            cv2.putText(image,datetime.now(timezone.utc).isoformat(),(5,20),cv2.FONT_HERSHEY_SIMPLEX,.4,(0,0,0),1)
            cv2.putText(image,'REAL LAN INPUT / VIRTUAL ACTUATORS',(5,42),cv2.FONT_HERSHEY_SIMPLEX,.45,(0,0,0),1)
            cv2.putText(image,f"armed={frame['armed']} mask={frame['activeMask']} {frame.get('activeMotion')}",(5,64),cv2.FONT_HERSHEY_SIMPLEX,.45,(0,0,0),1)
            writer.write(image); last_render=now
        elif not record and writer:
            writer.release(); writer=None
        next_step+=1/240
        time.sleep(max(0,min(.01,next_step-time.monotonic())))
except KeyboardInterrupt: pass
finally:
    if writer: writer.release()
    server.close()
    world.apply(dict(virtual=True,armed=False,activeMask=0,targets=[300]*8))
    (args.output/'final.json').write_text(json.dumps(world.diagnostics(),indent=2)+'\n')
    world.close(); events.close(); samples.close()

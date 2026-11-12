"""Read-only live Pi camera/telemetry viewer for genuine screen recordings.

No motion commands, target changes, ARM or recovery requests are sent.
Display refresh is independent of, and is not a measurement of, capture FPS.
"""
import argparse
import base64
from datetime import datetime, timezone
import json
import time
import urllib.request
import tkinter as tk
import cv2
import numpy as np

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:17000')
    parser.add_argument('--seconds',type=float,default=1800)
    args=parser.parse_args()
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def get(path):
        with opener.open(args.url+'/'+path,timeout=2) as reply: return json.load(reply)
    title='Quadruped107 - REAL Pi camera / VIRTUAL actuators'
    window=tk.Tk();window.title(title)
    label=tk.Label(window);label.pack()
    closed=[False]
    def close(): closed[0]=True
    window.protocol('WM_DELETE_WINDOW',close);window.bind('<Escape>',lambda event:close())
    start=time.monotonic()
    while not closed[0] and time.monotonic()-start<args.seconds:
        canvas=np.full((650,1120,3),24,np.uint8)
        lines=[datetime.now(timezone.utc).isoformat(timespec='seconds'),
               'REAL USB CAMERA | VIRTUAL OUTPUTS ONLY']
        try:
            frame=get('qualification/frame');state=get('api/state')
            raw=cv2.imdecode(np.frombuffer(base64.b64decode(frame['annotatedJpeg']),np.uint8),cv2.IMREAD_COLOR)
            canvas[100:580,:640]=cv2.resize(raw,(640,480))
            m=state['motion'];s=state['sensors'];b=state['bridge'];v=state['vision'];c=state['camera']
            lines += [f"Target mode: {frame['targetColor']} | frame {frame['sequence']}",
                f"Camera: {c['actualFps']} FPS | processing: {v.get('processingFps')} FPS",
                f"Frame age: {c['frameAge']:.3f} s",
                f"Decision: {state['autonomy']['state']}",
                f"Enabled: {m['enabled']} | intent age: {m['intentAgeS']:.3f} s",
                f"Virtual motion: {state['link']['activeMotion']} | mask: {state['link']['activeMask']}",
                f"UDP connected: {b['connected']} | ack age: {b['ackAge']}",
                f"Front range: {s['front_m']} m",
                f"Sensor fault: {s['fault']}",f"Motion fault: {m['fault']}",
                'Display refresh ~2 Hz; camera FPS comes from capture owner.',
                'Requested targets are not measured PyBullet joint positions.']
        except Exception as error: lines += ['READ FAILURE: '+str(error)[:75]]
        for i,line in enumerate(lines):
            x,y=(12,30+i*30) if i<2 else (650,110+(i-2)*36)
            cv2.putText(canvas,line,(x,y),cv2.FONT_HERSHEY_SIMPLEX,.44,(220,230,220),1,cv2.LINE_AA)
        label.image=tk.PhotoImage(data=cv2.imencode('.ppm',canvas)[1].tobytes())
        label.configure(image=label.image);window.update();time.sleep(.5)
    window.destroy()

if __name__=='__main__': main()

"""Real V4L2 camera benchmark. No image retention or actuator interfaces.

Run with exclusive camera ownership. Capture FPS and detector processing FPS
use separate monotonic durations. Failed reads are observable; driver-level
dropped frames cannot be inferred from OpenCV read success alone.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import resource
import time
import cv2
from quadruped.vision import detect_blue_ball

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=300)
    args=parser.parse_args()
    records=[]
    for width,height,request_fps,duration in ((640,480,8,20),(640,480,30,args.seconds),(320,240,30,args.seconds)):
        cap=cv2.VideoCapture('/dev/video0',cv2.CAP_V4L2)
        if not cap.isOpened(): raise RuntimeError('Real USB camera failed to open')
        properties={}
        for name,key,value in [('fourcc',cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc(*'YUYV')),
                               ('width',cv2.CAP_PROP_FRAME_WIDTH,width),('height',cv2.CAP_PROP_FRAME_HEIGHT,height),
                               ('fps',cv2.CAP_PROP_FPS,request_fps),('buffers',cv2.CAP_PROP_BUFFERSIZE,1)]:
            properties[name]=dict(requested=value,accepted=cap.set(key,value),reported=cap.get(key))
        started_utc=datetime.now(timezone.utc).isoformat()
        start=time.monotonic()
        cpu=time.process_time()
        latencies=[]
        process=[]
        failed=0
        dimensions=None
        samples=[]
        try:
            while time.monotonic()-start<duration:
                before=time.monotonic()
                ok,frame=cap.read()
                after=time.monotonic()
                if not ok or frame is None:
                    failed+=1
                    if failed>20: raise RuntimeError('Repeated capture failures')
                    continue
                dimensions=[frame.shape[1],frame.shape[0]]
                latencies.append((after-before)*1000)
                detect_blue_ball(frame)
                process.append(time.monotonic()-after)
                if not samples or time.monotonic()-samples[-1]['at_monotonic_s']>=5:
                    samples.append(dict(at_monotonic_s=time.monotonic(),elapsed_s=time.monotonic()-start,
                      captured=len(latencies),failed=failed,cpu_s=time.process_time()-cpu,
                      max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
        finally: cap.release()
        elapsed=time.monotonic()-start
        ordered=sorted(latencies)
        record=dict(started_utc=started_utc,ended_utc=datetime.now(timezone.utc).isoformat(),source='REAL PI USB V4L2',
          resolution=dimensions,properties=properties,duration_s=elapsed,successful_frames=len(latencies),
          failed_frames=failed,driver_dropped_frames=None,capture_fps=len(latencies)/elapsed,
          vision_throughput_fps=len(process)/elapsed,detector_compute_capacity_fps=len(process)/sum(process),
          read_mean_ms=sum(latencies)/len(latencies),read_p95_ms=ordered[int(.95*(len(ordered)-1))],
          process_mean_ms=1000*sum(process)/len(process),process_cpu_percent=100*(time.process_time()-cpu)/elapsed,
          max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,samples=samples,
          qualification='Capture/compute benchmark only; no actuator or physical target qualification')
        records.append(record)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(records,indent=2)+'\n')
        print(json.dumps(record),flush=True)

if __name__=='__main__': main()

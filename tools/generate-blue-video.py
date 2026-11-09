"""Create labeled synthetic blue-target video for explicit file-camera demonstrations."""
import argparse
from pathlib import Path
import cv2
import numpy as np

def generate(output):
    path=Path(output)
    path.parent.mkdir(parents=True,exist_ok=True)
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*"MJPG"),8,(640,480))
    if not writer.isOpened(): raise RuntimeError("MJPG file encoder unavailable")
    try:
        for index in range(160):
            frame=np.zeros((480,640,3),dtype=np.uint8)
            seconds=index/8
            x=90 if seconds<6 else 320 if seconds<10 else 550 if seconds<16 else None
            if x is not None: cv2.circle(frame,(x,240),35,(255,0,0),-1)
            cv2.putText(frame,"SYNTHETIC target fixture",(10,30),cv2.FONT_HERSHEY_SIMPLEX,.6,(255,255,255),1)
            writer.write(frame)
    finally: writer.release()
    return path

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",default="build/simulation/blue-target.avi")
    print(generate(parser.parse_args().output))

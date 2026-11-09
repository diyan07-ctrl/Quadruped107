"""Deterministic geometry/proxy diagnostic; commanded motion is explicit virtual data."""
import json
from .twin import World
from .environment import Scene
from quadruped.virtual_uno import VirtualUno

def main():
    clock=[0.]
    world=World()
    scene=Scene(world,"single_obstacle",clock=lambda:clock[0],latency=0,proxy=True)
    engine=VirtualUno(clock=lambda:clock[0])
    records=[]
    try:
        engine.feed(b"HELLO\nARM 1\nMOVE 2 forward\n")
        for step in range(720):
            clock[0]+=1/240
            engine.feed(b"PING\n")
            engine.advance()
            frame=engine.snapshot()
            scene.advance(frame)
            world.apply(frame)
            world.step()
            if step%120==0:
                records.append(dict(step=step,world=world.diagnostics(),sensors=scene.telemetry()))
        print("PROXY_PROBE_JSON="+json.dumps(records,sort_keys=True))
    finally: world.close()
if __name__=="__main__": main()

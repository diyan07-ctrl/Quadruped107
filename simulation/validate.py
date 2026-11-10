"""Deterministic accelerated articulation evidence; not a physical gait qualification."""
import json
from pathlib import Path
from .twin import World, SimulationFault
from quadruped.virtual_uno import VirtualUno

def main():
    output=Path("build/simulation")
    output.mkdir(parents=True,exist_ok=True)
    reports=[]
    for name in ("stand","initial","forward","backward","turn_left","turn_right","greeting","tail_wag"):
        clock=[0.0]
        engine=VirtualUno(clock=lambda:clock[0])
        world=World()
        signatures=set()
        try:
            engine.feed(b"HELLO\nARM 1\n")
            engine.feed(("MOVE 2 "+name+"\n").encode())
            for step in range(2400):
                clock[0]+=1/240
                engine.feed(b"PING\n")
                engine.advance()
                frame=engine.snapshot()
                signatures.add(tuple(frame["targets"]))
                world.apply(frame)
                world.step()
                if engine.snapshot()["activeMotion"] is None and step>10: break
            if engine.snapshot()["activeMotion"]: raise RuntimeError("Virtual gait exceeded ten-second bound: "+name)
            evidence=world.diagnostics()
            evidence.update(motion=name,distinctCommandedTargets=len(signatures),virtualSeconds=clock[0],
                            virtualUno=engine.snapshot(),classification="SIMULATED FIXED-BASE ARTICULATION")
            if name=="stand": world.capture(output/"stand.png")
            engine.feed(b"STOP 3\n")
            world.apply(engine.snapshot())
            if world.active_mask: raise RuntimeError("STOP left virtual motors enabled")
            reports.append(evidence)
        finally: world.close()
    # Exploratory stability probe: failure is an explicit model outcome, not a
    # locomotion acceptance pass. Production hardware is never involved.
    clock=[0.0]
    engine=VirtualUno(clock=lambda:clock[0])
    world=World(free_base=True)
    stability=dict(classification="PROVISIONAL FREE-BASE GRAVITY PROBE",outcome="NOT TESTED")
    try:
        engine.feed(b"HELLO\nARM 1\nMOVE 2 stand\n")
        try:
            for _ in range(720):
                clock[0]+=1/240
                engine.feed(b"PING\n")
                engine.advance()
                world.apply(engine.snapshot())
                world.step()
            stability["outcome"]="No configured fall/tilt/divergence fault in three virtual seconds"
        except SimulationFault as error:
            stability["outcome"]="MODEL FAULT: "+str(error)
        stability["diagnostics"]=world.diagnostics()
        stability["physicalLocomotionValidated"]=False
    finally: world.close()
    data=dict(stabilityProbe=stability,host="GitHub Actions when run by CI; not Raspberry Pi",physicalValidation=False,routines=reports)
    (output/"articulation.json").write_text(json.dumps(data,indent=2)+"\n")
    print(json.dumps(data,sort_keys=True))
if __name__=="__main__": main()

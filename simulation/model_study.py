"""Controlled provisional-model sensitivity study; no collision removal or torque increase."""
import json
from pathlib import Path
import tempfile
from .twin import World, MODEL
from quadruped.virtual_uno import VirtualUno


def experiment(motion,gain=.1,inertia_scale=1.0,*,warm_start=False,target_rate=0.0):
    params=json.loads((MODEL/"parameters.json").read_text())
    # Diagnostic sensitivity only. No canonical masses or physical calibration change.
    for key in ("base_mass_kg","upper_mass_kg","lower_and_foot_mass_kg"): params[key]*=inertia_scale
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/"parameters.json"
        path.write_text(json.dumps(params))
        world=World(parameters=path,position_gain=gain,target_rate=target_rate)
        clock=[0.]
        engine=VirtualUno(clock=lambda:clock[0])
        try:
            engine.feed(b"HELLO\nARM 1\n")
            warmup=None
            if warm_start:
                engine.feed(b"MOVE 0 stand\n")
                finished=None
                for _ in range(1000):
                    clock[0]+=1/240
                    engine.feed(b"PING\n")
                    engine.advance()
                    world.apply(engine.snapshot())
                    world.step()
                    if engine.snapshot()["activeMotion"] is None and finished is None: finished=clock[0]
                    if finished is not None and clock[0]-finished>=.5: break
                if finished is None: raise RuntimeError("Warm-up did not complete")
                warmup=world.diagnostics()
                world.start_measurement()
            engine.feed(("MOVE 2 "+motion+"\n").encode())
            completion=None
            for step in range(3000):
                clock[0]+=1/240
                engine.feed(b"PING\n")
                engine.advance()
                frame=engine.snapshot()
                world.apply(frame)
                actual=world.step()
                active=[abs(a-b) for i,(a,b) in enumerate(zip(actual,world.targets)) if frame["activeMask"]&(1<<i)]
                if engine.snapshot()["activeMotion"] is None and completion is None:
                    completion=clock[0]
                    error_at_completion=max(active,default=0.)
                if completion is not None and clock[0]-completion>=.5: break
            if completion is None: raise RuntimeError("Study routine did not finish")
            report=world.diagnostics()
            report.update(motion=motion,inertiaScale=inertia_scale,torqueCapNm=params["force_nm"],
                          errorAtCompletionRad=error_at_completion,settledErrorRad=max(active,default=0.),
                          physicalValidation=False,warmStart=warm_start,warmup=warmup)
            return report
        finally: world.close()


def main():
    reports=[]
    for motion in ("stand","forward","turn_left"):
        for gain in (.05,.1,.2): reports.append(experiment(motion,gain))
    for scale in (.5,2.): reports.append(experiment("forward",inertia_scale=scale))
    reports.append(experiment("forward",warm_start=True))
    for rate in (2.0,3.0): reports.append(experiment("forward",warm_start=True,target_rate=rate))
    reports.append(experiment("stand",target_rate=2.0))
    evidence=dict(classification="UNQUALIFIED MODEL SENSITIVITY",collisionsEnabled=True,torqueIncreased=False,
                  canonicalGeometryAndGaitsUnchanged=True,experiments=reports)
    path=Path("build/simulation/model-study.json")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(evidence,indent=2)+"\n")
    print("MODEL_STUDY_JSON="+json.dumps(evidence,sort_keys=True))
if __name__=="__main__": main()

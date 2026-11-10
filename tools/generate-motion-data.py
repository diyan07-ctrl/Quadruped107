"""Derive virtual target data from preserved Uno tables; review recipes on firmware change."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "software/pi/quadruped/data/motions.json"


def generate():
    raw = (ROOT / "firmware/uno/sketch/motion.h").read_bytes()
    text = raw.decode("utf-8")
    constants = {name:int(value) for name,value in re.findall(r"constexpr\s+\w+\s+(\w+)\s*=\s*(\d+)\s*;", text)}
    tables = {}
    for name, body in re.findall(r"const ServoTarget (\w+)\[\] = \{(.*?)\};", text, re.S):
        tables[name] = [[constants[channel], int(tick)] for channel,tick in re.findall(r"\{(Channel\w+),\s*(\d+)\}", body)]
    def target(name, delay="SmoothStepDelayMs"):
        return {"table":name, "delay_ms":constants[delay]}
    def pause(name): return {"pause_ms":constants[name]}
    stand = [target("StandShoulders"), pause("MotionStageDelayMs"), target("StandLegs")]
    routines = {
        "stand": stand,
        "initial": [target("InitialLegs","InitialArmsStepDelayMs"), pause("MotionStageDelayMs"), target("InitialShoulders")],
        "greeting": stand + [pause("MotionStageDelayMs"), target("GreetingSupportShoulders"),
            pause("MotionStageDelayMs"), target("GreetingSupportLegs"), pause("MotionStageDelayMs")] +
            [item for _ in range(constants["GreetingWaveCycles"]) for item in
                [target("GreetingShoulderForward"),pause("GreetingWavePauseMs"),target("GreetingShoulderBack"),pause("GreetingWavePauseMs")]] +
            [target("GreetingReturnFLToStand"),pause("MotionStageDelayMs"),target("GreetingReturnBRToStand")],
        "tail_wag": stand + [pause("MotionStageDelayMs"),target("TailWagPose"),pause("MotionStageDelayMs")] +
            [item for _ in range(constants["TailWagCycles"]) for item in
                [target("TailWagSideA"),pause("TailWagPauseMs"),target("TailWagSideB"),pause("TailWagPauseMs")]] + stand,
    }
    for name,prefix in (("forward","Forward"),("backward","Backward"),("turn_left","TurnLeft"),("turn_right","TurnRight")):
        names = ["ForwardPrepare","ForwardLiftA",prefix+"PlaceA","ForwardPlantA",prefix+"PushA",
                 "ForwardLiftB",prefix+"PlaceB","ForwardPlantB",prefix+"PushB"]
        routines[name] = [item for table in names for item in [target(table,"GaitStepDelayMs"),pause("GaitFramePauseMs")]]
    if len(tables) != 34: raise ValueError("Firmware table count changed; review recipe translator")
    return dict(schema=1, firmware_sha256=hashlib.sha256(raw).hexdigest(),
                constants=constants, tables=tables, routines=routines)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args=parser.parse_args()
    data=generate()
    if args.check:
        if json.loads(DEST.read_text()) != data: raise SystemExit("Virtual motion data differs from firmware; regenerate/review")
        print("Virtual target data matches preserved firmware tables.")
    else:
        DEST.parent.mkdir(parents=True,exist_ok=True)
        DEST.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")

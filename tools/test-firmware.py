"""Compile and execute deterministic native Arduino mocks; never opens hardware."""
import argparse
from pathlib import Path
import subprocess
import os

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zig',type=Path)
    args=parser.parse_args()
    out=ROOT/'build/phase5/native'
    out.mkdir(parents=True,exist_ok=True)
    compiler=[str(args.zig.resolve()),'c++'] if args.zig else ['g++']
    env=dict(os.environ,ZIG_LOCAL_CACHE_DIR=str(out/'cache'),ZIG_GLOBAL_CACHE_DIR=str(out/'global'))
    variants=[('policy','firmware_policy.cpp',[]),
              ('sensor-default','firmware_sensor.cpp',[]),
              ('sensor-configured','firmware_sensor.cpp',['-DURM37_PROFILE=1','-DTOUCH_ENABLED_MASK=31']),
              ('sensor-active-low','firmware_sensor.cpp',['-DURM37_PROFILE=1','-DTOUCH_ENABLED_MASK=7','-DTOUCH_ACTIVE_LOW_MASK=7']),
              ('calibration-disabled','firmware_calibration.cpp',[]),
              ('calibration-reviewed-unknown','firmware_calibration.cpp',['-DDIRECT_COMMISSIONING_REVIEWED=1'])]
    for name,source,defines in variants:
        binary=out/(name+('.exe' if os.name=='nt' else ''))
        command=compiler+['-std=c++11','-Wall','-Wextra','-Werror','-Wno-unused-function',
            '-Wno-unused-variable','-include',str(ROOT/'tests/firmware_fake/Arduino.h'),
            '-I'+str(ROOT/'tests/firmware_fake'),
            '-I'+str(ROOT/'firmware/uno/libraries/QuadrupedSafety/src'),*defines,
            str(ROOT/'tests'/source),'-o',str(binary)]
        subprocess.run(command,cwd=ROOT,env=env,check=True)
        subprocess.run([str(binary)],cwd=ROOT,check=True)
        print(name+' PASS',flush=True)
    print(f'{len(variants)} firmware mock executables PASS')

if __name__=='__main__': main()

"""Evidence-backed compile/mock qualification. Never probes or uploads hardware."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arduino-cli',type=Path,required=True)
    parser.add_argument('--zig',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'build/phase5/firmware-evidence')
    args=parser.parse_args()
    output=args.output.resolve(); output.mkdir(parents=True,exist_ok=True)
    git=['git','-c','safe.directory='+str(ROOT)]
    commit=subprocess.check_output(git+['rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    dirty=subprocess.check_output(git+['status','--porcelain'],cwd=ROOT,text=True).splitlines()
    native=[sys.executable,'tools/test-firmware.py']
    if args.zig: native+=['--zig',str(args.zig.resolve())]
    checks=[('native',native),('virtual-generate',[sys.executable,'tools/generate-virtual-firmware.py'])]
    for name,path,flags in (
        ('sensor-default','firmware/uno/sensor_only',[]),
        ('sensor-configured','firmware/uno/sensor_only',['--build-property','compiler.cpp.extra_flags=-DURM37_PROFILE=1 -DTOUCH_ENABLED_MASK=31']),
        ('sensor-three-low','firmware/uno/sensor_only',['--build-property','compiler.cpp.extra_flags=-DURM37_PROFILE=1 -DTOUCH_ENABLED_MASK=7 -DTOUCH_ACTIVE_LOW_MASK=7']),
        ('calibration','firmware/uno/direct_calibration',[]),
        ('production','firmware/uno/sketch',[]),
        ('virtual','build/virtual/sketch',[])):
        checks.append((name,[str(args.arduino_cli.resolve()),'compile','--profile','uno',
                      '--build-path',str(ROOT/'build/phase5/compiled'/name),*flags,path]))
    results=[]
    for name,command in checks:
        started=datetime.now(timezone.utc).isoformat(); before=time.monotonic()
        with (output/(name+'.log')).open('w',encoding='utf-8') as log:
            result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=600)
        row=dict(id=name,commit=commit,dirtyPathsAtStart=dirty,command=command,
                 startedUtc=started,durationS=round(time.monotonic()-before,3),
                 result='PASS' if result.returncode==0 else 'FAIL',exitCode=result.returncode,
                 physicalVerification=False,log=name+'.log')
        results.append(row)
        (output/'matrix.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
        print(name,row['result'],flush=True)
    return int(any(row['exitCode'] for row in results))

if __name__=='__main__': raise SystemExit(main())

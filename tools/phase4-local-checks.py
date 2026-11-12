"""Run existing software checks with timestamped, reproducible Phase 4 evidence.

No camera, physical serial, GPIO, firmware upload or physical ARM is used.
This runner does not qualify Raspberry Pi hardware or LAN integration.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    for name in ('environment','preflight','camera','vision','udp','pybullet','autonomy',
                 'safety','endurance','videos','screenshots','reports'):
        (out/name).mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['PYTHONPATH'] = str(ROOT/'software/pi')
    env['PYTHONIOENCODING'] = 'utf-8'
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    checks = [
        ('ENV-WIN','environment', ['git','status','--short','--branch']),
        ('ENV-DEPS','environment', [sys.executable,'-c',
          'import sys,platform,json,cv2,numpy,flask,serial,pybullet; from importlib.metadata import version; '
          'print(json.dumps(dict(python=sys.version,platform=platform.platform(),executable=sys.executable,'
          'opencv=cv2.__version__,packages={k:version(k) for k in ["numpy","Flask","pyserial","pybullet"]}),indent=2))']),
        ('REG-PIP','environment',[sys.executable,'-m','pip','check']),
        ('REG-PY','reports',[sys.executable,'-m','unittest','discover','-s','tests','-v']),
        ('REG-CAD','pybullet',[sys.executable,'simulation/build_model.py','--check']),
        ('REG-MOTION','autonomy',[sys.executable,'tools/generate-motion-data.py','--check']),
        ('REG-POWER','safety',[sys.executable,'hardware/Power/power_budget.py','--check']),
        ('REG-SIM','pybullet',[sys.executable,'-m','simulation.validate']),
        ('REG-MODEL','pybullet',[sys.executable,'-m','simulation.model_study']),
        ('REG-PROXY','autonomy',[sys.executable,'-m','simulation.proxy_probe']),
        ('REG-JS','reports',['node','--check','software/pi/quadruped/web/app.js']),
        ('REG-DOM','reports',['node','tools/check-dashboard.mjs']),
        ('REG-REPO','reports',['node','tools/check-repository.mjs']),
        ('REG-DIAGRAM','reports',['node','tools/check-mermaid.mjs']),
    ]
    records = []
    for ident, group, command in checks:
        started = datetime.now(timezone.utc).isoformat()
        clock = time.monotonic()
        path = out/group/(ident+'.log')
        with path.open('w',encoding='utf-8') as log:
            log.write(json.dumps(dict(id=ident,started_utc=started,commit=commit,
                                     argv=command,cwd=str(ROOT)))+'\n')
            log.flush()
            try:
                result = subprocess.run(command,cwd=ROOT,env=env,stdout=log,
                                        stderr=subprocess.STDOUT,timeout=600)
                code = result.returncode
            except (OSError,subprocess.TimeoutExpired) as error:
                log.write(repr(error)+'\n')
                code = -1
        record = dict(id=ident,date_utc=started,commit=commit,command=command,
                      objective=ident,preconditions='Windows software environment; physical outputs unused',
                      expected='Exit 0',actual=f'Exit {code}',result='PASS' if code==0 else 'FAIL',
                      duration_s=round(time.monotonic()-clock,3),exit_code=code,
                      log=str(path.relative_to(out)),classification='SOFTWARE / SIMULATED ONLY',
                      hardware_validation=False,recordings=[],issues=[],fixes=[])
        records.append(record)
        (out/'reports/local-checks.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
        print(ident,record['result'],record['duration_s'],flush=True)
    return int(any(row['exit_code'] for row in records))

if __name__ == '__main__':
    raise SystemExit(main())

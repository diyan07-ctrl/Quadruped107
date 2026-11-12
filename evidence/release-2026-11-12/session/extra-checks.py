import ast
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

root=Path.cwd(); output=root/'build/release/extra'; output.mkdir(parents=True,exist_ok=True)
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
env=dict(os.environ,PYTHONPATH=str(root/'software/pi'),PYTHONIOENCODING='utf-8')
commands=[('compileall',[sys.executable,'-m','compileall','-q','software/pi/quadruped','tools','tests','simulation']),
          ('freeze',[sys.executable,'-m','pip','freeze']),
          ('wheel',[sys.executable,'-m','pip','wheel','--no-deps','--no-build-isolation','software/pi','-w',str(output/'wheels')]),
          ('vision',[sys.executable,'tools/evaluate-vision.py','--compare-ref','488b837','--output',str(output/'vision-comparison.json')]),
          ('recording',[sys.executable,'-m','simulation.twin','--headless','--demo','forward','--arm-demo','--steps','240','--record',str(output/'virtual-forward.avi'),'--report',str(output/'virtual-forward.json')])]
rows=[]
def run(name,command):
    start=time.monotonic()
    with (output/(name+'.log')).open('w',encoding='utf-8') as log:
        log.write(json.dumps(dict(commit=commit,command=command,startedUtc=datetime.now(timezone.utc).isoformat()))+'\n');log.flush()
        result=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    rows.append(dict(id=name,commit=commit,command=command,exitCode=result.returncode,result='PASS' if result.returncode==0 else 'FAIL',durationS=time.monotonic()-start))
    (output/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n')
for name,command in commands: run(name,command)
wheel=next((output/'wheels').glob('*.whl')); unpack=output/'installed-wheel'
with zipfile.ZipFile(wheel) as archive: archive.extractall(unpack)
tree=ast.parse((root/'tools/check-installed.py').read_text())
code=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in node.targets))
run('installed-wheel',[sys.executable,'-c','import sys; sys.path.insert(0,'+repr(str(unpack))+'); import quadruped; assert quadruped.__file__.startswith('+repr(str(unpack))+'); '+code])
run('firmware-source-identity',['git','diff','--exit-code','a5d488c','HEAD','--','firmware','tools/test-firmware.py','tools/qualify-firmware.py','tests/firmware_sensor.cpp'])
print(json.dumps(rows,indent=2))
raise SystemExit(int(any(row['exitCode'] for row in rows)))

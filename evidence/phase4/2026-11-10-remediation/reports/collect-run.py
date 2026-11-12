import argparse,gzip,hashlib,json,subprocess,time
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('run');args=parser.parse_args()
assert args.run in ('headless-fiveg-905','gui-fiveg-905')
root=Path('evidence/phase4/2026-11-10-remediation');art=Path('build/phase4-remediation/public-artifacts')
out=root/'endurance'/args.run;out.mkdir(parents=True,exist_ok=True)
records=[]
for name in ['result.json','console.log','samples.jsonl']:
    target=(art/'endurance'/args.run/'samples.jsonl.gz') if name=='samples.jsonl' else out/name
    target.parent.mkdir(parents=True,exist_ok=True)
    command=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','diyan07@192.168.1.42',
        ('gzip -c ' if name=='samples.jsonl' else 'cat ')+'Quadruped107-phase4-qualification/build/phase4-remediation/'+args.run+'/'+name]
    with target.open('wb') as stream: result=subprocess.run(command,stdout=stream,stderr=subprocess.PIPE,timeout=300)
    assert result.returncode==0,result.stderr.decode()
    records.append(dict(path=str(target),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size,command=command))
    print(target,target.stat().st_size,flush=True)
(out/'collection.json').write_text(json.dumps(records,indent=2)+'\n')

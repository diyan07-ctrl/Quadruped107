from pathlib import Path
import gzip,hashlib,json,shutil,struct,zipfile
root=Path('evidence/phase4/2026-11-10-remediation');build=Path('build/phase4-remediation');art=build/'public-artifacts'
records=[]
# A cancelled bulk transfer cannot be called a complete runtime log.
partial=art/'runtime/pi-v4/state.jsonl.gz'
if partial.exists():
    total=0;valid=True
    try:
        with gzip.open(partial,'rb') as stream:
            while chunk:=stream.read(1024*1024): total+=len(chunk)
    except (EOFError,OSError): valid=False
    complete=valid and total==2889992107
    print('Pi-v4 gzip',valid,total,'complete',complete,flush=True)
    if not complete:
        target=build/'incomplete-transfer-pi-v4.jsonl.gz'
        assert partial.resolve().is_relative_to(Path.cwd()) and target.resolve().is_relative_to(Path.cwd())
        partial.rename(target)
        (root/'reports/interrupted-transfer.json').write_text(json.dumps(dict(sourceBytes=2889992107,receivedUncompressedBytes=total,validGzip=valid,complete=False,sourceRetainedOnPi=True)))
for twin in ['twin-headless','twin-qpc','twin-retry','twin-cache','twin-robust','twin-gui','twin-fiveg','twin-gui-fiveg']:
    folder=build/twin
    if not folder.exists(): continue
    (root/'pybullet'/twin).mkdir(parents=True,exist_ok=True)
    for name in ['trace.jsonl','result.json']:
        source=folder/name
        if not source.exists(): continue
        target=(art/'pybullet'/twin/(name+'.gz')) if name.endswith('.jsonl') else (root/'pybullet'/twin/name)
        target.parent.mkdir(parents=True,exist_ok=True)
        with source.open('rb') as src, (gzip.open(target,'wb') if name.endswith('.jsonl') else target.open('wb')) as dst: shutil.copyfileobj(src,dst,1024*1024)
    (root/'pybullet'/twin/'README.md').write_text(f'# {twin}\n\nFull trace: `pybullet/{twin}/trace.jsonl.gz` in the [remediation release archive](https://github.com/diyan07-ctrl/Quadruped107/releases/tag/phase4-remediation-evidence-2026-11-10).\n\nA missing result JSON indicates an interrupted source; idle/disarmed runtime is not endurance.\n')
for file in (build/'retry-smoke').glob('*'):
    target=root/'endurance/windows-owned'/file.name;target.parent.mkdir(parents=True,exist_ok=True)
    if file.suffix=='.jsonl':
        with gzip.open(target.with_suffix('.jsonl.gz'),'wb') as stream: stream.write(file.read_bytes())
    else: target.write_bytes(file.read_bytes())
for source,target in [('recording-sample-v2.mp4','viewer-fault-latch-sample.mp4'),('gui-capture-sample.mp4','gui-capture-failed-black-pybullet.mp4')]:
    dest=art/'videos'/target;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(build/source,dest)
shutil.copyfile(build/'recording-sample-v2.png',root/'screenshots/recording-sample-v2.png')
for name in ['recording-sample.log','recording-sample-v2.log','gui-capture-sample.log']:
    dest=root/'videos'/name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(build/name,dest)
for file in art.rglob('*'):
    if file.is_file(): records.append(dict(path=file.relative_to(art).as_posix(),bytes=file.stat().st_size,sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
(art/'MANIFEST.json').write_text(json.dumps(records,indent=2)+'\n')
(root/'reports/artifacts.json').write_text(json.dumps(records,indent=2)+'\n')
archive=build/'phase4-remediation-evidence-2026-11-10.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as target:
    for file in art.rglob('*'):
        if file.is_file(): target.write(file,file.relative_to(art))
(root/'reports/archive.json').write_text(json.dumps(dict(file=archive.name,bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),url='https://github.com/diyan07-ctrl/Quadruped107/releases/download/phase4-remediation-evidence-2026-11-10/'+archive.name),indent=2)+'\n')
print('Archive',archive.stat().st_size,flush=True)

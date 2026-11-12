import argparse,gzip,json,statistics
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('run');parser.add_argument('twin');args=parser.parse_args()
root=Path('evidence/phase4/2026-11-10-remediation');art=Path('build/phase4-remediation/public-artifacts')
out=root/'endurance'/args.run
r=json.loads((out/'result.json').read_text())
values={k:[] for k in ('captureFps','visionFps','cameraAgeS','frontAgeS','intentAgeS','ackAgeS','cpuPercent','rssBytes')}
source_stamps=[];unhealthy=[];times=[];first=None;last=None
with gzip.open(art/'endurance'/args.run/'samples.jsonl.gz','rt') as stream:
 for line in stream:
    row=json.loads(line);s=row['state'];times.append(row['elapsedS'])
    if first is None: first=s
    last=s
    vals=[s['camera']['actualFps'],s['vision']['processingFps'],s['camera']['frameAge'],s['sensors']['observations']['urm37']['age'],s['motion']['intentAgeS'],s['bridge']['ackAge'],s['system']['processCpuPercent'],s['system']['rssBytes']]
    for key,value in zip(values,vals):
        if value is not None: values[key].append(value)
    source_stamps.append(s['sensors']['diagnostics']['recentBatches'][-1]['ranges']['urm37']['sampledAtSenderMonotonic'])
    if not(s['motion']['enabled'] and s['link']['armed'] and s['link']['activeMask'] and s['bridge']['connected'] and not s['sensors']['fault'] and s['camera']['available']): unhealthy.append(row['elapsedS'])
def stats(v):
    v=sorted(v)
    return dict(n=len(v),min=min(v),mean=statistics.mean(v),p50=v[int((len(v)-1)*.5)],p95=v[int((len(v)-1)*.95)],p99=v[int((len(v)-1)*.99)],max=max(v))
physics=[];udp_rejected=0;udp_traces=0
source_start,source_end=min(source_stamps),max(source_stamps)
for line in (Path('build/phase4-remediation')/args.twin/'trace.jsonl').open():
    row=json.loads(line)
    if source_start<=row['localMonotonic']<=source_end:
        if row['kind']=='physics': physics.append(row)
        elif row['kind']=='udp':
            udp_rejected+=bool(row.get('rejected'))
            udp_traces+=row.get('messageType')=='trace'
spans=[];born=None;previous=None;bad=0
for row in physics:
    healthy=row['receiver']['armed'] and row['receiver']['activeMask'] and row['receiver']['fault'] is None
    if healthy:
        if born is None: born=row['localMonotonic']
        previous=row['localMonotonic']
    else:
        bad+=1
        if born is not None: spans.append(previous-born);born=None
if born is not None: spans.append(previous-born)
active=[row for row in physics if row['receiver']['armed'] and row['receiver']['activeMask']]
windows=[]
for start in range(0,int(max(source_stamps)-min(source_stamps))-9,10):
    chunk=[row for row in active if start<=row['localMonotonic']-min(source_stamps)<start+10]
    if chunk: windows.append(dict(startSourceOffsetS=start,samples=len(chunk),jointRangesRad=[max(row['actualJointRad'][i] for row in chunk)-min(row['actualJointRad'][i] for row in chunk) for i in range(8)]))
summary=dict(run=args.run,requestedResult=r['result'],durationS=r['durationS'],samples=len(times),unhealthySampleTimesS=unhealthy,
    metrics={k:stats(v) for k,v in values.items() if v},maximumStateSampleGapS=max(b-a for a,b in zip(times,times[1:])),
    sensorRejectionsDelta=last['sensors']['rejected']-first['sensors']['rejected'],bridgeErrorsDelta=last['bridge']['errors']-first['bridge']['errors'],
    sensorRejectionReasonsDelta={k:v-first['sensors']['diagnostics']['rejectionReasons'].get(k,0) for k,v in last['sensors']['diagnostics']['rejectionReasons'].items()},
    sourceRejectedDatagrams=udp_rejected,sourceTraceDatagrams=udp_traces,
    sourceAlignment='Source acquisition timestamps retained by Pi are matched to the same Windows monotonic clock; no cross-host one-way latency calculation',
    sourceStart=min(source_stamps),sourceEnd=max(source_stamps),sourcePhysicsSamples=len(physics),inactiveSourceSamples=bad,
    longestContinuousHealthySourceS=max(spans,default=0),maximumPhysicsTickS=max(row['tickMaxS'] for row in physics),
    measuredJointRangesRad=[max(row['actualJointRad'][i] for row in active)-min(row['actualJointRad'][i] for row in active) for i in range(8)],
    tenSecondMovementWindows=windows,automaticRearm=r['automaticRearm'],journalDrops=r['journalDrops'])
summary['result']='PASS' if r['result']=='PASS' and not unhealthy and max(spans,default=0)>=900 and all(min(w['jointRangesRad'])>.03 for w in windows) else 'FAIL'
(out/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('metrics','tenSecondMovementWindows')},indent=2))

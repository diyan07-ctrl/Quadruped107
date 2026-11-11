"""Derive qualification measurements from genuine saved Pi and twin samples."""
import gzip,json,statistics
from pathlib import Path
root=Path('evidence/phase4/2026-11-10')
def read(path):
    rows=[]
    with gzip.open(path,'rt') as file:
        for line in file:
            try: rows.append(json.loads(line))
            except json.JSONDecodeError: pass  # live snapshot may end in a partial final line
    return rows
pi=read(root/'endurance/pi-state.jsonl.gz')
joints=read(root/'pybullet/joints.jsonl.gz')
packets=read(root/'pybullet/packets.jsonl.gz')
def stats(rows,section,key):
    values=[r.get(section,{}).get(key) for r in rows]
    values=[v for v in values if isinstance(v,(int,float))]
    return dict(n=len(values),mean=statistics.mean(values),minimum=min(values),maximum=max(values)) if values else None
segments=[]; current=[]
for row in pi:
    good=(row['camera']['available'] and row['bridge']['connected'] and not row['sensors']['fault'])
    if current and row['elapsed_s']-current[-1]['elapsed_s']>2.5:
        segments.append(current); current=[]
    if good: current.append(row)
    elif current: segments.append(current); current=[]
if current: segments.append(current)
best=max(segments,key=lambda s:s[-1]['elapsed_s']-s[0]['elapsed_s'])
window=[r for r in best if r['elapsed_s']<=best[0]['elapsed_s']+901]
active=[r for r in joints if r['receiver']['armed'] and r['receiver']['activeMask']]
movement=[]
for i in range(8):
    values=[r['actual_joint_positions_rad'][i] for r in active]
    ticks=[r['requested_targets_ticks'][i] for r in active]
    movement.append(dict(channel=i,actual_min_rad=min(values),actual_max_rad=max(values),
       actual_range_rad=max(values)-min(values),requested_min_ticks=min(ticks),requested_max_ticks=max(ticks)))
colors={}
for color in ('blue','yellow'):
    rows=[r for r in pi if r['vision'].get('targetColor')==color]
    detections=[r for r in rows if r['vision'].get('blueBall',{}).get('detected')]
    positions={name:[] for name in ('left','center','right')}
    for row in detections:
        ball=row['vision']['blueBall']; offset=ball['offset']
        label='left' if offset<-.32 else 'right' if offset>.32 else 'center'
        if len(positions[label])<4:
            positions[label].append(dict(utc=row['utc'],x=ball['x'],y=ball['y'],offset=offset,
              lock=ball.get('lockState'),revision=ball.get('revision'),radius=ball.get('radius')))
    colors[color]=dict(samples=len(rows),detected_samples=len(detections),positions=positions,
       missing_samples=len(rows)-len(detections),lock_ids=sorted(set(r['vision']['blueBall'].get('lockId',0) for r in detections)))
report=dict(source_commit='d29dfdbfc42f6f49c0e96837cc53d816bbf8a47e',classification='REAL PI USB / REAL LAN / VIRTUAL OUTPUTS',
 full_log=dict(samples=len(pi),first_utc=pi[0]['utc'],last_utc=pi[-1]['utc'],duration_s=pi[-1]['elapsed_s']-pi[0]['elapsed_s']),
 longest_healthy_segment_s=best[-1]['elapsed_s']-best[0]['elapsed_s'],
 endurance_window=dict(first_utc=window[0]['utc'],last_utc=window[-1]['utc'],duration_s=window[-1]['elapsed_s']-window[0]['elapsed_s'],
  samples=len(window),enabled_samples=sum(r['motion']['enabled'] for r in window),
  note='Mostly disarmed integration observation with short deliberate manual command intervals; not sustained autonomous pursuit.',
  camera_reported_ema_fps=stats(window,'camera','actualFps'),vision_reported_fps=stats(window,'vision','processingFps'),
  cpu_percent_one_core=stats(window,'system','processCpuPercent'),rss_bytes=stats(window,'system','rssBytes'),
  frame_age_s=stats(window,'camera','frameAge'),camera_error_count=max(r['camera']['errors'] for r in window),
  udp_error_count=max(r['bridge']['errors'] for r in window),max_sensor_rejected_count=max(r['sensors']['rejected'] for r in window)),
 actual_joint_movement=movement,colors=colors,
 rejected_udp_records=sum(p.get('rejected',False) for p in packets),world_fault_samples=sum(bool(r['world_fault']) for r in joints))
(root/'reports/runtime-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='colors'},indent=2))
print(json.dumps(colors,indent=2))

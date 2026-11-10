"""Observe a physical yellow target; explicit single enable, never auto re-arm."""
from datetime import datetime,timezone
import base64,json,runpy,time
from pathlib import Path
c=runpy.run_path('evidence/phase4/2026-11-10/reports/live-client.py')
api=c['api']; samples=[]; saved=set(); result={}
try:
    c['stop'](); c['ready']()
    c['wait'](lambda s:s['vision']['blueBall'].get('detected'),timeout=15)
    assert api('arm',{})[0]==200
    assert api('mode',dict(mode='opencv'))[0]==200
    start=time.monotonic()
    while time.monotonic()-start<120:
        api('heartbeat',{})
        state=api('state')[1]
        sample=dict(utc=datetime.now(timezone.utc).isoformat(),elapsed_s=time.monotonic()-start,
                   **{k:state[k] for k in ('camera','vision','motion','link','bridge','autonomy')})
        samples.append(sample)
        ball=state['vision']['blueBall']
        if ball.get('detected'):
            x=ball['offset']; label='left' if x<-.32 else 'right' if x>.32 else 'center'
            if label not in saved:
                image=api('camera-frame')[1]
                if image.get('data'):
                    Path('evidence/phase4/2026-11-10/screenshots/yellow-real-'+label+'.jpg').write_bytes(base64.b64decode(image['data']))
                    saved.add(label)
        time.sleep(.12)
    result=dict(source='REAL PI USB CAMERA / PHYSICAL YELLOW TENNIS BALL',automatic_rearm=False,
                observed_positions=sorted(saved),duration_s=time.monotonic()-start,samples=samples)
except Exception as error:
    result=dict(error=str(error),samples=samples)
finally:
    c['stop']()
    Path('evidence/phase4/2026-11-10/vision/yellow-live.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='samples'}))

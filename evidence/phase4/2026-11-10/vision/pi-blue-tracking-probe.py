"""Controlled physical-blue sweep/removal, one explicit enable and no re-arm."""
import base64,json,runpy,time
from pathlib import Path
c=runpy.run_path('build/hil-retest/live-client.py')
api,wait,ready,stop=[c[k] for k in ('api','wait','ready','stop')]
out=Path('build/hil-retest/blue-tracking');out.mkdir(exist_ok=True)
samples=[];saved=set();motions=set();result={}
try:
    stop();ready();wait(lambda s:s['vision']['blueBall'].get('detected'),timeout=10)
    assert api('arm',{})[0]==200
    assert api('mode',dict(mode='opencv'))[0]==200
    print('READY_FOR_PHYSICAL_BLUE_SWEEP',flush=True)
    start=time.monotonic()
    while time.monotonic()-start<180:
        api('heartbeat',{})
        state=api('state')[1]
        sample=dict(elapsed_s=time.monotonic()-start,**{k:state[k] for k in ('vision','motion','link','bridge','camera','autonomy')})
        samples.append(sample)
        if state['link'].get('activeMotion'): motions.add(state['link']['activeMotion'])
        ball=state['vision']['blueBall']
        if ball.get('detected'):
            label='left' if ball['offset']<-.32 else 'right' if ball['offset']>.32 else 'center'
            if label not in saved:
                frame=api('camera-frame')[1]
                if frame.get('data'):
                    (out/(label+'.jpg')).write_bytes(base64.b64decode(frame['data']));saved.add(label)
        if not state['motion']['enabled']:
            time.sleep(2)
            assert not api('state')[1]['motion']['enabled']
            break
        time.sleep(.12)
    reason=state['motion']['fault']
    result=dict(id='C-BLUE-LIVE',result='PASS' if {'stand','turn_left','turn_right'}<=motions and reason and 'Target lost' in reason else 'FAIL',
      duration_s=time.monotonic()-start,source='REAL PI USB / PHYSICAL BLUE OBJECT / REAL LAN',
      observed_positions=sorted(saved),accepted_motions=sorted(motions),stop_reason=reason,automatic_rearm=False,samples=samples)
except Exception as error: result=dict(id='C-BLUE-LIVE',result='FAIL',error=str(error),samples=samples)
finally:
    stop();(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='samples'}),flush=True)

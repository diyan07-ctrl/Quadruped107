"""Inject stopped real-camera acquisition; never opens a physical actuator."""
import json,runpy,time
from pathlib import Path
c=runpy.run_path('build/hil-retest/live-client.py')
api,wait,ready,stop=[c[k] for k in ('api','wait','ready','stop')]
path=Path('build/hil-retest/control.json')
def control(**changes):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(dict(action_id=time.time_ns(),**changes))); temporary.replace(path)
result=dict(id='F-CAMERA-ACQUISITION-STOP',classification='REAL CAMERA; SOFTWARE CAPTURE-WORKER FAULT INJECTION, NOT USB UNPLUG')
try:
    stop(); ready()
    wait(lambda s:s['vision']['blueBall'].get('detected'),timeout=12)
    assert api('arm',{})[0]==200
    assert api('mode',dict(mode='opencv'))[0]==200
    before=wait(lambda s:s['link']['activeMask']!=0 and s['motion']['enabled'])
    result['before']={k:before[k] for k in ('camera','vision','motion','link')}
    started=time.monotonic(); control(camera_stop=True)
    state=wait(lambda s:not s['motion']['enabled'] and not s['link']['armed'] and s['link']['activeMask']==0,timeout=4)
    result.update(result='PASS',injection_to_output_off_ms=1000*(time.monotonic()-started),
                  after={k:state[k] for k in ('camera','vision','motion','link')})
    control(camera_resume=True)
    wait(lambda s:s['camera']['available'])
    state=ready(); assert not state['motion']['enabled']
    result['automatic_rearm']=False
except Exception as error:
    result.update(result='FAIL',error=str(error))
finally:
    stop(); control(camera_resume=True)
    Path('build/hil-retest/camera-fault.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

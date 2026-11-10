"""Execute deliberate virtual manual commands on the real Pi/LAN pipeline."""
from datetime import datetime,timezone
import json
from pathlib import Path
import runpy
import time

client=runpy.run_path('evidence/phase4/2026-11-10/reports/live-client.py')
api,wait,ready,stop=[client[k] for k in ('api','wait','ready','stop')]
out=Path('evidence/phase4/2026-11-10/autonomy/manual-lan.json')
results=[]
try:
    for motion in ('stand','forward','backward','turn_left','turn_right','greeting'):
        result=dict(id='E-'+motion.upper(),started_utc=datetime.now(timezone.utc).isoformat(),
          source='REAL PI USB CAMERA + REAL LAN + VIRTUAL ACTUATORS',samples=[])
        try:
            stop(); ready()
            status,response=api('arm',{})
            assert status==200,(status,response)
            status,response=api('mode',dict(mode=motion))
            assert status==200,(status,response)
            wait(lambda s:s['link'].get('activeMotion')==motion or s['motion'].get('currentMotion')==motion,
                 motion=motion)
            until=time.monotonic()+3
            while time.monotonic()<until:
                api('heartbeat',dict(motion=motion))
                state=api('state')[1]
                assert state['physicalActuationAllowed'] is False
                result['samples'].append({k:state[k] for k in ('motion','link','bridge','camera')})
                time.sleep(.15)
            started=time.monotonic()
            state=stop()
            result.update(result='PASS',stop_api_and_observation_ms=1000*(time.monotonic()-started),
                          final_active_mask=state['link']['activeMask'])
        except Exception as error:
            result.update(result='FAIL',error=str(error))
            stop()
        results.append(result)
        out.write_text(json.dumps(results,indent=2)+'\n')
        print(result['id'],result['result'],result.get('stop_api_and_observation_ms'),flush=True)
    ready(); assert api('arm',{})[0]==200
    status,response=api('mode',dict(mode='invalid-motion'))
    assert status>=400,(status,response)
    results.append(dict(id='F-INVALID',result='PASS',http_status=status,response=response))
finally:
    stop()
    out.write_text(json.dumps(results,indent=2)+'\n')

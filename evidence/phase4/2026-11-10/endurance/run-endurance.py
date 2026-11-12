"""900-second real Pi/LAN integration run; explicit manual virtual forward.

Never re-arms after a fault. Camera/vision continue operating and are recorded;
manual forward does not establish autonomous target-following endurance.
"""
from datetime import datetime,timezone
import json,runpy,time
from pathlib import Path
c=runpy.run_path('evidence/phase4/2026-11-10/reports/live-client.py')
api,wait,ready,stop=[c[k] for k in ('api','wait','ready','stop')]
out=Path('evidence/phase4/2026-11-10/endurance')
errors=[];samples=[];start=None
try:
    stop();ready()
    assert api('arm',{})[0]==200
    assert api('mode',dict(mode='forward'))[0]==200
    before=wait(lambda s:s['link'].get('activeMotion')=='forward',motion='forward')
    start=time.monotonic();last_sample=last_progress=-1
    print('ENDURANCE_STARTED_UTC='+datetime.now(timezone.utc).isoformat(),flush=True)
    with (out/'headless-samples.jsonl').open('w') as log:
        while time.monotonic()-start<900:
            elapsed=time.monotonic()-start
            try:
                api('heartbeat',dict(motion='forward'))
                if elapsed-last_sample>=1:
                    state=api('state')[1]
                    row=dict(utc=datetime.now(timezone.utc).isoformat(),elapsed_s=elapsed,
                      **{k:state[k] for k in ('camera','vision','system','motion','bridge','link')},
                      sensors={k:state['sensors'][k] for k in ('fault','front_m','receivedAge','rejected')})
                    samples.append(row);log.write(json.dumps(row)+'\n');log.flush();last_sample=elapsed
                    healthy=(state['motion']['enabled'] and state['camera']['available'] and
                             state['bridge']['connected'] and not state['sensors']['fault'])
                    if not healthy and not errors:
                        errors.append(dict(elapsed_s=elapsed,error='Unexpected loss of enabled/fresh/connected state',state=row))
                        stop()
                if elapsed-last_progress>=30:
                    print('ENDURANCE_SECONDS',round(elapsed,1),'FAULTS',len(errors),flush=True);last_progress=elapsed
            except Exception as error:
                errors.append(dict(elapsed_s=elapsed,error=str(error)))
                try: stop()
                except Exception: pass
            time.sleep(.18)
except Exception as error:
    errors.append(dict(error=str(error)))
finally:
    try: stop()
    except Exception as error: errors.append(dict(error='Final STOP: '+str(error)))
    result=dict(id='G-ENDURANCE-HEADLESS',result='PASS' if start is not None and time.monotonic()-start>=900 and not errors else 'FAIL',
      duration_s=time.monotonic()-start if start is not None else 0,classification='REAL PI CAMERA/LAN + VIRTUAL MANUAL FORWARD',
      samples=len(samples),errors=errors,automatic_rearm=False,
      note='Actual camera/vision active; manual motion override. Not 15 minutes of autonomous ball pursuit.')
    (out/'headless-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)

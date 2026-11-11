"""Deliberate LAN fault injections. Every recovery requires an explicit API ARM."""
from datetime import datetime,timezone
import json,runpy,time
from pathlib import Path
c=runpy.run_path('evidence/phase4/2026-11-10/reports/live-client.py')
api,wait,ready,stop=[c[k] for k in ('api','wait','ready','stop')]
control=Path('build/phase4/headless-control.json')
records=[]
def inject(**changes):
    value=dict(action_id=time.time_ns(),**changes)
    temporary=control.with_suffix('.tmp')
    temporary.write_text(json.dumps(value)); temporary.replace(control)
    return value
def enable(mode='forward'):
    stop(); ready()
    assert api('arm',{})[0]==200
    assert api('mode',dict(mode=mode))[0]==200
    return wait(lambda s:s['link'].get('activeMotion')=='forward',motion='forward' if mode=='forward' else None)
try:
    for ident,fault in [('F-UDP-LOSS',dict(pause_udp=True)),('F-SIM-RESET',dict(reset=True)),
                         ('F-SENSOR-STALE',dict(stale_sensors=True)),('F-OBSTACLE',dict(obstacle=True))]:
        record=dict(id=ident,started_utc=datetime.now(timezone.utc).isoformat(),
          classification='REAL PI/LAN; SIMULATED SENSOR/ACTUATOR FAULTS',injection=fault)
        try:
            before=enable()
            started=time.monotonic(); inject(**fault)
            state=wait(lambda s:not s['motion']['enabled'] and not s['link']['armed'] and not s['link']['activeMask'],timeout=5)
            record.update(injection_to_observed_output_off_ms=1000*(time.monotonic()-started),
                          observed={k:state[k] for k in ('motion','link','bridge','sensors','autonomy')})
            inject(reset=True)
            ready()
            until=time.monotonic()+1
            while time.monotonic()<until:
                state=api('state')[1]; assert not state['motion']['enabled']; time.sleep(.1)
            record.update(result='PASS',automatic_rearm=False)
        except Exception as error:
            record.update(result='FAIL',error=str(error))
            stop(); inject(reset=True)
        records.append(record)
        Path('evidence/phase4/2026-11-10/safety/lan-faults.json').write_text(json.dumps(records,indent=2)+'\n')
        print(ident,record['result'],record.get('injection_to_observed_output_off_ms'),flush=True)
    record=dict(id='E-VIRTUAL-TOUCH',classification='SIMULATED TOUCH OVER REAL LAN')
    try:
        enable('explore'); inject(touch='head')
        state=wait(lambda s:s['autonomy']['state']=='TOUCH_REACTION' or s['link'].get('activeMotion')=='greeting',timeout=4)
        record.update(result='PASS',observed={k:state[k] for k in ('autonomy','link','sensors')})
        inject(); stop()
    except Exception as error: record.update(result='FAIL',error=str(error))
    records.append(record)
    record=dict(id='E-INTERACTION',classification='VIRTUAL PERSONALITY OVER REAL LAN')
    try:
        stop(); inject(reset=True); ready()
        assert api('arm',{})[0]==200
        assert api('mode',dict(mode='interaction'))[0]==200
        assert api('interaction',dict(name='greeting'))[0]==200
        state=wait(lambda s:s['link'].get('activeMotion')=='greeting')
        record.update(result='PASS',observed={k:state[k] for k in ('autonomy','link')})
    except Exception as error: record.update(result='FAIL',error=str(error))
    records.append(record)
finally:
    Path('evidence/phase4/2026-11-10/safety/lan-faults.json').write_text(json.dumps(records,indent=2)+'\n')
    try: stop()
    finally: inject(reset=True)

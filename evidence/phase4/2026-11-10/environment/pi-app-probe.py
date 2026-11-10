"""Real USB camera + unchanged app with qualification logging and fault injection.

Only virtual actuators/sensors. Camera-stop injection closes the capture worker;
it does not claim a physical USB unplug. A new worker never enables motion.
"""
from datetime import datetime,timezone
import json
from pathlib import Path
import threading
import time
import faulthandler
import signal
from werkzeug.serving import make_server
from quadruped.main import Runtime,create_app
from quadruped.camera import Camera

faulthandler.register(signal.SIGUSR1,all_threads=True)

out=Path('build/hil')
out.mkdir(parents=True,exist_ok=True)
benchmark=Path.home()/'Quadruped107/build/phase4-qualification/camera.json'
while not benchmark.exists() or len(json.loads(benchmark.read_text()))<3:
    time.sleep(5)
runtime=Runtime(camera_backend='usb',camera_device='/dev/video0',width=320,height=240,fps=30,
    actuator_backend='virtual',virtual_sensors=True,simulator_host='192.168.1.43',simulator_port=17012,
    vision_state=out/'vision.json')
runtime.start()
server=make_server('127.0.0.1',7000,create_app(runtime),threaded=True)
thread=threading.Thread(target=server.serve_forever,daemon=True)
thread.start()
started=time.monotonic()
last_action=None
try:
    with (out/'state.jsonl').open('w') as log:
        while time.monotonic()-started<3600:
            control=json.loads((out/'control.json').read_text()) if (out/'control.json').exists() else {}
            action=control.get('action_id')
            if action!=last_action:
                if control.get('camera_stop'): runtime.camera.close()
                if control.get('camera_resume'):
                    runtime.camera.close()
                    runtime.camera=Camera(backend='usb',device='/dev/video0',width=320,height=240,fps=30)
                    runtime.camera.start()
                last_action=action
            if control.get('shutdown'): break
            state=runtime.state()
            assert state['physicalActuationAllowed'] is False
            keep={key:state.get(key) for key in ('camera','vision','motion','bridge','system','link','autonomy')}
            keep['sensors']={k:state['sensors'].get(k) for k in ('front_m','fault','receivedAge','rejected','touches')}
            keep.update(utc=datetime.now(timezone.utc).isoformat(),elapsed_s=time.monotonic()-started)
            log.write(json.dumps(keep)+'\n'); log.flush()
            time.sleep(1)
finally:
    runtime.motion.stop('Qualification process shutdown')
    server.shutdown()
    runtime.close()

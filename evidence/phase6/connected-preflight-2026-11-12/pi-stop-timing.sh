set -eu
export PYTHONDONTWRITEBYTECODE=1
session=$(cat /tmp/quadruped107-phase6-session-path)
export PYTHONPATH="$session/candidate/software/pi"
"$session/venv/bin/python" - <<'PY'
import json,time,threading
from quadruped.main import Runtime,create_app
from quadruped.display import MockDisplay
entered=threading.Event();release=threading.Event()
class Blocked(MockDisplay):
    def show(self,frame):entered.set();release.wait(10)
runtime=Runtime(simulate=True,display_backend=Blocked())
runtime.display.start()
assert entered.wait(2)
try:
    start=time.monotonic();app=create_app(runtime);constructed=time.monotonic()
    client=app.test_client();client_ready=time.monotonic()
    response=client.post('/api/stop',json={});stopped=time.monotonic()
    print(json.dumps(dict(classification='PI SOFTWARE / MOCK BLOCKED DISPLAY ONLY',
        applicationConstructionS=constructed-start,testClientConstructionS=client_ready-constructed,
        stopRequestS=stopped-client_ready,totalS=stopped-start,httpStatus=response.status_code,
        displayStillBlocked=not release.is_set(),physicalActuationAllowed=False)))
finally:release.set();runtime.close()
PY

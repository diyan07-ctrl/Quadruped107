"""Check installed imports and packaged assets outside the repository directory."""
import os
import subprocess
import sys
import tempfile

code = """
from quadruped.main import Runtime, create_app
from quadruped.virtual_uno import VirtualUno
from quadruped.bridge import TraceReceiver
from quadruped.sensors import SensorManager
from quadruped.navigation import Navigation
assert SensorManager().snapshot()["fault"]
assert Navigation().snapshot()["state"] == "IDLE"
engine = VirtualUno()
assert len(engine.snapshot()["targets"]) == 8
assert not engine.snapshot()["armed"]
runtime = Runtime(simulate=True)
client = create_app(runtime).test_client()
for name in ('/', '/app.js', '/styles.css', '/poses/stand.webp'):
    response = client.get(name)
    assert response.status_code == 200, (name, response.status_code)
    if name == "/": assert b"virtualAutonomy" in response.data
    response.close()
assert not runtime.state()['motion']['enabled']
print('Installed package imports and browser assets passed; hardware was not opened.')
"""
environment = dict(os.environ)
environment.pop("PYTHONPATH", None)
with tempfile.TemporaryDirectory() as directory:
    subprocess.run([sys.executable, "-c", code], cwd=directory, env=environment, check=True)

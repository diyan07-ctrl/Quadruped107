set -eu
export PYTHONDONTWRITEBYTECODE=1
session=$(cat /tmp/quadruped107-phase6-session-path)
candidate="$session/candidate"
cd "$candidate"
python3 -m venv "$session/venv"
PY="$session/venv/bin/python"
"$PY" -m pip install -r software/pi/requirements-dev.txt -e software/pi > "$session/isolated-install.log" 2>&1
"$PY" -m pip check > "$session/isolated-pip-check.log" 2>&1
"$PY" -m pip freeze > "$session/isolated-freeze.txt"
"$PY" -c 'import sys,cv2,numpy,flask,serial,json; print(json.dumps(dict(python=sys.version,executable=sys.executable,opencv=cv2.__version__,numpy=numpy.__version__,serial=serial.__version__)))'
export PYTHONPATH="$candidate/software/pi"
for name in test_telemetry.py test_readiness.py test_two_touch.py test_commission_recorder.py test_runtime.py test_pi_preflight.py; do
  "$PY" -m unittest discover -s tests -p "$name" -v > "$session/$name.log" 2>&1
  echo "$name PASS"
done
command -v arduino-cli || true
find /home/diyan07 -maxdepth 4 -type f -name arduino-cli -print 2>/dev/null || true
ls -d /home/diyan07/.arduino15/packages/arduino/tools/avrdude/*/bin/avrdude 2>/dev/null || true
id
fuser /dev/ttyUSB0 /dev/video0 2>/dev/null || true
original=/home/diyan07/Quadruped107
git -C "$original" status --porcelain > "$session/operator-after.status"
git -C "$original" diff --binary HEAD | sha256sum > "$session/operator-after.sha256"
git -C "$original" rev-parse HEAD > "$session/operator-after.head"
cmp "$session/operator-before.status" "$session/operator-after.status"
cmp "$session/operator-before.sha256" "$session/operator-after.sha256"
cmp "$session/operator-before.head" "$session/operator-after.head"
echo "SESSION=$session"
echo 'Isolated software tests only; Uno port unopened; no display package or I2C probe.'

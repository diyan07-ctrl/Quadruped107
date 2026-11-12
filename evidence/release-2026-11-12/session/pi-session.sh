set -eu
candidate=$(mktemp -d /tmp/quadruped107-release.XXXXXX)
PY=/home/diyan07/Quadruped107/.venv-pi-virtual/bin/python
"$PY" -m zipfile -e /tmp/quadruped107-release-candidate.zip "$candidate"
cd "$candidate"
printf '%s\n' "$candidate" > /tmp/quadruped107-release-session-path
git -C /home/diyan07/Quadruped107 diff --binary HEAD | sha256sum > operator-before.sha256
git -C /home/diyan07/Quadruped107 status --porcelain > operator-before.status
export PYTHONPATH="$candidate/software/pi"
"$PY" --version
"$PY" tools/pi-preflight.py --output preflight.json
for test in test_vision_readiness.py test_telemetry.py test_readiness.py test_pi_preflight.py test_runtime.py test_recorded_vision.py; do
  "$PY" -m unittest discover -s tests -p "$test" -v > "$test.log" 2>&1 && echo "$test PASS" || echo "$test FAIL"
done
printf '%s\n' '{"target_color":"yellow"}' > yellow.json
nohup "$PY" -m quadruped.main --camera-backend usb --camera-device /dev/video0 --width 640 --height 480 --fps 8 --actuator-backend virtual --sensor-source none --vision-config "$candidate/yellow.json" --oled mock --host 127.0.0.1 --port 7001 > app.log 2>&1 < /dev/null &
echo $! > app.pid
printf 'CANDIDATE=%s\n' "$candidate"
git -C /home/diyan07/Quadruped107 diff --binary HEAD | sha256sum > operator-after.sha256
git -C /home/diyan07/Quadruped107 status --porcelain > operator-after.status
cmp operator-before.sha256 operator-after.sha256
cmp operator-before.status operator-after.status

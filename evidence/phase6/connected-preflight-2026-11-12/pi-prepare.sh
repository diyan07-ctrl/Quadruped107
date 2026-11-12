set -eu
export PYTHONDONTWRITEBYTECODE=1
original=/home/diyan07/Quadruped107
session=$(mktemp -d /home/diyan07/Quadruped107-phase6-session.XXXXXX)
printf '%s\n' "$session" > /tmp/quadruped107-phase6-session-path
git -C "$original" status --porcelain > "$session/operator-before.status"
git -C "$original" diff --binary HEAD | sha256sum > "$session/operator-before.sha256"
git -C "$original" rev-parse HEAD > "$session/operator-before.head"
git -C "$original" fetch --no-tags origin phase6/two-touch-commissioning
candidate="$session/candidate"
git -C "$original" worktree add --detach "$candidate" 80de015063417d3579181198020501940f1624db
git -C "$candidate" status --porcelain
git -C "$candidate" rev-parse HEAD
PY=/home/diyan07/Quadruped107/.venv-pi-virtual/bin/python
export PYTHONPATH="$candidate/software/pi"
cd "$candidate"
"$PY" -m pip check > "$session/pip-check.log" 2>&1
for name in test_telemetry.py test_readiness.py test_two_touch.py test_commission_recorder.py test_runtime.py test_pi_preflight.py; do
  "$PY" -m unittest discover -s tests -p "$name" -v > "$session/$name.log" 2>&1
  echo "$name PASS"
done
command -v arduino-cli || true
find /home/diyan07 -maxdepth 4 -type f -name arduino-cli -print 2>/dev/null || true
ls -l /dev/serial/by-id /dev/serial/by-path
id
fuser /dev/ttyUSB0 /dev/video0 2>/dev/null || true
git -C "$original" status --porcelain > "$session/operator-after.status"
git -C "$original" diff --binary HEAD | sha256sum > "$session/operator-after.sha256"
git -C "$original" rev-parse HEAD > "$session/operator-after.head"
cmp "$session/operator-before.status" "$session/operator-after.status"
cmp "$session/operator-before.sha256" "$session/operator-after.sha256"
cmp "$session/operator-before.head" "$session/operator-after.head"
echo "SESSION=$session"
echo 'Software tests only; Uno serial not opened; no upload or OS/service changes.'

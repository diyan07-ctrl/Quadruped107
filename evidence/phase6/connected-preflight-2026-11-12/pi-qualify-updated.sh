set -eu
export PYTHONDONTWRITEBYTECODE=1
session=$(cat /tmp/quadruped107-phase6-session-path)
case "$session" in /home/diyan07/Quadruped107-phase6-session.*) ;; *) exit 2 ;; esac
original=/home/diyan07/Quadruped107
candidate="$session/candidate"
test "$(realpath "$candidate")" = "$candidate"
test -z "$(git -C "$candidate" status --porcelain)"
git -C "$original" fetch --no-tags origin phase6/two-touch-commissioning
git -C "$candidate" switch --detach 01f0bb9
cd "$candidate"
export PYTHONPATH="$candidate/software/pi"
PY="$session/venv/bin/python"
"$PY" -m pip check > "$session/qualified-pip-check.log" 2>&1
mkdir -p "$session/qualified"
for name in test_telemetry.py test_readiness.py test_two_touch.py test_commission_recorder.py test_runtime.py test_pi_preflight.py; do
  "$PY" -m unittest discover -s tests -p "$name" -v > "$session/qualified/$name.log" 2>&1
  echo "$name PASS"
done
export XDG_CACHE_HOME="$session/cache"
cli="$session/tools/arduino-cli"
mkdir -p "$session/compiled"
for mask in 0 1 2 3; do
  "$cli" --config-file "$session/arduino-cli.yaml" compile --profile uno --build-path "$session/compiled/two-$mask" --build-property "compiler.cpp.extra_flags=-DURM37_PROFILE=1 -DTOUCH_ENABLED_MASK=3 -DTOUCH_ACTIVE_LOW_MASK=$mask" firmware/uno/sensor_only > "$session/qualified/avr-two-$mask.log" 2>&1
  sha256sum "$session/compiled/two-$mask/sensor_only.ino.hex"
done
git -C "$candidate" rev-parse HEAD > "$session/qualified/source.txt"
git -C "$original" status --porcelain > "$session/qualified/operator-after.status"
git -C "$original" diff --binary HEAD | sha256sum > "$session/qualified/operator-after.sha256"
git -C "$original" rev-parse HEAD > "$session/qualified/operator-after.head"
cmp "$session/operator-before.status" "$session/qualified/operator-after.status"
cmp "$session/operator-before.sha256" "$session/qualified/operator-after.sha256"
cmp "$session/operator-before.head" "$session/qualified/operator-after.head"
fuser /dev/ttyUSB0 /dev/video0 2>/dev/null || true
echo 'Pi software/mock qualification and AVR compilation only; no Uno port open or upload.'

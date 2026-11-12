set -eu
export PYTHONDONTWRITEBYTECODE=1
s=$(cat /tmp/quadruped107-phase6-session-path)
c="$s/candidate"
test -z "$(git -C "$c" status --porcelain)"
git -C "$c" fetch --no-tags origin phase6/two-touch-commissioning
git -C "$c" switch --detach 7f4768e
cd "$c"
export PYTHONPATH="$c/software/pi"
mkdir -p "$s/final-tests"
git rev-parse HEAD > "$s/final-tests/source.txt"
"$s/venv/bin/python" -m pip check > "$s/final-tests/pip-check.log" 2>&1
for name in test_telemetry.py test_readiness.py test_two_touch.py test_commission_recorder.py test_runtime.py test_pi_preflight.py; do
  "$s/venv/bin/python" -m unittest discover -s tests -p "$name" -v > "$s/final-tests/$name.log" 2>&1
  echo "$name PASS"
done
git status --porcelain
echo 'Software mocks only; no physical serial port opened.'

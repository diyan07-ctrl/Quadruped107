set -eu
cd /tmp/quadruped107-release.7S0kKt
kill -TERM "$(cat diagnostics-app.pid)"
sleep 2
PY=/home/diyan07/Quadruped107/.venv-pi-virtual/bin/python
export PYTHONPATH="$PWD/software/pi"
nohup "$PY" tools/phase4-hil.py pi --host 192.168.1.43 --seconds 1000 --output "$PWD/hil-pi" --control "$PWD/hil-control.json" > hil-pi-console.log 2>&1 < /dev/null &
echo $! > hil-pi.pid
sleep 3
nohup "$PY" tools/phase4-hil.py run --url http://127.0.0.1:7000 --seconds 905 --output "$PWD/hil-run" > hil-run-console.log 2>&1 < /dev/null &
echo $! > hil-run.pid
echo 'Started Pi-owned finite heartbeat trial, source archive 9fe42b1; real camera, virtual sensors and outputs only.'

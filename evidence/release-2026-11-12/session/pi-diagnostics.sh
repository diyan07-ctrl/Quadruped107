set -eu
cd /tmp/quadruped107-release.7S0kKt
kill -TERM "$(cat app.pid)"
sleep 2
PY=/home/diyan07/Quadruped107/.venv-pi-virtual/bin/python
export PYTHONPATH="$PWD/software/pi"
nohup "$PY" live-diagnostics.py > diagnostics-app.log 2>&1 < /dev/null &
echo $! > diagnostics-app.pid
v4l2-ctl --device /dev/video0 --all > camera-driver.txt 2>&1 || true
v4l2-ctl --device /dev/video0 --list-formats-ext >> camera-driver.txt 2>&1 || true
cat camera-driver.txt

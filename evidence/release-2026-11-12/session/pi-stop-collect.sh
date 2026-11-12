set -eu
cd /tmp/quadruped107-release.7S0kKt
printf '%s\n' '{"shutdown":true,"action_id":"release-final-stop"}' > hil-control.json
sleep 3
PY=/home/diyan07/Quadruped107/.venv-pi-virtual/bin/python
"$PY" -m pip freeze > dependency-freeze.txt
"$PY" -c 'import cv2,numpy,sys,json; print(json.dumps(dict(python=sys.version,opencv=cv2.__version__,numpy=numpy.__version__)))' > dependency-imports.json
git -C /home/diyan07/Quadruped107 diff --binary HEAD | sha256sum > operator-final.sha256
git -C /home/diyan07/Quadruped107 status --porcelain > operator-final.status
cmp operator-before.sha256 operator-final.sha256
cmp operator-before.status operator-final.status
for pidfile in hil-pi.pid hil-run.pid; do
  pid=$(cat "$pidfile")
  if kill -0 "$pid" 2>/dev/null; then
    ps -o pid=,stat=,comm= -p "$pid"
  fi
done
tar -czf /tmp/quadruped107-release-pi-evidence.tgz preflight.json *.log *.sha256 *.status dependency-freeze.txt dependency-imports.json admission-state.json camera-driver.txt yellow*.json yellow*.png yellow*.jpg hil-pi hil-run pi-session.sh 2>/dev/null || {
  tar -czf /tmp/quadruped107-release-pi-evidence.tgz preflight.json *.log *.sha256 *.status dependency-freeze.txt dependency-imports.json admission-state.json camera-driver.txt yellow*.json yellow*.png yellow*.jpg hil-pi hil-run
}
cat hil-run/result.json
echo
cat dependency-imports.json

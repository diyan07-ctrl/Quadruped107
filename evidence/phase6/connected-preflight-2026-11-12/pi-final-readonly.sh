set -eu
export PYTHONDONTWRITEBYTECODE=1
s=$(cat /tmp/quadruped107-phase6-session-path)
original=/home/diyan07/Quadruped107
date -u
echo 'Original checkout status delta; no restoration attempted'
diff -u "$s/operator-before.status" "$s/qualified/operator-after.status" || true
echo 'Original HEAD before / after'
cat "$s/operator-before.head" "$s/qualified/operator-after.head"
echo 'Original diff HEAD before / after; current staged diff'
cat "$s/operator-before.sha256" "$s/qualified/operator-after.sha256"
git -C "$original" diff --cached --binary | sha256sum
echo 'Candidate status / HEAD'
git -C "$s/candidate" status --porcelain
git -C "$s/candidate" rev-parse HEAD
echo 'Device metadata only; no port open'
ls -l /dev/serial/by-id /dev/serial/by-path
udevadm info --query=property --name=/dev/ttyUSB0
fuser /dev/ttyUSB0 /dev/video0 2>/dev/null || true
df -h / /tmp
"$s/venv/bin/python" -c 'import sys,cv2,numpy,serial,json;print(json.dumps(dict(python=sys.version,opencv=cv2.__version__,numpy=numpy.__version__,serial=serial.__version__)))'
"$s/venv/bin/python" -m pip check
echo 'No serial open, upload, GPIO, I2C, service or network changes.'

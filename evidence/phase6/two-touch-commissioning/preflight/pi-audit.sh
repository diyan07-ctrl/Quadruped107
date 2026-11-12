set -eu
export PYTHONDONTWRITEBYTECODE=1
date -u
uname -a
df -h / /tmp
for checkout in /home/diyan07/Quadruped107 /home/diyan07/Quadruped107-phase4-qualification; do
  echo "CHECKOUT $checkout"
  git -C "$checkout" status --porcelain
  git -C "$checkout" branch --show-current
  git -C "$checkout" rev-parse HEAD
  git -C "$checkout" diff --stat
  git -C "$checkout" diff --cached --stat
  git -C "$checkout" diff --binary HEAD | sha256sum
done
systemctl list-units --type=service --state=running --no-pager --no-legend
ps -eo pid,comm
fuser /dev/video0 /dev/ttyACM0 /dev/ttyUSB0 2>/dev/null || true
ls -l /dev/serial/by-id /dev/serial/by-path /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || true
for device in /dev/ttyACM* /dev/ttyUSB*; do
  [ -e "$device" ] || continue
  udevadm info --query=property --name="$device"
done
/home/diyan07/Quadruped107/.venv-pi-virtual/bin/python - <<'PY'
import sys,cv2,numpy,flask,serial,json
print(json.dumps(dict(python=sys.version,executable=sys.executable,opencv=cv2.__version__,numpy=numpy.__version__,serial=serial.__version__)))
PY
echo 'READ-ONLY AUDIT: no serial open, firmware upload, GPIO, I2C or service modification.'

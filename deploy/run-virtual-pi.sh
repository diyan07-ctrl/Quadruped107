#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
if [ "$#" -ne 1 ]; then
  echo "Usage: sh deploy/run-virtual-pi.sh LAPTOP_PRIVATE_IP"
  exit 2
fi
exec .venv-pi-virtual/bin/python -m quadruped.main --camera-backend usb --camera-device /dev/video0 --width 640 --height 480 --fps 8 --actuator-backend virtual --sensor-source virtual --vision-config deploy/vision.example.json --simulator "$1" --host 0.0.0.0

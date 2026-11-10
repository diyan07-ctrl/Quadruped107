#!/bin/sh
# Run from the checkout on Raspberry Pi OS; no services, GPIO or firmware are changed.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
command -v python3 >/dev/null
python3 -c 'import cv2, numpy' || {
  echo "Install OS packages first: sudo apt install python3-venv python3-opencv python3-numpy"
  exit 1
}
test -d .venv-pi-virtual || python3 -m venv --system-site-packages .venv-pi-virtual
.venv-pi-virtual/bin/python -m pip install -r software/pi/requirements.txt -e software/pi
.venv-pi-virtual/bin/python -m pip check
echo "Installed isolated virtual-actuator application. No service was started."
echo "Launch: sh deploy/run-virtual-pi.sh LAPTOP_PRIVATE_IP"

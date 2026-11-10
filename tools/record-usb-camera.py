"""Record a bounded diagnostic USB webcam clip without starting motion software.

Run on Pi with the dashboard stopped so /dev/video0 has only one owner.
This tool never opens Arduino, GPIO, or servo interfaces.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import time
import cv2


def record(device: str, output: Path, seconds: float, width: int, height: int, fps: float):
    if not 0 < seconds <= 30 or not 1 <= fps <= 30:
        raise ValueError("Duration must be 0..30 s and FPS 1..30")
    if output.suffix.lower() != ".avi":
        raise ValueError("Use an .avi output file")
    output.parent.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(int(device) if device.isdecimal() else device, cv2.CAP_V4L2)
    writer = None
    frames = 0
    started = time.monotonic()
    try:
        if not capture.isOpened():
            raise RuntimeError("USB webcam unavailable; close other camera applications")
        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        capture.set(cv2.CAP_PROP_FPS, fps)
        deadline = started + seconds
        while time.monotonic() < deadline:
            ok, image = capture.read()
            if not ok or image is None:
                raise RuntimeError("USB camera read failed")
            if writer is None:
                image_height, image_width = image.shape[:2]
                writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"MJPG"), fps,
                                         (image_width, image_height))
                if not writer.isOpened():
                    raise RuntimeError("VideoWriter failed to open")
            writer.write(image)
            frames += 1
    finally:
        if writer is not None:
            writer.release()
        capture.release()
    print(f"Recorded {frames} frames to {output}; elapsed={time.monotonic()-started:.2f}s")
    if not frames:
        raise RuntimeError("No frames were captured")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="/dev/video0")
    parser.add_argument("--output", type=Path, default=Path("build/recordings/usb-camera.avi"))
    parser.add_argument("--seconds", type=float, default=10)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=float, default=8)
    args = parser.parse_args()
    record(args.device, args.output, args.seconds, args.width, args.height, args.fps)

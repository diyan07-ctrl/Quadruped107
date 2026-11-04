"""Exercise the real HTTP server and CLI in explicit no-hardware simulation."""
import json
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib.request import Request, urlopen


class HttpSmokeTests(unittest.TestCase):
    def test_cli_serves_camera_and_controls(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        main = Path(__file__).resolve().parents[1] / "Dev/Quadruped107-connect/python/main.py"
        process = subprocess.Popen(
            [sys.executable, str(main), "--simulate", "--host", "127.0.0.1", "--port", str(port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        base = f"http://127.0.0.1:{port}"
        def call(path, data=None):
            request = Request(base + path, data=json.dumps(data).encode() if data is not None else None,
                              headers={"Content-Type": "application/json"})
            with urlopen(request, timeout=2) as response:
                return json.load(response)
        try:
            deadline = time.monotonic() + 10
            while True:
                try:
                    state = call("/api/state")
                    if state["camera"]["available"]: break
                except OSError: pass
                if time.monotonic() > deadline: self.fail("Simulation server did not become ready")
                time.sleep(0.05)
            self.assertTrue(state["simulation"])
            self.assertFalse(state["motion"]["enabled"])
            with urlopen(base + "/", timeout=2) as response:
                self.assertIn(b"Raspberry Pi 4 + Arduino Uno", response.read())
            call("/api/arm", {})
            call("/api/mode", {"mode": "forward"})
            call("/api/heartbeat", {"motion": "forward"})
            self.assertEqual(call("/api/state")["motion"]["desiredMotion"], "forward")
            with urlopen(base + "/video-feed", timeout=2) as response:
                self.assertIn(b"image/jpeg", response.read(150))
            call("/api/stop", {})
            self.assertFalse(call("/api/state")["motion"]["enabled"])
        finally:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=3)


if __name__ == "__main__": unittest.main()

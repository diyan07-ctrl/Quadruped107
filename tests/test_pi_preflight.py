"""Read-only Pi preflight produces an explicitly non-hardware-qualified report."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / "tools" / "pi-preflight.py"
spec = importlib.util.spec_from_file_location("pi_preflight", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class PreflightTests(unittest.TestCase):
    def test_observational_contract(self):
        report = module.preflight()
        self.assertEqual(report["schema"], 1)
        self.assertEqual(report["camera_device"], "/dev/video0")
        self.assertFalse(report["physical_actuation_tested"])
        self.assertEqual(report["camera_frames_captured"], 0)
        self.assertEqual(report["qualification"], "READ_ONLY_PREFLIGHT_NOT_CAMERA_ACCEPTANCE")
        self.assertIn(report["dashboard_tcp"]["state"], ("occupied", "free", "unknown"))
        self.assertIn("cv2", report["imports_available"])

    def test_missing_ss_reports_unknown(self):
        with patch.object(module.subprocess, "run", side_effect=FileNotFoundError):
            self.assertEqual(module.probe_port(7000)["state"], "unknown")

if __name__ == "__main__":
    unittest.main()

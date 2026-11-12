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

    def test_explicit_missing_devices_and_failed_imports_are_reported(self):
        from types import SimpleNamespace
        with patch.object(module.subprocess,'run',return_value=SimpleNamespace(returncode=1,stderr='ABI failure')):
            report=module.preflight('/missing/camera','/missing/uno',1)
        self.assertFalse(report['serial']['exists'])
        self.assertFalse(report['import_execution']['cv2']['ok'])
        self.assertIn('ABI failure',report['import_execution']['cv2']['error'])
        self.assertEqual(report['camera_device'],'/missing/camera')
        self.assertFalse(report['physical_actuation_allowed'])

if __name__ == "__main__":
    unittest.main()

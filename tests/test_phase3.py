"""Phase 3 multicolor target selection regression checks."""
import sys
import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "software/pi"))
from quadruped.autonomy import VisionSettings
from quadruped.vision import detect_blue_ball, encode_vision_frame


class MulticolorTests(unittest.TestCase):
    def test_blue_default_unchanged(self):
        self.assertEqual(VisionSettings().target_color, "blue")
        self.assertEqual(VisionSettings().hsv_lower, (95, 70, 30))

    def test_explicit_yellow_preset(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "yellow.json"
            config.write_text(json.dumps({"target_color": "yellow"}))
            settings = VisionSettings.load(config)
        self.assertEqual(settings.hsv_lower, (20, 70, 70))
        self.assertEqual(settings.hsv_upper, (45, 255, 255))

    def test_explicit_custom_hsv_overrides_preset(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "yellow.json"
            config.write_text(json.dumps({"target_color": "yellow", "hsv_lower": [22, 90, 90]}))
            settings = VisionSettings.load(config)
        self.assertEqual(settings.hsv_lower, (22, 90, 90))
        self.assertEqual(settings.hsv_upper, (45, 255, 255))

    def test_invalid_target_rejected(self):
        with self.assertRaises(ValueError):
            VisionSettings(target_color="infrared")

    def test_yellow_ball_detected(self):
        img = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.circle(img, (110, 100), 35, (0, 255, 255), -1)
        result = detect_blue_ball(img, lower=(20, 70, 70), upper=(45, 255, 255))
        self.assertTrue(result["detected"])
        self.assertLess(result["offset"], 0)

    def test_yellow_overlay_encodes(self):
        img = np.zeros((240, 320, 3), dtype=np.uint8)
        detection = {"detected": False}
        self.assertTrue(encode_vision_frame(img, detection, "TARGET_LOST", "hold", target_name="yellow"))


if __name__ == "__main__":
    unittest.main()

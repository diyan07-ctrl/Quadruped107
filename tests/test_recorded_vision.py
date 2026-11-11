"""Frozen real Pi images: diagnostic regression, never proof of physical pursuit."""
from pathlib import Path
import sys
import unittest
import cv2

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'software/pi'))
from quadruped.vision import detect_blue_ball,TargetLock
from quadruped.autonomy import VisionSettings,Behavior


class RecordedYellowTests(unittest.TestCase):
    def frames(self):
        directory=ROOT/'evidence/phase4/2026-11-10-remediation/vision/yellow-center-initial'
        return [cv2.imread(str(directory/name)) for name in ('frame-001-original.png','frame-010-original.png')]
    def detect(self,frame,settings=None):
        settings=settings or VisionSettings(target_color='yellow')
        return detect_blue_ball(frame,lower=settings.hsv_lower,upper=settings.hsv_upper)
    def test_clipped_low_saturation_recordings_remain_rejected(self):
        for frame in self.frames():
            result=self.detect(frame)
            self.assertFalse(result['detected'])
            self.assertEqual(result['rejectReason'],'no_circular_candidate')
            self.assertTrue(result['contourDiagnostics'][0]['touchesFrameEdge'])
            self.assertEqual(result['contourDiagnostics'][0]['rejectionReason'],'circularity')
            self.assertGreater(result['hsvDiagnostics']['saturationRejectedWithinHue'],3000)
    def test_background_only_distractors_from_recording(self):
        # Top half excludes the operator-recorded ball at bottom (y >=144).
        for frame in self.frames():
            self.assertFalse(self.detect(frame[:120])['detected'])
    def test_switch_and_loss_do_not_invent_identity(self):
        tracker=TargetLock(VisionSettings(target_color='yellow'))
        for index,frame in enumerate(self.frames()):
            result=tracker.process(self.detect(frame),index*.1,allow_new=False)
            self.assertFalse(result['detected'])
            self.assertEqual(result['lockId'],0)
            blue=self.detect(frame,VisionSettings(target_color='blue'))
            # Any blue background candidate cannot carry a yellow identity.
            self.assertNotIn('lockId',blue)
    def test_diagnostic_work_is_bounded(self):
        for frame in self.frames():
            result=self.detect(frame)
            self.assertLessEqual(len(result['contourDiagnostics']),8)
            self.assertLessEqual(len(result['candidates']),8)

if __name__=='__main__': unittest.main()

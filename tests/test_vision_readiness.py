"""Vision selection, stable association and real runtime cancellation contracts."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import cv2
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"software/pi"))
from quadruped.autonomy import VisionSettings, Behavior
from quadruped.vision import detect_blue_ball,TargetLock
from quadruped.main import Runtime,create_app
from quadruped.vision_config import load_state
from test_runtime import wait_for

def image(circles,color=(255,0,0),size=(480,640)):
    frame=np.zeros((*size,3),dtype=np.uint8)
    for x,y,r in circles: cv2.circle(frame,(x,y),r,color,-1)
    return frame

class CandidateTests(unittest.TestCase):
    def test_yellow_green_and_false_positive_filters(self):
        cfg=VisionSettings(target_color="yellow")
        for hue in (25,40):
            bgr=cv2.cvtColor(np.uint8([[[hue,230,230]]]),cv2.COLOR_HSV2BGR)[0,0]
            detected=detect_blue_ball(image([(200,200,35)],tuple(map(int,bgr))),lower=cfg.hsv_lower,upper=cfg.hsv_upper)
            self.assertTrue(detected["detected"])
        rectangle=np.zeros((480,640,3),dtype=np.uint8)
        cv2.rectangle(rectangle,(20,100),(500,120),(0,255,255),-1)
        self.assertFalse(detect_blue_ball(rectangle,lower=cfg.hsv_lower,upper=cfg.hsv_upper)["detected"])
        self.assertFalse(detect_blue_ball(image([(200,200,3)]))["detected"])

    def test_same_color_candidates_stay_on_original_target(self):
        tracker=TargetLock(VisionSettings())
        first=tracker.process(detect_blue_ball(image([(100,200,35),(500,200,30)])),0)
        second=tracker.process(detect_blue_ball(image([(110,200,35),(500,200,50)])),.1,allow_new=False)
        self.assertEqual(first["lockId"],second["lockId"])
        self.assertLess(second["x"],200)

    def test_disappearance_does_not_switch_to_unrelated_object(self):
        tracker=TargetLock(VisionSettings())
        tracker.process(detect_blue_ball(image([(100,200,35)])),0)
        for timestamp in (.1,.3,1.):
            result=tracker.process(detect_blue_ball(image([(500,200,35)])),timestamp,allow_new=False)
            self.assertFalse(result["detected"])
        self.assertTrue(tracker.process(detect_blue_ball(image([(500,200,35)])),1.1,allow_new=True)["detected"])

    def test_bounded_same_target_reacquisition(self):
        tracker=TargetLock(VisionSettings())
        tracker.process(detect_blue_ball(image([(100,200,35)])),0)
        tracker.process(detect_blue_ball(image([])),.1,allow_new=False)
        result=tracker.process(detect_blue_ball(image([(120,200,35)])),.2,allow_new=False)
        self.assertTrue(result["detected"])
        self.assertEqual(result["lockId"],1)

    def test_offset_smoothing_and_workload_bound(self):
        tracker=TargetLock(VisionSettings(smoothing_alpha=.5))
        first=tracker.process(detect_blue_ball(image([(100,200,35)])),0)
        second=tracker.process(detect_blue_ball(image([(160,200,35)])),.1)
        self.assertAlmostEqual(second["offset"],(first["rawOffset"]+second["rawOffset"])/2)
        result=detect_blue_ball(image([(800,600,70)],size=(1200,1600)))
        self.assertLessEqual(max(result["processingWidth"],result["processingHeight"]),640)
        self.assertAlmostEqual(result["x"],800,delta=5)

    def test_duplicate_observation_does_not_satisfy_persistence(self):
        behavior=Behavior()
        observation=dict(detected=True,offset=-.8,observed_at=0.)
        self.assertEqual(behavior.step(observation,0).state,"IDLE")
        self.assertEqual(behavior.step(observation,.1).state,"IDLE")
        observation["observed_at"]=.2
        self.assertEqual(behavior.step(observation,.2).motion,"turn_left")

    def test_invalid_settings_are_rejected(self):
        for settings in ({"smoothing_alpha":0},{"min_area":True},{"lock_distance":float("nan")},
                         {"hsv_lower":"invalid"},{"unsupported":1},{"target_color":"red"}):
            with self.assertRaises(ValueError): VisionSettings.from_dict(settings)

class PreferenceTests(unittest.TestCase):
    def test_safe_persistence_and_stale_revision(self):
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder)/"preferences.json"
            runtime=Runtime(simulate=True,vision_state=state)
            api=create_app(runtime).test_client()
            response=api.post("/api/vision",json=dict(revision=1,target_color="yellow"))
            self.assertEqual(response.status_code,200,response.json)
            self.assertFalse(runtime.motion.snapshot()["enabled"])
            settings,revision=load_state(state)
            self.assertEqual((settings.target_color,revision),("yellow",2))
            self.assertEqual(settings.hsv_lower,(20,70,70))
            self.assertEqual(api.post("/api/vision",json=dict(revision=1,target_color="blue")).status_code,409)
            restored=Runtime(simulate=True,vision_state=state)
            self.assertEqual(restored.vision_settings.target_color,"yellow")

    def test_color_change_cancels_motion_and_requires_reenable(self):
        runtime=Runtime(simulate=True)
        api=create_app(runtime).test_client()
        self.assertEqual(api.post("/api/arm",json={}).status_code,200)
        api.post("/api/mode",json={"mode":"forward"})
        response=api.post("/api/vision",json={"revision":1,"target_color":"yellow"})
        self.assertEqual(response.status_code,200)
        self.assertFalse(runtime.motion.snapshot()["enabled"])
        self.assertFalse(runtime.link.snapshot()["armed"])
        self.assertEqual(runtime.vision["blueBall"],{})

    def test_other_browser_cannot_change_target(self):
        runtime=Runtime(simulate=True)
        app=create_app(runtime)
        first,other=app.test_client(),app.test_client()
        first.post("/api/arm",json={})
        self.assertEqual(other.post("/api/vision",json={"revision":1,"target_color":"yellow"}).status_code,409)
        self.assertEqual(runtime.vision_revision,1)

    def test_failed_persistence_stays_disarmed_with_old_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime=Runtime(simulate=True,vision_state=Path(folder)/"settings.json")
            api=create_app(runtime).test_client()
            api.post("/api/arm",json={})
            with patch("quadruped.vision_config.save_state",side_effect=OSError("fixture")):
                response=api.post("/api/vision",json={"revision":1,"target_color":"yellow"})
            self.assertEqual(response.status_code,409)
            self.assertFalse(runtime.motion.snapshot()["enabled"])
            self.assertEqual(runtime.vision_settings.target_color,"blue")

    def test_physical_target_configuration_is_rejected(self):
        runtime=Runtime()
        response=create_app(runtime).test_client().post("/api/vision",json={"revision":1,"target_color":"yellow"})
        self.assertEqual(response.status_code,409)

    def test_invalid_runtime_state_does_not_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder)/"bad.json"
            state.write_text('{"schema":99}')
            with self.assertRaises(ValueError): Runtime(simulate=True,vision_state=state)

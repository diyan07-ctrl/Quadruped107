"""Optional MediaPipe Tasks recognizer. A separately supplied .task model is required."""
import time
import cv2

GESTURES = {"Open_Palm": "initial", "Thumb_Up": "stand",
            "Victory": "greeting", "Closed_Fist": "tail_wag"}


class GestureDetector:
    def __init__(self, model_path):
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        self.mp = mp
        options = vision.GestureRecognizerOptions(
            base_options=python.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO, num_hands=1)
        self.recognizer = vision.GestureRecognizer.create_from_options(options)
        self.timestamp = 0

    def detect(self, bgr):
        self.timestamp = max(self.timestamp + 1, int(time.monotonic() * 1000))
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        result = self.recognizer.recognize_for_video(
            self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb), self.timestamp)
        if not result.gestures: return None
        best = result.gestures[0][0]
        if best.score < 0.65 or best.category_name not in GESTURES: return None
        return dict(gesture=best.category_name, motion=GESTURES[best.category_name], confidence=best.score)

    def close(self): self.recognizer.close()

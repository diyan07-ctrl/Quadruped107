"""Session-only instrumentation of the existing non-actuating Runtime."""
import base64
import time
import cv2
from flask import jsonify
from werkzeug.serving import make_server
from quadruped.main import Runtime, create_app
from quadruped.vision import detect_blue_ball, encode_vision_frame
from quadruped.display import MockDisplay

runtime=Runtime(camera_backend='usb',camera_device='/dev/video0',width=640,height=480,fps=8,
    actuator_backend='virtual',sensor_source='none',vision_config='yellow.json',display_backend=MockDisplay())
app=create_app(runtime)
@app.get('/qualification/frame')
def frame():
    raw,_,sequence,_,captured=runtime.camera.latest(with_timestamp=True)
    if raw is None: return jsonify(available=False)
    with runtime.settings_lock: settings=runtime.vision_settings
    detection=detect_blue_ball(raw,lower=settings.hsv_lower,upper=settings.hsv_upper,
        min_area=settings.min_area,min_radius=settings.min_radius,
        max_radius_ratio=settings.max_radius_ratio,min_circularity=settings.min_circularity)
    def encode(image,ext): return base64.b64encode(cv2.imencode(ext,image)[1]).decode()
    mask=detection.pop('mask')
    annotated=encode_vision_frame(raw,detection,'DISARMED','hold',target_name=settings.target_color)
    return jsonify(available=True,sequence=sequence,frameAgeS=time.monotonic()-captured,
        targetColor=settings.target_color,settings=settings.to_dict(),detection=detection,
        rawPng=encode(raw,'.png'),maskPng=encode(mask,'.png'),annotatedJpeg=base64.b64encode(annotated).decode())

runtime.start()
server=make_server('127.0.0.1',7001,app,threaded=True)
try: server.serve_forever()
finally: runtime.close(); server.server_close()

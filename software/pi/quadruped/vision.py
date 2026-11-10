"""Blue-ball detector retained from the original motion app; BGR input."""
from __future__ import annotations
import math
from typing import Any
import cv2

BLUE_HSV_LOWER = (95, 70, 30)
BLUE_HSV_UPPER = (140, 255, 255)
BLUE_MIN_MASK_AREA = 150
BLUE_MIN_RADIUS = 8
BLUE_MAX_RADIUS_RATIO = 0.38
BLUE_CLOSE_RADIUS_RATIO = 0.24
BLUE_MIN_CIRCULARITY = 0.55
BLUE_MIN_FILL_RATIO = 0.40
BLUE_MAX_FILL_RATIO = 1.18
BLUE_CENTER_DEADZONE_RATIO = 0.32
BLUE_STABLE_DETECTIONS_REQUIRED = 2


def detect_blue_ball(frame: Any, *, lower=BLUE_HSV_LOWER, upper=BLUE_HSV_UPPER,
                     min_area=BLUE_MIN_MASK_AREA,min_radius=BLUE_MIN_RADIUS,
                     max_radius_ratio=BLUE_MAX_RADIUS_RATIO,min_circularity=BLUE_MIN_CIRCULARITY) -> dict[str, Any]:
    height, width = frame.shape[:2]
    scale=min(1.0,640/max(width,height))
    if scale<1: frame=cv2.resize(frame,(round(width*scale),round(height*scale)),interpolation=cv2.INTER_AREA)
    work_height,work_width=frame.shape[:2]
    blurred_frame = cv2.GaussianBlur(frame, (5, 5), 0)
    hsv = cv2.cvtColor(blurred_frame, cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(hsv, lower, upper)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))

    # Primero rellena huecos causados por sombras.
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # Después elimina pequeños puntos de ruido.
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    mask_area = int(cv2.countNonZero(mask))

    detection = {
        "detected": False,
        "x": None,
        "y": None,
        "radius": None,
        "offset": None,
        "maskArea": mask_area,
        "circleArea": 0,
        "circularity": 0,
        "fillRatio": 0,
        "rejectReason": "no_color_mask",
        "bbox": None,
        "area": 0,
        "frameWidth": width,
        "frameHeight": height,
        "mask": mask,
        "candidates": [],
        "processingWidth": work_width,
        "processingHeight": work_height,
    }
    if mask_area < min_area:
        detection["rejectReason"] = "mask_too_small"
        return detection

    contours, _hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    if len(contours)>128:
        detection["rejectReason"]="scene_too_complex"
        return detection
    max_radius = int(min(work_width, work_height) * max_radius_ratio)

    for contour in contours:
        contour_area = cv2.contourArea(contour)
        if contour_area < min_area:
            continue

        perimeter = cv2.arcLength(contour, True)
        if perimeter <= 0:
            continue

        (x_float, y_float), radius_float = cv2.minEnclosingCircle(contour)
        radius = int(round(radius_float))
        if radius < min_radius:
            continue
        if radius > max_radius:
            continue

        circle_area = math.pi * radius_float * radius_float
        if circle_area <= 0:
            continue

        circularity = (4 * math.pi * contour_area) / (perimeter * perimeter)
        fill_ratio = contour_area / circle_area
        if circularity < min_circularity:
            continue
        if fill_ratio < BLUE_MIN_FILL_RATIO or fill_ratio > BLUE_MAX_FILL_RATIO:
            continue

        x, y = int(round(x_float)), int(round(y_float))
        candidates.append(
            {
                "x": round(x/scale),
                "y": round(y/scale),
                "bbox": [round(v/scale) for v in cv2.boundingRect(contour)],
                "radius": round(radius/scale),
                "contourArea": round(contour_area/scale**2),
                "circleArea": round(circle_area/scale**2),
                "circularity": round(circularity, 3),
                "fillRatio": round(fill_ratio, 3),
            }
        )

    if not candidates:
        detection["rejectReason"] = "no_circular_candidate"
        return detection

    candidates.sort(key=lambda item:(-item["contourArea"],item["x"],item["y"],item["radius"]))
    detection["candidates"]=candidates[:8]
    candidate = candidates[0]
    x = candidate["x"]
    y = candidate["y"]
    radius = candidate["radius"]
    offset = (x - (width / 2)) / (width / 2)
    detection.update(
        {
            "detected": True,
            "x": x,
            "y": y,
            "radius": radius,
            "offset": round(offset, 3),
            "circleArea": candidate["circleArea"],
            "circularity": candidate["circularity"],
            "fillRatio": candidate["fillRatio"],
            "rejectReason": None,
            "bbox": candidate["bbox"],
            "area": candidate["contourArea"],
        }
    )
    return detection


def choose_blue_ball_motion(detection: dict[str, Any]) -> tuple[str, str]:
    if not detection["detected"]:
        return "search", "turn_right"

    close_radius = int(min(int(detection["frameWidth"]), int(detection["frameHeight"])) * BLUE_CLOSE_RADIUS_RATIO)
    if int(detection["radius"]) >= close_radius:
        return "close_stop", "hold"

    offset = float(detection["offset"])
    if offset < -BLUE_CENTER_DEADZONE_RATIO:
        return "correct_left", "turn_left"
    if offset > BLUE_CENTER_DEADZONE_RATIO:
        return "correct_right", "turn_right"
    return "centered_advance", "forward"



def encode_vision_frame(frame: Any, detection: dict[str, Any], action: str, motion: str, *, target_name: str = "blue") -> bytes | None:
    annotated = frame.copy()
    height, width = annotated.shape[:2]
    center_x = width // 2
    deadzone_px = int(width * BLUE_CENTER_DEADZONE_RATIO)
    left_limit = center_x - deadzone_px
    right_limit = center_x + deadzone_px

    cv2.line(annotated, (center_x, 0), (center_x, height), (255, 255, 255), 1)
    cv2.line(annotated, (left_limit, 0), (left_limit, height), (0, 255, 255), 1)
    cv2.line(annotated, (right_limit, 0), (right_limit, height), (0, 255, 255), 1)

    if detection["detected"]:
        center = (int(detection["x"]), int(detection["y"]))
        radius = int(detection["radius"])
        cv2.circle(annotated, center, radius, (255, 0, 0), 3)
        if detection.get("bbox"):
            bx, by, bw, bh = detection["bbox"]
            cv2.rectangle(annotated, (bx, by), (bx+bw, by+bh), (0, 255, 255), 2)
        cv2.circle(annotated, center, 3, (0, 255, 255), -1)

    label = f"OpenCV {target_name} ball: {action} -> {motion}"
    cv2.rectangle(annotated, (8, height - 42), (min(width - 8, 470), height - 8), (0, 0, 0), -1)
    cv2.putText(annotated, label, (18, height - 19), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)

    success, jpeg = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
    if not success:
        return None
    return jpeg.tobytes()




class TargetLock:
    """One vision-owner lock. Geometry association is not semantic object identity."""
    def __init__(self,settings):
        self.settings=settings
        self.center=None
        self.radius=None
        self.last_seen=None
        self.smoothed=None
        self.identity=0

    def process(self,detection,observed_at,*,allow_new=True):
        result=dict(detection)
        candidates=detection.get("candidates",[])
        if not candidates and detection.get("detected"):
            candidates=[dict(x=detection["x"],y=detection["y"],radius=detection["radius"],
                bbox=detection.get("bbox"),contourArea=detection.get("area",0),
                circleArea=detection.get("circleArea",0),circularity=detection.get("circularity",0),fillRatio=detection.get("fillRatio",0))]
        selected=None
        width,height=detection.get("frameWidth",640),detection.get("frameHeight",480)
        if self.center is None:
            selected=candidates[0] if candidates else None
        else:
            eligible=[c for c in candidates if .5<=c["radius"]/max(1,self.radius)<=2 and
                math.hypot((c["x"]-self.center[0])/width,(c["y"]-self.center[1])/height)<=self.settings.lock_distance]
            if observed_at-self.last_seen<=self.settings.reacquire_seconds and eligible:
                selected=min(eligible,key=lambda c:((c["x"]-self.center[0])**2+(c["y"]-self.center[1])**2,-c["contourArea"],c["x"],c["y"]))
            elif observed_at-self.last_seen>self.settings.reacquire_seconds and allow_new:
                self.center=None
                self.smoothed=None
                selected=candidates[0] if candidates else None
        if selected is None:
            result.update(detected=False,offset=None,lockState="reacquiring" if self.center else "searching",
                          lockId=self.identity,rejectReason="locked_target_missing" if self.center else detection.get("rejectReason"))
            return result
        if self.center is None: self.identity+=1
        self.center=(selected["x"],selected["y"])
        self.radius=selected["radius"]
        self.last_seen=observed_at
        raw=(selected["x"]-width/2)/(width/2)
        self.smoothed=raw if self.smoothed is None else self.settings.smoothing_alpha*raw+(1-self.settings.smoothing_alpha)*self.smoothed
        result.update(selected,area=selected["contourArea"],detected=True,rawOffset=raw,offset=self.smoothed,
                      lockState="locked",lockId=self.identity,rejectReason=None)
        return result

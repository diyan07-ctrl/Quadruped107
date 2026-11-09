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


def detect_blue_ball(frame: Any, *, lower=BLUE_HSV_LOWER, upper=BLUE_HSV_UPPER) -> dict[str, Any]:
    height, width = frame.shape[:2]
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
        "rejectReason": "no_blue_mask",
        "bbox": None,
        "area": 0,
        "frameWidth": width,
        "frameHeight": height,
        "mask": mask,
    }
    if mask_area < BLUE_MIN_MASK_AREA:
        detection["rejectReason"] = "mask_too_small"
        return detection

    contours, _hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    max_radius = int(min(width, height) * BLUE_MAX_RADIUS_RATIO)

    for contour in contours:
        contour_area = cv2.contourArea(contour)
        if contour_area < BLUE_MIN_MASK_AREA:
            continue

        perimeter = cv2.arcLength(contour, True)
        if perimeter <= 0:
            continue

        (x_float, y_float), radius_float = cv2.minEnclosingCircle(contour)
        radius = int(round(radius_float))
        if radius < BLUE_MIN_RADIUS:
            continue
        if radius > max_radius:
            continue

        circle_area = math.pi * radius_float * radius_float
        if circle_area <= 0:
            continue

        circularity = (4 * math.pi * contour_area) / (perimeter * perimeter)
        fill_ratio = contour_area / circle_area
        if circularity < BLUE_MIN_CIRCULARITY:
            continue
        if fill_ratio < BLUE_MIN_FILL_RATIO or fill_ratio > BLUE_MAX_FILL_RATIO:
            continue

        x, y = int(round(x_float)), int(round(y_float))
        candidates.append(
            {
                "x": x,
                "y": y,
                "bbox": list(cv2.boundingRect(contour)),
                "radius": radius,
                "contourArea": int(contour_area),
                "circleArea": int(circle_area),
                "circularity": round(circularity, 3),
                "fillRatio": round(fill_ratio, 3),
            }
        )

    if not candidates:
        detection["rejectReason"] = "no_circular_candidate"
        return detection

    candidate = max(candidates, key=lambda item: item["contourArea"])
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



def encode_vision_frame(frame: Any, detection: dict[str, Any], action: str, motion: str) -> bytes | None:
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

    label = f"OpenCV blue ball: {action} -> {motion}"
    cv2.rectangle(annotated, (8, height - 42), (min(width - 8, 470), height - 8), (0, 0, 0), -1)
    cv2.putText(annotated, label, (18, height - 19), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)

    success, jpeg = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
    if not success:
        return None
    return jpeg.tobytes()



"""Offline calibration-profile validation; never activates a servo or rewrites gaits."""
import math

JOINTS = ("shoulder_fl", "leg_fl", "shoulder_fr", "leg_fr",
          "shoulder_bl", "leg_bl", "shoulder_br", "leg_br")


def finite_positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def ticks_to_microseconds(ticks, actual_frequency_hz=50.0):
    if type(ticks) is not int or not 0 <= ticks < 4096:
        raise ValueError("ticks must be 0..4095 integer")
    return ticks * 1_000_000 / (4096 * finite_positive(actual_frequency_hz, "frequency"))


def validate_profile(data, *, require_qualified=True):
    if not isinstance(data, dict) or data.get("schema_version") != 1 or type(data.get("schema_version")) is not int:
        raise ValueError("Unsupported calibration schema")
    if type(data.get("revision")) is not int or data["revision"] < 1:
        raise ValueError("Positive profile revision required")
    if not isinstance(data.get("robot_id"), str) or not data["robot_id"].strip():
        raise ValueError("Unique robot_id required")
    if data.get("pwm_hz") != 50: raise ValueError("Current firmware requires 50Hz")
    joints = data.get("joints")
    if not isinstance(joints, list) or len(joints) not in (8, 9):
        raise ValueError("Eight leg joints and optional pan required")
    channels = set()
    for joint in joints:
        if not isinstance(joint, dict): raise ValueError("Joint must be an object")
        channel = joint.get("channel")
        if type(channel) is not int or not 0 <= channel <= 8 or channel in channels:
            raise ValueError("Unique channel 0..8 required")
        channels.add(channel)
        expected = JOINTS[channel] if channel < 8 else "camera_pan"
        if joint.get("id") != expected: raise ValueError("Joint ID/channel mismatch")
        if type(joint.get("direction")) is not int or joint["direction"] not in (-1, 1):
            raise ValueError("Direction must be -1 or +1")
        finite_positive(joint.get("max_ticks_per_second"), "speed limit")
        qualified = joint.get("qualified")
        if type(qualified) is not bool: raise ValueError("Explicit qualification status required")
        values = [joint.get(key) for key in ("min_tick", "neutral_tick", "max_tick")]
        if not qualified:
            if require_qualified: raise ValueError("Joint NOT YET QUALIFIED")
            if any(value is not None for value in values):
                raise ValueError("Unqualified template must not invent limits")
            continue
        if not isinstance(joint.get("evidence"), str) or not joint["evidence"].strip():
            raise ValueError("Calibration evidence required")
        if any(type(value) is not int or not 50 <= value <= 600 for value in values):
            raise ValueError("Limits must fit current firmware 50..600 guards")
        if not values[0] < values[1] < values[2]: raise ValueError("Require min < neutral < max")
    if channels != set(range(len(joints))): raise ValueError("Missing joint channel")
    return data


def bounded_target(profile, channel, tick):
    validate_profile(profile)
    if type(channel) is not int: raise ValueError("Integer channel required")
    joint = next((item for item in profile["joints"] if item["channel"] == channel), None)
    if joint is None or type(tick) is not int: raise ValueError("Unknown joint or noninteger target")
    if not joint["min_tick"] <= tick <= joint["max_tick"]:
        raise ValueError("Target exceeds qualified joint limit")
    return tick  # reject instead of silently clamping a gait into another pose


def ramp_tick(commanded_tick, target_tick, max_ticks_per_second, elapsed_seconds):
    # A first movement with no trustworthy starting command cannot be made safe
    # by fabricating a measured servo position.
    if commanded_tick is None: raise ValueError("Unknown initial position: supported commissioning required")
    for value in (commanded_tick, target_tick):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("Finite commanded tick estimates required")
    step = finite_positive(max_ticks_per_second, "speed") * finite_positive(elapsed_seconds, "elapsed time")
    if elapsed_seconds > .1: raise ValueError("Drop stale ramp update rather than catching up")
    return commanded_tick + max(-step, min(step, target_tick - commanded_tick))

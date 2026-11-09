#!/usr/bin/env python3
"""Deterministic planning estimates, never measured/qualified electrical ratings."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

# Editable planning assumptions. Current allowances are not measured maxima.
SERVO_V = 6.0
PACK_V, PACK_AH = 7.4, 1.8
NEW_PACK_V, NEW_PACK_AH = 11.1, 2.2
STALL_A = {"MG996R_manufacturer": 1.4, "MG996R_legacy_sheet": 2.5}
CONVERTER_CONT_A = 10.0
HEADROOM_FACTOR = 1.25
FIXED_INPUT_ALLOWANCE_W = 0.1  # additional reserve, not a measured quiescent current
ROUND_TRIP_OHM = 0.020        # illustrative cable + connector resistance
BOUNDS = {  # usable energy fraction, conversion efficiency, average load multiplier
    "optimistic": (0.85, 0.95, 0.80),
    "nominal": (0.75, 0.90, 1.00),
    "conservative": (0.60, 0.85, 1.25),
}
# rail, nominal V, quantity, idle A/unit, active A/unit, peak ALLOWANCE A/unit,
# accepted supply / interface caveat, source, confidence
COMPONENTS = [
    ("Pi 4 bare board", "logic", 5.1, 1, .60, 1.20, 2.00, "5V USB-C; qualify at connector", "S1", "active/peak allowances; no measured peak"),
    ("Uno R3", "logic", 5.0, 1, .05, .07, .10, "USB 5V; not VIN", "S2", "estimated board load"),
    ("PCA9685 breakout logic", "logic", 5.0, 1, .01, .015, .025, "IC 2.3–5.5V; breakout verify", "S3", "board allowance incl. LEDs"),
    ("CSI camera incremental", "logic", 5.0, 1, 0, .25, .35, "Pi CSI; 5V-equivalent load, not direct feed", "S1", "reference allowance; actual model unknown"),
    ("URM37", "logic", 5.0, 1, .02, .02, .05, "V5 reference 3.3–5.5V; verify revision", "S4", "published active; peak unknown"),
    ("HC-SR04", "logic", 5.0, 1, .015, .015, .03, "5V reference; module verify", "S5", "published active; peak unknown"),
    ("Touch module", "logic", 5.0, 5, .005, .005, .020, "unknown until module identified", "A1", "low-confidence allocation only"),
    ("Optional SSD1306 module", "optional_logic", 3.3, 1, .005, .030, .050, "Pi 3.3V-compatible breakout only", "S6/A1", "display-pattern dependent allocation"),
    ("Eight leg servos", "servo", 6.0, 8, .01, .70, 2.50, "MG996R S7 4.8–6.6V; MG995 S9 4.8–6.6V", "S7/S8/S9", "variant-dependent; scenario values"),
    ("Optional pan servo", "optional_servo", 6.0, 1, .01, .20, 2.50, "assume same family until identified", "A1", "allocation, not actual pan specification"),
]
# name: (count, current per powered joint A, duty fraction) groups, Pi current A,
# camera-equivalent current A, optional accessories. Groups count all 8 legs.
SCENARIOS = {
    "disabled_streaming": ([(8, .01, 1)], .80, .25, False),
    "standing": ([(8, .35, 1)], .80, .25, False),
    "slow_walking": ([(4, .70, 1), (4, .35, 1)], .90, .25, False),
    "turning": ([(4, .90, 1), (4, .50, 1)], 1.00, .25, False),
    "exploration": ([(6, .70, 1), (2, .35, 1)], 1.20, .25, False),
    "vision_standing": ([(8, .35, 1)], 1.20, .25, False),
    "pan_oled_exploration": ([(6, .70, 1), (2, .35, 1)], 1.20, .25, True),
    "high_load": ([(8, .90, 1)], 1.20, .25, False),
}
SERVO_CASES = {
    "powered idle / PWM disabled allowance": [(8, .01, 1)],
    "no-load MG996R reference": [(8, .17, 1)],
    "standing assumption": [(8, .35, 1)],
    "walking mixed support": [(4, .70, 1), (4, .35, 1)],
    "turning mixed support": [(4, .90, 1), (4, .50, 1)],
    "high-load assumption": [(8, .90, 1)],
    "simultaneous acceleration allowance": [(8, 1.40, 1)],
    "three stalls lower / five moving": [(3, 1.40, 1), (5, .70, 1)],
    "three stalls upper / five moving": [(3, 2.50, 1), (5, .70, 1)],
    "eight stall lower bound scenario": [(8, 1.40, 1)],
    "eight stall upper bound scenario": [(8, 2.50, 1)],
    "nine stall upper bound scenario": [(9, 2.50, 1)],
}


def number(value, name, zero=False):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite numeric")
    if value < 0 or (not zero and value == 0):
        raise ValueError(f"{name} must be {'nonnegative' if zero else 'positive'}")
    return value


def fraction(value, name):
    number(value, name)
    if value > 1: raise ValueError(f"{name} must be <= 1")
    return value


def power(voltage_v, current_a):
    return number(voltage_v, "voltage") * number(current_a, "current", zero=True)


def energy(voltage_v, capacity_ah):
    return number(voltage_v, "voltage") * number(capacity_ah, "capacity")


def aggregate(groups):
    total = 0.0
    for count, current, duty in groups:
        if type(count) is not int or count < 0: raise ValueError("count must be a nonnegative integer")
        number(current, "current", zero=True)
        number(duty, "duty", zero=True)
        if duty > 1: raise ValueError("duty must be <= 1")
        total += count * current * duty
    return total


def input_power(output_w, efficiency, fixed_w=0.0):
    return number(output_w, "output", zero=True) / fraction(efficiency, "efficiency") + number(fixed_w, "fixed power", zero=True)


def converter_loss(output_w, efficiency, fixed_w=0.0):
    return input_power(output_w, efficiency, fixed_w) - output_w


def input_current(output_w, voltage_v, efficiency, fixed_w=0.0):
    return input_power(output_w, efficiency, fixed_w) / number(voltage_v, "input voltage")


def runtime_hours(nominal_wh, usable_fraction, average_input_w):
    return number(nominal_wh, "energy") * fraction(usable_fraction, "usable fraction") / number(average_input_w, "average input power")


def wire_loss(current_a, round_trip_ohm):
    return number(current_a, "current", zero=True) ** 2 * number(round_trip_ohm, "resistance", zero=True)


def capacitor_f(step_a, seconds, delta_v):
    return number(step_a, "step current") * number(seconds, "duration") / number(delta_v, "allowed droop")


def logic_w(pi_a, camera_a, optional=False):
    base = sum(v * count * active for name, rail, v, count, idle, active, peak, accepted, source, confidence in COMPONENTS
               if rail == "logic" and name not in {"Pi 4 bare board", "CSI camera incremental"})
    return base + 5.1 * pi_a + 5.0 * camera_a + (.030 * 3.3 if optional else 0)


def scenario(name):
    groups, pi_a, camera_a, optional = SCENARIOS[name]
    current = aggregate(groups) + (.20 if optional else 0)
    return {"servo_a": current, "servo_w": power(SERVO_V, current),
            "logic_w": logic_w(pi_a, camera_a, optional)}


def runtimes(name, bound):
    load = scenario(name)
    usable, efficiency, multiplier = BOUNDS[bound]
    servo_input = input_power(load["servo_w"] * multiplier, efficiency, FIXED_INPUT_ALLOWANCE_W)
    half_input = input_power(load["servo_w"] * multiplier / 2, efficiency, FIXED_INPUT_ALLOWANCE_W)
    shared_input = servo_input + input_power(load["logic_w"] * multiplier, efficiency, FIXED_INPUT_ALLOWANCE_W)
    return {
        "A_servo_minutes": 60 * runtime_hours(energy(PACK_V, PACK_AH), usable, servo_input),
        # Equal balanced branches; real B runtime is minimum of branch runtimes.
        "B_balanced_servo_minutes": 60 * runtime_hours(energy(PACK_V, PACK_AH), usable, half_input),
        "C_shared_3S_minutes": 60 * runtime_hours(energy(NEW_PACK_V, NEW_PACK_AH), usable, shared_input),
        "D_3S_servo_minutes": 60 * runtime_hours(energy(NEW_PACK_V, NEW_PACK_AH), usable, servo_input),
        "bank_minutes_per_delivered_wh": 60 / (load["logic_w"] * multiplier),
    }


def report():
    return {
        "status": "ESTIMATES ONLY; installed parts and batteries NOT YET QUALIFIED",
        "nominal_pack_wh": energy(PACK_V, PACK_AH),
        "three_separate_pack_inventory_wh": 3 * energy(PACK_V, PACK_AH),
        "replacement_3S_wh": energy(NEW_PACK_V, NEW_PACK_AH),
        "servo_cases": {name: {"current_a": aggregate(groups), "output_w": power(SERVO_V, aggregate(groups))}
                        for name, groups in SERVO_CASES.items()},
        "scenarios": {name: {**scenario(name), "runtimes": {bound: runtimes(name, bound) for bound in BOUNDS}}
                      for name in SCENARIOS},
        "upper_fault": {"input_a_at_6v_85pct": input_current(120, 6, .85, .1),
                        "input_a_at_9v_85pct": input_current(120, 9, .85, .1)},
        "high_load": {"converter_loss_w_85pct": converter_loss(43.2, .85, .1),
                      "continuous_target_a_with_headroom": 7.2 * HEADROOM_FACTOR,
                      "candidate_10a_reserve_pct": (CONVERTER_CONT_A / 7.2 - 1) * 100},
        "distribution": {"20a_drop_v_at_20mohm": 20 * ROUND_TRIP_OHM,
                         "20a_wire_loss_w": wire_loss(20, ROUND_TRIP_OHM),
                         "10a_2ms_250mv_capacitance_f": capacitor_f(10, .002, .25)},
        "components": [dict(zip(("name", "rail", "v", "quantity", "idle_a_each", "active_a_each",
                                 "peak_allowance_a_each", "accepted", "source", "confidence"), row))
                       for row in COMPONENTS],
    }


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |",
                      "| " + " | ".join("---" for _ in headers) + " |"] +
                     ["| " + " | ".join(map(str, row)) + " |" for row in rows])


def generated_tables():
    component_rows = []
    for name, rail, v, n, idle, active, peak, accepted, source, confidence in COMPONENTS:
        component_rows.append([name, n, f"{v:.1f}", f"{idle:.3f}", f"{active:.3f}", f"{peak:.3f}",
                               f"{v*n*active:.3f}", accepted, source, confidence])
    servo_rows = [[name, f"{aggregate(groups):.2f}", f"{power(SERVO_V, aggregate(groups)):.2f}"]
                  for name, groups in SERVO_CASES.items()]
    load_rows = []
    runtime_rows = []
    architecture_rows = []
    for name in SCENARIOS:
        s = scenario(name)
        load_rows.append([name, f"{s['servo_a']:.2f}", f"{s['servo_w']:.2f}", f"{s['logic_w']:.3f}",
                          f"{s['servo_w']+s['logic_w']:.3f}",
                          f"{input_power(s['servo_w'], .90, .1):.3f}",
                          f"{input_current(s['servo_w'], 6, .85, .1):.3f}"])
        estimates = [runtimes(name, bound) for bound in BOUNDS]
        runtime_rows.append([name] + [f"{r['A_servo_minutes']:.1f}" for r in estimates])
        r = runtimes(name, "nominal")
        architecture_rows.append([name] + [f"{r[key]:.1f}" for key in
                                 ("B_balanced_servo_minutes", "C_shared_3S_minutes", "D_3S_servo_minutes", "bank_minutes_per_delivered_wh")])
    return {
        "COMPONENT_LOADS.md": table(["Component", "Qty", "Model V", "Idle A/each", "Active A/each", "Peak allowance A/each", "Active W total", "Supply / range caveat", "Source", "Confidence"], component_rows),
        "SERVO_ANALYSIS.md": table(["Scenario at 6V distribution output", "A", "W"], servo_rows),
        "POWER_BUDGET.md": table(["Scenario", "Servo A", "Servo W", "Logic W", "Total output W", "Servo input W at 90%", "Servo input A at 6V / 85%"], load_rows),
        "RUNTIME_ESTIMATES.md": table(["Scenario", "A optimistic min", "A nominal min", "A conservative min"], runtime_rows) + "\n\n" +
            table(["Scenario", "B balanced servo min", "C shared 3S min", "D 3S servo min", "Bank min per delivered Wh"], architecture_rows),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check", action="store_true", help="Check generated Markdown table blocks")
    parser.add_argument("--write-tables", action="store_true", help="Regenerate documented table blocks")
    args = parser.parse_args()
    if args.check or args.write_tables:
        for name, generated in generated_tables().items():
            destination = Path(__file__).resolve().parent / name
            content = destination.read_text(encoding="utf-8")
            start, end = "<!-- POWER_TABLE_START -->", "<!-- POWER_TABLE_END -->"
            before, remainder = content.split(start, 1)
            old, after = remainder.split(end, 1)
            expected = "\n" + generated + "\n"
            if args.write_tables:
                destination.write_text(before + start + expected + end + after, encoding="utf-8")
            elif old != expected:
                raise SystemExit(f"Outdated assumptions/table: {name}; run --write-tables")
        print("Power Markdown tables match calculator assumptions.")
    else:
        print(json.dumps(report(), indent=2, sort_keys=True, allow_nan=False) if args.json else
              "ESTIMATES ONLY — no qualified hardware ratings\n" +
              "\n\n".join(name + "\n" + value for name, value in generated_tables().items()) +
              "\n\nEngineering quantities:\n" + json.dumps({k:v for k,v in report().items() if k in
                  {"nominal_pack_wh","replacement_3S_wh","upper_fault","high_load","distribution"}}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

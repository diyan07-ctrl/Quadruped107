import copy
import importlib.util
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "software/pi"))
from quadruped.calibration import JOINTS, validate_profile, ticks_to_microseconds, bounded_target, ramp_tick
spec = importlib.util.spec_from_file_location("power_budget", ROOT / "hardware/Power/power_budget.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class PowerTests(unittest.TestCase):
    def test_power_energy_and_efficiency(self):
        self.assertEqual(p.power(6, 2.5), 15)
        self.assertAlmostEqual(p.energy(7.4, 1.8), 13.32)
        self.assertAlmostEqual(p.input_power(18, .9), 20)
        self.assertAlmostEqual(p.converter_loss(18, .9), 2)
        self.assertAlmostEqual(p.input_current(18, 10, .9), 2)

    def test_runtime_and_independent_branches(self):
        self.assertAlmostEqual(p.runtime_hours(13.32, .75, 30), .333)
        r = p.runtimes("slow_walking", "nominal")
        self.assertLess(r["B_balanced_servo_minutes"], r["A_servo_minutes"] * 2)
        self.assertGreater(r["D_3S_servo_minutes"], r["C_shared_3S_minutes"])
        self.assertGreater(p.runtimes("slow_walking", "optimistic")["A_servo_minutes"],
                           p.runtimes("slow_walking", "conservative")["A_servo_minutes"])

    def test_multi_servo_aggregation(self):
        self.assertAlmostEqual(p.aggregate([(4, .7, 1), (4, .35, 1)]), 4.2)
        self.assertAlmostEqual(p.aggregate([(8, 2.5, 1)]), 20)
        self.assertAlmostEqual(p.aggregate([(9, 2.5, 1)]), 22.5)
        self.assertEqual(p.aggregate([(8, 2.5, 0)]), 0)
        self.assertEqual(p.power(6, 0), 0)

    def test_wire_heat_capacitance_and_headroom(self):
        self.assertAlmostEqual(p.wire_loss(20, .02), 8)
        self.assertAlmostEqual(p.capacitor_f(10, .002, .25), .08)
        self.assertAlmostEqual(p.report()["high_load"]["continuous_target_a_with_headroom"], 9)
        self.assertAlmostEqual(p.report()["upper_fault"]["input_a_at_6v_85pct"], (120/.85+.1)/6)

    def test_invalid_inputs(self):
        for bad in (0, -1, math.nan, math.inf, True, "5"):
            for function in (lambda: p.energy(bad, 1), lambda: p.power(bad, 1),
                             lambda: p.runtime_hours(1, 1, bad), lambda: p.input_current(1, bad, .9),
                             lambda: p.input_power(1, bad)):
                with self.assertRaises(ValueError): function()
        for efficiency in (1.01, 2):
            with self.assertRaises(ValueError): p.input_power(1, efficiency)
        for groups in ([(-1, 1, 1)], [(True, 1, 1)], [(1, -1, 1)], [(1, 1, 2)], [(1, 1, -1)]):
            with self.assertRaises(ValueError): p.aggregate(groups)

    def test_every_case_is_finite_and_runtime_bounds_ordered(self):
        for name in p.SCENARIOS:
            values = [p.runtimes(name, bound)["A_servo_minutes"] for bound in p.BOUNDS]
            self.assertGreater(values[0], values[1])
            self.assertGreater(values[1], values[2])
            self.assertTrue(all(math.isfinite(value) and value > 0 for value in values))


class CalibrationTests(unittest.TestCase):
    def profile(self):
        return dict(schema_version=1, revision=1, robot_id="test-fixture", pwm_hz=50,
                    joints=[dict(channel=i, id=name, direction=1, min_tick=200, neutral_tick=300,
                                 max_tick=400, qualified=True, evidence="synthetic unit-test fixture",
                                 max_ticks_per_second=50) for i, name in enumerate(JOINTS)])

    def test_profile_and_joint_limits(self):
        data = self.profile()
        self.assertIs(validate_profile(data), data)
        self.assertEqual(bounded_target(data, 0, 250), 250)
        with self.assertRaises(ValueError): bounded_target(data, 0, 401)
        data["joints"][1]["channel"] = 0
        with self.assertRaises(ValueError): validate_profile(data)

    def test_unqualified_template_and_version_rejected(self):
        data = self.profile()
        data["joints"][0].update(qualified=False, min_tick=None, neutral_tick=None, max_tick=None)
        with self.assertRaises(ValueError): validate_profile(data)
        validate_profile(data, require_qualified=False)
        data["schema_version"] = True
        with self.assertRaises(ValueError): validate_profile(data, require_qualified=False)

    def test_tick_conversion_and_safe_ramp(self):
        self.assertAlmostEqual(ticks_to_microseconds(300), 1464.84375)
        self.assertAlmostEqual(ramp_tick(300, 400, 50, .02), 301)
        with self.assertRaises(ValueError): ramp_tick(None, 300, 50, .02)
        with self.assertRaises(ValueError): ramp_tick(300, 400, 50, 1)
        with self.assertRaises(ValueError): ticks_to_microseconds(300, 0)

    def test_optional_ninth_joint_does_not_change_leg_mapping(self):
        data = self.profile()
        pan = copy.deepcopy(data["joints"][0])
        pan.update(channel=8, id="camera_pan")
        data["joints"].append(pan)
        validate_profile(data)
        self.assertEqual(len(data["joints"]), 9)


if __name__ == "__main__": unittest.main()

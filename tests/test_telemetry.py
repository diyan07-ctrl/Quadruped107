"""TEL1 is passive, bounded and never qualifies physical acquisition age or output state."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"software/pi"))
from quadruped.telemetry import parse_tel1,TelemetryStream
from quadruped.serial_link import SerialLink,Pending
from quadruped.explain import DecisionHistory

class TelemetryTests(unittest.TestCase):
    def test_fields_and_unknown_output_enable(self):
        stream=TelemetryStream()
        self.assertTrue(stream.ingest("TEL 1 42 123456 380 1 15 3 7600 5980"))
        result=stream.snapshot()
        self.assertEqual(result["distanceM"],.38)
        self.assertIsNone(result["servoOutputsEnabled"])
        self.assertFalse(result["acquisitionFreshnessKnown"])
        self.assertFalse(result["controlQualified"])

    def test_invalid_and_reserved_fields(self):
        valid="TEL 1 42 123456 380 1 15 3 7600 5980"
        for line in (valid+" x",valid.replace(" 15 "," 256 "),valid.replace(" 380 "," -2 "),
                     valid.replace(" 380 "," -1 "),valid.replace(" 3 "," 32 "),"TEL 2 1 1 1 1 1 1 1 1",
                     "TEL 1 "+"1 "*70):
            with self.assertRaises(ValueError): parse_tel1(line)

    def test_duplicate_out_of_order_expiration_and_wrap(self):
        clock=[0.]
        stream=TelemetryStream(clock=lambda:clock[0])
        stream.ingest("TEL 1 65535 4294967290 380 1 15 0 7600 5980")
        self.assertTrue(stream.ingest("TEL 1 0 4 380 1 15 0 7600 5980"))
        self.assertFalse(stream.ingest("TEL 1 0 4 380 1 15 0 7600 5980"))
        self.assertFalse(stream.ingest("TEL 1 65535 3 380 1 15 0 7600 5980"))
        clock[0]=.31
        self.assertFalse(stream.snapshot()["rangeValid"])
        self.assertIsNone(stream.snapshot()["distanceM"])

    def test_reset_requires_new_session(self):
        stream=TelemetryStream()
        stream.ingest("TEL 1 10 5000 380 1 15 0 7600 5980")
        self.assertFalse(stream.ingest("TEL 1 11 10 380 1 15 0 7600 5980"))
        stream.reset()
        self.assertTrue(stream.ingest("TEL 1 0 0 -1 0 0 0 -1 -1"))

    def test_tel_cannot_complete_motion_or_arm(self):
        link=SerialLink()
        pending=Pending("ARM",identifier=42)
        link.pending[42]=pending
        link._receive("TEL 1 42 123456 380 1 15 3 7600 5980")
        self.assertFalse(pending.event.is_set())
        self.assertFalse(link.armed)

    def test_history_is_bounded_and_records_actual_outcomes(self):
        history=DecisionHistory()
        for index in range(400):
            history.record("fixture"+str(index),status="requested",generation=index)
        self.assertEqual(len(history.snapshot()),128)
        self.assertLessEqual(len(history.last),32)
        self.assertTrue(all(item["status"]=="requested" for item in history.snapshot()))

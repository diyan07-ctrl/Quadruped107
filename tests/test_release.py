"""Non-actuating release regressions for defects found in the integration audit."""
import importlib.util
from pathlib import Path
import sys
import json
import os
import subprocess
import tempfile
import io
import urllib.error
import unittest
from unittest.mock import patch, Mock
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'software/pi'))
from quadruped.vision import detect_blue_ball
from simulation.twin import validate_render, SimulationFault
from quadruped.telemetry import TelemetryStream


class ReleaseTests(unittest.TestCase):
    def test_live_trial_rejection_preserves_stage_and_reason(self):
        sys.path.insert(0,str(ROOT/'tools'))
        spec=importlib.util.spec_from_file_location('release_hil',ROOT/'tools/phase4-hil.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        client=module.Client('http://127.0.0.1:7000')
        failure=urllib.error.HTTPError('http://127.0.0.1:7000/api/arm',409,'Conflict',{},
                                      io.BytesIO(b'{"error":"stale sensing"}'))
        with patch.object(client.opener,'open',side_effect=failure):
            with self.assertRaisesRegex(RuntimeError,'HTTP 409 at api/arm; server rejection: .*stale sensing'):
                client.call('api/arm',{})

    def test_recording_preserves_measured_samples_and_disarms_at_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            result=subprocess.run([sys.executable,'-m','simulation.twin','--headless',
                '--demo','forward','--arm-demo','--steps','96','--record',str(base/'test.avi'),
                '--report',str(base/'test.json')],cwd=ROOT,
                env=dict(os.environ,PYTHONPATH=str(ROOT/'software/pi')),capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            report=json.loads((base/'test.json').read_text())
            samples=[json.loads(row) for row in (base/'test.joints.jsonl').read_text().splitlines()]
            self.assertEqual(len(samples),12)
            self.assertEqual(report['recording']['frames'],len(samples))
            self.assertFalse(report['virtualUno']['armed'])
            self.assertEqual(report['activeMask'],0)
            self.assertTrue(all(len(row['measuredJointPositionsRad'])==8 for row in samples))
            self.assertTrue(any(row['measuredJointPositionsRad']!=row['requestedTargetsRad'] for row in samples))
            video=cv2.VideoCapture(str(base/'test.avi'))
            try:
                frames=0
                while True:
                    ok,frame=video.read()
                    if not ok: break
                    validate_render(frame); frames+=1
                self.assertEqual(frames,len(samples))
            finally: video.release()

    def test_poll_token_wrap_consumes_each_token_once(self):
        stream=TelemetryStream(clock=lambda:1.)
        stream.poll_sequence=65534
        for sequence,expected in enumerate((65535,0,1)):
            self.assertEqual(stream.poll(),expected)
            packet=f'TEL 2 {sequence} {100+sequence} 400 1 19 0 10 0 {expected} 0'
            self.assertTrue(stream.ingest(packet))
            self.assertFalse(stream.ingest(packet))
        self.assertFalse(stream.snapshot()['controlQualified'])

    def test_edge_clipped_circles_never_become_targets(self):
        for color,lower,upper in (((255,0,0),(95,70,30),(140,255,255)),
                                  ((0,255,255),(20,70,30),(40,255,255))):
            for center in ((12,240),(628,240),(320,12),(320,468)):
                image=np.zeros((480,640,3),np.uint8)
                cv2.circle(image,center,35,color,-1)
                result=detect_blue_ball(image,lower=lower,upper=upper)
                self.assertFalse(result['detected'],center)
                self.assertTrue(any(d['touchesFrameEdge'] for d in result['contourDiagnostics']))
            image=np.zeros((480,640,3),np.uint8)
            cv2.circle(image,(320,240),35,color,-1)
            self.assertTrue(detect_blue_ball(image,lower=lower,upper=upper)['detected'])

    def test_render_rejects_black_flat_and_missing_frames(self):
        for frame in (None,np.zeros((480,640,3),np.uint8),
                      np.full((480,640,3),255,np.uint8),np.zeros((1,1,3),np.uint8)):
            with self.assertRaises(SimulationFault): validate_render(frame)
        image=np.zeros((480,640,3),np.uint8)
        image[100:200,100:200]=200
        validate_render(image)

    def test_qualification_runner_propagates_failed_check(self):
        spec=importlib.util.spec_from_file_location('release_checks',ROOT/'tools/phase4-local-checks.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(sys,'argv',['checks','--output',directory]), \
                 patch.object(module.subprocess,'check_output',return_value='test-revision'), \
                 patch.object(module.subprocess,'run',return_value=Mock(returncode=1)):
                self.assertEqual(module.main(),1)


if __name__=='__main__': unittest.main()

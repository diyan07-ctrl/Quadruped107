"""Recorder safety tests use UART doubles; they do not qualify physical hardware."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('commission_two',ROOT/'tools/commission-two-sensors.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class RecorderTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        base=Path(self.directory.name);binary=base/'sensor.hex';binary.write_bytes(b'TEST ONLY NOT FIRMWARE')
        self.args=SimpleNamespace(electrical_verified=True,upload_verified=True,port='UART_DOUBLE',
            seconds=1,binary=binary,firmware_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
            output=base/'evidence',reference_m=None,label='UNIT TEST')
        self.now=0.;self.created=[]
    def clock(self):self.now+=.001;return self.now
    def factory(self,capability='caps_sensor2_t2',corrupt=False):
        outer=self
        class UART:
            def __init__(self,**kwargs):self.lines=[];self.writes=[];self.closed=False;self.seq=0;outer.created.append(self)
            def reset_input_buffer(self):pass
            def write(self,data):
                self.writes.append(data);line=data.decode().strip();parts=line.split()
                if line=='HELLO':self.lines.append('READY Quadruped107 1')
                elif line=='CAPS 1':self.lines.append('DONE 1 '+capability)
                elif parts[0] in ('ARM','MOVE','SERVO'):self.lines.append('ERR '+parts[1]+' sensor_only')
                elif parts[0]=='STOP':self.lines.append('DONE '+parts[1]+' stopped')
                elif parts[0]=='TELEM':
                    self.lines.append('DONE '+parts[1]+' telemetry')
                    if parts[-1]=='1':self.lines.append('TEL 1 0 1000 800 1 19 0 -1 -1')
                elif line=='PING':self.lines.append('PONG')
                elif parts[0]=='POLL':
                    self.lines.append('TEL 2 corrupt' if corrupt else f'TEL 2 {self.seq} {int(outer.now*1000)} 800 1 19 0 0 0 {parts[2]} 0')
                    self.seq+=1
                return len(data)
            def readline(self,*args):
                outer.now+=.02
                return ((self.lines.pop(0)+'\n').encode() if self.lines else b'')
            def close(self):self.closed=True
        return UART
    def collect(self,**kwargs):
        with patch.object(module.time,'sleep'),patch.object(module.subprocess,'check_output',return_value='TEST_SOURCE'):
            return module.collect(self.args,serial_factory=self.factory(**kwargs),clock=self.clock)

    def test_missing_gate_or_hash_mismatch_never_opens_port(self):
        for field in ('electrical_verified','upload_verified'):
            setattr(self.args,field,False)
            with self.assertRaises(ValueError):self.collect()
            setattr(self.args,field,True)
        self.args.firmware_sha256='0'*64
        with self.assertRaises(ValueError):self.collect()
        self.assertEqual(self.created,[])

    def test_unknown_firmware_never_receives_arm_probe(self):
        result=self.collect(capability='caps_motion')
        self.assertEqual(result['status'],'FAIL')
        self.assertFalse(any(line.startswith(b'ARM') for line in self.created[0].writes))
        self.assertTrue(self.created[0].closed)

    def test_exact_t2_records_real_parser_semantics_and_closes_with_stop(self):
        result=self.collect()
        self.assertEqual(result['status'],'PASS',result)
        self.assertEqual(result['evidenceClass'],'TEST DOUBLE')
        rows=[json.loads(line) for line in (self.args.output/'serial.jsonl').read_text().splitlines()]
        states=[row['sensors'] for row in rows if 'sensors' in row]
        self.assertTrue(states)
        self.assertEqual(set(states[-1]['touches']),{'touch_back','touch_front_bottom'})
        self.assertEqual(result['tel1Diagnostics'],'PASS')
        self.assertEqual(result['actuatorRejections'],'PASS')
        self.assertTrue(self.created[0].closed)
        self.assertEqual(self.created[0].writes[-1],b'STOP 99\n')
        self.assertFalse(result['uploadedByThisTool'])

    def test_corruption_is_failed_evidence_and_never_fabricates_samples(self):
        result=self.collect(corrupt=True)
        self.assertEqual(result['status'],'FAIL')
        self.assertEqual(result['samples'],0)
        self.assertGreater(result['rejectedRecords'],0)
        self.assertTrue(self.created[0].closed)

if __name__=='__main__':unittest.main()

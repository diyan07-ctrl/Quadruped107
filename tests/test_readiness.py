"""Physical interfaces qualified with deterministic inputs; no hardware opened."""
import queue
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'software/pi'))
from quadruped.telemetry import TelemetryStream, parse_tel2
from quadruped.serial_link import SerialLink, Pending
from quadruped.sensors import SensorManager
from quadruped.physical_sensors import PhysicalSensorProvider
from quadruped.display import render, DisplayService, MockDisplay, SSD1306
from quadruped.main import Runtime, create_app


def tel(seq=0, uptime=100, distance=400, flags=19, mask=0, range_age=10, touch_age=0, token=1, faults=0):
    return f'TEL 2 {seq} {uptime} {distance} 1 {flags} {mask} {range_age} {touch_age} {token} {faults}'


class AgeTests(unittest.TestCase):
    def setUp(self):
        self.now=[10.]
        self.stream=TelemetryStream(clock=lambda:self.now[0])
    def ingest(self,**kwargs):
        token=self.stream.poll()
        return self.stream.ingest(tel(token=token,**kwargs))
    def test_acquisition_age_plus_full_rtt(self):
        token=self.stream.poll(); self.now[0]+=.2
        self.assertTrue(self.stream.ingest(tel(token=token,range_age=150)))
        self.assertFalse(self.stream.snapshot()['rangeValid'])
        self.assertGreaterEqual(self.stream.snapshot()['rangeAge'],.349)
    def test_expired_poll_and_unsolicited(self):
        self.assertFalse(self.stream.ingest(tel()))
        token=self.stream.poll(); self.now[0]+=.301
        self.assertFalse(self.stream.ingest(tel(token=token)))
    def test_sequence_drop_wrap_and_reset(self):
        self.assertTrue(self.ingest(seq=65534,uptime=4294967290))
        self.now[0]+=.01
        self.assertTrue(self.ingest(seq=0,uptime=4))
        self.assertEqual(self.stream.snapshot()['drops'],1)
        self.assertFalse(self.ingest(seq=0,uptime=4))
        self.assertFalse(self.ingest(seq=65535,uptime=3))
        self.assertFalse(self.ingest(seq=1,uptime=0))
        self.stream.reset()
        self.assertTrue(self.ingest(seq=0,uptime=0))
    def test_timeout_and_no_qualification(self):
        self.assertTrue(self.ingest())
        self.assertTrue(self.stream.snapshot()['rangeValid'])
        self.assertFalse(self.stream.snapshot()['controlQualified'])
        self.now[0]+=.3
        self.assertFalse(self.stream.snapshot()['rangeValid'])
    def test_malformed_bounds(self):
        for line in (tel(range_age=1000),tel(flags=128),tel(distance=-1),tel(mask=32),
                     tel(token=65536),tel(faults=256),tel().replace(' 400 ',' +400 '),tel()+' extra'):
            with self.subTest(line=line),self.assertRaises(ValueError): parse_tel2(line)
    def test_worst_case_line_budget(self):
        line=tel(seq=65535,uptime=4294967295,distance=4000,flags=127,mask=31,
                 range_age=300,touch_age=300,token=65535,faults=255)
        self.assertLessEqual(len(line),63)
        parse_tel2(line)
    def test_local_faults_override_validity(self):
        self.assertTrue(self.ingest(faults=15))
        self.assertFalse(self.stream.snapshot()['rangeValid'])
        self.assertFalse(self.stream.snapshot()['touchValid'])
    def test_replay_poll_consumed(self):
        token=self.stream.poll()
        self.assertTrue(self.stream.ingest(tel(token=token)))
        self.assertFalse(self.stream.ingest(tel(seq=1,token=token)))


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.now=[10.]
        self.link=SerialLink('mock',sensor_only=True)
        self.link.connected=True
        self.link.capability='caps_sensor2'
        self.link.telemetry=TelemetryStream(clock=lambda:self.now[0])
        self.manager=SensorManager(clock=lambda:self.now[0],source='physical_uno')
        self.provider=PhysicalSensorProvider(self.link,self.manager)
    def feed(self,seq,**kwargs):
        token=self.link.telemetry.poll()
        self.link._receive(tel(seq=seq,uptime=100+seq*200,token=token,**kwargs))
        self.provider.update()
    def test_range_metres_and_missing_clearance(self):
        self.feed(0)
        state=self.manager.snapshot()
        self.assertEqual(state['observations']['urm37']['measurement'],.4)
        self.assertFalse(state['virtual'])
        self.assertTrue(state['monitoringOnly'])
        self.assertNotIn('hcsr04',state['observations'])
        self.assertNotIn('sweep_forward',state['observations'])
        self.assertIsNotNone(state['fault'])
    def test_no_retimestamp_of_same_record(self):
        self.feed(0)
        self.now[0]+=.31; self.provider.update()
        self.assertFalse(self.manager.snapshot()['observations']['urm37']['valid'])
    def test_boot_press_not_event_release_then_debounced_press(self):
        self.feed(0,mask=1)
        self.assertEqual(self.manager.snapshot()['events'],[])
        for seq,mask in ((1,0),(2,0),(3,1),(4,1)):
            self.now[0]+=.2; self.feed(seq,mask=mask)
        self.assertTrue(any(e['pressed'] for e in self.manager.snapshot()['events']))
    def test_disconnect_clears_state_and_reconnect_disarms(self):
        self.feed(0,mask=1)
        self.link._fail('USB lost'); self.provider.update()
        self.assertEqual(self.manager.snapshot()['observations'],{})
        self.assertFalse(self.link.armed)
        self.assertEqual(self.link.telemetry.snapshot()['record'],None)
    def test_legacy_cannot_masquerade(self):
        self.link.capability=None
        self.link._receive('TEL 1 1 100 400 1 3 0 -1 -1')
        self.provider.update()
        self.assertEqual(self.manager.snapshot()['observations'],{})
    def test_invalid_range_never_healthy(self):
        self.feed(0,distance=-1,flags=18,faults=2)
        self.assertFalse(self.manager.snapshot()['observations']['urm37']['valid'])
    def test_sensor_link_never_arms_even_before_negotiation(self):
        self.link.capability=None
        for verb,args in (('ARM',()),('MOVE',('stand',)),('SERVO',(0,300))):
            with self.subTest(verb=verb),self.assertRaises(RuntimeError): self.link.submit(verb,*args)
        self.link.submit('STOP')
    def test_negotiation_does_not_complete_motion(self):
        pending=Pending('ARM',identifier=9)
        self.link.pending[9]=pending
        self.link._receive('DONE 0 caps_sensor2')
        self.link._receive('DONE 0 telemetry')
        self.feed(9)
        self.assertFalse(pending.event.is_set())
        self.assertFalse(self.link.armed)
        self.assertEqual(self.link.snapshot()['telemetryRate'],5)
    def test_physical_sensors_virtual_output_dashboard_stop(self):
        runtime=Runtime(simulate=True,actuator_backend='virtual',sensor_source='physical_uno',sensor_link=self.link)
        try:
            token=self.link.telemetry.poll()
            self.link._receive(tel(token=token))
            runtime.physical_provider.update()
            state=runtime.state()
            self.assertFalse(state['sensors']['virtual'])
            self.assertFalse(state['physicalActuationAllowed'])
            self.assertEqual(state['sensorSource'],'physical_uno')
            self.assertIsNotNone(runtime._sensor_inhibition('forward'))
            self.assertIsNone(runtime.bridge)
            response=create_app(runtime).test_client().post('/api/stop',json={})
            self.assertEqual(response.status_code,200)
            self.assertFalse(self.link.armed)
        finally: runtime.close()
    def test_conflicting_sensor_sources_rejected(self):
        with self.assertRaises(ValueError):
            Runtime(simulate=True,actuator_backend='virtual',virtual_sensors=True,sensor_source='physical_uno')


class DisplayTests(unittest.TestCase):
    def test_screens(self):
        self.assertEqual(render({}).screen,'startup')
        cases=[({'motion':{}},'idle'),
               ({'motion':{'stopping':True},'sensors':{'fault':'bad'}},'stop'),
               ({'link':{'connected':False}},'fault'),
               ({'sensors':{'touches':{'head':{'pressed':True}}}},'touch'),
               ({'sensors':{'front_m':.2}},'obstacle'),
               ({'vision':{'targetFresh':True}},'target'),
               ({'vision':{'behavior':'SEARCH'}},'search'),
               ({'sensors':{'observations':{'urm37':{'valid':True,'measurement':.4}}}},'distance'),
               ({'motion':{'currentMotion':'greeting'}},'happy')]
        for state,screen in cases:
            self.assertEqual(render(state).screen,screen)
        self.assertTrue(render({'motion':{}},19).blink)
    def test_rate_limit_and_bounded_mock(self):
        now=[0.]; backend=MockDisplay()
        display=DisplayService(backend,lambda:{},clock=lambda:now[0])
        display.step(); display.step()
        self.assertEqual(len(backend.frames),1)
        for _ in range(60): now[0]+=.21; display.step()
        self.assertEqual(len(backend.frames),32)
    def test_failure_recovery_and_stop_independence(self):
        now=[0.]
        class Missing(MockDisplay):
            failed=True
            def connect(self):
                if self.failed: raise OSError('wrong I2C address')
        backend=Missing()
        runtime=Runtime(simulate=True,display_backend=backend)
        try:
            runtime.display.clock=lambda:now[0]
            runtime.display.step()
            self.assertFalse(runtime.display.snapshot()['connected'])
            self.assertEqual(create_app(runtime).test_client().post('/api/stop',json={}).status_code,200)
            backend.failed=False; now[0]=2.1; runtime.display.step()
            self.assertTrue(runtime.display.snapshot()['connected'])
        finally: runtime.close()
    def test_ssd1306_address_validation(self):
        with self.assertRaises(ValueError): SSD1306(address=0x40)


class NegotiationTests(unittest.TestCase):
    def test_real_worker_mock_usb_and_legacy(self):
        for capability in ('caps_sensor2','unknown_command'):
            with self.subTest(capability=capability):
                class USB:
                    def __init__(self,**options): self.lines=queue.Queue(); self.writes=[]
                    def reset_input_buffer(self): pass
                    def write(self,data):
                        self.writes.append(data)
                        if data==b'HELLO\n': self.lines.put(b'READY Quadruped107 1\n')
                        elif data==b'CAPS 0\n': self.lines.put(f'{"DONE" if capability=="caps_sensor2" else "ERR"} 0 {capability}\n'.encode())
                        elif data==b'TELEM 0 5\n': self.lines.put(b'DONE 0 telemetry\n')
                        elif data==b'PING\n': self.lines.put(b'PONG\n')
                        elif data.startswith(b'POLL '):
                            token=int(data.split()[2]); self.lines.put((tel(token=token)+'\n').encode())
                        return len(data)
                    def readline(self,*args):
                        try: return self.lines.get(timeout=.01)
                        except queue.Empty: return b''
                    def close(self): pass
                usb=USB(); link=SerialLink('mock',sensor_only=True,factory=lambda **kw:usb)
                link.start()
                try:
                    deadline=time.monotonic()+4
                    while time.monotonic()<deadline:
                        snapshot=link.snapshot()
                        if snapshot['connected'] and (capability!='caps_sensor2' or snapshot['telemetry']['record']): break
                        time.sleep(.01)
                    self.assertTrue(snapshot['connected'])
                    self.assertFalse(link.armed)
                    self.assertFalse(any(data.startswith(b'ARM') for data in usb.writes))
                    self.assertEqual(link.capability,'caps_sensor2' if capability=='caps_sensor2' else None)
                    if capability=='caps_sensor2': self.assertTrue(snapshot['telemetry']['acquisitionFreshnessKnown'])
                finally: link.close()

if __name__=='__main__': unittest.main()

"""Exactly two physical-profile inputs, driven by explicit mock/replay records only."""
import sys
from pathlib import Path
import threading
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'software/pi'))
from quadruped.sensors import SensorConfig,SensorManager,TWO_TOUCH_PROFILE,TOUCH_IDS
from quadruped.serial_link import SerialLink
from quadruped.telemetry import TelemetryStream
from quadruped.physical_sensors import PhysicalSensorProvider
from quadruped.navigation import Navigation,motion_inhibition
from quadruped.main import Runtime,create_app
from test_runtime import wait_for

def config(): return SensorConfig(touch_count=2,touch_profile=TWO_TOUCH_PROFILE)
def packet(seq,token,mask=0,flags=19,faults=0,distance=1000,uptime=None):
    return f'TEL 2 {seq} {seq*40 if uptime is None else uptime} {distance} 1 {flags} {mask} 0 0 {token} {faults}'


class TwoTouchTests(unittest.TestCase):
    def setUp(self):
        self.now=10.; self.seq=0
        self.link=SerialLink('mock-only',sensor_only=True);self.link.connected=True
        self.link._receive('DONE 0 caps_sensor2_t2')
        self.link.telemetry=TelemetryStream(clock=lambda:self.now)
        self.manager=SensorManager(config(),source='physical_uno',clock=lambda:self.now)
        self.provider=PhysicalSensorProvider(self.link,self.manager)
        self.feed()

    def feed(self,mask=0,**kwargs):
        self.now+=.05; token=self.link.telemetry.poll()
        self.assertTrue(self.link.telemetry.ingest(packet(self.seq,token,mask,**kwargs)))
        self.seq+=1;self.provider.update();return self.manager.snapshot()

    def press(self,mask): self.feed(mask);return self.feed(mask)
    def step(self,nav,state=None,**kwargs):
        return nav.step(kwargs.pop('mode','interaction'),kwargs.pop('enabled',True),1,
                        state or self.manager.snapshot(),{},self.now,generation=1,**kwargs)

    def test_explicit_config_and_unchanged_virtual_defaults(self):
        self.assertEqual(SensorConfig().touch_count,5)
        self.assertEqual(TOUCH_IDS[:2],('head','back'))
        self.assertEqual(config().touch_ids,('back','front_bottom'))
        for arguments in (dict(touch_count=2),dict(touch_count=3,touch_profile=TWO_TOUCH_PROFILE),
                          dict(touch_count=2,touch_profile='unknown'),dict(touch_count=1)):
            with self.assertRaises(ValueError): SensorConfig(**arguments)
        with self.assertRaises(ValueError): SensorManager(config())

    def test_exact_mapping_and_no_fictitious_coverage(self):
        state=self.manager.snapshot()
        self.assertEqual(set(state['touches']),{'touch_back','touch_front_bottom'})
        self.assertEqual(state['touchMapping'],[dict(bit=0,pin=6,id='touch_back'),dict(bit=1,pin=7,id='touch_front_bottom')])
        self.assertEqual(state['configuredTouchCount'],2)
        self.assertNotIn('touch_head',state['observations'])
        self.assertNotIn('sweep_forward',state['observations'])
        self.assertFalse(self.link.armed)

    def test_back_and_front_are_independent_semantic_events(self):
        state=self.press(1)
        self.assertEqual([(e['id'],e['gestureRequest']) for e in state['events'] if e['pressed']], [('touch_back','REAR_LOWER')])
        self.press(0);state=self.press(2)
        self.assertEqual([e['gestureRequest'] for e in state['events'] if e['pressed'] and e['id']=='touch_front_bottom'],['FRONT_LOWER'])
        self.assertFalse(state['touches']['touch_back']['pressed'])

    def test_bounce_held_release_and_repeated_activation(self):
        self.feed(1);self.feed(0)
        self.assertFalse(any(e['pressed'] for e in self.manager.snapshot()['events']))
        self.press(1)
        for _ in range(3):self.feed(1)
        self.assertEqual(sum(e['pressed'] for e in self.manager.events),1)
        self.press(0);self.press(1)
        self.assertEqual(sum(e['pressed'] for e in self.manager.events),2)

    def test_boot_held_and_reset_do_not_create_activation(self):
        self.manager.reset('reset'); self.provider.last=None
        self.feed(1);self.feed(1)
        self.assertEqual(list(self.manager.events),[])
        self.press(0);self.press(1)
        self.assertTrue(any(e['pressed'] for e in self.manager.events))
        self.link._fail('mock reset');self.provider.update()
        self.assertEqual(self.manager.snapshot()['observations'],{})
        self.link.connected=True;self.link._receive('DONE 0 caps_sensor2_t2');self.seq=0
        self.feed(1);self.feed(1)
        self.assertFalse(any(e['pressed'] for e in self.manager.events))
        self.assertFalse(self.link.armed)

    def test_capability_mismatch_and_absent_bits_fail_closed(self):
        for capability in ('caps_sensor2_t0','caps_sensor2_t3','caps_sensor2_t5'):
            self.link._receive('DONE 0 '+capability);self.provider.update()
            self.assertIsNotNone(self.manager.snapshot()['fault'])
        self.link._receive('DONE 0 caps_sensor2_t2');self.feed(mask=4)
        self.assertEqual(self.manager.snapshot()['observations'],{})
        self.link.capability=None;self.link._receive('DONE 0 caps_sensor2_t1')
        self.assertIsNone(self.link.capability)

    def test_invalid_missing_and_stale_observations_stop(self):
        nav=Navigation();self.step(nav)
        state=self.feed(flags=17) # Touch-valid bit absent.
        self.assertTrue(self.step(nav,state).stop)
        self.assertIsNotNone(state['fault'])
        self.feed();self.now+=.301;self.provider.update()
        self.assertIsNotNone(self.manager.snapshot()['fault'])
        self.assertFalse(self.link.telemetry.ingest('TEL 2 corrupt'))
        self.assertFalse(self.link.armed)

    def test_corrupt_or_duplicate_packet_invalidates_until_new_valid_record(self):
        self.assertFalse(self.link.telemetry.ingest('TEL 2 corrupt'))
        self.provider.update()
        self.assertIsNotNone(self.manager.snapshot()['fault'])
        self.provider.update()
        self.assertEqual(self.manager.snapshot()['observations'],{})
        self.feed()
        self.assertIsNone(self.manager.snapshot()['fault'])
        self.assertFalse(self.link.armed)

    def test_stuck_input_and_release_recovery_do_not_arm(self):
        self.press(1)
        for _ in range(43):self.feed(1)
        self.assertTrue(self.manager.snapshot()['touches']['touch_back']['stuck'])
        self.assertIsNotNone(self.manager.snapshot()['fault'])
        self.press(0)
        self.assertIsNone(self.manager.snapshot()['fault'])
        self.assertFalse(self.link.armed)

    def test_mapping_changes_reset_existing_event_state(self):
        self.press(1)
        self.manager.config=SensorConfig(touch_count=3)
        self.link._receive('DONE 0 caps_sensor2_t3')
        state=self.feed(1)
        self.assertIn('touch_head',state['touches'])
        self.assertNotIn('touch_front_bottom',state['touches'])
        self.assertFalse(any(e['pressed'] for e in state['events']))
        self.manager.config=config();self.link._receive('DONE 0 caps_sensor2_t2')
        state=self.feed(2)
        self.assertEqual(set(state['touches']),{'touch_back','touch_front_bottom'})
        self.assertFalse(any(e['pressed'] for e in state['events']))

    def test_both_semantic_requests_use_labeled_bounded_placeholders(self):
        for mask,request in ((1,'REAR_LOWER'),(2,'FRONT_LOWER')):
            self.press(0);nav=Navigation();self.step(nav)
            decision=self.step(nav,self.press(mask))
            self.assertEqual(decision.motion,'stand')
            self.assertIn(request,decision.reason)
            self.assertEqual(nav.snapshot()['touchGesture']['physicalCalibration'],'PENDING')
            nav.accepted('stand',self.now)
            self.assertIsNone(self.step(nav,self.feed(mask)).motion)
            self.now+=nav.settings.touch_seconds
            self.feed(mask)
            self.assertTrue(self.step(nav).stop) # Freshness/stuck or action budget always closes output.

    def test_simultaneous_contacts_stop_and_never_choose_an_order(self):
        nav=Navigation();self.step(nav)
        decision=self.step(nav,self.press(3))
        self.assertTrue(decision.stop);self.assertIsNone(decision.motion)
        self.assertEqual(nav.snapshot()['touchGesture']['status'],'rejected_simultaneous')

    def test_front_contact_is_protective_outside_explicit_placeholder_mode(self):
        state=self.press(2);nav=Navigation()
        self.assertIsNotNone(motion_inhibition(state,'stand',nav.settings))
        self.assertIsNone(motion_inhibition(state,'stand',nav.settings,virtual_touch_gesture=True))
        self.assertIsNotNone(motion_inhibition(state,'servo',nav.settings,virtual_touch_gesture=True))
        self.assertTrue(self.step(nav,state,mode='manual').stop)

    def test_placeholder_context_never_waives_body_safety_or_range_clearance(self):
        nav=Navigation();state=self.manager.snapshot()
        state['touches']={**state['touches'],'touch_body':dict(pressed=True,valid=True,stuck=False)}
        self.assertEqual(motion_inhibition(state,'stand',nav.settings,virtual_touch_gesture=True),'Body safety contact')
        state=self.feed(distance=400)
        self.assertIsNotNone(motion_inhibition(state,'stand',nav.settings,virtual_touch_gesture=True))

    def test_manual_takeover_disarmed_fault_and_old_events_never_execute(self):
        nav=Navigation();self.step(nav)
        self.assertEqual(self.step(nav,self.press(1)).motion,'stand')
        self.assertIsNone(self.step(nav,mode='manual').motion)
        self.assertEqual(nav.snapshot()['touchGesture']['status'],'cancelled_context_change')
        self.assertIsNone(self.step(nav,enabled=False).motion)
        self.assertIsNone(self.step(nav).motion) # Prior activation consumed on context entry.
        for motion in ('forward','backward','turn_left','turn_right'):
            self.assertIsNotNone(motion_inhibition(self.manager.snapshot(),motion,nav.settings))


class ReplayLink(SerialLink):
    """Explicit serial-record replay; never constructs or opens serial.Serial."""
    def __init__(self):
        super().__init__('REPLAY_ONLY',sensor_only=True)
        self.mask=0;self.flags=19;self.faults=0;self.distance=1000
        self.replay_stop=threading.Event();self.replay_paused=False
        self.connected=True;self._receive('DONE 0 caps_sensor2_t2')
        self.replay_thread=threading.Thread(target=self.generate,daemon=True)
    def start(self):self.replay_thread.start()
    def generate(self):
        seq=0
        while not self.replay_stop.wait(.04):
            if self.replay_paused:continue
            token=self.telemetry.poll()
            self._receive(packet(seq,token,self.mask,self.flags,self.faults,self.distance));seq+=1
    def close(self):
        self.replay_stop.set()
        if self.replay_thread.is_alive():self.replay_thread.join(1)


class TwoTouchRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.link=ReplayLink()
        self.runtime=Runtime(simulate=True,actuator_backend='virtual',sensor_source='physical_uno',sensor_link=self.link,
                             sensor_config=ROOT/'deploy/sensors.two.json')
        self.runtime.start();self.client=create_app(self.runtime).test_client()
        wait_for(lambda:self.runtime.sensors.snapshot()['fault'] is None)
    def tearDown(self):self.runtime.close()
    def enable(self):
        wait_for(lambda:self.runtime.link.snapshot()['connected'])
        response=self.client.post('/api/arm',json={})
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(self.client.post('/api/mode',json={'mode':'interaction'}).status_code,200)
        wait_for(lambda:self.runtime.navigation_state()['state']=='READY')

    def test_d6_back_and_d7_front_requests_reach_controller_without_physical_commands(self):
        for mask,request in ((1,'REAR_LOWER'),(2,'FRONT_LOWER')):
            self.link.mask=0;time.sleep(.1);self.enable();self.link.mask=mask
            wait_for(lambda:(self.runtime.navigation_state().get('touchGesture') or {}).get('status')=='virtual_placeholder_dispatched')
            state=self.runtime.state()
            self.assertEqual(state['autonomy']['touchGesture']['request'],request)
            self.assertEqual(state['motion']['lastRequest']['motion'],'stand')
            self.assertFalse(state['physicalActuationAllowed'])
            self.assertFalse(self.link.armed)
            self.assertEqual(self.link.outgoing.qsize(),0)
            self.assertEqual(self.client.post('/api/stop',json={}).status_code,200)
            self.assertFalse(self.runtime.motion.snapshot()['enabled'])

    def test_explicit_stop_held_release_and_reconnect_never_reenable(self):
        self.enable();self.link.mask=1
        wait_for(lambda:(self.runtime.navigation_state().get('touchGesture') or {}).get('motion')=='stand')
        self.client.post('/api/stop',json={});self.link.mask=0;time.sleep(.15)
        self.link._fail('Replay USB reset');time.sleep(.08)
        self.link.connected=True;self.link._receive('DONE 0 caps_sensor2_t2');time.sleep(.15)
        self.assertFalse(self.runtime.motion.snapshot()['enabled'])
        self.assertFalse(self.link.armed)

    def test_simultaneous_contact_cancels_interaction(self):
        self.enable();self.link.mask=3
        wait_for(lambda:not self.runtime.motion.snapshot()['enabled'])
        self.link.mask=0;time.sleep(.15)
        self.assertFalse(self.runtime.motion.snapshot()['enabled'])

    def test_bad_packet_cancels_current_placeholder_and_cannot_rearm(self):
        self.enable();self.link.mask=1
        wait_for(lambda:(self.runtime.navigation_state().get('touchGesture') or {}).get('motion')=='stand')
        self.link.replay_paused=True
        self.assertFalse(self.link.telemetry.ingest('TEL 2 broken'))
        wait_for(lambda:not self.runtime.motion.snapshot()['enabled'])
        self.link.replay_paused=False;self.link.mask=0;time.sleep(.15)
        self.assertFalse(self.runtime.motion.snapshot()['enabled'])

    def test_front_bottom_contact_stops_manual_virtual_output(self):
        wait_for(lambda:self.runtime.link.snapshot()['connected'])
        self.assertEqual(self.client.post('/api/arm',json={}).status_code,200)
        self.assertEqual(self.client.post('/api/mode',json={'mode':'stand'}).status_code,200)
        self.link.mask=2
        wait_for(lambda:not self.runtime.motion.snapshot()['enabled'])
        self.link.mask=0;time.sleep(.15)
        self.assertFalse(self.runtime.motion.snapshot()['enabled'])

    def test_no_echo_and_timeout_cancel_without_recovery_arm(self):
        self.enable();self.link.mask=1
        wait_for(lambda:(self.runtime.navigation_state().get('touchGesture') or {}).get('motion')=='stand')
        self.link.distance=-1;self.link.flags=18;self.link.faults=2
        wait_for(lambda:not self.runtime.motion.snapshot()['enabled'])
        self.link.flags=19;self.link.distance=1000;self.link.faults=0;self.link.mask=0;time.sleep(.15)
        self.assertFalse(self.runtime.motion.snapshot()['enabled'])
        self.enable();self.link.replay_paused=True
        wait_for(lambda:not self.runtime.motion.snapshot()['enabled'])
        self.link.replay_paused=False;time.sleep(.1)
        self.assertFalse(self.runtime.motion.snapshot()['enabled'])

    def test_manual_takeover_and_dashboard_match_actual_profile(self):
        self.enable();self.link.mask=1
        wait_for(lambda:(self.runtime.navigation_state().get('touchGesture') or {}).get('motion')=='stand')
        response=self.client.post('/api/mode',json={'mode':'manual'})
        self.assertEqual(response.status_code,200)
        self.assertFalse(self.runtime.motion.snapshot()['enabled'])
        state=self.client.get('/api/state').json
        self.assertEqual(state['sensors']['configuredTouchCount'],2)
        self.assertEqual(set(state['sensors']['touches']),{'touch_back','touch_front_bottom'})
        self.assertFalse(state['oled']['enabled'])
        self.assertEqual(self.client.post('/api/interaction',json={'name':'greeting'}).status_code,409)
        for mode in ('explore','opencv'):
            self.assertEqual(self.client.post('/api/mode',json={'mode':mode}).status_code,409)


if __name__=='__main__':unittest.main()

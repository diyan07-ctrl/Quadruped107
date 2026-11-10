"""Deterministic acquisition-age and concurrent safety-evaluation regressions."""
import sys
import importlib.util
import threading
import socket
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'software/pi'))
from quadruped.sensors import SensorManager,fixture_batch
from quadruped.navigation import motion_inhibition,NavigationSettings
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from hil_lease import HeldIntentLease
from quadruped.controller import MotionController
from test_safety import GateLink
from quadruped.bridge import TraceReceiver,TraceClient,encode,decode

class SnapshotGate:
    """Pause one reader immediately before it acquires the actual state lock."""
    def __init__(self,lock):
        self.lock=lock
        self.arrived=threading.Event()
        self.release=threading.Event()
    def __enter__(self):
        if threading.current_thread().name=='delayed-safety-reader':
            self.arrived.set()
            if not self.release.wait(2): raise AssertionError('Reader gate timed out')
        return self.lock.__enter__()
    def __exit__(self,*args): return self.lock.__exit__(*args)

class SensorAtomicTimeTests(unittest.TestCase):
    def interleave(self,update):
        now=[1.0]
        manager=SensorManager(clock=lambda:now[0])
        manager.ingest(fixture_batch(1,distance=2.77))
        gate=SnapshotGate(manager.lock); manager.lock=gate
        result=[]
        def read(): result.append(manager.snapshot())
        worker=threading.Thread(name='delayed-safety-reader',target=read)
        worker.start()
        try:
            self.assertTrue(gate.arrived.wait(2))
            update(manager,now)
        finally:
            gate.release.set();worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(len(result),1)
        return result[0]

    def test_new_fresh_sample_cannot_appear_from_future_to_safety_reader(self):
        def update(manager,now):
            now[0]=1.02
            self.assertTrue(manager.ingest(fixture_batch(2,distance=2.77)))
        state=self.interleave(update)
        self.assertIsNone(state['fault'])
        self.assertIsNone(motion_inhibition(state,'forward',NavigationSettings()))
        self.assertTrue(state['observations']['urm37']['fresh'])

    def test_reader_wait_does_not_hide_genuine_measurement_expiry(self):
        def delay(manager,now): now[0]=1.31
        state=self.interleave(delay)
        self.assertIsNotNone(state['fault'])
        self.assertFalse(state['observations']['urm37']['fresh'])
        self.assertIsNotNone(motion_inhibition(state,'forward',NavigationSettings()))

    def test_repeated_identical_new_measurements_remain_healthy(self):
        now=[0.0];manager=SensorManager(clock=lambda:now[0])
        for seq in range(10001):
            now[0]=seq*.05
            self.assertTrue(manager.ingest(fixture_batch(seq,distance=2.77),transport_age=.01))
            self.assertIsNone(manager.snapshot()['fault'])

    def test_fresh_packet_cannot_refresh_stale_individual_range(self):
        manager=SensorManager(clock=lambda:2.0)
        batch=fixture_batch(1,distance=2.77)
        batch['observations'][0]['age']=.31
        self.assertTrue(manager.ingest(batch))
        state=manager.snapshot()
        self.assertEqual(state['receivedAge'],0)
        self.assertIsNotNone(state['fault'])
        self.assertFalse(state['observations']['urm37']['valid'])

    def test_packet_loss_and_reordering_do_not_renew_measurements(self):
        now=[0.0];manager=SensorManager(clock=lambda:now[0])
        manager.ingest(fixture_batch(2))
        now[0]=.2
        self.assertFalse(manager.ingest(fixture_batch(1)))
        self.assertFalse(manager.ingest(fixture_batch(2)))
        now[0]=.31
        self.assertIsNotNone(manager.snapshot()['fault'])
        self.assertEqual(manager.snapshot()['seq'],2)

    def test_restart_missing_and_invalid_values_fail_closed(self):
        manager=SensorManager(clock=lambda:1.0)
        manager.ingest(fixture_batch(10),session='old')
        manager.reset('new')
        self.assertIsNotNone(manager.snapshot()['fault'])
        for value in (None,float('nan'),-1,True):
            self.assertTrue(manager.ingest(fixture_batch(manager.seq+1,distance=value),session='new'))
            self.assertIsNotNone(manager.snapshot()['fault'])
        batch=fixture_batch(manager.seq+1)
        batch['observations']=batch['observations'][1:]
        manager.ingest(batch,session='new')
        self.assertIsNotNone(manager.snapshot()['fault'])
        self.assertTrue(manager.ingest(fixture_batch(manager.seq+1),session='new'))
        self.assertIsNone(manager.snapshot()['fault'])

class IntentFreshnessTests(unittest.TestCase):
    def test_generic_heartbeat_does_not_extend_a_held_direction(self):
        now=[0.0]
        with patch('quadruped.controller.time.monotonic',side_effect=lambda:now[0]):
            controller=MotionController(GateLink())
            controller.arm();controller.set_mode('forward')
            now[0]=.51
            controller.heartbeat(None)
            original=controller.stop
            def stop(*args,**kwargs):
                original(*args,**kwargs);controller.stop_event.set()
            controller.stop=stop
            controller._run()
            self.assertFalse(controller.snapshot()['enabled'])
            self.assertEqual(controller.snapshot()['fault'],'Stale motion intent')

    def test_matching_renewals_survive_slow_independent_telemetry(self):
        now=[0.0]
        telemetry_blocked=threading.Event();release=threading.Event()
        def telemetry(): telemetry_blocked.set();release.wait(2)
        reader=threading.Thread(target=telemetry);reader.start()
        self.assertTrue(telemetry_blocked.wait(2))
        try:
            with patch('quadruped.controller.time.monotonic',side_effect=lambda:now[0]):
                controller=MotionController(GateLink())
                controller.arm();controller.set_mode('forward')
                lease=HeldIntentLease(controller.heartbeat,'forward',1,clock=lambda:now[0])
                for step in range(7):
                    now[0]=step*.1
                    self.assertTrue(lease.tick())
                self.assertTrue(reader.is_alive())
                self.assertEqual(controller.snapshot()['intentAgeS'],0)
                self.assertTrue(controller.snapshot()['enabled'])
                now[0]=1
                self.assertFalse(lease.tick())
                self.assertEqual(len(lease.records),7)
        finally:
            release.set();reader.join(2)

    def test_failed_renewal_is_latched_and_never_retried(self):
        calls=[]
        def fail(motion): calls.append(motion);raise TimeoutError('request timed out')
        lease=HeldIntentLease(fail,'forward',1,clock=lambda:0)
        self.assertFalse(lease.tick());self.assertFalse(lease.tick())
        self.assertEqual(calls,['forward'])
        self.assertIn('TimeoutError',lease.error)

    def test_explicit_cancellation_prevents_further_renewals(self):
        calls=[]
        lease=HeldIntentLease(calls.append,'forward',1,clock=lambda:0)
        lease.close();self.assertFalse(lease.tick());self.assertEqual(calls,[])

@unittest.skipUnless(importlib.util.find_spec('pybullet'),'PyBullet not installed')
class AcquisitionCadenceTests(unittest.TestCase):
    def test_newly_available_range_is_not_hidden_by_batch_cache(self):
        from simulation.twin import World
        from simulation.environment import Scene
        now=[0.0];world=World()
        try:
            scene=Scene(world,'empty',clock=lambda:now[0],latency=.02)
            frame=dict(virtual=True,armed=False,activeMask=0,targets=[300]*8)
            scene.advance(frame)
            now[0]=.099
            old=scene.telemetry()
            now[0]=.1;scene.advance(frame)
            now[0]=.121;scene.advance(frame)
            new=scene.telemetry()
            self.assertGreater(new['seq'],old['seq'])
            for record in new['observations']:
                if record['kind']=='range':
                    self.assertEqual(record['sampleSeq'],2)
                    self.assertAlmostEqual(record['age'],.021)
        finally: world.close()

    def test_sensor_acquisition_continues_between_udp_sensor_requests(self):
        from simulation.twin import World
        from simulation.environment import Scene
        now=[0.0];world=World()
        try:
            scene=Scene(world,'empty',clock=lambda:now[0],latency=.02)
            scene.telemetry()  # One request at startup, then no UDP request for .2 s.
            frame=dict(virtual=True,armed=False,activeMask=0,targets=[300]*8)
            for step in range(1,49):
                now[0]=step/240
                scene.advance(frame);world.apply(frame);world.step()
            records={r['id']:r for r in scene.telemetry()['observations']}
            for identity in ('urm37','hcsr04'):
                self.assertTrue(records[identity]['valid'])
                self.assertLess(records[identity]['age'],.13)
        finally: world.close()

class LossRecoveryTests(unittest.TestCase):
    def test_stop_during_challenge_precedes_disarmed_handshake(self):
        now=[1.0];receiver=TraceReceiver(clock=lambda:now[0]);pending=[];sent=[]
        state=dict(armed=True,activeMask=255,targets=[300]*8,stopEpoch=0)
        client=TraceClient('127.0.0.1',7002,lambda:dict(state))
        class Wire:
            def settimeout(self,value): pass
            def close(self): pass
            def sendto(self,raw,address):
                msg=decode(raw);sent.append(msg)
                reply=receiver.handle(raw,('127.0.0.1',1234))
                if reply: pending.append(reply)
            def recvfrom(self,size):
                if pending:
                    reply=pending.pop(0)
                    if decode(reply)['type']=='challenge': state.update(armed=False,activeMask=0,stopEpoch=1)
                    if decode(reply)['type']=='ack': client.stop_event.set()
                    return reply,('127.0.0.1',7002)
                now[0]+=.02
                if now[0]>2: client.stop_event.set()
                raise socket.timeout()
        with patch('quadruped.bridge.socket.socket',return_value=Wire()),patch('quadruped.bridge.time.monotonic',side_effect=lambda:now[0]):
            client._run()
        stop=next(i for i,m in enumerate(sent) if m['type']=='stop')
        disarmed=next(i for i,m in enumerate(sent) if m['type']=='trace' and not m['armed'])
        self.assertLess(stop,disarmed)

    def test_repeated_hello_preserves_inflight_nonce_and_original_expiry(self):
        now=[0.0];receiver=TraceReceiver(clock=lambda:now[0]);peer=('127.0.0.1',1234)
        hello=encode(dict(v=1,type='hello',client='ab'*16))
        first=decode(receiver.handle(hello,peer))
        now[0]=.05
        second=decode(receiver.handle(hello,peer))
        self.assertEqual(first['nonce'],second['nonce'])
        now[0]=.151
        trace=dict(v=1,type='trace',client='ab'*16,server=first['server'],nonce=first['nonce'],seq=1,
                   virtual=True,armed=False,activeMask=0,targets=[300]*8)
        self.assertIsNone(receiver.handle(encode(trace),peer))
        self.assertFalse(receiver.snapshot()['armed'])

    def test_one_lost_datagram_does_not_force_full_challenge_timeout(self):
        for lost_type in ('challenge','trace','ack'):
            with self.subTest(lost_type=lost_type):
                now=[0.0];receiver=TraceReceiver(clock=lambda:now[0]);pending=[];hello_times=[];dropped=[False]
                client=TraceClient('127.0.0.1',7002,lambda:dict(armed=False,activeMask=0,targets=[300]*8))
                class Wire:
                    def settimeout(self,value): pass
                    def close(self): pass
                    def sendto(self,raw,address):
                        msg=decode(raw)
                        if msg['type']=='hello': hello_times.append(now[0])
                        if msg['type']==lost_type and not dropped[0]: dropped[0]=True;return
                        reply=receiver.handle(raw,('127.0.0.1',1234))
                        if reply:
                            if decode(reply)['type']==lost_type and not dropped[0]: dropped[0]=True
                            else: pending.append(reply)
                    def recvfrom(self,size):
                        if pending:
                            reply=pending.pop(0)
                            if decode(reply)['type']=='ack': client.stop_event.set()
                            return reply,('127.0.0.1',7002)
                        now[0]+=.02
                        if now[0]>.5: client.stop_event.set()
                        raise socket.timeout()
                with patch('quadruped.bridge.socket.socket',return_value=Wire()),patch('quadruped.bridge.time.monotonic',side_effect=lambda:now[0]):
                    client._run()
                self.assertTrue(dropped[0]);self.assertTrue(client.ready)
                self.assertLessEqual(hello_times[1]-hello_times[0],.081)

if __name__=='__main__': unittest.main()

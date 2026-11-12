"""Compile and execute deterministic native Arduino mocks; never opens hardware."""
import argparse
from pathlib import Path
import subprocess
import os
import sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zig',type=Path)
    args=parser.parse_args()
    out=ROOT/'build/phase5/native'
    out.mkdir(parents=True,exist_ok=True)
    compiler=[str(args.zig.resolve()),'c++'] if args.zig else ['g++']
    env=dict(os.environ,ZIG_LOCAL_CACHE_DIR=str(out/'cache'),ZIG_GLOBAL_CACHE_DIR=str(out/'global'))
    variants=[('policy','firmware_policy.cpp',[]),
              ('sensor-default','firmware_sensor.cpp',[]),
              ('sensor-configured','firmware_sensor.cpp',['-DURM37_PROFILE=1','-DTOUCH_ENABLED_MASK=31']),
              ('sensor-active-low','firmware_sensor.cpp',['-DURM37_PROFILE=1','-DTOUCH_ENABLED_MASK=7','-DTOUCH_ACTIVE_LOW_MASK=7']),
              ('sensor-four-high','firmware_sensor.cpp',['-DURM37_PROFILE=1','-DTOUCH_ENABLED_MASK=15']),
              ('sensor-four-low','firmware_sensor.cpp',['-DURM37_PROFILE=1','-DTOUCH_ENABLED_MASK=15','-DTOUCH_ACTIVE_LOW_MASK=15']),
              ('sensor-three-high','firmware_sensor.cpp',['-DURM37_PROFILE=1','-DTOUCH_ENABLED_MASK=7']),
              ('sensor-five-low','firmware_sensor.cpp',['-DURM37_PROFILE=1','-DTOUCH_ENABLED_MASK=31','-DTOUCH_ACTIVE_LOW_MASK=31']),
              ('sensor-two-high','firmware_two_touch.cpp',['-DURM37_PROFILE=1','-DTOUCH_ENABLED_MASK=3']),
              ('sensor-two-low','firmware_two_touch.cpp',['-DURM37_PROFILE=1','-DTOUCH_ENABLED_MASK=3','-DTOUCH_ACTIVE_LOW_MASK=3']),
              ('sensor-two-mixed-a','firmware_two_touch.cpp',['-DURM37_PROFILE=1','-DTOUCH_ENABLED_MASK=3','-DTOUCH_ACTIVE_LOW_MASK=1']),
              ('sensor-two-mixed-b','firmware_two_touch.cpp',['-DURM37_PROFILE=1','-DTOUCH_ENABLED_MASK=3','-DTOUCH_ACTIVE_LOW_MASK=2']),
              ('calibration-disabled','firmware_calibration.cpp',[]),
              ('calibration-reviewed-unknown','firmware_calibration.cpp',['-DDIRECT_COMMISSIONING_REVIEWED=1']),
              ('production-present','firmware_production.cpp',[]),
              ('production-absent','firmware_production.cpp',['-DMOCK_PCA_PRESENT=0'])]
    for name,source,defines in variants:
        binary=out/(name+('.exe' if os.name=='nt' else ''))
        command=compiler+['-std=c++11','-Wall','-Wextra','-Werror','-Wno-unused-function',
            '-Wno-unused-variable','-include',str(ROOT/'tests/firmware_fake/Arduino.h'),
            '-I'+str(ROOT/'tests/firmware_fake'),
            '-I'+str(ROOT/'firmware/uno/libraries/QuadrupedSafety/src'),*defines,
            str(ROOT/'tests'/source),'-o',str(binary)]
        subprocess.run(command,cwd=ROOT,env=env,check=True)
        result=subprocess.run([str(binary)],cwd=ROOT,capture_output=True,text=True)
        print(result.stdout,end='')
        if result.stderr: print(result.stderr,end='',file=sys.stderr)
        result.check_returncode()
        if name.startswith('sensor-two-'):
            sys.path.insert(0,str(ROOT/'software/pi'))
            from quadruped.serial_link import SerialLink
            from quadruped.telemetry import TelemetryStream,parse_tel2
            from quadruped.sensors import SensorManager,SensorConfig
            from quadruped.physical_sensors import PhysicalSensorProvider
            now=[0.]
            link=SerialLink('mock',sensor_only=True);link.connected=True
            link._receive('DONE 0 caps_sensor2_t2')
            link.telemetry=TelemetryStream(clock=lambda:now[0])
            manager=SensorManager(SensorConfig(touch_count=2,touch_profile='back_front_bottom_v1'),source='physical_uno',clock=lambda:now[0])
            provider=PhysicalSensorProvider(link,manager)
            for row in result.stdout.splitlines():
                if not row.startswith('WIRE_TWO='): continue
                line=row.split('=',1)[1];record=parse_tel2(line)
                now[0]=record.uptime_ms/1000
                assert link.telemetry.poll()==record.token
                assert link.telemetry.ingest(line),line
                provider.update()
                state=manager.snapshot()
                assert set(state['touches'])=={'touch_back','touch_front_bottom'}
                if record.token==3: assert any(e['pressed'] and e['id']=='touch_back' and e['gestureRequest']=='REAR_LOWER' for e in state['events'])
                if record.token==7: assert any(e['pressed'] and e['id']=='touch_front_bottom' and e['gestureRequest']=='FRONT_LOWER' for e in state['events'])
                if record.token==12: assert state['fault'] and not link.armed
            assert not link.armed
            print(name+' real sketch -> TEL2 -> exact two semantic Pi inputs; stuck invalidation PASS')
        elif name.startswith('sensor-'):
            # Consume the actual C++ sketch's wire record in the Pi provider.
            sys.path.insert(0,str(ROOT/'software/pi'))
            from quadruped.serial_link import SerialLink
            from quadruped.telemetry import TelemetryStream
            from quadruped.sensors import SensorManager
            from quadruped.physical_sensors import PhysicalSensorProvider
            line=next(row.split('=',1)[1] for row in result.stdout.splitlines() if row.startswith('WIRE_RECORD='))
            link=SerialLink('mock',sensor_only=True)
            link.connected=True
            link.capability='caps_sensor2'
            link.sensor_touch_count=4 if name.startswith('sensor-four-') else 3 if name in ('sensor-active-low','sensor-three-high') else 5 if name in ('sensor-configured','sensor-five-low') else 0
            link.telemetry=TelemetryStream(clock=lambda:1.)
            for _ in range(42): link.telemetry.poll()
            assert link.telemetry.ingest(line),line
            manager=SensorManager(source='physical_uno',clock=lambda:1.)
            PhysicalSensorProvider(link,manager).update()
            state=manager.snapshot()
            assert state['observations']['urm37']['valid']==(name!='sensor-default')
            if name!='sensor-default': assert state['observations']['urm37']['measurement']==.4
            assert state['safetyInhibits'] and not state['virtual'] and not link.armed
            if name=='sensor-default': assert state['fault']
            assert len(state['touches'])==5  # Missing configured inputs stay invalid.
            if name=='sensor-configured':
                now=[1.]
                link.telemetry.clock=manager.clock=lambda:now[0]
                provider=PhysicalSensorProvider(link,manager)
                provider.epoch=(link.epoch,manager.config.touch_profile,manager.config.touch_count,link.sensor_touch_count)
                provider.last=(provider.epoch,link.telemetry.record.seq)
                provider.batch_seq=manager.seq
                for row in result.stdout.splitlines():
                    if not row.startswith('WIRE_TOUCH_RECORD='): continue
                    now[0]+=.2
                    link.telemetry.poll()
                    assert link.telemetry.ingest(row.split('=',1)[1])
                    provider.update()
                assert any(e['pressed'] and e['id']=='touch_head' for e in manager.snapshot()['events'])
                assert not link.armed
                print('mock touch -> real C++ telemetry -> Pi interaction event; actuation inhibited PASS')
            print(name+' C++ wire -> Pi SensorManager PASS',flush=True)
            # Replay the same sketch after missing echoes, not a Python-generated packet.
            link.telemetry.reset()
            for _ in range(46): link.telemetry.poll()
            invalid=next(row.split('=',1)[1] for row in result.stdout.splitlines() if row.startswith('WIRE_INVALID_RECORD='))
            assert link.telemetry.ingest(invalid),invalid
            PhysicalSensorProvider(link,manager).update()
            assert not manager.snapshot()['observations']['urm37']['valid']
            assert not link.armed
            try: link.submit('ARM')
            except RuntimeError: pass
            else: raise AssertionError('Sensor link accepted ARM')
            stop=link.submit('STOP')
            assert link.urgent is not None and not link.armed and stop.verb=='STOP'
            print(name+' C++ no-echo -> Pi invalidation / ARM rejection / urgent STOP PASS',flush=True)
        print(name+' PASS',flush=True)
    print(f'{len(variants)} firmware mock executables PASS')

if __name__=='__main__': main()

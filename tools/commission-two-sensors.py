"""Finite real-Uno recorder. NO UPLOAD, GPIO, I2C or actuator backend.

Do not execute until electrical review and a separately authorized sensor-only
upload have passed. Explicit flags record operator attestations, not measurements.
Only one owner opens USB. ARM rejection probes require strict t2 negotiation first.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import serial

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'software/pi'))
from quadruped.serial_link import SerialLink
from quadruped.sensors import SensorConfig,SensorManager
from quadruped.physical_sensors import PhysicalSensorProvider
from quadruped.telemetry import parse_tel1


def collect(args,*,serial_factory=serial.Serial,clock=time.monotonic):
    if not args.electrical_verified or not args.upload_verified:
        raise ValueError('Electrical review and separately authorized upload must be verified before serial access')
    if not args.port or args.port=='auto':raise ValueError('Use an explicit verified serial device')
    if not 1<=args.seconds<=120:raise ValueError('Recording duration must be 1..120 seconds')
    digest=hashlib.sha256(args.binary.read_bytes()).hexdigest()
    if digest!=args.firmware_sha256:raise ValueError('Reviewed firmware binary hash mismatch')
    args.output.mkdir(parents=True,exist_ok=True)
    result=dict(status='FAIL',label=args.label,startedUtc=datetime.now(timezone.utc).isoformat(),
        port=args.port,binarySha256=digest,operatorElectricalAttestation=True,operatorUploadAttestation=True,
        evidenceClass='PHYSICAL SERIAL' if serial_factory is serial.Serial else 'TEST DOUBLE',
        physicalActuatorAllowed=False,uploadedByThisTool=False,referenceM=args.reference_m,samples=0,rejectedRecords=0)
    git=['git','-c','safe.directory='+str(ROOT)]
    result['source']=subprocess.check_output(git+['rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    result['dirtyPathsAtStart']=subprocess.check_output(git+['status','--porcelain'],cwd=ROOT,text=True).splitlines()
    connection=None
    with (args.output/'serial.jsonl').open('w',encoding='utf-8') as log:
        def record(**values):
            log.write(json.dumps(dict(atMonotonic=clock(),**values))+'\n');log.flush()
        def send(text):
            wire=(text+'\n').encode('ascii')
            if connection.write(wire)!=len(wire):raise RuntimeError('Partial USB write')
            record(direction='TX',line=text)
        def read():
            wire=connection.readline(128)
            if not wire:return ''
            if not wire.endswith(b'\n') or len(wire)>64:raise RuntimeError('Truncated/oversized serial record')
            line=wire.decode('ascii',errors='strict').strip();record(direction='RX',line=line);return line
        def expect(wanted,seconds=2):
            deadline=clock()+seconds
            while clock()<deadline:
                line=read()
                if line==wanted:return
                if line.startswith(('ERR ','FAULT ')):raise RuntimeError('Unexpected firmware response: '+line)
            raise TimeoutError('Missing expected firmware response: '+wanted)
        try:
            options=dict(port=args.port,baudrate=115200,timeout=.05,write_timeout=.25)
            if sys.platform!='win32':options['exclusive']=True
            connection=serial_factory(**options)
            time.sleep(2) # Uno USB reset/boot; no commands or sensor assumptions during boot.
            connection.reset_input_buffer()
            send('HELLO');expect('READY Quadruped107 1',3)
            send('CAPS 1');expect('DONE 1 caps_sensor2_t2')
            result['capability']='caps_sensor2_t2'
            # These are intentional rejection tests ONLY after exact sensor-only identity.
            for command,answer in [('ARM 3','ERR 3 sensor_only'),('MOVE 4 stand','ERR 4 sensor_only'),
                                   ('SERVO 5 0 300','ERR 5 sensor_only'),('STOP 6','DONE 6 stopped')]:
                send(command);expect(answer)
            result['actuatorRejections']='PASS'
            send('TELEM 7 5 1');expect('DONE 7 telemetry');send('PING')
            deadline=clock()+1
            while clock()<deadline:
                line=read()
                if line.startswith('TEL 1 '):
                    parse_tel1(line);result['tel1Diagnostics']='PASS';break
            else:raise TimeoutError('Missing TEL1 diagnostic record')
            send('TELEM 2 5 2');expect('DONE 2 telemetry')
            monitor=SerialLink('PASSIVE_MONITOR_NO_THREAD',sensor_only=True)
            monitor.connected=True;monitor._receive('DONE 0 caps_sensor2_t2')
            monitor.telemetry.clock=clock
            manager=SensorManager(SensorConfig.load(ROOT/'deploy/sensors.two.json'),source='physical_uno',clock=clock)
            provider=PhysicalSensorProvider(monitor,manager)
            started=clock();last_ping=last_poll=started-1
            while clock()-started<args.seconds:
                now=clock()
                if now-last_ping>=.3:send('PING');last_ping=now
                if now-last_poll>=.2:
                    send('POLL 0 '+str(monitor.telemetry.poll()));last_poll=now
                line=read()
                if line.startswith('TEL '):
                    accepted=monitor.telemetry.ingest(line);provider.update()
                    state=manager.snapshot();record(accepted=accepted,sensors=state)
                    result['samples']+=int(accepted)
                    result['rejectedRecords']+=int(not accepted)
                    if args.reference_m is not None and state['observations'].get('urm37',{}).get('valid'):
                        record(operatorReferenceM=args.reference_m,errorM=state['observations']['urm37']['measurement']-args.reference_m)
                elif line.startswith(('FAULT ','READY ')):
                    raise RuntimeError('Firmware reset/fault during collection: '+line)
            result['status']='PASS' if result['samples'] and not result['rejectedRecords'] else 'FAIL'
            result['scope']='Transport/rejections/record capture only; validity, distances and contacts require operator review'
        except Exception as error:
            result['error']=type(error).__name__+': '+str(error)
        finally:
            if connection:
                try:send('STOP 99')
                except Exception as error:result.update(status='FAIL',stopWriteError=str(error))
                try:connection.close()
                except Exception as error:result.update(status='FAIL',closeError=str(error))
            result['endedUtc']=datetime.now(timezone.utc).isoformat()
            (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',required=True)
    parser.add_argument('--binary',required=True,type=Path)
    parser.add_argument('--firmware-sha256',required=True)
    parser.add_argument('--electrical-verified',action='store_true',required=True)
    parser.add_argument('--upload-verified',action='store_true',required=True)
    parser.add_argument('--seconds',type=float,default=10)
    parser.add_argument('--label',required=True)
    parser.add_argument('--reference-m',type=float)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.reference_m is not None and not .02<=args.reference_m<=4:parser.error('Ruler reference must be .02..4 metres')
    result=collect(args);print(json.dumps(result,indent=2))
    return int(result['status']!='PASS')


if __name__=='__main__':raise SystemExit(main())

"""Execute a reviewed shell script over SSH and retain timestamped evidence.

Uses the existing local SSH client/key agent; never reads private keys.
The supplied script owns its safety contract. Authentication is noninteractive.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='diyan07@192.168.1.42')
    parser.add_argument('--script', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=90)
    args=parser.parse_args()
    command=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8',args.host,'bash -s']
    args.log.parent.mkdir(parents=True,exist_ok=True)
    started=datetime.now(timezone.utc).isoformat()
    clock=time.monotonic()
    with args.log.open('w',encoding='utf-8') as output:
        output.write(json.dumps(dict(started_utc=started,command=command,script=str(args.script)))+'\n')
        output.write(args.script.read_text(encoding='utf-8')+'\n--- OBSERVED OUTPUT ---\n')
        output.flush()
        result=subprocess.run(command,input=args.script.read_bytes().replace(b'\r\n',b'\n'),
                              stdout=output,stderr=subprocess.STDOUT,timeout=args.timeout)
    print(json.dumps(dict(log=str(args.log),exit_code=result.returncode,duration_s=time.monotonic()-clock)))
    raise SystemExit(result.returncode)

if __name__=='__main__': main()

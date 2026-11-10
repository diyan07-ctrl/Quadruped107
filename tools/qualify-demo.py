"""Read-only environment/application diagnostics. No camera capture, ARM, GPIO or serial."""
import argparse
import importlib
import ipaddress
import json
from pathlib import Path
import platform
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import build_opener,ProxyHandler

def collect(url=None):
    result=dict(atUtc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
                host=platform.node(),architecture=platform.machine(),python=platform.python_version(),
                hardwareAcceptance=False,cameraImagesRetained=False,modules={},cameraDevices=[])
    for name in ("cv2","numpy","flask","serial"):
        try:
            module=importlib.import_module(name)
            result["modules"][name]=getattr(module,"__version__","imported")
        except ImportError: result["modules"][name]=None
    result["cameraDevices"]=[str(path) for path in Path("/dev").glob("video*")] if sys.platform=="linux" else []
    check=subprocess.run([sys.executable,"-m","pip","check"],capture_output=True,text=True,timeout=20)
    result["pipCheck"]=dict(returnCode=check.returncode,output=(check.stdout+check.stderr)[:8000])
    if url:
        parsed=urlsplit(url)
        if parsed.scheme!="http" or parsed.username or parsed.password or not parsed.hostname:
            raise ValueError("Use trusted local HTTP without URL credentials")
        address=ipaddress.ip_address(socket.gethostbyname(parsed.hostname))
        if not address.is_private and not address.is_loopback: raise ValueError("Private/loopback address required")
        opener=build_opener(ProxyHandler({}))
        with opener.open(url.rstrip("/")+"/api/state",timeout=3) as response:
            raw=response.read(131073)
            if len(raw)>131072: raise ValueError("State response too large")
            state=json.loads(raw)
        result["application"]={key:state.get(key) for key in ("simulation","physicalActuationAllowed","camera","system","visionConfig","motion","bridge")}
        if state.get("physicalActuationAllowed") is not False: raise ValueError("Application does not report physical inhibition")
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url",help="Running local/trusted application base URL; GET only")
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result=collect(args.url)
    text=json.dumps(result,indent=2,allow_nan=False)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text,encoding="utf-8")
    print(text,end="")
    if result["pipCheck"]["returnCode"] or any(value is None for value in result["modules"].values()):
        raise SystemExit(1)
if __name__=="__main__": main()

"""Bounded private-LAN reachability discovery; no authentication/configuration writes."""
from concurrent.futures import ThreadPoolExecutor
import ipaddress,json,subprocess,socket,time
from pathlib import Path

out=Path('build/phase6/network');out.mkdir(parents=True,exist_ok=True)
current=subprocess.check_output(['ipconfig'],text=True)
if '192.168.1.43' not in current:raise SystemExit('Expected local subnet changed; no scan attempted')
(out/'ipconfig.txt').write_text(current)
network=ipaddress.ip_network('192.168.1.0/24')
known_mac='dc-a6-32-52-27-d8'
def ping(address):
    result=subprocess.run(['ping','-n','1','-w','300',str(address)],capture_output=True,text=True,
                          creationflags=subprocess.CREATE_NO_WINDOW,timeout=3)
    return dict(address=str(address),icmpReply='TTL=' in result.stdout)
started=time.monotonic()
with ThreadPoolExecutor(max_workers=32) as pool:
    rows=list(pool.map(ping,[ip for ip in network.hosts() if str(ip)!='192.168.1.43']))
neighbors=subprocess.check_output(['arp','-a'],text=True)
(out/'neighbors.txt').write_text(neighbors)
matching=[line.strip() for line in neighbors.splitlines() if known_mac in line.lower()]
result=dict(scope=str(network),durationS=time.monotonic()-started,knownPiMac=known_mac,
    matchingNeighbors=matching,icmpReplies=[r['address'] for r in rows if r['icmpReply']],
    configurationChanged=False,authenticatedToDevices=False)
(out/'discovery.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2));print(neighbors)

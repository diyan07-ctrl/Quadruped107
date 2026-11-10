"""Operator-driven client for the actual Pi dashboard, through an SSH tunnel.

Cookies stay in ignored build/. No credentials are retained in evidence.
"""
import http.cookiejar
import json
from pathlib import Path
import time
import urllib.request
import urllib.error

cookie=http.cookiejar.LWPCookieJar('build/phase4/control-cookies.txt')
if Path(cookie.filename).exists(): cookie.load(ignore_discard=True)
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(cookie))
def api(path,data=None):
    req=urllib.request.Request('http://127.0.0.1:17000/api/'+path,
      data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'})
    started=time.monotonic()
    try:
        with opener.open(req,timeout=5) as response: result=json.load(response); status=response.status
    except urllib.error.HTTPError as error: result=json.load(error); status=error.code
    cookie.save(ignore_discard=True)
    if data is not None and path!='heartbeat':
        with Path('build/phase4/http-actions.jsonl').open('a') as log:
            log.write(json.dumps(dict(local_monotonic_s=started,path=path,body=data,status=status,
               duration_ms=1000*(time.monotonic()-started),response=result))+'\n')
    return status,result

def wait(predicate,timeout=8,motion=None):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        api('heartbeat',dict(motion=motion))
        _,state=api('state')
        if predicate(state): return state
        time.sleep(.07)
    raise AssertionError(json.dumps({k:state.get(k) for k in ('motion','bridge','link','sensors','vision')}))

def ready():
    return wait(lambda s:s['bridge']['connected'] and s['bridge']['readyToArm'] and
      not s['motion']['stopping'] and not s['motion']['busy'] and not s['sensors']['fault'])

def stop():
    status,result=api('stop',{})
    assert status==200,(status,result)
    return wait(lambda s:not s['motion']['enabled'] and not s['link']['armed'] and s['link']['activeMask']==0)

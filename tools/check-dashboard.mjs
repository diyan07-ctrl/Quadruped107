// DOM behavior checks, not screenshot or mobile hardware validation.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const require=createRequire(path.join(root,'build/mermaid/package.json'));
const {JSDOM}=require('jsdom');
const html=fs.readFileSync(path.join(root,'software/pi/quadruped/web/index.html'),'utf8');
const script=fs.readFileSync(path.join(root,'software/pi/quadruped/web/app.js'),'utf8');
const dom=new JSDOM(html,{url:'http://127.0.0.1:7000',runScripts:'outside-only'});
const w=dom.window;
let data={
  simulation:true,features:{virtualSensors:true,handGesture:false},
  controlModes:['manual','opencv','explore','sensor_test','idle'],
  link:{connected:true,armed:true,kind:'virtual-uno',targets:Array(8).fill(300),activeMask:255},
  motion:{enabled:true,appMode:'explore',desiredMotion:'forward',currentMotion:'forward',generation:1,busy:false,lastResult:'Virtual'},
  camera:{available:false,status:'Synthetic DOM fixture'},vision:{targetColor:'yellow',targetFresh:true,observationAge:.1,blueBall:{detected:true,offset:-.5,lockState:'locked'}},system:{},
  visionConfig:{revision:7,settings:{target_color:'yellow',search_enabled:false}},
  decisionHistory:[{seq:1,time:'12:00:00',kind:'motion_request',status:'requested',motion:'turn_left',reason:'<img id=historyInjected>'}],
  bridge:{connected:true},sensors:{front_m:2,fault:null,observations:{urm37:{age:.1}},touches:{}},
  autonomy:{state:'EXPLORING',obstacle:'CLEAR',reason:'<img id="injected">',lastRequestedMotion:'forward'}
};
const calls=[];
w.fetch=async(url,options={})=>{
  const pathname=new URL(String(url),'http://127.0.0.1:7000').pathname;
  calls.push([pathname,options.method||'GET',options.body]);
  return {ok:true,status:200,json:async()=>pathname==='/api/state'?data:pathname==='/api/camera-frame'?{available:false,status:'Fixture'}:{ok:true,state:data.motion}};
};
w.setInterval=()=>0;
w.requestAnimationFrame=()=>0;
w.eval(script);
const flush=()=>new Promise(resolve=>setTimeout(resolve,5));
try {
  await flush();
  assert.equal(w.document.getElementById('virtualAutonomy').hidden,false);
  assert.match(w.document.getElementById('navState').textContent,/EXPLORING/);
  assert.equal(w.document.getElementById('injected'),null);
  assert.equal(w.document.getElementById('historyInjected'),null);
  assert.equal(w.document.getElementById('targetColorSelect').value,'yellow');
  assert.match(w.document.getElementById('decisionHistory').textContent,/requested/);
  w.document.getElementById('targetColorSelect').value='blue';
  w.document.getElementById('targetColorSelect').dispatchEvent(new w.Event('change'));
  await flush();
  const selection=calls.find(([url,method])=>url==='/api/vision'&&method==='POST');
  assert.equal(JSON.parse(selection[2]).revision,7);
  assert.equal(JSON.parse(selection[2]).target_color,'blue');
  assert.equal(w.document.querySelector('[data-app-mode="explore"]').hidden,false);
  assert.equal(w.document.querySelector('[data-app-mode="hand_gesture"]').hidden,true);
  data={...data,motion:{...data.motion,enabled:false},link:{...data.link,armed:false}};
  await w.loadState();
  assert.equal(w.document.querySelector('[data-drive-mode="forward"]').disabled,true);
  assert.equal(w.document.getElementById('stopButton').disabled,false);
  w.document.getElementById('stopButton').click();
  await flush();
  assert(calls.some(([url,method])=>url==='/api/stop'&&method==='POST'));
  data={...data,features:{virtualSensors:false,handGesture:false},controlModes:['manual','opencv','idle'],sensors:null,autonomy:null};
  await w.loadState();
  assert.equal(w.document.getElementById('virtualAutonomy').hidden,true);
  assert.equal(w.document.querySelector('[data-app-mode="explore"]').hidden,true);
  console.log('Dashboard DOM passed: virtual/legacy modes, text escaping, disabled motion and available STOP.');
} finally {w.close();}

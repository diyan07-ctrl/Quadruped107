"""Publish the qualification matrix from observed results, including blockers."""
from datetime import datetime,timezone
import csv,json
from pathlib import Path
root=Path('evidence/phase4/2026-11-10')
rows=[]
def row(ident,status,objective,actual,path,command,classification='REAL PI / VIRTUAL ACTUATORS'):
    if path and not (root/path).exists() and (root/(path+'.gz')).exists(): path+='.gz'
    rows.append(dict(id=ident,result=status,date_utc='2026-11-10',
      commit='d29dfdbfc42f6f49c0e96837cc53d816bbf8a47e',objective=objective,
      environment='Pi 4 Debian 13.7 Python 3.13.5; Windows Python 3.11.18/PyBullet 3.2.5',
      command=command,preconditions='Physical outputs prohibited; explicit virtual backend; deliberate enable per movement test',
      expected='Fresh, correct observations/decisions and safe explicit control; all required assertions pass',
      actual=actual,classification=classification,logs=[path] if path else [],
      measurements='See linked original JSON/log; units retained',screenshots=[],recordings=[],
      issues=[] if status=='PASS' else [actual],fixes='See PHASE4_VALIDATION.md and before/after guard evidence'))
row('ENV-SSH','PASS','Authenticated Pi execution','Real SSH commands executed; public-key handoff repaired access','preflight/pi-audit.log','python tools/phase4-ssh.py --script build/phase4/pi-audit.sh --log evidence/phase4/2026-11-10/preflight/pi-audit.log')
row('ENV-GIT','PASS','Preserve original edits and select Phase 4','Added missing refspec; isolated d29dfdb worktree; original patch hashes unchanged','udp/pi-protocol-and-tests.log','git remote set-branches --add origin phase4/pi-hil-qualification; git fetch origin; git worktree add --detach ~/Quadruped107-phase4-qualification origin/phase4/pi-hil-qualification')
row('A-PREFLIGHT','PASS','Pi environment and project dependencies','Required imports/dependencies, camera permissions, memory/disk/network and 0x0 throttling verified','preflight/pi-isolated-checkout.log','PYTHONPATH=software/pi ~/Quadruped107/.venv-pi-virtual/bin/python tools/pi-preflight.py --output build/preflight.json')
row('B-640','PASS','Five-minute real camera benchmark','5952 frames / 300.008 s = 19.839 FPS; zero failed reads','camera/benchmark.json','PYTHONPATH=software/pi .venv-pi-virtual/bin/python build/phase4-qualification/camera-benchmark.py --output build/phase4-qualification/camera.json')
rows[-1].update(commit='a15c39775a4063b396c3cd844f66324cd250021c',dirty=True,notes='Original Pi checkout with preserved staged Phase 4 overlay; benchmark script subsequently committed as d29dfdb.')
row('B-320','PASS','Five-minute lower-resolution benchmark','5953 frames / 300.029 s = 19.841 FPS; detector 5.080 ms; CPU 27.64%','camera/benchmark.json','Same benchmark command; 320x240 interval')
rows[-1].update(commit='a15c39775a4063b396c3cd844f66324cd250021c',dirty=True,notes='Original Pi checkout with preserved staged Phase 4 overlay; benchmark script subsequently committed as d29dfdb.')
row('C01-BLUE-CENTER','PASS','Real centered blue observation','Session HSV saturation floor 40: 54/55 detected samples over 12 s','vision/blue-tuned-center.json','python build/phase4/tune-blue.py','REAL CAMERA / SESSION HSV TRIAL')
for ident,label in [('C02-BLUE-LEFT','left'),('C03-BLUE-RIGHT','right')]:
    row(ident,'PASS','Real horizontal blue candidate observation','Operator moved physical blue object; locked '+label+' candidates retained with coordinates; continuous closed-loop pursuit remains unqualified','reports/runtime-analysis.json','Pi app-probe.py continuous 1 Hz state logging','REAL CAMERA / POSITIONAL OBSERVATION')
row('C04-YELLOW-CENTER','FAIL','Reliable real yellow target detection','Genuine locks occurred, but controlled tuned interval had 0/68 detections; overexposure/low saturation unresolved','vision/yellow-tuned-center.json','python build/phase4/tune-yellow.py','REAL CAMERA / FAILED HSV TRIAL')
for ident,objective in [('C05-YELLOW-LEFT','Confirmed physical yellow target at left'),('C06-YELLOW-RIGHT','Confirmed physical yellow target at right'),('C07-PERSISTENCE','Controlled continuous identity/smoothing through sweep'),('C09-MULTIPLE','Controlled multiple physical candidate selection')]:
    row(ident,'BLOCKED',objective,'No complete controlled qualifying run; incidental/background candidates are not credited','reports/runtime-analysis.json','Not completed with controlled physical targets','REAL CAMERA / INCOMPLETE')
row('C08-TARGET-LOSS','BLOCKED','Physical target removal during accepted tracking','Operator removal was logged in perception; later controlled active sweep could not establish all prerequisites','vision/blue-live-result.json','Pi: python build/hil-retest/blue-probe.py','REAL CAMERA / INCOMPLETE ACTIVE REMOVAL')
row('C10-NO-TARGET','PASS','Real no-target perception','Searching/mask_too_small observations occurred during operator removal; this is perception evidence','endurance/pi-state.jsonl.gz','Pi app-probe.py continuous state logging','REAL CAMERA / PERCEPTION ONLY')
row('C11-STALE','PASS','Stale actual acquisition inhibits tracking','Stopped capture owner during blue tracking; stale vision caused disarm/mask zero; recovery stayed disarmed','safety/camera-fault.json','python tools/phase4-ssh.py --script build/phase4/camera-fault.sh --log evidence/phase4/2026-11-10/safety/camera-fault.log','REAL CAMERA / SOFTWARE FAULT INJECTION')
row('C12-COLOR-SWITCH','PASS','Real-camera color mode selection','Blue/yellow revisions persisted; color changes disarmed and old detector context was replaced','vision/blue-center.json','POST /api/vision with current revision and target_color','REAL CAMERA / CONFIGURATION')
row('D-UDP','PASS','Cross-machine challenge/lease transport','Observed peer 192.168.1.42 and accepted/rejected traces on Windows LAN receiver','pybullet/packets.jsonl.gz','python evidence/phase4/2026-11-10/pybullet/twin-probe.py --gui --port 17012 --output build/phase4/gui-twin --control build/phase4/gui-control.json')
row('D-VUNO','PASS','Accepted and rejected virtual commands on Pi','Separate virtual Uno accepted forward, rejected disarmed/out-of-range commands, ended disarmed','udp/pi-protocol-and-tests.log','PYTHONPATH=software/pi Pi python: VirtualUno.feed(HELLO/MOVE/ARM/STOP/SERVO) as preserved in log','PI VIRTUAL PROTOCOL INSTANCE')
row('D-JOINTS','PASS','Actual motion on all eight virtual joints','Measured armed joint ranges 0.205-0.493 rad; requested ticks separately retained','reports/runtime-analysis.json','Windows twin-probe.py records World.step() joint positions')
row('D-DASHBOARD','PASS','Live real-camera and virtual status dashboard','Observed live camera, rates, target mode, decisions, sensors, bridge and output-mask status','screenshots/pi-dashboard.png','SSH -L 127.0.0.1:17000:127.0.0.1:7000; browser http://127.0.0.1:17000')
for item in json.loads((root/'autonomy/manual-lan.json').read_text()):
    row(item['id'],item['result'],'Execute '+item['id'],'Virtual command accepted and STOP mask zero' if item['result']=='PASS' else item.get('error','See evidence'),'autonomy/manual-lan.json','python evidence/phase4/2026-11-10/autonomy/manual-lan-probe.py')
for item in json.loads((root/'safety/lan-faults.json').read_text()):
    row(item['id'],item['result'],item['id'],'Observed required short-case assertion; deliberate re-enable between cases; virtual sensors only','safety/lan-faults.json','python evidence/phase4/2026-11-10/safety/lan-fault-probe.py')
row('E-EXPLORE','PASS','Existing exploration state','Explore produced accepted forward before the simulated touch case','safety/lan-faults.json','lan-fault-probe.py: enable(explore)')
row('E-AVOIDANCE','PASS','Existing bounded virtual recovery policy','Automated known-geometry/navigation cases passed; this is simulated coverage, not physical sensing or a qualified real-target pursuit','retest/reports/REG-PY.log','python -m unittest discover -s tests -v','AUTOMATED SIMULATED COVERAGE')
row('F-STOP','PASS','STOP preempts active virtual routines','Six manual routines ended with output mask zero; observed RTT 125-235 ms','autonomy/manual-lan.json','POST /api/stop; poll /api/state')
row('F-APP-RESTART','PASS','Startup/restart does not re-enable','Fresh process session 0, disarmed, mask zero, ready handshake','safety/restart-state.json','Safe shutdown and restart script preserved in safety/app-restart.log')
row('F-SIM-PROCESS-RESTART','PASS','Actual simulator process restart','New receiver accepted a disarmed Pi trace; no automatic enable; final mask zero','safety/final-cleanup.log','Restart twin-probe.py process on UDP 7002; pi-cleanup.sh inspects state and issues final STOP')
row('F-VIRTUAL-ONLY','PASS','Keep physical interfaces inactive','Runtime physicalActuationAllowed=false, virtual://uno; compilation only; no physical upload/GPIO/PCA9685 operations','safety/restart-state.json','Runtime(... actuator_backend=virtual, virtual_sensors=True)','SOFTWARE INHIBITION; NO ELECTRICAL MEASUREMENT')
row('G-GUI','FAIL','Uninterrupted healthy endurance','Initial 3167 s log snapshot; longest fully healthy segment only 560.807 s','reports/runtime-analysis.json','Pi app-probe.py + Windows GUI twin-probe.py')
row('G-WINDOWS-CONTROL','FAIL','Windows-owned manual-forward endurance','Stale motion intent at about 6.4 s; attempt interrupted; not a full successful run','endurance/windows-attempt.jsonl.gz','python evidence/phase4/2026-11-10/endurance/run-endurance.py')
end=json.loads((root/'endurance/pi-headless-result.json').read_text())
row('G-PI-CONTROL',end['result'],'15-minute Pi-owned integration retest',f"Completed {end['duration_s']:.3f} s monitoring; unexpected stale front range at {end['errors'][0]['elapsed_s']:.3f} s; no automatic re-arm",'endurance/pi-headless-result.json','Pi: nohup python -u build/hil-retest/run-endurance.py','REAL PI CAMERA/LAN; VIRTUAL MANUAL FORWARD')
row('REG-PY','PASS','Full repaired Python regression','163/163 passed; original 160/161 failure retained separately','retest/reports/REG-PY.log','python -m unittest discover -s tests -v','SOFTWARE / SIMULATED ONLY')
row('REG-PI-SUBSET','PASS','Pi Python 3.13 preflight/telemetry subset','8/8 passed on the actual Pi','udp/pi-protocol-and-tests.log','PYTHONPATH=software/pi:tests Pi python -m unittest test_pi_preflight test_telemetry -v','ACTUAL PI / SOFTWARE SUBSET')
row('REG-UNO','PASS','Compile both firmware variants','Production 10198/998 bytes; virtual 6756/831 bytes; no upload','reports/uno-production.log','arduino-cli compile --profile uno firmware/uno/sketch; generate-virtual-firmware.py; arduino-cli compile --profile uno build/virtual/sketch','COMPILE ONLY')
row('REG-CHECKS','PASS','CAD, configuration, simulation, DOM and repository checks','All 14 checks passed in the repaired local-checks run','retest/reports/local-checks.json','python tools/phase4-local-checks.py --output evidence/phase4/2026-11-10/retest','SOFTWARE / SIMULATED ONLY')
row('VIDEO-SET','BLOCKED','Seven complete demonstration recordings','Genuine USB/GUI captures retained; black dashboard capture and incomplete synchronized/target/endurance demonstrations are explicitly identified','videos/README.md','FFmpeg gdigrab / HTTP MJPEG commands in recording manifest','GENUINE CAPTURES; INCOMPLETE SET')
(root/'reports/test-matrix.json').write_text(json.dumps(dict(overall='PARTIALLY VERIFIED',tests=rows),indent=2)+'\n')
with (root/'reports/test-matrix.csv').open('w',newline='') as file:
    writer=csv.DictWriter(file,fieldnames=['id','result','objective','actual','classification','command','logs']);writer.writeheader()
    for r in rows: writer.writerow({k:r[k] for k in writer.fieldnames})
body='# Phase 4 test matrix\n\n**PARTIALLY VERIFIED.** Source `d29dfdb`; 10 November 2026. '
body+='Each result is limited to its stated evidence class. [Full records](../evidence/phase4/2026-11-10/reports/test-matrix.json) include commands, preconditions, environment, expected/actual results and limitations.\n\n'
body+='| Test ID | Result | Observation / evidence |\n| --- | --- | --- |\n'
for r in rows:
    path=r['logs'][0] if r['logs'] else 'README.md'
    body+=f"| {r['id']} | {r['result']} | [{r['actual']}](../evidence/phase4/2026-11-10/{path}) |\n"
Path('docs/PHASE4_TEST_MATRIX.md').write_text(body)
print('Matrix tests:',len(rows))

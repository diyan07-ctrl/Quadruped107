"""Offline frozen-image evaluation. No camera, network or actuator access.

--compare-ref executes the detector source from an explicitly trusted Git revision.
Unknown labels remain unknown; detections are observations, not confirmed targets.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import types
import cv2

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'software/pi'))
from quadruped.vision import detect_blue_ball
from quadruped.autonomy import VisionSettings


def evaluate(detector):
    directory=ROOT/'evidence/phase4/2026-11-10-remediation/vision/yellow-center-initial'
    cases=[(directory/name,'yellow','clipped yellow target; rejection expected',False)
           for name in ('frame-001-original.png','frame-010-original.png')]
    cases += [(p,None,'unknown; annotated historical screenshot',None)
              for p in sorted((ROOT/'evidence/phase4/2026-11-10/screenshots').glob('*real*.jpg'))]
    rows=[]
    for path,expected,note,want in cases:
        frame=cv2.imread(str(path))
        if frame is None: raise ValueError('Unreadable frozen image: '+str(path))
        for crop in ('full','background_top_120') if expected=='yellow' else ('full',):
            image=frame if crop=='full' else frame[:120]
            for color in ('blue','yellow'):
                settings=VisionSettings(target_color=color)
                start=time.perf_counter()
                result=detector(image,lower=settings.hsv_lower,upper=settings.hsv_upper)
                runtime=(time.perf_counter()-start)*1000
                known=want if color==expected else None
                if crop!='full' and color==expected: known=False
                rows.append(dict(source=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    crop=crop,expectedCategory=expected,note=note,color=color,
                    detected=result['detected'],rejectionReason=result['rejectReason'],
                    position=[result['x'],result['y']],circularity=result['circularity'],
                    fillRatio=result['fillRatio'],runtimeMs=round(runtime,3),
                    hsvDiagnostics=result.get('hsvDiagnostics'),contours=result.get('contourDiagnostics'),
                    expectedDetection=known,falsePositiveObservation=result['detected'] if known is False else None))
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--compare-ref')
    args=parser.parse_args()
    result=dict(classification='OFFLINE RECORDED FRAMES ONLY',physicalTrackingQualified=False,
                commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),after=evaluate(detect_blue_ball))
    if args.compare_ref:
        source=subprocess.check_output(['git','show',args.compare_ref+':software/pi/quadruped/vision.py'],cwd=ROOT,text=True)
        module=types.ModuleType('baseline_vision');exec(compile(source,'baseline_vision.py','exec'),module.__dict__)
        result.update(compareRef=args.compare_ref,before=evaluate(module.detect_blue_ball))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(cases=len(result['after']),knownFalsePositives=sum(r['falsePositiveObservation'] is True for r in result['after']))))
    return int(any(r['expectedDetection'] is not None and r['detected']!=r['expectedDetection'] for r in result['after']))


if __name__=='__main__': raise SystemExit(main())

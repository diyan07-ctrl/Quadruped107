"""Timed physical-target study from the actual Pi qualification camera endpoint."""
import argparse,base64,importlib.util,json,time,math
from pathlib import Path
import cv2
import numpy as np
spec=importlib.util.spec_from_file_location('phase4hil',Path(__file__).with_name('phase4-hil.py'))
hil=importlib.util.module_from_spec(spec);spec.loader.exec_module(hil)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:17000')
    parser.add_argument('--color',choices=('blue','yellow'),required=True)
    parser.add_argument('--label',required=True)
    parser.add_argument('--seconds',type=float,default=8)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    client=hil.Client(args.url);client.call('api/stop',{})
    state=client.call('api/state')
    if state['visionConfig']['settings']['target_color']!=args.color:
        client.call('api/vision',dict(revision=state['visionConfig']['revision'],target_color=args.color))
    start=time.monotonic();started=hil.utc();rows=[];seen=set()
    while time.monotonic()-start<args.seconds:
        sample=client.call('qualification/frame')
        if sample.get('available') and sample['sequence'] not in seen:
            seen.add(sample['sequence'])
            encoded=sample.get('rawPng') or sample['rawJpeg']
            raw=cv2.imdecode(np.frombuffer(base64.b64decode(encoded),np.uint8),cv2.IMREAD_COLOR)
            mask=cv2.imdecode(np.frombuffer(base64.b64decode(sample['maskPng']),np.uint8),cv2.IMREAD_GRAYSCALE)
            annotated=cv2.imdecode(np.frombuffer(base64.b64decode(sample['annotatedJpeg']),np.uint8),cv2.IMREAD_COLOR)
            hsv=cv2.cvtColor(raw,cv2.COLOR_BGR2HSV)
            # Central ROI is declared explicitly, independent of detector acceptance.
            h,w=raw.shape[:2];roi=hsv[h//4:3*h//4,w//4:3*w//4]
            stats=dict(centralRoi=[w//4,h//4,w//2,h//2],
              hsvPercentiles=np.percentile(roi.reshape(-1,3),[10,25,50,75,90],axis=0).tolist(),
              overexposedFraction=float((roi[:,:,2]>=250).mean()))
            contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            probes=[]
            for contour in sorted(contours,key=cv2.contourArea,reverse=True)[:8]:
                area=cv2.contourArea(contour);perimeter=cv2.arcLength(contour,True)
                (x,y),radius=cv2.minEnclosingCircle(contour)
                bbox=list(cv2.boundingRect(contour));circle=math.pi*radius*radius
                circularity=4*math.pi*area/perimeter**2 if perimeter else 0
                fill=area/circle if circle else 0
                settings=sample['settings']
                reason=('min_area' if area<settings['min_area'] else 'min_radius' if round(radius)<settings['min_radius']
                  else 'max_radius' if round(radius)>int(min(w,h)*settings['max_radius_ratio'])
                  else 'circularity' if circularity<settings['min_circularity'] else 'fill_ratio' if not .40<=fill<=1.18 else None)
                probes.append(dict(area=area,perimeter=perimeter,x=x,y=y,radius=radius,bbox=bbox,
                    circularity=circularity,fillRatio=fill,rejectionReason=reason,
                    touchesFrameEdge=bbox[0]<=0 or bbox[1]<=0 or bbox[0]+bbox[2]>=w or bbox[1]+bbox[3]>=h))
            rows.append(dict(elapsedS=time.monotonic()-start,sequence=sample['sequence'],
                frameAgeS=sample['frameAgeS'],detection=sample['detection'],stats=stats,settings=sample['settings'],contourDiagnostics=probes))
            if len(rows) in (1,10,20):
                name=f"frame-{len(rows):03}"
                cv2.imwrite(str(args.output/(name+'-original.png')),raw)
                cv2.imwrite(str(args.output/(name+'-mask.png')),mask)
                composite=np.hstack([raw,cv2.cvtColor(mask,cv2.COLOR_GRAY2BGR),annotated])
                cv2.imwrite(str(args.output/(name+'-comparison.png')),composite)
        time.sleep(.15)
    result=dict(id=args.label,result='PASS' if rows and all(r['detection']['detected'] for r in rows) else 'FAIL',
      source='REAL PI USB CAMERA; operator declared target placement',color=args.color,label=args.label,
      startedUtc=started,endedUtc=hil.utc(),durationS=time.monotonic()-start,uniqueObservedFrames=len(rows),
      detectedFrames=sum(r['detection']['detected'] for r in rows),
      note='Observed sampled frames, not camera capture FPS; original is decoded PNG when available, otherwise JPEG.',samples=rows)
    (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='samples'},indent=2))
if __name__=='__main__':main()

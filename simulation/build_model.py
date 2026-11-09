"""Generate a CAD-mesh articulated fixture; joint axes/masses are explicitly provisional."""
import argparse
import hashlib
import json
import math
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/"simulation/model"
JOINTS=("shoulder_fl","leg_fl","shoulder_fr","leg_fr","shoulder_bl","leg_bl","shoulder_br","leg_br")


def mesh_info(path):
    raw=path.read_bytes()
    count=struct.unpack_from("<I",raw,80)[0]
    if len(raw)!=84+50*count: raise ValueError("Unsupported/malformed binary STL")
    low=[math.inf]*3
    high=[-math.inf]*3
    for offset in range(84,len(raw),50):
        for vertex in range(3):
            xyz=struct.unpack_from("<fff",raw,offset+12+vertex*12)
            if not all(math.isfinite(v) for v in xyz): raise ValueError("Nonfinite mesh")
            for k,value in enumerate(xyz):
                low[k]=min(low[k],value)
                high[k]=max(high[k],value)
    return dict(sha256=hashlib.sha256(raw).hexdigest(),triangles=count,min=low,max=high,
                size=[b-a for a,b in zip(low,high)],center=[(a+b)/2 for a,b in zip(low,high)])


def format_vec(v): return " ".join(f"{x:.10g}" for x in v)


def inertia(link,mass,size,com):
    element=ET.SubElement(link,"inertial")
    ET.SubElement(element,"origin",xyz=format_vec(com))
    ET.SubElement(element,"mass",value=str(mass))
    x,y,z=size
    ET.SubElement(element,"inertia",ixx=str(mass*(y*y+z*z)/12),iyy=str(mass*(x*x+z*z)/12),
                  izz=str(mass*(x*x+y*y)/12),ixy="0",ixz="0",iyz="0")


def visual(link,name,info,destination,rotate=False):
    center=[v*.001 for v in info["center"]]
    # R_y(pi/2) maps original shoulder long X to link -Z.
    rotated=[center[2],center[1],-center[0]] if rotate else center
    origin=[a-b for a,b in zip(destination,rotated)]
    node=ET.SubElement(link,"visual")
    ET.SubElement(node,"origin",xyz=format_vec(origin),rpy="0 1.5707963267948966 0" if rotate else "0 0 0")
    geometry=ET.SubElement(node,"geometry")
    ET.SubElement(geometry,"mesh",filename="../../hardware/stl/"+name,scale=".001 .001 .001")
    material=ET.SubElement(node,"material",name="cad")
    ET.SubElement(material,"color",rgba=".25 .45 .65 1")


def collision(link,size,com):
    node=ET.SubElement(link,"collision")
    ET.SubElement(node,"origin",xyz=format_vec(com))
    ET.SubElement(ET.SubElement(node,"geometry"),"box",size=format_vec(size))


def generate():
    names=["Base.stl","Case.stl"]+[prefix+leg+".stl" for leg in ("FL","FR","BL","BR") for prefix in ("Shoulder","Leg","Foot")]
    meshes={name:mesh_info(ROOT/"hardware/stl"/name) for name in names}
    step=(ROOT/"hardware/cad/Quadruped107.step").read_bytes()
    if b"SI_UNIT(.MILLI.,.METRE.)" not in step: raise ValueError("STEP millimetre context missing")
    data=json.loads((ROOT/"software/pi/quadruped/data/motions.json").read_text())
    neutral=[300]*8
    for table in ("StandShoulders","StandLegs"):
        for channel,tick in data["tables"][table]: neutral[channel]=tick
    sx,sy,_=meshes["Base.stl"]["size"]
    sz=meshes["Case.stl"]["max"][2]-meshes["Base.stl"]["min"][2]
    body=[sx*.001,sy*.001,sz*.001]
    upper=max(meshes["ShoulderFL.stl"]["size"])*.001
    lower=max(meshes["LegFL.stl"]["size"])*.001
    params=dict(schema=1,provisional=True,units="metres; STL mm scale inferred from STEP context",
        base_mass_kg=.8,upper_mass_kg=.12,lower_and_foot_mass_kg=.08,
        friction=.8,force_nm=.5,max_velocity_rad_s=3.0,upper_span_m=upper,lower_span_m=lower,
        initial_height_m=body[2]/2+upper+lower+.02,
        channels=[dict(channel=i,joint=name,neutral_tick=neutral[i],min_tick=50,max_tick=600,
                       direction=1,min_angle_rad=-1.2,max_angle_rad=1.2) for i,name in enumerate(JOINTS)])
    robot=ET.Element("robot",name="Quadruped107_PROVISIONAL")
    base=ET.SubElement(robot,"link",name="chassis")
    inertia(base,.8,body,[0,0,0])
    center_z=(meshes["Base.stl"]["min"][2]+meshes["Case.stl"]["max"][2])/2000
    for name in ("Base.stl","Case.stl"):
        # Preserve the shared body export coordinates; center their common frame.
        node=ET.SubElement(base,"visual")
        ET.SubElement(node,"origin",xyz=f"0 0 {-center_z}")
        ET.SubElement(ET.SubElement(node,"geometry"),"mesh",filename="../../hardware/stl/"+name,scale=".001 .001 .001")
    collision(base,body,[0,0,0])
    for leg,front,left in (("FL",1,1),("FR",1,-1),("BL",-1,1),("BR",-1,-1)):
        suffix=leg.lower()
        upper_link=ET.SubElement(robot,"link",name="upper_"+suffix)
        lower_link=ET.SubElement(robot,"link",name="lower_"+suffix)
        inertia(upper_link,.12,[.03,.03,upper],[0,0,-upper/2])
        inertia(lower_link,.08,[.01,.03,lower],[0,0,-lower/2])
        visual(upper_link,"Shoulder"+leg+".stl",meshes["Shoulder"+leg+".stl"],[0,0,-upper/2],True)
        visual(lower_link,"Leg"+leg+".stl",meshes["Leg"+leg+".stl"],[0,0,-lower/2])
        visual(lower_link,"Foot"+leg+".stl",meshes["Foot"+leg+".stl"],[0,0,-lower])
        collision(upper_link,[.025,.025,upper],[0,0,-upper/2])
        collision(lower_link,[.01,.025,lower],[0,0,-lower/2])
        collision(lower_link,[.02,.025,.015],[0,0,-lower])
        for joint_name,parent,child,xyz in (
            ("shoulder_"+suffix,"chassis","upper_"+suffix,[front*body[0]*.375,left*(body[1]/2+.018),-body[2]/2]),
            ("leg_"+suffix,"upper_"+suffix,"lower_"+suffix,[0,0,-upper])):
            joint=ET.SubElement(robot,"joint",name=joint_name,type="revolute")
            ET.SubElement(joint,"parent",link=parent)
            ET.SubElement(joint,"child",link=child)
            ET.SubElement(joint,"origin",xyz=format_vec(xyz))
            ET.SubElement(joint,"axis",xyz="0 1 0")
            ET.SubElement(joint,"limit",lower="-1.2",upper="1.2",effort=".5",velocity="3")
            ET.SubElement(joint,"dynamics",damping=".05",friction=".01")
    ET.indent(robot)
    urdf='<?xml version="1.0"?>\n<!-- Provisional axes, origins, masses and collision proxies; not calibrated hardware. -->\n'+ET.tostring(robot,encoding="unicode")+"\n"
    manifest=dict(schema=1,step_sha256=hashlib.sha256(step).hexdigest(),meshes=meshes,
        geometry="Original STL surfaces and raw bounding boxes; original files untouched",
        unknown=["actual joint pivots/axes","actual masses/COM/inertia","friction/torque/servo calibration","assembled STL export transforms"],
        assumption="STL millimetre scaling inferred; part spans proxy joint separations; independent leg meshes recentered",
        fusion_archive="Preserved native F3Z; mechanical constraints not decoded")
    return {"robot.urdf":urdf,"parameters.json":json.dumps(params,indent=2,sort_keys=True)+"\n",
            "cad_manifest.json":json.dumps(manifest,indent=2,sort_keys=True)+"\n"}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    for name,text in generate().items():
        path=MODEL/name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8")!=text: raise SystemExit("Model drift: "+name)
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(text,encoding="utf-8")
    print("CAD-derived provisional model "+("matches source." if args.check else "generated."))

"""Read-only geometry checks after normalizing PTZ angles, then restore tracking."""
import json,socket,time,uuid
from core.config import ROOT
def rpc(c,p):
    with socket.create_connection(('127.0.0.1',50051),timeout=4) as peer:
        peer.sendall((json.dumps(dict(version=1,request_id=uuid.uuid4().hex,command=c,payload=p))+chr(10)).encode());r=json.loads(peer.makefile('rb').readline());assert r['status']=='ok',r;return r['payload']
token=uuid.uuid4().hex;output=ROOT/'runtime'/f'geometry-{token}.json'
for ident in ('ptz-01','ptz-02'):rpc('gimbal.set_angles',dict(device_id=ident,yaw_deg=0,pitch_deg=0))
code='''import unreal,json
from pathlib import Path
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
rigs=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.WiseEyeDemo)
rows=[]
for rig in rigs:
 mount=rig
 while mount.get_attach_parent_actor():mount=mount.get_attach_parent_actor()
 group=[mount]+list(mount.get_attached_actors(reset_array=True,recursively_include_attached_actors=True))
 low=1e9;high=-1e9;count=0
 for actor in group:
  for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
   mesh=comp.static_mesh
   if not mesh or '/PTZRecovered/' not in mesh.get_path_name():continue
   box=mesh.get_bounding_box();transform=comp.get_world_transform()
   for x in (box.min.x,box.max.x):
    for y in (box.min.y,box.max.y):
     for z in (box.min.z,box.max.z):
      p=unreal.MathLibrary.transform_location(transform,unreal.Vector(x,y,z));low=min(low,p.z);high=max(high,p.z)
   count+=1
 rows.append(dict(actor=rig.get_name(),position_cm=list(rig.get_actor_location().to_tuple()),ptz_meshes=count,height_cm=high-low))
Path(OUTPUT).write_text(json.dumps(rows,indent=2),encoding='utf8')
'''.replace('OUTPUT',repr(str(output)))
try:
    (ROOT/'runtime/editor-request.py').write_text(code,encoding='utf-8')
    deadline=time.monotonic()+15
    while not output.exists() and time.monotonic()<deadline:time.sleep(.1)
    rows=json.loads(output.read_text(encoding='utf-8'));assert len(rows)==2
    assert all(r['ptz_meshes']==4 and abs(r['height_cm']-80)<.2 for r in rows),rows
    config=json.loads((ROOT/'ue5/WISEYE/Config/WISEYE/Fleets/original.json').read_text(encoding='utf-8-sig'))
    import math
    for d in config['devices']:
        if d['kind']=='gimbal':assert min(math.dist(d['position_cm'],r['position_cm']) for r in rows)<.1
    report=dict(passed=True,zero_angle_reference_height_cm=80,instances=rows)
    (ROOT/'docs/evidence/fleet_geometry_20261021.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(report,flush=True)
finally:
    for ident in ('ptz-01','ptz-02'):rpc('gimbal.set_tracking',dict(device_id=ident,enabled=True))

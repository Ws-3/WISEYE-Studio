"""Read-only check after reopening the saved scene in the visible editor.

World Partition actors must be loaded; do not run as a map-only commandlet.
"""
import json
from pathlib import Path
import unreal

world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name()=='WISEYE-test'
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'Stop PIE first'
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors={a.get_actor_label():a for a in sub.get_all_level_actors()}
demo=actors['WISEYE_Demo']
assert len(demo.rotors)==4, 'Four rotor references were not saved'
assert all(isinstance(r,unreal.WiseEyeRotor) for r in demo.rotors)
assert all(r.get_attach_parent_actor()==demo.drone for r in demo.rotors)
assert all(len(r.get_attached_actors())==3 for r in demo.rotors)
assert demo.automatic_flight and demo.tracking_enabled and demo.rotors_running
assert abs(demo.flight_radius-600)<.01 and abs(demo.period-24)<.01
assert abs(demo.field_of_view-25)<.01

def vec(p): return [p.x,p.y,p.z]
def family(root):
    pending,result=[root],[]
    while pending:
        a=pending.pop(); result.append(a); pending.extend(a.get_attached_actors())
    return result
def size(group):
    lo,hi=[float('inf')]*3,[-float('inf')]*3
    for a in group:
        if 'plane' in a.get_actor_label().lower(): continue
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            if not c.static_mesh: continue
            b=c.static_mesh.get_bounds()
            for x in (-1,1):
                for y in (-1,1):
                    for z in (-1,1):
                        p=unreal.MathLibrary.transform_location(c.get_world_transform(),b.origin+unreal.Vector(x*b.box_extent.x,y*b.box_extent.y,z*b.box_extent.z))
                        for i,v in enumerate(vec(p)):
                            lo[i],hi[i]=min(lo[i],v),max(hi[i],v)
    return [hi[i]-lo[i] for i in range(3)]

drone_size=size(family(demo.drone))
ptz_size=size([actors[n] for n in ('bottom','bottom2','camera','ptz')])
assert abs(max(drone_size[:2])-60)<.1, drone_size
assert abs(ptz_size[2]-40)<.1, ptz_size
assert actors['bottom2'].get_editor_property('root_component').get_attach_parent()==demo.yaw_pivot
assert all(actors[n].get_editor_property('root_component').get_attach_parent()==demo.pitch_pivot for n in ('camera','ptz'))
report={'passed':True,'drone_size_cm':drone_size,'ptz_size_cm':ptz_size,'rotors':[r.get_actor_label() for r in demo.rotors],'checks':['reopened editor scene','four saved rotor roots and twelve mesh children','scaled drone and PTZ bounds','saved flight and camera parameters','gimbal attachment hierarchy']}
out=Path(unreal.Paths.project_saved_dir())/'WISEYE'
out.mkdir(exist_ok=True)
(out/'controls_scene_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
unreal.log('WISEYE SAVED CONTROLS SCENE VALIDATION PASSED')

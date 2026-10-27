"""Calibrate the existing assembly in an editor map, outside Play; idempotent.

Run calibrate_current_scene() for existing maps, then export_rig() in original.
Leaves source meshes intact. Mavic body excludes eight propeller blades.
"""
import json
from pathlib import Path
import unreal

CONFIG = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_config_dir())) / 'WISEYE'
BLADES = {'Mesh_ncl_'+str(i) for i in (92,94,110,111,119,120,99,100)}

def family(root):
    return [root] + list(root.get_attached_actors(recursively_include_attached_actors=True))

def vector(v):
    return [v.x,v.y,v.z]

def bounds(actors, frame=None, exclude_blades=False):
    points=[]
    for actor in actors:
        for c in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh=c.static_mesh
            if not mesh or mesh.get_path_name().startswith('/Engine/EditorMeshes/') or (exclude_blades and mesh.get_name() in BLADES):
                continue
            b=mesh.get_bounds()
            for x in (-1,1):
                for y in (-1,1):
                    for z in (-1,1):
                        p=unreal.MathLibrary.transform_location(c.get_world_transform(),b.origin+unreal.Vector(x*b.box_extent.x,y*b.box_extent.y,z*b.box_extent.z))
                        if frame:
                            p=unreal.MathLibrary.inverse_transform_location(frame,p)
                        points.append(vector(p))
    assert points, 'No physical meshes'
    return ([min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)])

def calibrate_current_scene():
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert not editor.get_game_world(), 'Stop Play first'
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    demo=next(a for a in actors.get_all_level_actors() if isinstance(a,unreal.WiseEyeDemo))
    spec=json.loads((CONFIG/'device_dimensions.json').read_text(encoding='utf8'))
    drone=demo.drone
    group=family(drone)
    mount=demo
    while mount.get_attach_parent_actor():
        mount=mount.get_attach_parent_actor()
    gimbal_group=family(mount)
    # Only the four PTZ housing meshes, excluding optical and editor helpers.
    housings=[a for a in gimbal_group if any(c.static_mesh and '/PTZRecovered/' in c.static_mesh.get_path_name() for c in a.get_components_by_class(unreal.StaticMeshComponent))]
    for actor in group+gimbal_group:
        actor.modify()
        actor.root_component.modify()
    lo,hi=bounds(group,drone.get_actor_transform(),True)
    target=spec['mavic3']['body_size_xyz_cm']
    drone.set_actor_scale3d(unreal.Vector(*[target[i]/(hi[i]-lo[i]) for i in range(3)]))
    before_lo,before_hi=bounds(housings)
    factor=spec['gimbal']['height_cm']/(before_hi[2]-before_lo[2])
    mount.set_actor_scale3d(mount.get_actor_scale3d()*factor)
    after_lo,_=bounds(housings)
    mount.set_actor_location(mount.get_actor_location()+unreal.Vector(0,0,before_lo[2]-after_lo[2]),False,True)
    lo,hi=bounds(group,drone.get_actor_transform(),True)
    scale=vector(drone.get_actor_scale3d())
    body_size=[(hi[i]-lo[i])*scale[i] for i in range(3)]
    ptz_lo,ptz_hi=bounds(housings)
    ptz_size=[ptz_hi[i]-ptz_lo[i] for i in range(3)]
    assert max(abs(body_size[i]-target[i]) for i in range(3))<.02,body_size
    assert abs(ptz_size[2]-80)<.02,ptz_size
    scene_path=CONFIG/'Scenes'/f'{demo.scene_id}.json'
    scene=json.loads(scene_path.read_text(encoding='utf8'))
    scene['gimbal_location_cm']=vector(demo.get_actor_location())
    scene['device_dimensions_revision']=1
    scene_path.write_text(json.dumps(scene,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    assert unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True), 'Save failed'
    report={'scene':demo.scene_id,'mavic_body_size_cm':body_size,'gimbal_size_cm':ptz_size,'mavic_scale':scale,'gimbal_location_cm':scene['gimbal_location_cm']}
    if demo.scene_id=='original':
        cal_path=CONFIG/'calibration.json'
        cal=json.loads(cal_path.read_text(encoding='utf8'))
        full_lo,full_hi=bounds(group)
        cal.update(drone_bounds_cm=[full_lo,full_hi],drone_size_cm=[full_hi[i]-full_lo[i] for i in range(3)],mavic_body_size_cm=body_size,ptz_size_cm=ptz_size,yaw_world_cm=vector(demo.yaw_pivot.get_world_location()),pitch_world_cm=vector(demo.pitch_pivot.get_world_location()),optical_world_cm=vector(demo.camera.get_world_location()),note='Manufacturer body envelope: Mavic 3 without blades, Avata guards included. Gimbal total height 80 cm. Source meshes are unchanged; this does not calibrate mass/inertia or optical intrinsics.')
        cal_path.write_text(json.dumps(cal,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report

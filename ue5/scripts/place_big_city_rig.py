"""Apply the runtime-verified Big City manifest to its editor rig, own actors only."""
import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
scene=json.loads((root/'Config/WISEYE/Scenes/city_large.json').read_text(encoding='utf-8-sig'))
assert scene['map']=='/Game/WISEYE/Scenes/city_large/BigCity'
assert scene.get('layout_surface_reference',{}).get('kind')=='runtime_fastgeo_trace'
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert not editor.get_game_world()
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert levels.load_level(scene['map'])
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
rigs=[a for a in actors.get_all_level_actors() if isinstance(a,unreal.WiseEyeDemo)]
assert len(rigs)==1
demo=rigs[0];mount=demo
while mount.get_attach_parent_actor():mount=mount.get_attach_parent_actor()
def family(actor):
    found=[actor]
    for a in found:
        found.extend(p for p in a.get_attached_actors() if p not in found)
    return found
owned=set(family(mount)+family(demo.drone)+([demo.overview] if demo.overview else []))
for actor in owned:actor.modify()
mount.add_actor_world_offset(unreal.Vector(*scene['gimbal_location_cm'])-demo.get_actor_location(),False,True)
demo.drone.set_actor_location(unreal.Vector(*scene['flight_origin_cm']),False,True)
demo.flight_origin=unreal.Vector(*scene['flight_origin_cm'])
if demo.overview:
    demo.overview.set_actor_location(unreal.Vector(*scene['overview_location_cm']),False,True)
    p,y,r=scene['overview_rotation_deg']
    demo.overview.set_actor_rotation(unreal.Rotator(pitch=p,yaw=y,roll=r),True)
packages={a.get_package() for a in owned}
assert all(p.get_name()==scene['map'] or p.get_name().startswith('/Game/__ExternalActors__/WISEYE/Scenes/city_large/') for p in packages)
assert unreal.EditorLoadingAndSavingUtils.save_packages(list(packages),True)
unreal.log('WISEYE_BIG_CITY_RUNTIME_LAYOUT_SAVED')

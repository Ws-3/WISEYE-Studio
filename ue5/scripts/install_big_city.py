"""Install only into the completed WISEYE Big City copy, never the source map.

The inspected placement plan must already exist in Config/WISEYE/Scenes/city_large.json.
Prepared remains false until a separate real runtime test passes.
"""
import json
from pathlib import Path
import sys
import unreal

sys.path.insert(0,str(Path(__file__).resolve().parent))
from scene_tools import install_rig, ACTORS, EDITOR, LEVELS, CONFIG

path=CONFIG/'Scenes/city_large.json'
scene=json.loads(path.read_text(encoding='utf-8-sig'))
assert scene['id']=='city_large' and scene['map']=='/Game/WISEYE/Scenes/city_large/BigCity'
fleet_path=CONFIG/'Fleets/city_large.json'
if fleet_path.exists():
    assert json.loads(fleet_path.read_text(encoding='utf-8-sig'))['scene_id']=='city_large'
assert LEVELS.load_level(scene['map'])
world=EDITOR.get_editor_world()
assert not EDITOR.get_game_world()
assert not any(isinstance(a,unreal.WiseEyeDemo) for a in ACTORS.get_all_level_actors()), 'Rig already installed; refusing duplicate'
partition=world.get_world_settings().get_editor_property('world_partition')
# UE 5.8 protects the streaming flag from Python. Runtime uses the public C++
# IsStreamingEnabled API and refuses physics startup if streaming is disabled.
assert partition
descs=unreal.WorldPartitionBlueprintLibrary.get_actor_descs()
special=[d for d in descs if any(t in (str(d.label)+' '+str(d.native_class)+' '+str(d.class_)).lower()
                               for t in ('spawner','nightmode'))]
unreal.WorldPartitionBlueprintLibrary.load_actors([d.guid for d in special])
removed=[]
packages={world.get_package()}
for actor in ACTORS.get_all_level_actors():
    if isinstance(actor,unreal.MassSpawner) or actor.get_class().get_name().lower()=='bp_nightmode_c':
        packages.add(actor.get_package())
        removed.append(actor.get_actor_label())
        assert ACTORS.destroy_actor(actor)
# Only load an 80m placement district. The runtime sources move independently.
x,y,z=scene['flight_origin_cm']
box=unreal.Box(min=unreal.Vector(x-8000,y-8000,z-3000),max=unreal.Vector(x+8000,y+8000,z+15000))
nearby=[d for d in unreal.WorldPartitionBlueprintLibrary.get_intersecting_actor_descs(box)
        if not d.actor_is_editor_only and 'hlod' not in str(d.native_class).lower()]
unreal.WorldPartitionBlueprintLibrary.load_actors([d.guid for d in nearby])
# Preserve the supplied placement plan. Editor visibility traces can hit the
# lower collision proxy instead of runtime FastGeo roads; never overwrite a
# runtime-verified height using that proxy. A new plan must be probed in-game.
hits=scene.get('layout_surface_reference',{})
install_rig(scene)
packages.update(a.get_package() for a in ACTORS.get_all_level_actors()
                if a.get_package().get_name()==scene['map'] or
                a.get_package().get_name().startswith('/Game/__ExternalActors__/WISEYE/Scenes/city_large/'))
assert all(p.get_name()==scene['map'] or p.get_name().startswith('/Game/__ExternalActors__/WISEYE/Scenes/city_large/') for p in packages)
assert unreal.EditorLoadingAndSavingUtils.save_packages(list(packages),True)
scene.update(prepared=False,assembly_revision=2,integration_status='assembled_pending_validation')
path.write_text(json.dumps(scene,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
fleet=dict(version=1,scene_id='city_large',devices=[
    dict(id='uav-01',kind='drone',name='大城市试验无人机',model_id='mavic3',position_cm=scene['flight_origin_cm'],rotation_deg=[0,0,0]),
    dict(id='ptz-01',kind='gimbal',name='大城市试验双光云台',model_id='eo80',position_cm=scene['gimbal_location_cm'],rotation_deg=[0,0,0],tracking_target='uav-01')])
fleet_path.parent.mkdir(parents=True,exist_ok=True)
if not fleet_path.exists():
    fleet_path.write_text(json.dumps(fleet,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
out=Path(unreal.Paths.project_dir())/'Saved/WISEYE/big_city/assembly.json'
out.write_text(json.dumps(dict(scene=scene,removed_spawners=removed,surface_checks=hits),ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('WISEYE_BIG_CITY_ASSEMBLED_PENDING_VALIDATION')

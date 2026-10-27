"""Install the calibrated WISEYE rig in the copied WP city, never in the source map.

Requires logs/city_placement_plan.json produced from verified city road locations.
"""
import unreal,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from scene_tools import install_rig,ACTORS,EDITOR,LEVELS,CONFIG
config=CONFIG/'Scenes/city.json';scene=json.loads(config.read_text(encoding='utf8'))
assert scene['map']=='/Game/WISEYE/Scenes/city/CitySample'
current=EDITOR.get_editor_world()
if not current or current.get_path_name().split('.')[0]!=scene['map']:assert LEVELS.load_level(scene['map'])
assert not EDITOR.get_game_world()
assert not any(isinstance(a,unreal.WiseEyeDemo) for a in ACTORS.get_all_level_actors())
plan_path=CONFIG/'CitySample/placement.json'
if not plan_path.is_file():plan_path=ROOT/'logs/city_placement_plan.json'
plan=json.loads(plan_path.read_text(encoding='utf8'))
# Explicitly load the installation district, including its collision proxies.
p=plan['flight_origin_cm']
box=unreal.Box(min=unreal.Vector(p[0]-8000,p[1]-8000,-2000),max=unreal.Vector(p[0]+8000,p[1]+8000,12000))
nearby=unreal.WorldPartitionBlueprintLibrary.get_intersecting_actor_descs(box)
unreal.WorldPartitionBlueprintLibrary.load_actors([d.guid for d in nearby if not d.actor_is_editor_only])
for actor in ACTORS.get_all_level_actors():
    if isinstance(actor,unreal.WorldPartitionHLOD):
        actor.modify();actor.set_actor_enable_collision(False);actor.set_is_temporarily_hidden_in_editor(True)
for key in ('gimbal_location_cm','flight_origin_cm','overview_location_cm','overview_rotation_deg'):scene[key]=plan[key]
# Remove autonomous traffic/crowd generators only from the WISEYE map copy.
descs=unreal.WorldPartitionBlueprintLibrary.get_actor_descs()
spawners=[d for d in descs if 'spawner' in (str(d.label)+' '+str(d.native_class)+' '+str(d.class_)).lower()]
unreal.WorldPartitionBlueprintLibrary.load_actors([d.guid for d in spawners])
removed=[]
for a in ACTORS.get_all_level_actors():
    # The sample's day/night controller binds to its original GameState.
    # WISEYE uses a static city and its own AirSim GameMode.
    if isinstance(a,unreal.MassSpawner) or a.get_class().get_name().lower()=='bp_nightmode_c':
        removed.append(a.get_actor_label());ACTORS.destroy_actor(a)
before={a.get_path_name() for a in ACTORS.get_all_level_actors()}
demo=install_rig(scene)
for a in ACTORS.get_all_level_actors():
    if a.get_path_name() not in before:
        a.modify();a.set_editor_property('is_spatially_loaded',False)
assert unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
# Saving new external actors can unload them in an editor without an active WP region.
labels={r['label'] for r in json.loads((CONFIG/'standard_rig.json').read_text(encoding='utf8'))['actors']}
rig_descs=[d for d in unreal.WorldPartitionBlueprintLibrary.get_actor_descs() if str(d.label) in labels or str(d.label) in ('WISEYE_Gimbal_Assembly','WISEYE_Drone_Assembly') or any(str(d.label).startswith(label+'_visual_') for label in labels)]
unreal.WorldPartitionBlueprintLibrary.load_actors([d.guid for d in rig_descs])
scene.update(name='City Sample · 小城市',source_map='/Game/Map/Small_City_LVL',prepared=False,assembly_revision=2,integration_status='assembled_pending_validation',notes='真实 Small City。首轮使用静态城市环境，已移除副本中的自动人群/交通生成器。需通过运行验证后启用。')
config.write_text(json.dumps(scene,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(ROOT/'logs/city_assembly.json').write_text(json.dumps(dict(map=scene['map'],removed_spawners=removed,scene=scene),ensure_ascii=False,indent=2),encoding='utf8')
unreal.log('WISEYE CITY ASSEMBLY COMPLETE; RUNTIME VALIDATION REQUIRED')

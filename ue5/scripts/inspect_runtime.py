import unreal, json
from pathlib import Path
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world,'Simulation is not running'
demo=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.WiseEyeDemo)[0]
def v(p): return [p.x,p.y,p.z]
def r(p): return [p.pitch,p.yaw,p.roll]
rows={}
for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor):
    if a.get_actor_label() in ['camera','ptz','bottom2','bottom','Mavic3']:
        rows[a.get_actor_label()]={'location':v(a.get_actor_location()),'rotation':r(a.get_actor_rotation()),'parent_component':a.get_editor_property("root_component").get_attach_parent().get_name() if a.get_editor_property("root_component").get_attach_parent() else None}
demo.export_frame()
RESULT={'time':demo.simulation_time,'error_deg':demo.pointing_error,'actors':rows}
output=Path(unreal.Paths.project_saved_dir())/'WISEYE'
output.mkdir(parents=True,exist_ok=True)
(output/'runtime_state.json').write_text(json.dumps(RESULT,indent=2),encoding='utf-8')

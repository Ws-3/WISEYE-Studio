"""Read-only PIE check after a surface-aligned preset reload; uses runtime expectation."""
import json
import sys
from pathlib import Path
import unreal

root=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve().parents[1]
sys.path.insert(0,str(root/'ue5/scripts'))
from calibrate_device_dimensions import family, bounds

expected=json.loads((root/'runtime/placement_expected.json').read_text(encoding='utf-8'))
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world, 'PIE must be running'
demo=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.WiseEyeDemo)[0]
mount=demo
while mount.get_attach_parent_actor():
    mount=mount.get_attach_parent_actor()
housings=[actor for actor in family(mount) if any(
    component.static_mesh and '/PTZRecovered/' in component.static_mesh.get_path_name()
    for component in actor.get_components_by_class(unreal.StaticMeshComponent))]
low,high=bounds(housings)
report=dict(passed=False, gimbal_bottom_cm=low[2], surface_z_cm=expected['surface_z_cm'],
            gimbal_height_cm=high[2]-low[2], anchor_z_cm=demo.get_actor_location().z)
try:
    assert abs(low[2]-expected['surface_z_cm'])<.15,report
    assert abs(high[2]-low[2]-80)<.05,report
    report['passed']=True
finally:
    (root/'runtime/placement_geometry_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

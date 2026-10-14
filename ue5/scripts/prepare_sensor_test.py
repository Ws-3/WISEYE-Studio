"""Outside PIE, prepare the temporary occluder used by verify_sensors.

Do not save the test actor. After stopping PIE, run with --cleanup to remove it.
"""
import sys
import unreal

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'Stop PIE first'
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in sub.get_all_level_actors():
    if a.get_actor_label()=='WISEYE_TestOccluder':
        assert sub.destroy_actor(a)
if '--cleanup' not in sys.argv:
    actor=sub.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(8197,1377,600))
    actor.set_actor_label('WISEYE_TestOccluder')
    actor.set_editor_property('is_spatially_loaded',False)
    component=actor.get_editor_property('static_mesh_component')
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    actor.set_actor_scale3d(unreal.Vector(3,3,3))
    actor.set_actor_hidden_in_game(True)
    unreal.log('WISEYE temporary sensor occluder ready; start PIE and run verify_sensors.py')
else:
    unreal.log('WISEYE temporary sensor occluder removed')

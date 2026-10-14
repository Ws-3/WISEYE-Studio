"""Restore the four deleted PTZ mesh components from isolated pre-edit backup assets.

The restored assets in /Game/WISEYE/PTZRecovered are included in this repository.
Does not overwrite /Game/Mesh* (those names are also used by the drone importer).
"""
import unreal
from pathlib import Path
import json

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'Stop Play before restoration'
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors={a.get_actor_label():a for a in sub.get_all_level_actors()}
demo=actors['WISEYE_Demo']
root=actors['PTZ_Camera']
folder='/Game/WISEYE/PTZRecovered/'
unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([folder.rstrip('/')],True)
specs={
    'camera':('Mesh',(9863.562367,1318.680704,307.956874),10,'pitch_pivot'),
    'ptz':('Mesh_ncl_1',(9977.038855,1364.654180,22.268493),1,'pitch_pivot'),
    'bottom2':('Mesh_ncl_2',(9971.843555,1368.462664,239.463985),10,'yaw_pivot'),
    'bottom':('Mesh_ncl_3',(9997.253516,1377.711118,46.068656),10,None),
}
loaded={name:unreal.load_asset(folder+spec[0]) for name,spec in specs.items()}
assert all(loaded.values()),'Missing backup meshes'
assert loaded['camera'].get_bounds().box_extent.x<20,'Unexpected camera mesh: possible importer name collision'
assert 290<loaded['ptz'].get_bounds().origin.z<293,'Unexpected PTZ mesh'
material_names=['d855abb4-e8c1-4d64-8a00-78dd86fd264c','bb0b1a9f-e887-4a39-a703-9b1ca2a371cd']
materials=[unreal.load_asset(folder+n) for n in material_names]
assert all(materials),'Missing backup materials'
for mat in materials:
    mat.modify()
    for param in mat.get_editor_property('texture_parameter_values'):
        tex=param.parameter_value
        if tex:
            restored=unreal.load_asset(folder+tex.get_name())
            if restored:
                unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mat,param.parameter_info.name,restored)
    unreal.MaterialEditingLibrary.update_material_instance(mat)

# Detach only the four affected actors before restoring zero poses.
keep=unreal.AttachmentRule.KEEP_WORLD
for name in specs:
    if name in actors:
        actors[name].modify()
        actors[name].detach_from_actor(unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD)
demo.modify()
root.modify()
demo.yaw_pivot.modify(); demo.pitch_pivot.modify(); demo.camera.modify()
root.set_actor_location(unreal.Vector(9997.253516,1377.711118,46.068656),False,True)
demo.set_actor_location_and_rotation(unreal.Vector(9997.253516,1377.711118,46.068656),unreal.Rotator(pitch=0,yaw=-160,roll=0),False,True)
demo.set_actor_scale3d(unreal.Vector(1,1,1))
demo.yaw_pivot.set_relative_rotation(unreal.Rotator(),False,True)
demo.pitch_pivot.set_relative_rotation(unreal.Rotator(),False,True)
demo.yaw_pivot.set_world_location(unreal.Vector(9971.843555,1368.462664,239.463985),False,True)
demo.pitch_pivot.set_world_location(unreal.Vector(9970.786179,1368.525888,314.228515),False,True)
demo.camera.set_world_location(unreal.Vector(9815.043624,1301.021327,352.956874),False,True)
rows=[]
for name,(asset_name,position,scale,parent_name) in specs.items():
    actor=actors.get(name)
    if not actor:
        actor=sub.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*position))
        actor.set_actor_label(name)
        actors[name]=actor
    actor.modify()
    component=actor.get_editor_property('static_mesh_component')
    component.modify()
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_static_mesh(loaded[name])
    loaded[name].modify()
    loaded[name].set_material(0,materials[0 if name=='camera' else 1])
    component.set_material(0,materials[0 if name=='camera' else 1])
    component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    actor.set_actor_scale3d(unreal.Vector(scale,scale,scale))
    actor.set_actor_location_and_rotation(unreal.Vector(*position),unreal.Rotator(pitch=0,yaw=110,roll=0),False,True)
    parent=demo.get_editor_property(parent_name) if parent_name else root.get_editor_property('root_component')
    actor.attach_to_component(parent,'',keep,keep,keep,False)
    actor.set_folder_path('WISEYE/PTZ')
    center=unreal.MathLibrary.transform_location(component.get_world_transform(),loaded[name].get_bounds().origin)
    rows.append({'part':name,'asset':loaded[name].get_path_name(),'axis':parent.get_name(),'mesh_center_cm':[center.x,center.y,center.z]})
demo.capture.clear_hidden_components()
demo.capture.hide_actor_components(actors['camera'])
demo.capture.hide_actor_components(actors['ptz'])
unreal.EditorAssetLibrary.save_directory(folder,only_if_is_dirty=False,recursive=True)
assert unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True),'Save failed'
sub.set_selected_level_actors([demo])
p=unreal.Vector(9200,2200,650)
unreal.EditorLevelLibrary.set_level_viewport_camera_info(p,unreal.MathLibrary.find_look_at_rotation(p,unreal.Vector(9950,1360,260)))
result={'restored':rows,'source':'pre-edit Backup-Content','isolated_asset_folder':folder}
(Path(unreal.Paths.project_saved_dir())/'WISEYE'/'ptz_recovery.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
RESULT=result

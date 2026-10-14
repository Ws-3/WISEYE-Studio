"""Run in the test UE editor after building WiseEyeDemo. Safe to run again."""
import unreal
import json
from pathlib import Path

SUB = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
WORLD = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
ACTORS = SUB.get_all_level_actors()
BY_LABEL = {a.get_actor_label(): a for a in ACTORS}
KEEP = unreal.AttachmentRule.KEEP_WORLD
DETACH = unreal.DetachmentRule.KEEP_WORLD

def mesh_component(actor):
    return next(c for c in actor.get_components_by_class(unreal.StaticMeshComponent)
                if c.get_editor_property('static_mesh'))

def mesh_center(actor):
    c = mesh_component(actor)
    return unreal.MathLibrary.transform_location(c.get_world_transform(),c.static_mesh.get_bounds().origin)

def movable(actor):
    actor.modify()
    for c in actor.get_components_by_class(unreal.SceneComponent):
        c.modify()
        c.set_mobility(unreal.ComponentMobility.MOVABLE)

def attach_component(actor, component):
    movable(actor)
    actor.attach_to_component(component,'',KEEP,KEEP,KEEP,False)

def vec(v): return [v.x,v.y,v.z]

if 'WISEYE_Demo' in BY_LABEL and not BY_LABEL['WISEYE_Demo'].get_editor_property('render_target'):
    incomplete=BY_LABEL.pop('WISEYE_Demo')
    for child in incomplete.get_attached_actors():
        child.attach_to_actor(BY_LABEL['PTZ_Camera'],'',KEEP,KEEP,KEEP,False)
    SUB.destroy_actor(incomplete)
    if 'WISEYE_Overview' in BY_LABEL:
        SUB.destroy_actor(BY_LABEL.pop('WISEYE_Overview'))

if 'WISEYE_Demo' not in BY_LABEL:
    required = ['Mavic3','PTZ_Camera','camera','ptz','bottom2','bottom']
    for label in required:
        assert label in BY_LABEL, 'Missing actor: '+label
    root, bottom, bottom2 = BY_LABEL['PTZ_Camera'], BY_LABEL['bottom'], BY_LABEL['bottom2']
    camera_mesh, ptz, drone = BY_LABEL['camera'], BY_LABEL['ptz'], BY_LABEL['Mavic3']
    base_position = mesh_center(bottom)
    yaw_position = mesh_center(bottom2)
    pitch_position = mesh_center(ptz)
    # Imported front plate is thin on local Y: +Y points out of the lens panel.
    optical_forward = mesh_component(camera_mesh).get_world_rotation().get_right_vector()
    zero_rotation = unreal.MathLibrary.make_rot_from_x(optical_forward)
    # Recenter imported root without moving any imported child geometry.
    children = root.get_attached_actors()
    for child in children:
        child.detach_from_actor(DETACH,DETACH,DETACH)
    movable(root)
    root.set_actor_location(base_position,False,True)
    for child in children:
        movable(child)
        child.attach_to_actor(root,'',KEEP,KEEP,KEEP,False)
    demo = SUB.spawn_actor_from_class(unreal.WiseEyeDemo,base_position,zero_rotation)
    demo.set_actor_label('WISEYE_Demo')
    demo.set_folder_path('WISEYE')
    yaw=demo.get_editor_property('yaw_pivot')
    pitch=demo.get_editor_property('pitch_pivot')
    yaw.set_world_location(yaw_position,False,True)
    pitch.set_world_location(pitch_position,False,True)
    attach_component(bottom2,yaw)
    attach_component(camera_mesh,pitch)
    attach_component(ptz,pitch)
    demo.attach_to_actor(root,'',KEEP,KEEP,KEEP,False)
    # A configurable optical mount just in front of the upper aperture.
    c = mesh_component(camera_mesh)
    depth=c.static_mesh.get_bounds().box_extent.y*c.get_world_scale().y
    optical_position=mesh_center(camera_mesh)+optical_forward*(depth+2)+unreal.Vector(0,0,45)
    camera=demo.get_editor_property('camera')
    camera.set_world_location(optical_position,False,True)
    capture=demo.get_editor_property('capture')
    capture.hide_actor_components(camera_mesh)
    capture.hide_actor_components(ptz)
    movable(drone)
    lo=[float('inf')]*3
    hi=[-float('inf')]*3
    for child in drone.get_attached_actors():
        movable(child)
        if 'plane' in child.get_actor_label().lower():
            continue
        for mc in child.get_components_by_class(unreal.StaticMeshComponent):
            mesh=mc.get_editor_property('static_mesh')
            if not mesh: continue
            bounds=mesh.get_bounds()
            for x in (-1,1):
                for y in (-1,1):
                    for z in (-1,1):
                        local=bounds.origin+unreal.Vector(bounds.box_extent.x*x,bounds.box_extent.y*y,bounds.box_extent.z*z)
                        p=unreal.MathLibrary.transform_location(mc.get_world_transform(),local)
                        for i,v in enumerate(vec(p)):
                            lo[i]=min(lo[i],v); hi[i]=max(hi[i],v)
    center=unreal.Vector(*[(lo[i]+hi[i])/2 for i in range(3)])
    offset=unreal.MathLibrary.inverse_transform_location(drone.get_actor_transform(),center)
    demo.set_editor_property('drone',drone)
    demo.set_editor_property('target_offset',offset)
    demo.set_editor_property('flight_origin',drone.get_actor_location()+unreal.Vector(0,0,3200))
    overview_position=unreal.Vector(13000,10000,6500)
    overview=SUB.spawn_actor_from_class(unreal.CameraActor,overview_position,
             unreal.MathLibrary.find_look_at_rotation(overview_position,unreal.Vector(3500,500,2000)))
    overview.set_actor_label('WISEYE_Overview')
    overview.set_folder_path('WISEYE')
    overview.get_component_by_class(unreal.CameraComponent).set_field_of_view(75)
    demo.set_editor_property('overview',overview)
    asset_tools=unreal.AssetToolsHelpers.get_asset_tools()
    rt=unreal.load_asset('/Game/WISEYE/RT_EO')
    if not rt:
        rt=asset_tools.create_asset('RT_EO','/Game/WISEYE',unreal.TextureRenderTarget2D,unreal.TextureRenderTargetFactoryNew())
    rt.set_editor_property('size_x',1280)
    rt.set_editor_property('size_y',720)
    rt.set_editor_property('render_target_format',unreal.TextureRenderTargetFormat.RTF_RGBA8)
    demo.set_editor_property('render_target',rt)
    capture.set_editor_property('texture_target',rt)
    capture.set_editor_property('fov_angle',45)
    camera.set_field_of_view(45)
    calibration={'base_world_cm':vec(base_position),'yaw_world_cm':vec(yaw_position),
                 'pitch_world_cm':vec(pitch_position),'optical_world_cm':vec(optical_position),
                 'optical_forward':vec(optical_forward),'drone_bounds_cm':[lo,hi],
                 'target_offset_local_cm':vec(offset),'moving_yaw':['bottom2'],
                 'moving_yaw_pitch':['camera','ptz'],'fixed':['bottom'],
                 'note':'Imported scale retained. Aperture mounting is approximate and editable.'}
    output=Path(unreal.Paths.project_saved_dir())/'WISEYE'
    output.mkdir(exist_ok=True)
    (output/'calibration.json').write_text(json.dumps(calibration,indent=2),encoding='utf-8')
else:
    demo=BY_LABEL['WISEYE_Demo']

drone=demo.get_editor_property('drone')
movable(BY_LABEL['PTZ_Camera'])
movable(BY_LABEL['bottom'])
movable(drone)
for child in drone.get_attached_actors():
    movable(child)
for label in ['camera','ptz','bottom2']:
    movable(BY_LABEL[label])
overview=demo.get_editor_property('overview')
overview.modify()
overview_position=unreal.Vector(13500,-4500,3200)
overview.set_actor_location_and_rotation(overview_position,unreal.MathLibrary.find_look_at_rotation(overview_position,unreal.Vector(3000,1000,1000)),False,True)
WORLD.get_world_settings().set_editor_property('default_game_mode',unreal.WiseEyeGameMode)
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
SUB.set_selected_level_actors([demo])
p=unreal.Vector(13000,10000,6500)
unreal.EditorLevelLibrary.set_level_viewport_camera_info(p,unreal.MathLibrary.find_look_at_rotation(p,unreal.Vector(3500,500,2000)))
unreal.log('WISEYE: setup complete; Play starts simulation. TAB changes view, P exports PNG.')

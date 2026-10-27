"""UE PIE regression: a plane 1 m from the laser must export x=0.95 m.
Run with the editor Python console: exec(open('<repo>/ue5/scripts/validate_lidar_metric.py',encoding='utf-8-sig').read())
Only borrows an empty actor in the PIE world; always restores it. No editor assets are changed.
"""
import json
from pathlib import Path
import unreal
root=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve().parents[1]
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world, 'Play is required'
demo=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.WiseEyeDemo)[0]
wall=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.StaticMeshActor)
          if not a.static_mesh_component.static_mesh and not a.get_attached_actors())
mesh=wall.static_mesh_component
backup=(wall.get_attach_parent_actor(),wall.get_actor_transform(),mesh.mobility,mesh.get_collision_enabled())
tracking=demo.tracking_enabled
rotation=demo.lidar_mount.get_editor_property('relative_rotation').copy()
try:
    demo.tracking_enabled=False
    mount=demo.lidar_mount
    # Aim upward in world coordinates so terrain cannot occlude the reference plane.
    mount.set_world_rotation(unreal.Rotator(pitch=60,yaw=0,roll=0),False,False)
    wall.detach_from_actor(unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD)
    mesh.set_mobility(unreal.ComponentMobility.MOVABLE)
    mesh.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    mesh.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
    mesh.set_collision_response_to_all_channels(unreal.CollisionResponseType.ECR_IGNORE)
    mesh.set_collision_response_to_channel(unreal.CollisionChannel.ECC_VISIBILITY,unreal.CollisionResponseType.ECR_BLOCK)
    wall.set_actor_enable_collision(True)
    start=mount.get_world_location()+mount.get_forward_vector()*4
    wall.set_actor_location_and_rotation(start+mount.get_forward_vector()*100,mount.get_world_rotation(),False,True)
    wall.set_actor_scale3d(unreal.Vector(.1,8,8))
    assert demo.export_lidar_point_cloud()
    path=Path(unreal.Paths.convert_relative_path_to_full(demo.last_lidar_export_path))
    rows=path.read_text(encoding='utf-8-sig').split('end_header\n',1)[1].splitlines()
    points=[list(map(float,r.split())) for r in rows if r.strip()]
    assert len(points)==demo.lidar_horizontal_samples*demo.lidar_vertical_samples
    assert max(abs(p[0]-.95) for p in points)<.001
    scale=mount.get_world_scale()
    report=dict(passed=True,face_distance_m=.95,hits=len(points),min_x_m=min(p[0] for p in points),max_x_m=max(p[0] for p in points),mount_scale=[scale.x,scale.y,scale.z],ply=str(path))
    (root/'runtime/lidar_ply_metric_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
finally:
    parent,transform,mobility,collision=backup
    mesh.set_static_mesh(None)
    mesh.set_collision_enabled(collision)
    if parent: wall.attach_to_actor(parent,'',unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,False)
    wall.set_actor_transform(transform,False,True)
    mesh.set_mobility(mobility)
    demo.lidar_mount.set_relative_rotation(rotation,False,False)
    demo.tracking_enabled=tracking
    demo.scan_lidar()

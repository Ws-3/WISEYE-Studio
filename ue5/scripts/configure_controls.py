"""Resize the existing assembled scene and add four persisted rotor pivots.

Run in the WISEYE-test editor, outside PIE, after rebuilding the C++ module.
Does not reimport or alter mesh assets. Saves modified World Partition actors.
"""
import json
from pathlib import Path
import unreal

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name() == 'WISEYE-test', 'Open WISEYE-test first'
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'Stop Play first'
actors = {a.get_actor_label(): a for a in sub.get_all_level_actors()}
demo, drone, root = [actors[n] for n in ('WISEYE_Demo', 'Mavic3', 'PTZ_Camera')]
keep = unreal.AttachmentRule.KEEP_WORLD
detach = unreal.DetachmentRule.KEEP_WORLD

def vec(v):
    return [v.x, v.y, v.z]

def family(actor):
    result, pending = [], [actor]
    while pending:
        a = pending.pop()
        result.append(a)
        pending.extend(a.get_attached_actors())
    return result

def mark(actor):
    actor.modify()
    for c in actor.get_components_by_class(unreal.SceneComponent):
        c.modify()
        c.set_mobility(unreal.ComponentMobility.MOVABLE)

def bounds(group):
    lo, hi = [float('inf')]*3, [-float('inf')]*3
    for a in group:
        if 'plane' in a.get_actor_label().lower():
            continue
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            if not c.static_mesh:
                continue
            b = c.static_mesh.get_bounds()
            for x in (-1, 1):
                for y in (-1, 1):
                    for z in (-1, 1):
                        p = unreal.MathLibrary.transform_location(c.get_world_transform(), b.origin+unreal.Vector(x*b.box_extent.x, y*b.box_extent.y, z*b.box_extent.z))
                        for i, value in enumerate(vec(p)):
                            lo[i], hi[i] = min(lo[i], value), max(hi[i], value)
    assert all(v != float('inf') for v in lo), 'No mesh bounds'
    return lo, hi

def mesh(actor):
    return next(c for c in actor.get_components_by_class(unreal.StaticMeshComponent) if c.static_mesh)

def center(actor):
    c = mesh(actor)
    return unreal.MathLibrary.transform_location(c.get_world_transform(), c.static_mesh.get_bounds().origin)

drone_group = family(drone)
ptz_group = [actors[n] for n in ('bottom', 'bottom2', 'camera', 'ptz')]
for a in drone_group + family(root):
    mark(a)

before_drone, before_ptz = bounds(drone_group), bounds(ptz_group)
drone_factor = 60.0/max(before_drone[1][i]-before_drone[0][i] for i in (0, 1))
ptz_factor = 40.0/(before_ptz[1][2]-before_ptz[0][2])
drone.set_actor_scale3d(drone.get_actor_scale3d()*drone_factor)
root.set_actor_scale3d(root.get_actor_scale3d()*ptz_factor)

# Seat the base on the terrain without moving the assembled joints independently.
p = root.get_actor_location()
info = unreal.SystemLibrary.line_trace_single(world, p+unreal.Vector(0,0,3000), p-unreal.Vector(0,0,3000), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, family(root)+drone_group, unreal.DrawDebugTrace.NONE, True)
hit = info.to_dict()
assert hit['blocking_hit'], 'No terrain hit under the gimbal; layout remains unsaved'
ground = hit['location'].z
lo, hi = bounds(ptz_group)
root.set_actor_location(root.get_actor_location()+unreal.Vector(0,0,ground-lo[2]+1.0), False, True)

# Put the drone root at its geometric center, preserving all imported geometry.
lo, hi = bounds(drone_group)
drone_center = unreal.Vector(*[(lo[i]+hi[i])/2 for i in range(3)])
children = drone.get_attached_actors()
for a in children:
    a.detach_from_actor(detach, detach, detach)
drone.set_actor_location(drone_center, False, True)
for a in children:
    a.attach_to_actor(drone, '', keep, keep, keep, False)

by_mesh = {}
for a in family(drone):
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        if c.static_mesh:
            by_mesh[c.static_mesh.get_name()] = a
specs = [
    ('WISEYE_Rotor_FL', 'Mesh_ncl_91', ['Mesh_ncl_92','Mesh_ncl_94'], 1),
    ('WISEYE_Rotor_FR', 'Mesh_ncl_109', ['Mesh_ncl_110','Mesh_ncl_111'], -1),
    ('WISEYE_Rotor_RL', 'Mesh_ncl_121', ['Mesh_ncl_119','Mesh_ncl_120'], -1),
    ('WISEYE_Rotor_RR', 'Mesh_ncl_101', ['Mesh_ncl_99','Mesh_ncl_100'], 1),
]
rotors, rotor_records = [], []
for label, hub_name, blade_names, direction in specs:
    hub = by_mesh[hub_name]
    rotor = actors.get(label)
    if not rotor:
        rotor = sub.spawn_actor_from_class(unreal.WiseEyeRotor, center(hub), mesh(hub).get_world_rotation())
        rotor.set_actor_label(label)
        rotor.set_folder_path('WISEYE/Drone/Rotors')
        rotor.attach_to_actor(drone, '', keep, keep, keep, False)
    mark(rotor)
    rotor.set_editor_property('direction', direction)
    for name in [hub_name]+blade_names:
        a = by_mesh[name]
        mark(a)
        a.attach_to_actor(rotor, '', keep, keep, keep, False)
    rotors.append(rotor)
    rotor_records.append({'label': label, 'hub': hub_name, 'blades': blade_names, 'direction': direction})

base_position = root.get_actor_location()
flight_origin = base_position+unreal.Vector(-1800,0,600)
drone.set_actor_location(flight_origin, False, True)
for name, value in {
    'rotors': rotors, 'target_offset': unreal.Vector(), 'flight_origin': flight_origin,
    'flight_radius': 600.0, 'vertical_amplitude': 150.0, 'period': 24.0,
    'manual_speed': 300.0, 'manual_yaw_rate': 90.0, 'minimum_altitude': ground+120.0,
    'maximum_altitude': ground+5000.0, 'model_heading_offset': -90.0,
    'automatic_flight': True, 'tracking_enabled': True, 'rotors_running': True,
    'rotor_rpm': 600.0, 'field_of_view': 25.0,
}.items():
    demo.set_editor_property(name, value)
demo.camera.set_field_of_view(25.0)
demo.capture.set_editor_property('fov_angle',25.0)
overview = demo.overview
mark(overview)
overview_position = base_position+unreal.Vector(-900,-1800,650)
look_at = base_position+unreal.Vector(-850,0,230)
overview.set_actor_location_and_rotation(overview_position, unreal.MathLibrary.find_look_at_rotation(overview_position,look_at),False,True)
overview.get_component_by_class(unreal.CameraComponent).set_field_of_view(65.0)
unreal.EditorLevelLibrary.set_level_viewport_camera_info(overview_position,unreal.MathLibrary.find_look_at_rotation(overview_position,look_at))

after_drone, after_ptz = bounds(family(drone)), bounds(ptz_group)
drone_size = [after_drone[1][i]-after_drone[0][i] for i in range(3)]
ptz_size = [after_ptz[1][i]-after_ptz[0][i] for i in range(3)]
assert abs(max(drone_size[:2])-60.0)<0.1, drone_size
assert abs(ptz_size[2]-40.0)<0.1, ptz_size
calibration = {
    'base_world_cm': vec(center(actors['bottom'])),
    'yaw_world_cm': vec(demo.yaw_pivot.get_world_location()),
    'pitch_world_cm': vec(demo.pitch_pivot.get_world_location()),
    'optical_world_cm': vec(demo.camera.get_world_location()),
    'optical_forward': vec(demo.camera.get_forward_vector()),
    'drone_bounds_cm': after_drone, 'target_offset_local_cm': [0,0,0],
    'drone_size_cm': drone_size, 'ptz_size_cm': ptz_size,
    'moving_yaw': ['bottom2'], 'moving_yaw_pitch': ['camera','ptz'], 'fixed': ['bottom'],
    'rotors': rotor_records, 'terrain_z_cm': ground,
    'note': 'Demonstration scale: maximum horizontal drone span 60 cm, gimbal height 40 cm. Not manufacturer metrology. Optical center and rotor pivots are geometric approximations.',
}
assert unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True), 'Save failed'
config = Path(unreal.Paths.project_dir())/'Config'/'WISEYE'/'calibration.json'
config.write_text(json.dumps(calibration,indent=2),encoding='utf8')
saved = Path(unreal.Paths.project_saved_dir())/'WISEYE'
saved.mkdir(exist_ok=True)
# verify_demo prefers this file when present; keep it consistent with the saved scene.
(saved/'calibration.json').write_text(json.dumps(calibration,indent=2),encoding='utf8')
(saved/'controls_setup.json').write_text(json.dumps(calibration,indent=2),encoding='utf8')
sub.set_selected_level_actors([demo])
unreal.log('WISEYE controls setup saved: drone 60 cm, gimbal 40 cm, four rotor pivots')

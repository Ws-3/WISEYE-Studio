"""Run inside UE PIE with Avata selected; checks independent original propellers."""
import json, time, traceback
from pathlib import Path
import unreal
ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve().parents[1]
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
demo = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.WiseEyeDemo)[0]
rotors = list(demo.get_editor_property('avata_rotors'))
assert demo.drone_model == 'avata' and len(rotors) == 4
body = demo.alternate_drone_mesh
assert body.static_mesh.get_name() == 'AvataBody'
assert all(r.get_attach_parent() == body for r in rotors)
assert all(r.custom_depth_stencil_value == round(demo.rotor_heat * 255) for r in rotors)
visible_mavic = [c.get_name() for a in [demo.drone] + list(demo.drone.get_attached_actors(recursively_include_attached_actors=True)) for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.static_mesh and c.is_visible() and c != body and c not in rotors and not c.component_has_tag('RotorBlur')]
assert not visible_mavic, visible_mavic
b = body.static_mesh.get_bounds(); s = body.get_world_scale()
size = [b.box_extent.x*2*s.x, b.box_extent.y*2*s.y, b.box_extent.z*2*s.z]
assert max(abs(a-b) for a,b in zip(size, (18,18,8))) < .02, size
anchors = [r.get_editor_property('relative_location').copy() for r in rotors]
rpm = demo.rotor_rpm
demo.rotor_rpm = 137 # Deliberately away from frame-rate harmonics for deterministic sampling.
demo.rotors_running = True
samples = []
stage = 0
last = time.monotonic()
report = dict(passed=False, size_cm=size, visible_mavic=visible_mavic, samples=samples)
def angle(a,b): return (a-b+180)%360-180
def tick(dt):
    global stage,last
    if time.monotonic()-last < .17: return
    last=time.monotonic()
    try:
        if stage == 0: assert all(r.is_visible() for r in rotors)
        yaws=[r.get_editor_property('relative_rotation').yaw for r in rotors]
        phase=demo.rotor_phase
        assert all(max(abs(getattr(r.get_editor_property('relative_location'), k)-getattr(a,k)) for k in ('x','y','z')) < .00001 for r,a in zip(rotors,anchors)), 'shaft moved'
        for i,y in enumerate(yaws):
            assert abs(angle(y,phase*(1 if i in (0,3) else -1))) < .002
        samples.append(dict(stage=stage,phase=phase,yaws=yaws,running=demo.rotors_running))
        if stage in (1,2,6): assert abs(angle(yaws[0],samples[-2]['yaws'][0]))>.01, 'rotor stayed static'
        if stage == 2: demo.rotors_running=False
        if stage in (3,4,5):
            assert max(abs(angle(y,samples[2]['yaws'][i])) for i,y in enumerate(yaws))<.001, 'disabled rotor moved'
        if stage == 5: demo.rotors_running=True
        if stage == 7:
            demo.rotor_rpm=rpm
            report['passed']=True
            (ROOT/'runtime/avata_rotors_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
            pc=unreal.GameplayStatics.get_player_controller(world,0)
            pc.set_view_target_with_blend(demo.drone_view,0)
            demo.drone_view.get_component_by_class(unreal.CameraComponent).set_field_of_view(20)
            unreal.AutomationLibrary.take_high_res_screenshot(1280,720,str(ROOT/'runtime/avata_rotors_running.png'))
            unreal.unregister_slate_post_tick_callback(unreal._avata_validation)
        stage += 1
    except Exception:
        demo.rotor_rpm=rpm;demo.rotors_running=True
        report['error']=traceback.format_exc()
        (ROOT/'runtime/avata_rotors_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
        unreal.unregister_slate_post_tick_callback(unreal._avata_validation)
        unreal.log_error(report['error'])
unreal._avata_validation=unreal.register_slate_post_tick_callback(tick)

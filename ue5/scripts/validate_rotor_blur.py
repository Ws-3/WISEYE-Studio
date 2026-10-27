"""UE PIE: validate the selected model's fast disc, stop and restart appearance."""
import json,time,traceback
from pathlib import Path
import unreal
root=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve().parents[1]
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
demo=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.WiseEyeDemo)[0]
model=demo.drone_model
actors=[demo.drone]+list(demo.drone.get_attached_actors(recursively_include_attached_actors=True))
meshes=[c for a in actors for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.static_mesh]
blurs=[c for c in meshes if c.component_has_tag('RotorBlur') and c.is_visible()]
assert len(blurs)==4,(model,len(blurs))
diameters=[100*c.get_world_scale().x for c in blurs]
assert all(5<d<40 for d in diameters),diameters
assert demo.rotor_rpm==6000,demo.rotor_rpm
assert all(c.get_collision_enabled()==unreal.CollisionEnabled.NO_COLLISION for c in blurs)
assert all(c.custom_depth_stencil_value==round(demo.rotor_heat*255) for c in blurs)
blade_names={'Mesh_ncl_92','Mesh_ncl_94','Mesh_ncl_110','Mesh_ncl_111','Mesh_ncl_119','Mesh_ncl_120','Mesh_ncl_99','Mesh_ncl_100'}
blades=list(demo.get_editor_property('avata_rotors')) if model=='avata' else [c for c in meshes if c.static_mesh.get_name() in blade_names]
assert len(blades)==(4 if model=='avata' else 8),len(blades)
assert all(not c.is_visible() for c in blades)
phase=demo.rotor_phase
demo.rotors_running=False
stage=0
last=time.monotonic()
report=dict(passed=False,model=model,rpm=demo.rotor_rpm,disc_diameters_cm=diameters)
def tick(dt):
    global stage,last
    if time.monotonic()-last < .25:return
    last=time.monotonic()
    try:
        if stage in (0,1):
            assert all(not c.is_visible() for c in blurs)
            assert all(c.is_visible() for c in blades)
            assert abs(demo.rotor_phase-phase)<.001
        if stage==1:demo.rotors_running=True
        if stage==2:
            assert all(c.is_visible() for c in blurs)
            assert all(not c.is_visible() for c in blades)
            report.update(passed=True,stop_restores_blades=True,restart_restores_disc=True)
            unreal.unregister_slate_post_tick_callback(unreal._rotor_blur_validation)
            (root/f'runtime/rotor_blur_{model}.json').write_text(json.dumps(report,indent=2),encoding='utf8')
            pc=unreal.GameplayStatics.get_player_controller(world,0)
            pc.set_view_target_with_blend(demo.drone_view,0)
            demo.drone_view.get_component_by_class(unreal.CameraComponent).set_field_of_view(20 if model=='avata' else 35)
            unreal.AutomationLibrary.take_high_res_screenshot(1280,720,str(root/f'runtime/fast_rotors_{model}.png'))
        stage+=1
    except Exception:
        demo.rotors_running=True
        unreal.unregister_slate_post_tick_callback(unreal._rotor_blur_validation)
        report['error']=traceback.format_exc()
        (root/f'runtime/rotor_blur_{model}.json').write_text(json.dumps(report,indent=2),encoding='utf8')
        unreal.log_error(report['error'])
unreal._rotor_blur_validation=unreal.register_slate_post_tick_callback(tick)

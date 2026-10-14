"""PIE checks and native-resolution captures for visible / synthetic IR sensors."""
import json
import time
from pathlib import Path
import unreal

world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world,'Start PIE first'
demo=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.WiseEyeDemo)[0]
assert demo.thermal_instance, 'IR material missing'
assert (demo.render_target.size_x,demo.render_target.size_y)==(1920,1080)
assert (demo.infrared_target.size_x,demo.infrared_target.size_y)==(640,512)
assert demo.capture.texture_target==demo.render_target
assert demo.infrared_capture.texture_target==demo.infrared_target
assert any(a.get_actor_label()=='WISEYE_TestOccluder' for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.StaticMeshActor)), 'Run prepare_sensor_test.py outside PIE before this test'

saved=Path(unreal.Paths.project_saved_dir())/'WISEYE'
out=saved/'sensors_verification.json'
original={'paused':demo.paused,'fov':demo.field_of_view,'body':demo.body_heat,'noise':demo.thermal_noise}
if not demo.automatic_flight: demo.toggle_flight_mode()
if not demo.tracking_enabled: demo.toggle_tracking()
if not demo.paused: demo.toggle_pause()
demo.reset_simulation()
demo.infrared_mode=False
demo.black_hot=False
demo.thermal_noise=0.0
demo.refresh_sensors()
state={'stage':'visible','at':time.monotonic(),'files':set(saved.rglob('*.png')),'captures':{},'checks':['two native resolutions','two capture targets'],'blocker':None}

def capture(name):
    demo.export_frame()
    fresh=set(saved.rglob('*.png'))-state['files']
    assert len(fresh)==1, str(fresh)
    p=fresh.pop()
    state['files'].add(p)
    state['captures'][name]=str(p.resolve())

def next_stage(name):
    state['checks'].append(state['stage'])
    state['stage']=name
    state['at']=time.monotonic()

def finish(ok,error=None):
    unreal.unregister_slate_post_tick_callback(unreal._wise_sensor_verify)
    if state['blocker']: state['blocker'].destroy_actor()
    demo.body_heat=original['body']
    demo.thermal_noise=original['noise']
    demo.field_of_view=original['fov']
    demo.black_hot=False
    demo.infrared_mode=True
    demo.refresh_sensors()
    if demo.paused: demo.toggle_pause()
    out.write_text(json.dumps({'passed':ok,'error':error,'checks':state['checks'],'captures':state['captures'],'visible_size':[1920,1080],'infrared_size':[640,512],'model':'normalized synthetic heat, not radiometric'},indent=2),encoding='utf8')
    unreal.log('WISEYE sensors verification: '+str(ok)+' '+str(error))

def tick(dt):
    try:
        if time.monotonic()-state['at']<1.5: return
        stage=state['stage']
        a=demo.camera.get_world_location()
        b=demo.infrared_capture.get_world_location()
        assert (a-b).length()<.001, 'Optical mounts differ'
        assert abs(demo.capture.fov_angle-demo.infrared_capture.fov_angle)<.001
        if stage=='visible':
            assert demo.get_sensor_target()==demo.render_target
            assert abs(demo.camera.aspect_ratio-1920/1080)<.001
            capture('visible')
            demo.toggle_sensor_mode()
            assert demo.infrared_mode
            next_stage('white_hot')
        elif stage=='white_hot':
            assert demo.get_sensor_target()==demo.infrared_target
            assert abs(demo.camera.aspect_ratio-640/512)<.001
            capture('white_hot')
            demo.toggle_thermal_palette()
            assert demo.black_hot
            next_stage('black_hot')
        elif stage=='black_hot':
            capture('black_hot')
            demo.toggle_thermal_palette()
            demo.body_heat=.85
            demo.refresh_sensors()
            next_stage('adjusted_heat')
        elif stage=='adjusted_heat':
            capture('adjusted_heat')
            demo.body_heat=original['body']
            demo.refresh_sensors()
            position=(demo.camera.get_world_location()+demo.drone.get_actor_location())*.5
            blocker=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.StaticMeshActor) if a.get_actor_label()=='WISEYE_TestOccluder')
            blocker.set_actor_location(position,False,True)
            blocker.set_actor_hidden_in_game(False)
            state['blocker']=blocker
            next_stage('occlusion')
        elif stage=='occlusion':
            capture('occluded_white_hot')
            state['blocker'].destroy_actor()
            state['blocker']=None
            fov=demo.field_of_view
            demo.zoom_in()
            assert demo.field_of_view==fov-5
            assert demo.capture.fov_angle==demo.infrared_capture.fov_angle==demo.field_of_view
            demo.zoom_out()
            demo.toggle_sensor_mode()
            assert not demo.infrared_mode and demo.get_sensor_target()==demo.render_target
            state['checks']+=['occlusion capture','shared zoom','return to visible','same optical pose','aspect ratios']
            finish(True)
    except Exception as exc:
        finish(False,str(exc))

if hasattr(unreal,'_wise_sensor_verify'):
    try: unreal.unregister_slate_post_tick_callback(unreal._wise_sensor_verify)
    except Exception: pass
unreal._wise_sensor_verify=unreal.register_slate_post_tick_callback(tick)

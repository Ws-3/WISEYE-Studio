"""Live PIE integration check. Leaves the demonstration running after verification."""
import unreal, json, math, time
from pathlib import Path

world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world,'Start Play first'
demo=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.WiseEyeDemo)[0]
actors={a.get_actor_label():a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor)}
out=Path(unreal.Paths.project_saved_dir())/'WISEYE'/'verification.json'
def vector(v): return [v.x,v.y,v.z]
def rotation(v): return [v.pitch,v.yaw,v.roll]
def delta(a,b): return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
def mesh_center(a):
    c=next(c for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.get_editor_property('static_mesh'))
    return vector(unreal.MathLibrary.transform_location(c.get_world_transform(),c.static_mesh.get_bounds().origin))
def snapshot():
    return {'time':demo.simulation_time,'target':vector(demo.drone.get_actor_location()),
            'base':mesh_center(actors['bottom']),'base_rotation':rotation(actors['bottom'].get_actor_rotation()),
            'yaw':demo.yaw_pivot.get_editor_property("relative_rotation").yaw,'pitch':demo.pitch_pivot.get_editor_property("relative_rotation").pitch,
            'error':demo.pointing_error,
            'bottom2_up':vector(actors['bottom2'].get_actor_rotation().get_up_vector()),
            'camera_rotation':rotation(actors['camera'].get_actor_rotation()),
            'ptz_rotation':rotation(actors['ptz'].get_actor_rotation())}

if demo.paused: demo.toggle_pause()
demo.reset_simulation()
initial=snapshot()
calibration=out.parent/'calibration.json'
if not calibration.exists():
    calibration=Path(unreal.Paths.project_dir())/'Config'/'WISEYE'/'calibration.json'
cal=json.loads(calibration.read_text(encoding='utf-8'))
state={'start':time.monotonic(),'samples':[],'last_sample':-1,'paused_at':None,'pause_checked':False,'exports':0}
def finish(ok,error=None):
    unreal.unregister_slate_post_tick_callback(unreal._wise_verify_handle)
    if demo.paused: demo.toggle_pause()
    report={'passed':ok,'error':error,'initial':initial,'samples':state['samples'],
            'max_pointing_error_deg':max([s['error'] for s in state['samples']] or [0]),
            'checks':['fixed base and corrected root','bottom2 yaw only','camera and ptz move together',
                      'drone moves','yaw/pitch rate limits','pause/resume','FOV controls','reset','PNG export invoked']}
    out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.log('WISEYE verification: '+str(ok)+' '+str(error))

def tick(dt):
    try:
        elapsed=time.monotonic()-state['start']
        s=snapshot()
        assert delta(s['base'],cal['base_world_cm'])<.1, 'Saved base position differs from calibrated base'
        assert delta(s['base'],initial['base'])<.01,'Fixed base moved'
        assert delta(s['base_rotation'],initial['base_rotation'])<.001,'Fixed base rotated'
        assert delta(s['bottom2_up'],[0,0,1])<.0001,'bottom2 tilted'
        assert delta(s['camera_rotation'],s['ptz_rotation'])<.001,'camera and ptz separated'
        assert demo.min_pitch-.01<=s['pitch']<=demo.max_pitch+.01,'Pitch limit violated'
        if s['time']-state['last_sample']>=.5:
            if state['samples']:
                previous=state['samples'][-1]
                ds=s['time']-previous['time']
                assert abs((s['yaw']-previous['yaw']+180)%360-180)<=demo.yaw_rate*ds+.1,'Yaw rate limit violated'
                assert abs(s['pitch']-previous['pitch'])<=demo.pitch_rate*ds+.1,'Pitch rate limit violated'
            state['samples'].append(s)
            state['last_sample']=s['time']
        if s['time']>3 and state['exports']==0:
            assert delta(s['target'],initial['target'])>100,'Drone did not move'
            demo.export_frame(); state['exports']=1
        if s['time']>20 and state['exports']==1:
            demo.export_frame(); state['exports']=2
        if s['time']>24 and state['paused_at'] is None:
            demo.toggle_pause(); state['paused_at']=elapsed; state['paused_snapshot']=s
        if state['paused_at'] is not None and not state['pause_checked'] and elapsed-state['paused_at']>1:
            assert abs(s['time']-state['paused_snapshot']['time'])<.0001,'Pause did not stop time'
            assert delta(s['target'],state['paused_snapshot']['target'])<.001,'Pause did not stop drone'
            fov=demo.field_of_view
            demo.zoom_in(); assert demo.field_of_view==fov-5
            demo.zoom_out(); assert demo.field_of_view==fov
            demo.toggle_pause(); state['pause_checked']=True
        if s['time']>=40:
            assert state['pause_checked']
            assert max(x['yaw'] for x in state['samples'])-min(x['yaw'] for x in state['samples'])>10
            assert max(x['pitch'] for x in state['samples'])-min(x['pitch'] for x in state['samples'])>5
            demo.reset_simulation(); assert demo.simulation_time==0
            finish(True)
        elif elapsed>120:
            raise AssertionError('Timed out before a full trajectory cycle')
    except Exception as e:
        finish(False,str(e))

if hasattr(unreal,'_wise_verify_handle'):
    try: unreal.unregister_slate_post_tick_callback(unreal._wise_verify_handle)
    except Exception: pass
unreal._wise_verify_handle=unreal.register_slate_post_tick_callback(tick)
RESULT='Verification running for 40 simulation seconds'

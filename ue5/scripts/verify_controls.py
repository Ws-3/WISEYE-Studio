"""PIE checks for flight modes, rotor pivots, gimbal hold and scaled layout.

Run after verify_demo finishes. Leaves automatic flight/tracking/rotors enabled.
"""
import json
import math
import time
from pathlib import Path
import unreal

world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world, 'Start Play first'
demo=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.WiseEyeDemo)[0]
actors={a.get_actor_label():a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor)}
cal=json.loads((Path(unreal.Paths.project_dir())/'Config/WISEYE/calibration.json').read_text(encoding='utf8'))
out=Path(unreal.Paths.project_saved_dir())/'WISEYE/controls_verification.json'
assert len(demo.rotors)==4
assert all(abs(a-b)<.1 for a,b in zip(cal['mavic_body_size_cm'], (34.75,28.3,10.77)))
assert abs(cal['ptz_size_cm'][2]-80)<.1
assert all(len(r.get_attached_actors())==3 for r in demo.rotors), 'Each rotor needs hub and two blades'

def v(p): return [p.x,p.y,p.z]
def distance(a,b): return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
def xyz(): return v(demo.drone.get_actor_location())
def angles():
    return [demo.yaw_pivot.get_editor_property('relative_rotation').yaw,demo.pitch_pivot.get_editor_property('relative_rotation').pitch]
def phase(): return demo.rotor_phase
def seconds(): return unreal.GameplayStatics.get_time_seconds(world)
def radial():
    values=[]
    for root in demo.rotors:
        for child in root.get_attached_actors():
            c=next(c for c in child.get_components_by_class(unreal.StaticMeshComponent) if c.static_mesh)
            center=unreal.MathLibrary.transform_location(c.get_world_transform(),c.static_mesh.get_bounds().origin)
            values.append(distance(v(center),v(root.get_actor_location())))
    return values
def root_positions():
    return [v(r.get_editor_property('root_component').get_editor_property('relative_location')) for r in demo.rotors]

if demo.paused: demo.toggle_pause()
if not demo.automatic_flight: demo.toggle_flight_mode()
if not demo.tracking_enabled: demo.toggle_tracking()
if not demo.rotors_running: demo.toggle_rotors()
demo.reset_simulation()
original_limits=[demo.minimum_altitude,demo.maximum_altitude]
state={'stage':'auto','at':seconds(),'pos':xyz(),'phase':phase(),'radial':radial(),'roots':root_positions(),'checks':[],'start':time.monotonic()}
samples=[]

def advance(stage):
    state['checks'].append(state['stage'])
    state.update(stage=stage,at=seconds(),pos=xyz(),angles=angles(),phase=phase())

def finish(passed,error=None):
    unreal.unregister_slate_post_tick_callback(unreal._wise_controls_verify)
    demo.set_manual_input(0,0,0,0)
    demo.minimum_altitude,demo.maximum_altitude=original_limits
    if demo.paused: demo.toggle_pause()
    if not demo.automatic_flight: demo.toggle_flight_mode()
    if not demo.tracking_enabled: demo.toggle_tracking()
    if not demo.rotors_running: demo.toggle_rotors()
    demo.reset_simulation()
    out.write_text(json.dumps({'passed':passed,'error':error,'checks':state['checks'],'drone_size_cm':cal['drone_size_cm'],'ptz_size_cm':cal['ptz_size_cm'],'samples':samples},indent=2),encoding='utf8')
    unreal.log('WISEYE controls verification: '+str(passed)+' '+str(error))

def tick(dt):
    try:
        age=seconds()-state['at']
        stage=state['stage']
        assert time.monotonic()-state['start']<90, 'Controls check timed out'
        assert max(abs(x-y) for x,y in zip(radial(),state['radial']))<.05, 'Rotor geometry moved away from pivot'
        assert all(distance(x,y)<.001 for x,y in zip(root_positions(),state['roots'])), 'Rotor mounting position drifted'
        assert demo.min_pitch-.01<=angles()[1]<=demo.max_pitch+.01
        if age<1.0: return
        samples.append({'stage':stage,'position':xyz(),'angles':angles(),'rotor_phase':phase(),'world_time':seconds()})
        if stage=='auto':
            assert distance(xyz(),state['pos'])>20, 'Automatic flight did not move'
            assert abs(phase()-state['phase'])>.01, 'Rotors did not rotate'
            demo.toggle_tracking()
            advance('hold')
        elif stage=='hold':
            assert distance(xyz(),state['pos'])>20, 'Gimbal hold stopped the drone'
            assert distance(angles(),state['angles'])<.001, 'Held gimbal moved'
            demo.toggle_rotors()
            advance('rotors_off')
        elif stage=='rotors_off':
            assert abs(phase()-state['phase'])<.001, 'Stopped rotors kept spinning'
            assert distance(xyz(),state['pos'])>20, 'Rotor visual toggle stopped flight'
            before=xyz()
            demo.toggle_flight_mode()
            assert distance(xyz(),before)<.001, 'Manual mode teleported drone'
            demo.set_manual_input(1,1,0,0)
            advance('manual_diagonal')
        elif stage=='manual_diagonal':
            travel=distance(xyz(),state['pos'])
            assert abs(travel-demo.manual_speed*age)<3, 'Diagonal flight speed not normalized'
            assert distance(angles(),state['angles'])<.001, 'Manual flight changed held gimbal'
            demo.set_manual_input(0,0,1,1)
            state['yaw']=demo.drone.get_actor_rotation().yaw
            advance('manual_altitude_yaw')
        elif stage=='manual_altitude_yaw':
            assert xyz()[2]-state['pos'][2]>100, 'Manual climb failed'
            yaw=demo.drone.get_actor_rotation().yaw
            assert abs((yaw-state['yaw']+180)%360-180)>30, 'Manual yaw failed'
            demo.set_manual_input(0,0,0,0)
            advance('hover')
        elif stage=='hover':
            assert distance(xyz(),state['pos'])<.001, 'Manual hover drifted'
            demo.minimum_altitude=xyz()[2]-10
            demo.maximum_altitude=xyz()[2]+10
            demo.set_manual_input(0,0,1,0)
            advance('ceiling')
        elif stage=='ceiling':
            assert abs(xyz()[2]-demo.maximum_altitude)<.01, 'Altitude ceiling failed'
            demo.set_manual_input(0,0,-1,0)
            advance('floor')
        elif stage=='floor':
            assert abs(xyz()[2]-demo.minimum_altitude)<.01, 'Altitude floor failed'
            demo.minimum_altitude,demo.maximum_altitude=original_limits
            before=xyz()
            demo.toggle_flight_mode()
            assert distance(xyz(),before)<.001, 'Auto resume teleported drone'
            demo.toggle_tracking()
            demo.toggle_rotors()
            advance('resume_auto_tracking')
        elif stage=='resume_auto_tracking':
            assert distance(xyz(),state['pos'])>20, 'Resumed auto flight stopped'
            assert distance(angles(),state['angles'])>.1, 'Tracking did not resume'
            assert abs(phase()-state['phase'])>.01
            demo.toggle_pause()
            advance('pause')
        elif stage=='pause':
            assert distance(xyz(),state['pos'])<.001
            assert distance(angles(),state['angles'])<.001
            assert abs(phase()-state['phase'])<.001
            demo.toggle_pause()
            demo.reset_simulation()
            assert demo.simulation_time==0
            assert distance(xyz(),v(demo.flight_origin))<.001
            pc=unreal.GameplayStatics.get_player_controller(world,0)
            demo.switch_view(); assert pc.get_view_target()==demo
            demo.switch_view(); assert pc.get_view_target()==demo.drone_view
            demo.switch_view(); assert pc.get_view_target()==demo.overview
            state['checks']+=['pause','reset','three_camera_views','scale','four_rotor_pivots']
            finish(True)
    except Exception as exc:
        finish(False,str(exc))

if hasattr(unreal,'_wise_controls_verify'):
    try: unreal.unregister_slate_post_tick_callback(unreal._wise_controls_verify)
    except Exception: pass
unreal._wise_controls_verify=unreal.register_slate_post_tick_callback(tick)

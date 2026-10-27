"""Real UE/AirSim/Qt verification; preserves fleet layout and lands test aircraft."""
import json
import math
import socket
import time
from pathlib import Path
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from unittest.mock import patch
from core.config import AppConfig,ROOT
from apps.desktop_app.main_window import MainWindow
from integrations.gimbal_client import GimbalClient

app=QApplication([])
checks=[]
evidence=dict(checks=checks,flights=[])
window=None
airborne=[]


def rpc(command,payload=None,port=50051):
    with socket.create_connection(('127.0.0.1',port),5) as peer:
        peer.sendall((json.dumps(dict(version=1,request_id=f'rt-{time.time_ns()}',command=command,payload=payload or {}))+'\n').encode())
        response=json.loads(peer.makefile('rb').readline(16*1024*1024))
    assert response['status']=='ok',response
    return response['payload']


def wait(predicate,timeout=30):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        app.processEvents()
        if predicate():return
        time.sleep(.08)
    raise AssertionError('Timed out waiting for runtime condition')


def passed(message):
    checks.append(message)
    print('PASS '+message,flush=True)


def air(ident):return rpc('sim.get_state',dict(device_id=ident),50052)
def command(ident,name,**args):return rpc(name,dict(args,device_id=ident),50052)


original=rpc('sim.get_state')
gimbals=[d['id'] for d in original['devices'] if d['kind']=='gimbal']
saved={ident:rpc('sim.get_state',dict(device_id=ident)) for ident in gimbals}
try:
    assert original['performance_profile']=='balanced'
    for profile,rates in [('quality',(30,25,15)),('economy',(10,10,8)),('balanced',(20,15,10))]:
        state=rpc('sim.set_performance_profile',dict(profile=profile))
        assert tuple(state[k] for k in ('visible_capture_hz','infrared_capture_hz','observer_capture_hz'))==rates
    passed('three performance profiles report their native capture-rate budgets')
    target=gimbals[-1]
    sdk=GimbalClient(target)
    caps=sdk.capabilities()
    assert caps['input_watchdog_ms']==300 and caps['yaw_rate_deg_s']==30
    sdk.take_control();sdk.set_angles(10,5)
    other_before={ident:rpc('sim.get_state',dict(device_id=ident))['yaw_deg'] for ident in gimbals if ident!=target}
    started=time.monotonic()
    for _ in range(10):sdk.set_velocity(10);time.sleep(.1);app.processEvents()
    sdk.stop()
    elapsed=time.monotonic()-started
    yaw=sdk.state()['yaw_deg']
    observed_rate=(yaw-10)/elapsed
    assert 6<observed_rate<13,(yaw,elapsed,observed_rate)
    evidence['gimbal_observed_yaw_deg_s']=observed_rate
    sdk.set_velocity(10);time.sleep(.6)
    stopped=sdk.state()['yaw_deg'];time.sleep(.5)
    assert abs(sdk.state()['yaw_deg']-stopped)<.1
    for ident,before in other_before.items():
        # Tracking may move while the native drone settles; compare only held gimbals.
        if not saved[ident]['tracking']:assert abs(rpc('sim.get_state',dict(device_id=ident))['yaw_deg']-before)<.1
    passed('external gimbal SDK: capabilities, angles, rate control and 300 ms deadman stop')
    aircraft=[d for d in original['devices'] if d['kind']=='drone']
    assert all(air(d['id'])['flight_status']=='ready' for d in aircraft),'Test requires landed aircraft'
    for device in aircraft[:2]:
        ident=device['id']
        ground=air(ident)
        assert max(ground['motor_rpm'])<1
        command(ident,'flight.takeoff');airborne.append(ident)
        wait(lambda:not air(ident)['command_active'],45)
        # Takeoff completion precedes motor/controller settling. Compare live
        # samples after the asynchronous visual bridge has caught up.
        def motor_bridge_matches():
            native=air(ident)
            rendered=rpc('sim.get_state',dict(device_id=ident))
            return (rendered['rotor_telemetry_fresh'] and
                    abs(sum(native['motor_rpm'])/4-rendered['rotor_rpm'])<100 and
                    min(native['motor_rpm'])>1000)
        wait(motor_bridge_matches,15)
        hover=air(ident)
        assert ground['position_ned_m'][2]-hover['position_ned_m'][2]>1
        assert all(1000<v<6500 for v in hover['motor_rpm']),hover
        wait(lambda:rpc('sim.get_state',dict(device_id=ident))['rotor_telemetry_fresh'])
        visual=rpc('sim.get_state',dict(device_id=ident))
        assert visual['rotor_source']=='airsim_rad_s' and visual['rotors_running']
        assert abs(sum(hover['motor_rpm'])/4-visual['rotor_rpm'])<250
        assert all(air(d['id'])['flight_status']=='ready' for d in aircraft if d['id']!=ident)
        command(ident,'flight.land')
        wait(lambda:air(ident)['flight_status']=='ready',45)
        wait(lambda:max(air(ident)['motor_rpm'])<1,15)
        wait(lambda:not rpc('sim.get_state',dict(device_id=ident))['rotors_running'])
        airborne.remove(ident)
        evidence['flights'].append(dict(device_id=ident,model=device['model_id'],ground_rpm=ground['motor_rpm'],hover_rpm=hover['motor_rpm'],visual_rpm=visual['motor_rpm'],landed_rpm=air(ident)['motor_rpm']))
        passed(f'{ident}: actual motor telemetry drives ground / takeoff / hover / landed visuals')
    window=MainWindow(AppConfig.load());window.resize(1600,1000);window.show();window.connect_ue()
    wait(lambda:window.client.ready and window.air_client.ready and window.simulation_healthy)
    wait(lambda:all(k in window.gallery.frames for k in ('ptz-01/visible','ptz-01/infrared','scene/observer')),45)
    assert not window.rotors_button.isEnabled()
    window.health.advanced=time.monotonic()-10;window.check_health()
    assert not window.simulation_healthy and '推进' in window.health_label.text()
    with patch.object(window.air_client,'request') as request:
        window.command('flight.takeoff');request.assert_not_called()
    window.apply_state(rpc('sim.get_state'))
    wait(lambda:window.simulation_healthy)
    passed('desktop displays streams; injected progress stall is visible and blocks new takeoff')
    for ident in gimbals:
        for channel,shape in [('CH1',(1920,1080)),('CH2',(640,512))]:
            frame=rpc('camera.stream_frame',dict(device_id=ident,channel=channel))
            assert (frame['width'],frame['height'])==shape
    passed('all gimbal video sources retain 1920x1080 / 640x512 dimensions')
    window.grab().save(str(ROOT/'docs/evidence/runtime_controls_ui_v3_20261021.png'))
    evidence['passed']=True
finally:
    for ident in airborne:
        try:
            command(ident,'flight.land');wait(lambda:air(ident)['flight_status']=='ready',50)
        except Exception as error:print('Cleanup landing failed:',ident,error,flush=True)
    for ident,state in saved.items():
        sdk=GimbalClient(ident);sdk.stop();sdk.set_angles(state['yaw_deg'],state['pitch_deg'])
        sdk.request('gimbal.set_target',drone_id=state['tracking_target'])
        sdk.request('gimbal.set_tracking',enabled=state['tracking'])
    rpc('input.set_mode',dict(mode=original['input_mode']))
    rpc('sim.set_performance_profile',dict(profile='balanced'))
    if window:window.close()
    (ROOT/'docs/evidence/runtime_controls_ui_v3_20261021.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')

"""Two real AirSim robots and two independently addressed UE PTZ assemblies."""
import copy,json,math,socket,time
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from core.config import AppConfig,ROOT
from apps.desktop_app.main_window import MainWindow
from apps.desktop_app.device_manager import DeviceManager

checks=[]
def rpc(command,payload=None,port=50051,ok=True):
    with socket.create_connection(('127.0.0.1',port),timeout=4) as peer:
        peer.sendall((json.dumps(dict(version=1,request_id=f'fleet-{time.time_ns()}',command=command,payload=payload or {}))+chr(10)).encode())
        result=json.loads(peer.makefile('rb').readline(16*1024*1024))
    if ok:assert result['status']=='ok',result
    return result['payload'] if ok else result
def state(ident):return rpc('sim.get_state',dict(device_id=ident),50052 if ident.startswith('uav') else 50051)
def control(ident,command,**payload):return rpc(command,dict(payload,device_id=ident),50052 if ident.startswith('uav') else 50051)
def wait(predicate,timeout=25):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if app:app.processEvents()
        try:
            if predicate():return
        except (OSError,ValueError):pass
        time.sleep(.1)
    raise AssertionError('Timed out waiting for fleet state')
def passed(message):checks.append(message);print('PASS '+message,flush=True)
app=None;window=None
try:
    wait(lambda:len(rpc('sim.get_state')['devices'])==4,180)
    wait(lambda:len(state('uav-01').get('fleet',[]))==2,90)
    inventory=rpc('sim.get_state')['devices'];assert {d['id'] for d in inventory}=={'uav-01','uav-02','ptz-01','ptz-02'}
    manifest=json.loads((ROOT/'ue5/WISEYE/Config/WISEYE/Fleets/original.json').read_text(encoding='utf-8-sig'))
    for d in inventory:
        if d['kind']=='gimbal':assert math.dist(d['position_cm'],next(i['position_cm'] for i in manifest['devices'] if i['id']==d['id']))<.1
    assert state('uav-01')['flight_status']==state('uav-02')['flight_status']=='ready'
    passed('two PTZ instances and two actual AirSim robots start ready')
    for port in (50051,50052):assert rpc('flight.takeoff',dict(device_id='uav-99'),port,False)['status']=='error'
    passed('unknown instance IDs rejected instead of falling back')
    for ident,yaw in [('ptz-01',0),('ptz-02',35)]:control(ident,'gimbal.set_angles',yaw_deg=yaw,pitch_deg=5)
    assert abs(state('ptz-01')['yaw_deg'])<.1 and abs(state('ptz-02')['yaw_deg']-35)<.1
    control('ptz-02','gimbal.set_target',drone_id='uav-01');assert state('ptz-01')['tracking_target']=='uav-01';assert state('ptz-02')['tracking_target']=='uav-01'
    control('ptz-02','gimbal.set_target',drone_id='uav-02')
    passed('gimbal directions and tracking targets are independent')
    vis1=copy.deepcopy(state('ptz-01')['sensors']['visible']);vis2=copy.deepcopy(state('ptz-02')['sensors']['visible'])
    control('ptz-02','sensor.configure',sensor='visible',enabled=False,fov_deg=47)
    assert state('ptz-01')['sensors']['visible']==vis1
    assert rpc('camera.stream_frame',dict(channel='CH1',device_id='ptz-02'),ok=False)['status']=='error'
    assert rpc('camera.stream_frame',dict(channel='CH1',device_id='ptz-01'))['width']==1920
    control('ptz-02','sensor.configure',sensor='visible',**vis2)
    passed('sensor parameters, enable state and frame sources do not cross instances')
    for ident in ('ptz-01','ptz-02'):
        for sensor,shape in [('visible',(1920,1080)),('infrared',(640,512))]:
            frame=control(ident,'camera.capture',sensor=sensor)
            from pathlib import Path
            meta=json.loads(Path(frame['frame_path']+'.json').read_text(encoding='utf-8-sig'))
            assert meta['device_id']==ident and meta['sensor_id']==ident+'/'+sensor
            assert (frame['frame_width'],frame['frame_height'])==shape
    passed('native image exports carry device/sensor identity and preserve per-modality resolutions')
    app=QApplication([]);window=MainWindow(AppConfig.load());window.resize(1540,1040);window.show();window.connect_ue()
    wait(lambda:window.client.ready and window.air_client.ready)
    assert window.fleet_selection.drone.count()==window.fleet_selection.gimbal.count()==2
    window.fleet_selection.select('gimbal','ptz-02');wait(lambda:window.state.get('gimbal_id')=='ptz-02' and 'ptz-02/CH1' in window.video_client.url)
    wait(lambda:'CH1' in window.gallery.frames and 'CH2' in window.gallery.frames,40)
    assert window.client.device_id=='ptz-02'
    window.fov.setValue(61);window.sensor_settings.submit('visible');wait(lambda:not window.sensor_settings.pending)
    assert state('ptz-02')['sensors']['visible']['fov_deg']==61 and state('ptz-01')['sensors']['visible']['fov_deg']==vis1['fov_deg']
    control('ptz-02','sensor.configure',sensor='visible',**vis2)
    window.fleet_selection.select('drone','uav-02');wait(lambda:window.air_state.get('drone_id')=='uav-02')
    passed('desktop selects drone and gimbal separately; selected PTZ gets its own RTSP and settings')
    manager=DeviceManager(window);before=len(manager.data['devices']);manager.add('drone');assert len(manager.collect()['devices'])==before+1
    manager.remove();assert len(manager.collect()['devices'])==before;manager.close()
    passed('device draft editor adds and removes whole instances without moving runtime objects')
    ground1=state('uav-01')['position_ned_m'];control('uav-02','flight.takeoff');wait(lambda:not state('uav-02')['command_active'],40)
    assert state('uav-01')['flight_status']=='ready' and math.dist(ground1,state('uav-01')['position_ned_m'])<.1
    p2=state('uav-02')['position_ned_m'];control('uav-02','flight.set_mode',mode='manual');wait(lambda:not state('uav-02')['command_active'])
    control('uav-02','flight.set_input',forward=1,right=0,up=0,yaw=0);time.sleep(.5);control('uav-02','flight.set_input',forward=0,right=0,up=0,yaw=0);wait(lambda:not state('uav-02')['command_active'])
    assert math.dist(p2,state('uav-02')['position_ned_m'])>.1
    assert math.dist(ground1,state('uav-01')['position_ned_m'])<.1
    passed('only addressed UAV takes off and flies manually; other UAV remains grounded')
    control('uav-01','flight.takeoff');wait(lambda:not state('uav-01')['command_active'],40)
    routes={}
    for ident,axis in [('uav-01',0),('uav-02',1)]:
        control(ident,'flight.hover');wait(lambda:not state(ident)['command_active'])
        p=state(ident)['position_ned_m'];start=[p[0],p[1],-p[2]];end=start[:];end[axis]+=1.5
        route=dict(version=1,scene_id='original',frame='ue_world_m',name=ident+' route',speed_mps=1,repeat=False,waypoints=[start,end]);routes[ident]=route;control(ident,'route.upload',**route)
    control('uav-01','route.start');control('uav-02','route.start')
    wait(lambda:all(state(i)['route_status']=='completed' for i in routes),65)
    for ident,route in routes.items():
        p=state(ident)['position_ned_m'];assert math.dist([p[0],p[1],-p[2]],route['waypoints'][-1])<1.3
        assert state(ident)['route']['name']==ident+' route'
    passed('two UAVs execute different routes concurrently and hold at separate destinations')
    for ident in ('uav-01','uav-02'):control(ident,'flight.land')
    wait(lambda:all(state(i)['flight_status']=='ready' for i in routes),45)
    for ident in ('ptz-01','ptz-02'):control(ident,'gimbal.set_tracking',enabled=True)
    old=window.state['run_id'];window.switch_scene()
    wait(lambda:window.client.ready and window.state.get('run_id') not in (None,old),60)
    wait(lambda:window.air_client.ready and len(window.air_state.get('fleet',[]))==2 and all(s['flight_status']=='ready' for s in window.air_state['fleet']),60)
    wait(lambda:'CH1' in window.gallery.frames,40)
    passed('same-scene reload recreates both robot/gimbal instances and restores fresh sessions')
    window.grab().save(str(ROOT/'docs/evidence/fleet_20261021.png'))
    report=dict(passed=len(checks),checks=checks,inventory=inventory,final_fleet=window.air_state.get('fleet',[]))
    (ROOT/'docs/evidence/fleet_20261021.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(dict(passed=len(checks)),ensure_ascii=False),flush=True)
finally:
    if window:window.close();app.processEvents()

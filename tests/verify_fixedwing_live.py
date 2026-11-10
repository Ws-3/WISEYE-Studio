"""Owned isolated fixed-wing cruise, manual control, sensors and exit checks."""
import json, os, time, math, base64
from pathlib import Path


def main():
    assert 'fixedwing-test-data' in os.environ.get('WISEYE_DATA_DIR','')
    import apps.desktop_app.main
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    from core.config import AppConfig
    from core.local_rpc import request
    from apps.desktop_app.main_window import MainWindow
    out=Path('builds/fixedwing-live');out.mkdir(exist_ok=True)
    app=QApplication([])
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,str(out/'qt'))
    w=MainWindow(AppConfig.load());w.show();report={'passed':False}
    def settle(n):
        end=time.monotonic()+n
        while time.monotonic()<end:app.processEvents();time.sleep(.02)
    def wait(predicate,n=90):
        end=time.monotonic()+n
        while time.monotonic()<end:
            app.processEvents()
            if predicate():return
            time.sleep(.1)
        raise TimeoutError('Fixed-wing acceptance timeout')
    def rpc(command,port=50051,**payload):
        reply=request(port,command,payload,timeout=5)
        assert reply['status']=='ok',reply
        return reply['payload']
    try:
        w.launch_ue();wait(lambda:w.client.ready and w.air_client.ready,600);settle(2)
        s=rpc('sim.get_state');run=s['run_id'];report['run_id']=run
        geometry=next(d['fixedwing'] for d in s['devices'] if d['id']=='uav-01')
        assert abs(geometry['length_cm']-80)<.1,geometry
        report['geometry']=geometry
        fw=rpc('sim.get_state',50052,device_id='uav-01')
        assert fw['airframe']=='fixedwing' and fw['flight_status']=='ready',fw
        assert not fw['motor_rpm'],fw
        rpc('flight.takeoff',50052,device_id='uav-01');settle(2)
        a=rpc('sim.get_state',50052,device_id='uav-01');settle(2)
        b=rpc('sim.get_state',50052,device_id='uav-01')
        distance=math.dist(a['position_ned_m'],b['position_ned_m'])
        assert distance>15,(distance,a,b)
        report['cruise_displacement_m']=distance
        rpc('flight.set_mode',50052,device_id='uav-01',mode='manual')
        yaw=b['yaw_deg']
        for _ in range(12):
            rpc('flight.set_input',50052,device_id='uav-01',forward=1,right=1,up=1,yaw=0);settle(.12)
            manual=rpc('sim.get_state',50052,device_id='uav-01')
            assert abs(manual['roll_deg'])<=30.1 and manual['velocity_mps']<=15
        rpc('flight.set_input',50052,device_id='uav-01',forward=0,right=0,up=0,yaw=0);settle(.2)
        c=rpc('sim.get_state',50052,device_id='uav-01')
        assert abs((c['yaw_deg']-yaw+180)%360-180)>5
        assert c['position_ned_m'][2]<b['position_ned_m'][2]-1
        report['manual_state']=c
        rpc('flight.hover',50052,device_id='uav-01');settle(1)
        x,y,z=c['position_ned_m'];z=-z
        route=dict(version=1,scene_id='city',name='Fixed-wing acceptance',frame='ue_world_m',speed_mps=12,repeat=False,
                   waypoints=[[x+120,y+120,z],[x+240,y+120,z]])
        rpc('route.upload',50052,device_id='uav-01',**route)
        rpc('route.start',50052,device_id='uav-01');settle(2)
        assert rpc('sim.get_state',50052,device_id='uav-01')['route_status']=='running'
        rpc('gimbal.set_target',device_id='ptz-01',drone_id='uav-01')
        rpc('gimbal.set_tracking',device_id='ptz-01',enabled=True);settle(3)
        for sensor in ('visible','infrared'):
            options={}
            if sensor=='infrared':
                old=rpc('sim.get_state')['sensors'][sensor]
                options=dict(palette=old['palette'],noise=old['noise'])
            rpc('sensor.configure',device_id='ptz-01',sensor=sensor,enabled=True,fov_deg=5,**options)
        settle(2)
        for channel,name in [('CH1','visible'),('CH2','infrared')]:
            packet=rpc('camera.stream_frame',device_id='ptz-01',channel=channel)
            (out/(name+'.jpg')).write_bytes(base64.b64decode(packet['image_base64']))
        from training_client.client import Client, save_pair
        training=Client(device='ptz-01')
        training.configure(max_fps=2)
        pair=training.sample_pair()
        for sensor,packet in pair['samples'].items():
            assert any(o.get('model_id')=='fixedwing' for o in packet['objects']),packet['objects']
        save_pair(pair,out/'dataset')
        report['paired_gt_models']={sensor:[o['model_id'] for o in packet['objects']] for sensor,packet in pair['samples'].items()}
        rpc('observer.set_mode',mode='follow');settle(2)
        packet=rpc('camera.stream_frame',device_id='ptz-01',channel='OBS')
        (out/'fixedwing-follow.jpg').write_bytes(base64.b64decode(packet['image_base64']))
        from apps.desktop_app.language import manager
        manager().select('en_US');settle(.7)
        assert w.client.ready and w.air_client.ready
        assert w.drone_model.currentData()=='fixedwing'
        w.grab().save(str(out/'workbench-english.png'))
        manager().select('zh_CN')
        report['live_language_switch_kept_connection']=True
        w.grab().save(str(out/'workbench.png'))
        report['state']=rpc('sim.get_state')
        rpc('flight.land',50052,device_id='uav-01');settle(.5)
        a=rpc('sim.get_state',50052,device_id='uav-01');settle(.6)
        b=rpc('sim.get_state',50052,device_id='uav-01')
        assert a['flight_status']=='ready' and math.dist(a['position_ned_m'],b['position_ned_m'])<.001
        report['stop_ready']=True
        reply=request(50051,'flight.fixedwing',dict(device_id='uav-01',action='start',run_id='stale'),timeout=5)
        assert reply['status']=='error'
        fleet=rpc('sim.get_state',50052).get('fleet',[])
        if any(d['drone_id']=='uav-02' for d in fleet):
            rpc('flight.takeoff',50052,device_id='uav-02')
            wait(lambda:not rpc('sim.get_state',50052,device_id='uav-02')['command_active'])
            assert rpc('sim.get_state',50052,device_id='uav-02')['flight_status']=='active'
            rpc('flight.land',50052,device_id='uav-02')
            wait(lambda:rpc('sim.get_state',50052,device_id='uav-02')['flight_status']=='ready')
            report['mixed_avata_takeoff_land']=True
        report['stale_session_rejected']=True;report['passed']=True
    finally:
        w.close()
        if hasattr(w,'runtime_manager'):wait(lambda:not w.runtime_manager.running,90)
        report['owned_session_stopped']=True
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        app.quit()


if __name__=='__main__':main()

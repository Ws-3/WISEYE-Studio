"""Explicit owned preview acceptance; separate data, one drone, no source edits."""
import argparse
import base64
import json
import time
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--seconds',type=int,default=90)
    parser.add_argument('--switch-timeout',type=int,default=180)
    parser.add_argument('--scene',choices=('city','city_large'),default='city_large')
    parser.add_argument('--probe-layout',action='store_true',help='Probe runtime road surfaces only; never take off')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    import apps.desktop_app.main
    from PySide6.QtWidgets import QApplication
    from core.config import AppConfig
    from core.local_rpc import request
    from apps.desktop_app.main_window import MainWindow
    app=QApplication([]);window=MainWindow(AppConfig.load());window.show()
    report=dict(passed=False,scene_id=args.scene,samples=[],limits='Short editor-game test with native GUI, not Shipping, full-map traversal or a long-run guarantee')
    airborne=False;run=None
    def settle(seconds=.2):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:app.processEvents();time.sleep(.02)
    def rpc(port,command,**payload):
        result=request(port,command,payload)
        assert result['status']=='ok',result
        return result['payload']
    def wait(predicate,seconds=60):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            app.processEvents()
            try:
                if predicate():return
            except (OSError,ValueError):pass
            time.sleep(.2)
        raise TimeoutError('Big City live acceptance timed out')
    def capture(name):
        import io
        from PIL import Image
        for channel in ('visible','infrared','observer'):
            packet=rpc(50051,'camera.stream_frame',channel=dict(visible='CH1',infrared='CH2',observer='OBS')[channel],device_id='ptz-01')
            content=base64.b64decode(packet['image_base64'])
            size=Image.open(io.BytesIO(content)).size
            assert size==dict(visible=(1920,1080),infrared=(640,512),observer=(960,540))[channel],(channel,size)
            (args.output/f'{name}-{channel}.jpg').write_bytes(content)
    try:
        for i in range(window.scenes.count()):
            if (window.scenes.itemData(i) or {}).get('id')==args.scene:
                window.scenes.setCurrentIndex(i);break
        else:raise AssertionError('Test scene not discoverable')
        started=time.monotonic();window.launch_ue()
        wait(lambda:window.client.ready and window.air_client.ready,600)
        report['startup_seconds']=time.monotonic()-started
        state=rpc(50051,'sim.get_state');run=state['run_id'];report['initial_state']=state
        assert state['scene_id']==args.scene and state['performance_profile']=='economy'
        if args.scene=='city_large':
            assert state['world_streaming_ready'] and state['device_streaming_sources']==2
        assert len([d for d in state['devices'] if d['kind']=='drone'])==1
        assert len([d for d in state['devices'] if d['kind']=='gimbal'])==1
        origin=state['initial_drone_position_cm']
        # A source editor-game can compile textures after bridge/physics startup.
        # Keep the drone on the ground until the asset queue is drained and the
        # renderer has advanced normally for several successive samples.
        warm_started=time.monotonic();warm=[];stable=0
        while time.monotonic()-warm_started<600:
            settle(1)
            try:s=rpc(50051,'sim.get_state')
            except OSError:continue
            h=s.get('runtime_hardware',{});warm.append(h)
            stable=stable+1 if h.get('asset_compile_jobs')==0 and h.get('ue_fps',0)>=15 else 0
            if stable>=5:break
        report['warmup_seconds']=time.monotonic()-warm_started;report['warmup_samples']=warm
        assert stable>=5, 'Source assets did not finish warming to at least 15Hz; no takeoff attempted'
        if args.probe_layout:
            import uuid
            assert args.scene=='city_large'
            probes=[];selected=None
            for x,y in ((-72172.265625,-39996.578125),(-71672.265625,-40496.578125),(-71172.265625,-40796.578125),(-72672.265625,-39496.578125)):
                pair={}
                for device,xy in (('ptz-01',(x,y)),('uav-01',(x+1200,y+1200))):
                    try:
                        snap=rpc(50051,'placement.snap',scene_id=args.scene,request_token=uuid.uuid4().hex,
                                 device_id=device,position_cm=[*xy,600],clearance_cm=25 if device=='uav-01' else 0)
                        pair[device]=snap['placement']
                    except AssertionError as e:pair[device]={'error':str(e)}
                probes.append(pair)
                if all('surface_cm' in p and -500<p['surface_cm'][2]<1500 for p in pair.values()):
                    selected=pair;break
            report['surface_probes']=probes;report['probe_only']=True
            assert selected is not None,'No open low road surface found; no takeoff attempted'
            (args.output/'resolved-layout.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf-8')
            capture('probe')
            return
        settle(5);capture('ready')
        physical_start=rpc(50052,'sim.get_state',device_id='uav-01')
        rpc(50052,'flight.takeoff',device_id='uav-01');airborne=True
        report['flight_samples']=[]
        def flight_finished():
            f=rpc(50052,'sim.get_state',device_id='uav-01')
            if not report['flight_samples'] or time.monotonic()-report['flight_samples'][-1]['time_s']>=1:
                report['flight_samples'].append(dict(time_s=time.monotonic(),**{k:f.get(k) for k in ('flight_status','command_active','position_ned_m','motor_rpm','last_error')}))
            return not f['command_active']
        wait(flight_finished,90)
        flight=rpc(50052,'sim.get_state',device_id='uav-01')
        assert -flight['position_ned_m'][2]>-physical_start['position_ned_m'][2]+1
        report['takeoff_state']=flight
        rpc(50051,'gimbal.set_tracking',device_id='ptz-01',enabled=True)
        first=rpc(50051,'sim.get_state');begin=time.monotonic()
        while time.monotonic()-begin<args.seconds:
            settle(1)
            before=time.monotonic();s=rpc(50051,'sim.get_state')
            assert s['run_id']==run
            report['samples'].append(dict(elapsed_s=time.monotonic()-begin,rpc_ms=1000*(time.monotonic()-before),
                tick_seq=s['tick_seq'],runtime_hardware=s.get('runtime_hardware'),
                world_streaming_ready=s.get('world_streaming_ready')))
        after=rpc(50051,'sim.get_state')
        report['tick_hz']=(after['tick_seq']-first['tick_seq'])/(time.monotonic()-begin)
        capture('airborne');window.grab().save(str(args.output/'workbench.png'))
        # Controlled 3m move and return, within the surveyed initial district.
        rpc(50052,'flight.set_mode',device_id='uav-01',mode='manual')
        before=rpc(50052,'sim.get_state',device_id='uav-01')['position_ned_m']
        until=time.monotonic()+1
        while time.monotonic()<until:
            rpc(50052,'flight.set_input',device_id='uav-01',forward=1,right=0,up=0,yaw=0);settle(.1)
        rpc(50052,'flight.set_input',device_id='uav-01',forward=0,right=0,up=0,yaw=0)
        rpc(50052,'flight.hover',device_id='uav-01')
        wait(lambda:not rpc(50052,'sim.get_state',device_id='uav-01')['command_active'])
        moved=rpc(50052,'sim.get_state',device_id='uav-01')['position_ned_m']
        report['manual_displacement_m']=sum((a-b)**2 for a,b in zip(before,moved))**.5
        assert report['manual_displacement_m']>.5
        rpc(50052,'flight.land',device_id='uav-01')
        wait(lambda:rpc(50052,'sim.get_state',device_id='uav-01')['flight_status']=='ready',100)
        airborne=False;settle(3)
        final=rpc(50051,'sim.get_state');report['final_state']=final
        assert max(map(abs,final['motor_rpm']))<1
        if args.scene=='city_large':
            started=time.monotonic()
            rpc(50051,'sim.load_scene',scene_id='city')
            def small_ready():
                try:
                    ue=rpc(50051,'sim.get_state')
                    air=rpc(50052,'sim.get_state',device_id='uav-01')
                except AssertionError:return False  # transient backend restart
                return (ue['scene_id']=='city' and ue['run_id']!=run and
                        air.get('run_id')==ue['run_id'] and air['flight_status']=='ready')
            wait(small_ready,args.switch_timeout)
            report['switch_to_small_seconds']=time.monotonic()-started
            settle(10)
            small=rpc(50051,'sim.get_state');report['small_city_after_switch']=small
            assert small['device_streaming_sources']==0
            capture('small-city');window.grab().save(str(args.output/'small-city-workbench.png'))
        report['passed']=True
    finally:
        if airborne:
            try:
                rpc(50052,'flight.land',device_id='uav-01')
                wait(lambda:rpc(50052,'sim.get_state',device_id='uav-01')['flight_status']=='ready',100)
            except Exception as e:report['cleanup_land_error']=str(e)
        window.close()
        deadline=time.monotonic()+60
        while getattr(getattr(window,'runtime_manager',None),'running',False) and time.monotonic()<deadline:settle(.1)
        report['owned_session_stopped']=not getattr(getattr(window,'runtime_manager',None),'running',False)
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        app.quit()


if __name__=='__main__':main()

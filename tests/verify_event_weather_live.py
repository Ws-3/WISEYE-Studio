"""Owned Small/Big acceptance. Requires an isolated WISEYE_DATA_DIR; never flies."""
import argparse
import base64
import io
import json
import os
import time
from pathlib import Path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--small-only',action='store_true')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    assert 'event-weather-test-data' in os.environ.get('WISEYE_DATA_DIR',''), 'Use isolated test data'
    import apps.desktop_app.main
    import numpy as np
    from PIL import Image
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QSettings
    from apps.desktop_app.main_window import MainWindow
    from core.config import AppConfig
    from core.local_rpc import request
    app=QApplication([])
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,str(args.output/'qt-settings'))
    w=MainWindow(AppConfig.load());w.show();w.pages.setCurrentIndex(1)
    report=dict(passed=False,scenes={},limits='No flight; frame-driven event approximation, visual weather')
    def settle(seconds):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:app.processEvents();time.sleep(.02)
    def wait(predicate,seconds=45):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            app.processEvents()
            try:
                if predicate():return
            except (OSError,ValueError,KeyError):pass
            time.sleep(.05)
        raise TimeoutError('live acceptance timeout')
    def rpc(command,expected='ok',**payload):
        reply=request(50051,command,dict(device_id='ptz-01',**payload),timeout=10)
        assert reply['status']==expected,reply
        return reply['payload'] if expected=='ok' else reply
    def capture(folder,name,channel):
        p=rpc('camera.stream_frame',channel=channel);raw=base64.b64decode(p['image_base64'])
        (folder/(name+'.jpg')).write_bytes(raw)
        a=np.asarray(Image.open(io.BytesIO(raw)).convert('L'))
        return dict(mean=float(a.mean()),top_mean=float(a[:a.shape[0]//3].mean()),p95=float(np.percentile(a,95)),frame=p['frame_number'])
    try:
        for i in range(w.scenes.count()):
            if w.scenes.itemData(i)['id']=='city':w.scenes.setCurrentIndex(i);break
        w.launch_ue();wait(lambda:w.client.ready and w.air_client.ready,900);settle(6)
        for scene in (('city',) if args.small_only else ('city','city_large','city')):
            s=rpc('sim.get_state')
            if s['scene_id']!=scene:
                run=s['run_id'];assert w.client.request('sim.load_scene',dict(scene_id=scene))
                wait(lambda:w.client.ready and w.air_client.ready and w.state.get('scene_id')==scene and w.state.get('run_id')!=run,900)
                wait(lambda:rpc('sim.get_state')['runtime_hardware'].get('asset_compile_jobs',0)==0,900);settle(6)
            if scene in report['scenes']:report['return_to_small']=True;break
            folder=args.output/scene;folder.mkdir(exist_ok=True);result={};report['scenes'][scene]=result
            s=rpc('sim.get_state');assert not s['sensors']['event']['enabled'] and not s['sensors']['event']['capture_active']
            rpc('gimbal.set_tracking',enabled=False)
            rpc('gimbal.set_angles',yaw_deg=s['yaw_deg'],pitch_deg=30)
            rpc('observer.set_mode',mode='free');rpc('input.set_mode',mode='observer')
            # Raise the observer view to include the actual sky, not just rooftops.
            rpc('observer.set_input',forward=0,right=0,up=0,yaw_deg=0,pitch_deg=35)
            rpc('environment.configure',time_override=True,hour=12,fog=.15,rain=0,clouds=.75);settle(5)
            result['day']=capture(folder,'day-sky','OBS')
            rpc('environment.configure',time_override=True,hour=2,fog=.15,rain=0,clouds=.75);settle(5)
            result['night']=capture(folder,'night-sky','OBS');capture(folder,'night-optical','CH1')
            assert result['night']['top_mean']<result['day']['top_mean']*.5,(result['day'],result['night'])
            rpc('environment.configure',time_override=True,hour=12,fog=.15,rain=.7,clouds=.75);settle(4)
            result['rain']=rpc('sim.get_state')['environment']
            assert result['rain']['rain_active_streaks']>0 and result['rain']['rain_model']=='world_space_depth_tested_streaks'
            capture(folder,'rain-observer','OBS');capture(folder,'rain-optical','CH1')
            rpc('environment.reset');settle(2);assert rpc('sim.get_state')['environment']['rain_view_volumes']==0
            for sensor in ('visible','infrared'):rpc('sensor.set_enabled',sensor=sensor,enabled=False)
            rpc('sensor.set_enabled',sensor='event',enabled=True);settle(2)
            s=rpc('sim.get_state');assert s['sensors']['event']['capture_active']
            a=s['sensors']['event']['sample_frames'];rpc('gimbal.set_angles',yaw_deg=s['yaw_deg']+5,pitch_deg=20);settle(1)
            s=rpc('sim.get_state');assert s['sensors']['event']['sample_frames']>a
            assert not s['sensors']['visible']['enabled'] and not s['sensors']['infrared']['enabled']
            p=rpc('sensor.event.get_packet',max_events=20000,latest=True);assert p['events']
            assert 'truncated_events' in p and 'dropped_sample_frames' in p and p['sensor_state']['enabled']
            rows=p['events'];assert all(0<=x<640 and 0<=y<480 and polarity in (-1,1) for x,y,t,polarity in rows)
            assert all(rows[i][2]<=rows[i+1][2] for i in range(len(rows)-1))
            result['events']=dict(s['sensors']['event'],packet_count=len(rows),timebase=p['timebase'],skipped_events=p['skipped_events'])
            (folder/'event-packet.json').write_text(json.dumps(p),encoding='utf-8')
            export=rpc('sensor.event.capture');assert Path(export['event_last_export_path']).is_file()
            import subprocess,sys
            recorder=subprocess.run([sys.executable,'-m','examples.event_camera_stream','--output',str(folder/'events.jsonl'),'--seconds','.3'],capture_output=True,text=True,timeout=15)
            assert recorder.returncode==0,recorder.stderr
            result['jsonl_export']=recorder.stdout.strip()
            # Two independent readers can retrieve the same retained event sequence.
            cursor=p['next_cursor'];one=rpc('sensor.event.get_packet',after_sequence=cursor,max_events=2)
            two=rpc('sensor.event.get_packet',after_sequence=cursor,max_events=2)
            if one['events'] and two['skipped_events']==0:assert one['events']==two['events']
            rpc('sensor.configure',expected='error',sensor='event',enabled=True,fov_deg=25,sample_hz=30,positive_threshold=0,negative_threshold=.2,refractory_us=100)
            assert rpc('sim.get_state')['sensors']['event']['positive_threshold']==.2 or abs(rpc('sim.get_state')['sensors']['event']['positive_threshold']-.2)<1e-6
            w.gallery.add_source('ptz-01/event');settle(2)
            for step in range(4):
                rpc('gimbal.set_angles',yaw_deg=s['yaw_deg']+5+step*.3,pitch_deg=20);settle(.06)
            w.sensor_settings.setCurrentIndex(3);w.grab().save(str(folder/'event-workbench.png'))
            view=w.gallery.views['ptz-01/event'];assert not view.source.isNull(),'event preview did not render'
            view.grab().save(str(folder/'event-preview.png'))
            rpc('sensor.set_enabled',sensor='event',enabled=False);settle(1)
            off=rpc('sim.get_state')['sensors']['event'];assert not off['capture_active'];n=off['sample_frames'];settle(1)
            assert rpc('sim.get_state')['sensors']['event']['sample_frames']==n
            rpc('sensor.event.get_packet',expected='error')
            for sensor in ('visible','infrared'):rpc('sensor.set_enabled',sensor=sensor,enabled=True)
            result['event_off_released_capture']=True;result['hardware']=rpc('sim.get_state')['runtime_hardware']
            print(scene,'sky/rain/event PASS',flush=True)
        report['passed']=True
    finally:
        w.close();wait(lambda:not w.runtime_manager.running,90);report['owned_session_stopped']=True
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');app.quit()


if __name__=='__main__':main()

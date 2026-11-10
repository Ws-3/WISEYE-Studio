"""Owned isolated UE acceptance: default events, visible source response, JSBSim pilot."""
import base64,copy,hashlib,io,json,math,os,time
from pathlib import Path

def main():
    assert 'jsbsim-camera-test-data' in os.environ.get('WISEYE_DATA_DIR','')
    import apps.desktop_app.main
    import numpy as np
    from PIL import Image
    from PySide6.QtCore import QSettings,Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication,QMessageBox
    from unittest.mock import patch
    from apps.desktop_app.main_window import MainWindow
    from apps.desktop_app.event_preview_client import EventPreviewClient
    from core.local_rpc import request
    from core.config import AppConfig
    out=Path('builds/jsbsim-camera-live');out.mkdir(exist_ok=True)
    app=QApplication([]);QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,str(out/'qt'))
    w=MainWindow(AppConfig.load());w.show();report={'passed':False};preview=None
    def settle(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:app.processEvents();time.sleep(.02)
    def wait(predicate,seconds=60):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            app.processEvents()
            if predicate():return
            time.sleep(.04)
        raise TimeoutError('JSBSim/camera live acceptance timeout')
    def rpc(command,port=50051,**payload):
        reply=request(port,command,payload,timeout=8)
        assert reply['status']=='ok',reply
        return reply['payload']
    def state(device='ptz-01'):return rpc('sim.get_state',device_id=device)
    def fw():return next(d['fixedwing'] for d in state()['devices'] if d['id']=='uav-01')
    def flight():return rpc('sim.get_state',50052,device_id='uav-01')
    def key(code,seconds):
        w.raise_();w.activateWindow();w.setFocus();settle(.15)
        QTest.keyPress(w,code);settle(seconds);QTest.keyRelease(w,code);settle(.08)
    def image(name):
        p=rpc('camera.stream_frame',device_id='ptz-01',channel='CH1')
        data=base64.b64decode(p['image_base64']);(out/(name+'.jpg')).write_bytes(data)
        return np.asarray(Image.open(io.BytesIO(data)).convert('L')).astype(float)
    def sharpness(a):
        # Native pixels; no resize, comparing the same frozen camera/scene.
        return float(np.var(4*a[1:-1,1:-1]-a[:-2,1:-1]-a[2:,1:-1]-a[1:-1,:-2]-a[1:-1,2:]))
    try:
        w.launch_ue();wait(lambda:w.client.ready and w.air_client.ready,600);settle(2)
        run=state()['run_id'];report['run_id']=run
        for ident in ('ptz-01','ptz-02'):
            event=state(ident)['sensors']['event']
            assert event['enabled'] and event['capture_active'] and event['sample_frames']>2,event
            report[ident+'_default_event']=event
        preview=EventPreviewClient();frames=[];preview.frame_received.connect(lambda im,hz:frames.append(im.copy()))
        preview.start_source('127.0.0.1',50051,'event','ptz-01')
        wait(lambda:len(frames)>2)
        assert preview._connected;report['default_event_qt_frames']=len(frames)
        rpc('gimbal.set_tracking',device_id='ptz-01',enabled=False)
        s=state();rpc('gimbal.set_angles',device_id='ptz-01',yaw_deg=s['yaw_deg']+8,pitch_deg=0)
        settle(1);packet=rpc('sensor.event.get_packet',device_id='ptz-01',max_events=100,latest=True)
        assert packet['events'];report['event_without_power_cycle']=True
        # Show a static city-facing camera to isolate optical filtering.
        rpc('gimbal.set_angles',device_id='ptz-01',yaw_deg=0,pitch_deg=-8)
        rpc('sensor.configure',device_id='ptz-01',sensor='visible',enabled=True,fov_deg=40,blur_px=0,noise=0,contrast=1,saturation=1)
        settle(2);a=image('visible-neutral')
        second=state('ptz-02')['sensors']['visible']
        rpc('sensor.configure',device_id='ptz-01',sensor='visible',enabled=True,fov_deg=40,blur_px=2.8,noise=0,contrast=1,saturation=1)
        settle(1);b=image('visible-blur')
        ratio=sharpness(b)/max(.001,sharpness(a));report['visible_blur_sharpness_ratio']=ratio
        assert ratio<.85,ratio
        assert state('ptz-02')['sensors']['visible']['blur_px']==second['blur_px']
        invalid=request(50051,'sensor.configure',dict(device_id='ptz-01',sensor='visible',enabled=True,fov_deg=40,blur_px=4),timeout=5)
        assert invalid['status']=='error' and abs(state()['sensors']['visible']['blur_px']-2.8)<1e-5
        rpc('sensor.configure',device_id='ptz-01',sensor='visible',enabled=True,fov_deg=40,blur_px=.55,noise=.006,contrast=.96,saturation=.88)
        settle(1);image('visible-default');report['visible_default']=state()['sensors']['visible']
        # Power cycling remains independent; no reconnect required.
        rpc('sensor.set_enabled',device_id='ptz-01',sensor='event',enabled=False)
        assert not state()['sensors']['event']['capture_active'];settle(.3)
        rpc('sensor.set_enabled',device_id='ptz-01',sensor='event',enabled=True)
        wait(lambda:state()['sensors']['event']['capture_active'] and state()['sensors']['event']['actual_sample_hz']>0)
        rpc('flight.takeoff',50052,device_id='uav-01');settle(2)
        assert fw()['model']=='jsbsim_6dof' and fw()['active'],fw()
        w.pages.setCurrentIndex(1);w.fleet_selection.select('drone','uav-01');w.manual_takeover.click()
        wait(lambda:flight()['flight_mode']=='manual');settle(.5)
        before=fw();key(Qt.Key.Key_D,1.5);turn=fw()
        assert abs((turn['yaw_deg']-before['yaw_deg']+180)%360-180)>7,(before,turn)
        assert 8<turn['roll_deg']<36,turn
        settle(2);level=fw();assert abs(level['roll_deg'])<3,level
        before=flight();key(Qt.Key.Key_R,1.8);after=flight()
        assert after['position_ned_m'][2]<before['position_ned_m'][2]-.8,(before,after)
        before=fw();key(Qt.Key.Key_W,1.2);after=fw()
        assert after['speed_command_mps']>before['speed_command_mps']+1
        assert after['speed_mps']>before['speed_mps']+.3
        commanded=after['speed_command_mps'];settle(1.5);assert abs(fw()['speed_command_mps']-commanded)<.1
        report['jsbsim_pilot']={'before_turn':before,'turn':turn,'level':level,'speed_after':fw()}
        rpc('sim.pause',50052,device_id='uav-01');a=state()['devices'][0]['position_cm'];settle(.6)
        assert math.dist(a,state()['devices'][0]['position_cm'])<.001
        w.manual_takeover.click();wait(lambda:not flight()['paused']);settle(.5)
        assert fw()['active'];rpc('flight.land',50052,device_id='uav-01')
        assert flight()['flight_status']=='ready' and state()['run_id']==run
        w.grab().save(str(out/'workbench.png'));report['passed']=True
    finally:
        if preview:preview.stop()
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):w.close()
        wait(lambda:not w.runtime_manager.running,100)
        report['owned_session_stopped']=True
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');app.quit()

if __name__=='__main__':main()

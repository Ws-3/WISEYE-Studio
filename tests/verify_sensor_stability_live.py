"""Owned Small/Big City acceptance: sensor power, rain, gain and preview quality.

Use a separate WISEYE_DATA_DIR. Never edits Fleet files or takes off.
"""
import argparse
import base64
import json
import time
from pathlib import Path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--weather-ui',action='store_true',help='Also verify compact actions, rain particles, fog and night exposure')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    import apps.desktop_app.main
    from PySide6.QtWidgets import QApplication
    from apps.desktop_app.main_window import MainWindow
    from apps.desktop_app.lidar_view import LidarView
    from core.config import AppConfig
    from core.local_rpc import request
    app=QApplication([]);w=MainWindow(AppConfig.load());w.show();w.pages.setCurrentIndex(1)
    report=dict(passed=False,scenes={},limits='No flight, no all-city traversal, visual weather only; isolated data')
    acknowledgements={};failures={}
    w.client.request_completed.connect(lambda ident,cmd,submitted,state:acknowledgements.update({ident:state}))
    w.client.request_failed.connect(lambda ident,cmd,submitted,error:failures.update({ident:error}))
    def settle(seconds=.2):
        until=time.monotonic()+seconds
        while time.monotonic()<until:app.processEvents();time.sleep(.02)
    def wait(predicate,seconds=30):
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            app.processEvents()
            try:
                if predicate():return
            except (OSError,ValueError,KeyError):pass
            time.sleep(.05)
        raise TimeoutError('Sensor stability acceptance timed out')
    def rpc(command,port=50051,expected='ok',**payload):
        packet=request(port,command,dict(device_id='ptz-01',**payload),timeout=10)
        assert packet['status']==expected,packet
        return packet['payload'] if expected=='ok' else packet
    def qt(command,**payload):
        ident=w.client.request(command,dict(device_id='ptz-01',**payload));assert ident
        wait(lambda:ident in acknowledgements or ident in failures,12)
        assert ident not in failures,(command,failures.get(ident))
        return acknowledgements.pop(ident)
    def capture(folder,name,channel):
        packet=rpc('camera.stream_frame',channel=channel)
        assert packet['quality']==90,packet.get('quality')
        raw=base64.b64decode(packet['image_base64'])
        (folder/(name+'.jpg')).write_bytes(raw)
        from PIL import Image
        import io,numpy as np
        im=Image.open(io.BytesIO(raw));grey=np.array(im.convert('L'))
        return dict(size=im.size,bytes=len(raw),grey_percentiles=np.percentile(grey,[5,50,95]).tolist(),grey_std=float(grey.std()),grey_mean=float(grey.mean()),frame=packet['frame_number'])
    try:
        for i in range(w.scenes.count()):
            if w.scenes.itemData(i)['id']=='city':w.scenes.setCurrentIndex(i);break
        w.quick_connect.click() if args.weather_ui else w.launch_ue()
        wait(lambda:w.client.ready and w.air_client.ready,900);settle(8)
        if args.weather_ui:
            assert w.quick_connect.text()=='关闭仿真' and w.quick_connect.isEnabled()
            run=w.state['run_id'];w.badge.click();settle(.5)
            assert not w.client.ready and not w.air_client.ready and w.runtime_manager.running
            w.badge.click();wait(lambda:w.client.ready and w.air_client.ready,30)
            assert w.state['run_id']==run
            report['disconnect_reconnect_without_stopping']=True
        for scene in ('city','city_large','city'):
            current=rpc('sim.get_state')
            if current['scene_id']!=scene:
                run=current['run_id'];qt('sim.load_scene',scene_id=scene)
                wait(lambda:w.client.ready and w.air_client.ready and w.state.get('scene_id')==scene and
                     w.state.get('run_id')!=run and w.air_state.get('run_id')==w.state.get('run_id'),900)
                wait(lambda:rpc('sim.get_state')['runtime_hardware'].get('asset_compile_jobs')==0,900)
                settle(8)
            if scene in report['scenes']:
                report['return_to_small']=dict(connected=w.client.ready,run_id=w.state['run_id'],rain=rpc('sim.get_state')['environment'])
                assert report['return_to_small']['rain']['rain_supported'];break
            folder=args.output/scene;folder.mkdir(exist_ok=True)
            result=dict(power=[],gain=[]);report['scenes'][scene]=result
            initial=rpc('sim.get_state');result['initial_environment']=initial['environment']
            assert initial['environment']['rain_supported'],initial['environment']
            for sensor in ('visible','infrared'):
                qt('camera.set_mode',mode=sensor)
                for enabled in (False,True,False,True):
                    state=qt('sensor.set_enabled',sensor=sensor,enabled=enabled);settle(.4)
                    assert w.client.ready and w.air_client.ready
                    assert state['sensors'][sensor]['enabled'] is enabled
                    assert (state['width'],state['height'])==((1920,1080) if sensor=='visible' else (640,512))
                    channel='CH1' if sensor=='visible' else 'CH2'
                    if not enabled:
                        packet=rpc('camera.stream_frame',channel=channel,expected='error')
                        assert packet['error']['code']=='sensor_disabled'
                    result['power'].append(dict(sensor=sensor,enabled=enabled,connected=w.client.ready))
            qt('sensor.set_enabled',sensor='visible',enabled=False)
            qt('sensor.set_enabled',sensor='infrared',enabled=False)
            qt('sensor.set_enabled',sensor='lidar',enabled=False)
            off=rpc('sim.get_state');before=rpc('camera.stream_frame',channel='OBS')['frame_number'];settle(2)
            after=rpc('sim.get_state')
            assert after['tick_seq']>off['tick_seq'] and w.client.ready and w.air_client.ready
            assert rpc('camera.stream_frame',channel='OBS')['frame_number']>before
            assert all(after['sensors'][s]['capture_sequence']==off['sensors'][s]['capture_sequence'] for s in ('visible','infrared'))
            assert after['sensors']['lidar']['scan_sequence']==off['sensors']['lidar']['scan_sequence']
            result['all_off_control_and_observer_alive']=True
            for sensor in ('visible','infrared','lidar'):qt('sensor.set_enabled',sensor=sensor,enabled=True)
            settle(2)
            result['clear_visible']=capture(folder,'clear-visible','CH1')
            result['clear_infrared']=capture(folder,'clear-infrared','CH2')
            qt('environment.configure',time_override=False,hour=12,fog=0,rain=.7,clouds=0);settle(3)
            rain=rpc('sim.get_state')['environment'];assert rain['rain_supported'] and rain['rain_view_volumes']>=2 and abs(rain['rain']-.7)<.01
            if args.weather_ui:
                wait(lambda:rpc('sim.get_state')['environment'].get('rain_active_streaks',0)>0 or rpc('sim.get_state')['environment']['rain_active_particles']>0,12)
                rain=rpc('sim.get_state')['environment']
            result['rain']=rain;capture(folder,'rain-visible','CH1');capture(folder,'rain-observer','OBS')
            qt('environment.reset');settle(2)
            assert rpc('sim.get_state')['environment']['rain_view_volumes']==0
            if args.weather_ui:
                qt('gimbal.set_tracking',enabled=True)
                qt('camera.set_mode',mode='visible')
                qt('environment.configure',time_override=True,hour=12,fog=0,rain=0,clouds=0);settle(4)
                result['day']=capture(folder,'day-visible','CH1');result['day_observer']=capture(folder,'day-observer','OBS')
                qt('environment.configure',time_override=True,hour=12,fog=.9,rain=0,clouds=0);settle(4)
                result['fog']=capture(folder,'fog-visible','CH1')
                result['fog_contrast_ratio']=result['fog']['grey_std']/max(1,result['day']['grey_std'])
                result['fog_observer']=capture(folder,'fog-observer','OBS')
                result['fog_observer_contrast_ratio']=result['fog_observer']['grey_std']/max(1,result['day_observer']['grey_std'])
                # Near-field sensors may look at a surface only metres away;
                # fog attenuates by distance. Use the distant city for this check.
                assert result['fog_observer_contrast_ratio']<.95,result['fog_observer_contrast_ratio']
                qt('environment.configure',time_override=True,hour=2,fog=0,rain=0,clouds=0);settle(5)
                result['night']=capture(folder,'night-visible','CH1');capture(folder,'night-observer','OBS')
                result['night_environment']=rpc('sim.get_state')['environment']
                assert result['night_environment']['night_amount']>.99
                assert result['night']['grey_mean']<result['day']['grey_mean']*.8,(result['day'],result['night'])
                qt('environment.reset');settle(3)
                key=next(k for k in w.gallery.views if k.endswith('/visible'))
                view=w.gallery.views[key]
                from PySide6.QtCore import QPointF,QPoint,Qt
                from PySide6.QtGui import QWheelEvent
                from PySide6.QtTest import QTest
                from PySide6.QtWidgets import QPushButton
                before=view.source.size()
                event=QWheelEvent(QPointF(view.width()/2,view.height()/2),QPointF(400,300),QPoint(0,0),QPoint(0,120),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
                QApplication.sendEvent(view,event);assert view.zoom_factor>1 and view.source.size()==before
                QTest.mouseClick(view,Qt.MouseButton.LeftButton);assert not w.sensor_dock.isVisible()
                w.grab().save(str(folder/'workbench-zoom.png'));view.reset_zoom()
                popout=next(b for b in w.gallery.cards[key].findChildren(QPushButton) if b.accessibleName()=='弹出画面')
                popout.click();settle(.3);assert key in w.gallery.popouts;w.gallery.popouts[key][0].close()
            # Repoint the actual independent camera through wall/sky views.
            original=rpc('sim.get_state');ir=original['sensors']['infrared']
            def configure(mode):
                return qt('sensor.configure',sensor='infrared',enabled=True,fov_deg=ir['fov_deg'],palette=ir['palette'],
                          noise=ir['noise'],gain_mode=mode,stable_agc=True,agc_enabled=mode=='auto')
            configure('auto')
            yaw,pitch=original['yaw_deg'],original['pitch_deg']
            minimum,maximum=original['pitch_min_deg'],original['pitch_max_deg']
            pitch=max(minimum,min(maximum,pitch))
            for number,(y,p) in enumerate(((yaw,pitch),(yaw,60),(yaw+25,15),(yaw,pitch))):
                qt('gimbal.set_angles',yaw_deg=max(-179,min(179,y)),pitch_deg=max(minimum,min(maximum,p)))
                until=time.monotonic()+3
                while time.monotonic()<until:
                    settle(.2);s=rpc('sim.get_state')['sensors']['infrared']
                    result['gain'].append(dict(time=time.monotonic(),low=s['agc_low'],high=s['agc_high'],sky=s['sky_pixels'],target=s['target_pixels'],sequence=s['readout_sequence']))
                capture(folder,f'gain-view-{number}','CH2')
            configure('locked');settle(.6)
            lock=rpc('sim.get_state')['sensors']['infrared']
            qt('gimbal.set_angles',yaw_deg=yaw,pitch_deg=min(maximum,60));settle(2)
            locked=rpc('sim.get_state')['sensors']['infrared']
            assert abs(locked['agc_low']-lock['agc_low'])<1e-6 and abs(locked['agc_high']-lock['agc_high'])<1e-6
            result['lock_held']=True
            qt('gimbal.set_angles',yaw_deg=yaw,pitch_deg=pitch);configure(ir['gain_mode'])
            qt('camera.set_mode',mode=original['sensor_mode']);qt('gimbal.set_tracking',enabled=original['tracking'])
            cloud=rpc('sensor.lidar.get_points')
            view=LidarView();view.resize(900,500)
            view.set_points(cloud['lidar_points_m'],cloud['lidar_point_count'],cloud['lidar_rays'],cloud['lidar_horizontal_fov_deg'],cloud['lidar_vertical_fov_deg'])
            view.grab().save(str(folder/'lidar-sensor.png'))
            view.mode.setCurrentIndex(view.mode.findData('3d'));view.grab().save(str(folder/'lidar-orbit.png'));view.close()
            result['final_environment']=rpc('sim.get_state')['environment'];assert result['final_environment']['rain_supported']
            result['hardware']=rpc('sim.get_state')['runtime_hardware']
            w.grab().save(str(folder/'workbench.png'))
            print(scene,'power/rain/gain/quality PASS',flush=True)
        report['passed']=True
        if args.weather_ui:
            w.quick_connect.click();wait(lambda:not w.runtime_manager.running,70)
            settle(.5);assert not w.client.ready and not w.air_client.ready
            assert w.quick_connect.text()=='启动仿真'
            report['stop_button_stopped_owned_session']=True
    finally:
        w.close();wait(lambda:not getattr(getattr(w,'runtime_manager',None),'running',False),70)
        report['owned_session_stopped']=True
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');app.quit()


if __name__=='__main__':main()

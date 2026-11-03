"""Owned isolated city flight; measure actual landing and compare dusk/night lamps."""
import argparse,base64,io,json,os,time,statistics
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    assert 'event-weather-test-data' in os.environ.get('WISEYE_DATA_DIR','')
    import apps.desktop_app.main
    import numpy as np
    from PIL import Image
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QSettings
    from apps.desktop_app.main_window import MainWindow
    from core.config import AppConfig
    from core.local_rpc import request
    app=QApplication([]);QSettings.setDefaultFormat(QSettings.Format.IniFormat);QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,str(args.output/'qt-settings'))
    w=MainWindow(AppConfig.load());w.show();w.pages.setCurrentIndex(1);report=dict(passed=False);airborne=False
    def settle(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:app.processEvents();time.sleep(.02)
    def wait(test,seconds=70):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            app.processEvents()
            if test():return
            time.sleep(.05)
        raise TimeoutError('distance/night/landing acceptance timeout')
    def rpc(command,port=50051,**payload):
        r=request(port,command,dict(device_id='uav-01' if port==50052 else 'ptz-01',**payload),timeout=5)
        assert r['status']=='ok',r
        return r['payload']
    try:
        for i in range(w.scenes.count()):
            if w.scenes.itemData(i)['id']=='city':w.scenes.setCurrentIndex(i);break
        w.launch_ue();wait(lambda:w.client.ready and w.air_client.ready,900);settle(5)
        initial=rpc('sim.get_state');assert rpc('sim.get_state',50052)['flight_status']=='ready'
        rpc('gimbal.set_tracking',enabled=True)
        rpc('flight.takeoff',50052);airborne=True;wait(lambda:not rpc('sim.get_state',50052)['command_active']);settle(2)
        # This user's roof PTZ is above the takeoff hover and its parapet.
        # Ascend vertically until the target is in the camera's pitch range.
        rpc('flight.set_mode',50052,mode='manual')
        base_z=initial['gimbal_position_cm'][2]
        for _ in range(60):
            s=rpc('sim.get_state')
            if s['drone_position_cm'][2]>base_z+400:break
            rpc('flight.set_input',50052,forward=0,right=0,up=1,yaw=0);settle(.1)
        rpc('flight.set_input',50052,forward=0,right=0,up=0,yaw=0)
        wait(lambda:not rpc('sim.get_state',50052)['command_active']);settle(2)
        assert rpc('sim.get_state')['drone_position_cm'][2]>base_z+300
        s=rpc('sim.get_state');a=rpc('sim.get_state',50052);w.apply_air_state(a);w.apply_state(s)
        base=next(d['position_cm'] for d in s['devices'] if d['id']=='ptz-01')
        pos=a['position_ned_m'];expected=sum((x-y)**2 for x,y in zip([pos[0]*100,pos[1]*100,-pos[2]*100],base))**.5/100
        report['distance_m']=expected;report['distance_text']=w.distance_label.text();assert f'{expected:.2f} m' in w.distance_label.text()
        w.grab().save(str(args.output/'telemetry.png'))
        report['lights']={}
        for name,hour in [('dusk',18.1),('night',22)]:
            rpc('environment.configure',time_override=True,hour=hour,fog=0,rain=0,clouds=0);settle(3)
            snapshot=rpc('sim.get_state');(args.output/(name+'-state.json')).write_text(json.dumps(snapshot),encoding='utf-8')
            best=(-1,None);seen=set()
            for i in range(24):
                packet=rpc('camera.stream_frame',channel='CH1');raw=base64.b64decode(packet['image_base64'])
                rgb=np.asarray(Image.open(io.BytesIO(raw))).astype(float);h,b=rgb.shape[:2];roi=rgb[h//3:2*h//3,b//3:2*b//3]
                red,green,blue=roi[:,:,0],roi[:,:,1],roi[:,:,2]
                score=int(((((red-green>12)&(red-blue>12))|((green-red>12)&(green-blue>12)))&(roi.max(axis=2)>35)).sum())
                if score>best[0]:best=(score,raw)
                lights=next(d['navigation_lights'] for d in rpc('sim.get_state')['devices'] if d['id']=='uav-01')
                seen.add('red' if lights['red_on'] else 'green' if lights['green_on'] else 'off');settle(.07)
            assert seen=={'red','green','off'},seen
            (args.output/(name+'-lamp.jpg')).write_bytes(best[1]);report['lights'][name]=dict(color_pixels_max=best[0],phases=sorted(seen))
        rpc('environment.reset');settle(1)
        report['landing_samples']=samples=[];start=time.monotonic();rpc('flight.land',50052)
        while time.monotonic()-start<60:
            s=rpc('sim.get_state',50052);samples.append(dict(t=time.monotonic()-start,z=s['position_ned_m'][2],status=s['flight_status'],rpm=s['motor_rpm']))
            if s['flight_status']=='ready' and max(s['motor_rpm'])<1:airborne=False;break
            settle(.15)
        assert not airborne,'landing did not complete and disarm'
        rates=[(b['z']-a['z'])/(b['t']-a['t']) for a,b in zip(samples,samples[1:]) if b['t']>a['t'] and b['z']-a['z']>.01]
        report['landing_median_descent_m_s']=statistics.median(rates);report['landing_wall_seconds']=samples[-1]['t']
        assert .4<report['landing_median_descent_m_s']<1.4,report['landing_median_descent_m_s']
        assert report['lights']['night']['color_pixels_max']>0,'Lamp state toggles but target/light is not visible'
        assert report['lights']['night']['color_pixels_max']>report['lights']['dusk']['color_pixels_max'],'Deep-night lamps did not become more prominent'
        report['passed']=True;print('distance/night/landing PASS',flush=True)
    finally:
        if airborne:
            try:
                rpc('flight.land',50052);wait(lambda:rpc('sim.get_state',50052)['flight_status']=='ready',90)
            except Exception as error:report['cleanup_error']=str(error)
        w.close();wait(lambda:not w.runtime_manager.running,90);report['owned_session_stopped']=True
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');app.quit()

if __name__=='__main__':main()

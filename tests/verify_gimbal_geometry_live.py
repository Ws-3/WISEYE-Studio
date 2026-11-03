"""Explicitly launch an owned preview and verify native optical coordinate aim."""
import argparse,json,math,time
from pathlib import Path
from unittest.mock import patch
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication,QMessageBox
from core.config import AppConfig
from core.georeference import GeoReference,GeoReferenceStore
from apps.desktop_app.main_window import MainWindow
from apps.desktop_app.gimbal_device import GimbalDeviceDialog
from integrations.gimbal_client import GimbalClient,GimbalError
from training_client.client import Client


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    app=QApplication([]);w=MainWindow(AppConfig.load());w.show();g=GimbalClient();air=Client(port=50052,device='uav-01')
    report={'passed':False};original=None;airborne=False;dialog=None
    def settle(seconds=.2):
        end=time.monotonic()+seconds
        while time.monotonic()<end:app.processEvents();time.sleep(.02)
    def wait(check,seconds=30):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            app.processEvents()
            if check():return
            time.sleep(.2)
        raise TimeoutError('Live geometry condition timed out')
    def forward(sensor):
        pitch,yaw,_=map(math.radians,sensor['camera_rotation_pitch_yaw_roll_deg'])
        return math.cos(pitch)*math.cos(yaw),math.cos(pitch)*math.sin(yaw),math.sin(pitch)
    try:
        w.launch_ue();wait(lambda:w.client.ready and w.air_client.ready,300);original=g.state();report['run_id']=original['run_id']
        assert original['coordinate_pointing_supported']
        report['original_base_cm']=original['gimbal_position_cm'];report['camera_results']={}
        g.set_angles(-25,20);state=g.state();targets={}
        for sensor in ('visible','infrared'):
            data=state['sensors'][sensor]
            assert [data['width_px'],data['height_px']]==([640,512] if sensor=='infrared' else [1920,1080])
            expected=math.degrees(2*math.atan(math.tan(math.radians(data['fov_deg'])/2)*data['height_px']/data['width_px']))
            assert abs(expected-data['vertical_fov_deg'])<1e-7
            targets[sensor]=[p+2000*v for p,v in zip(data['camera_position_cm'],forward(data))]
        for sensor in ('visible','infrared'):
            g.set_angles(12,0)
            reply=g.point_at_world(targets[sensor],sensor,scene_id=original['scene_id'],run_id=original['run_id'])
            point=reply['coordinate_pointing'];assert point['error_deg']<.01
            assert abs(point['slant_range_m']-20)<.002
            report['camera_results'][sensor]=point
        before=g.state();bad=list(before['sensors']['visible']['camera_position_cm']);bad[2]-=10000
        for payload in (dict(position_cm=bad),dict(position_cm=targets['visible'],run_id='stale'),dict(position_cm=[True,0,0])):
            values=dict(position_cm=targets['visible'],sensor='visible',scene_id=original['scene_id'],run_id=original['run_id']);values.update(payload)
            try:g.request('gimbal.point_at',**values)
            except GimbalError:pass
            else:raise AssertionError('Invalid coordinate aim accepted')
            after=g.state();assert abs(after['yaw_deg']-before['yaw_deg'])<1e-7 and abs(after['pitch_deg']-before['pitch_deg'])<1e-7
        report['invalid_requests_preserve_pose']=True
        ref=GeoReference(original['scene_id'],30,120,100,tuple(original['gimbal_position_cm']),37)
        reply=g.point_at_geodetic(ref,*ref.world_to_geodetic(targets['infrared']),'infrared',run_id=original['run_id'])
        assert reply['coordinate_pointing']['error_deg']<.01;report['geodetic_optical_error_deg']=reply['coordinate_pointing']['error_deg']
        # Actual moving drone: rise above a possibly elevated user camera base.
        air.rpc('flight.takeoff');airborne=True;wait(lambda:not air.rpc('sim.get_state')['command_active'],60)
        air.rpc('flight.set_mode',mode='manual');height=original['gimbal_position_cm'][2]/100+3
        end=time.monotonic()+15
        while time.monotonic()<end:
            if -air.rpc('sim.get_state')['position_ned_m'][2]>=height:break
            air.rpc('flight.set_input',forward=0,right=0,up=1,yaw=0);settle()
        air.rpc('flight.set_input',forward=0,right=0,up=0,yaw=0);air.rpc('flight.hover');wait(lambda:not air.rpc('sim.get_state')['command_active'])
        errors=[]
        for i in range(10):
            state=g.state();drone=next(d for d in state['devices'] if d['id']=='uav-01')
            reply=g.point_at_geodetic(ref,*ref.world_to_geodetic(drone['position_cm']),'visible',run_id=original['run_id'])
            errors.append(reply['coordinate_pointing']['error_deg']);settle()
        assert max(errors)<.01;report['drone_coordinate_updates']=len(errors);report['drone_optical_errors_deg']=errors
        dialog=GimbalDeviceDialog(w);dialog.store=GeoReferenceStore(args.output/'isolated-config');dialog.scene_id=None;dialog.update_state(g.state())
        dialog.latitude.setValue(30);dialog.longitude.setValue(120);dialog.height.setValue(100);dialog.azimuth.setValue(37);dialog.save_reference()
        dialog.show();settle(.5);dialog.grab().save(str(args.output/'device-telemetry.png'))
        dialog.tabs.setCurrentIndex(1);settle();dialog.grab().save(str(args.output/'coordinate-pointing.png'))
        report['distance_text']=dialog.values['range'].text();report['passed']=True
    except BaseException as error:
        report['error']=repr(error);raise
    finally:
        try:
            if airborne:
                air.rpc('flight.set_mode',mode='manual');origin=next(d['position_cm'][2]/100 for d in original['devices'] if d['id']=='uav-01')
                end=time.monotonic()+25
                while time.monotonic()<end:
                    if -air.rpc('sim.get_state')['position_ned_m'][2]<=origin+2:break
                    air.rpc('flight.set_input',forward=0,right=0,up=-.6,yaw=0);settle()
                air.rpc('flight.set_input',forward=0,right=0,up=0,yaw=0);air.rpc('flight.land');wait(lambda:air.rpc('sim.get_state')['flight_status']=='ready',65)
            if original:
                g.set_angles(round(original['yaw_deg'],6),round(original['pitch_deg'],6));g.request('gimbal.set_tracking',enabled=original['tracking'])
                report['final_flight']=air.rpc('sim.get_state')
        except BaseException as error:report['passed']=False;report['cleanup_error']=repr(error)
        finally:
            if dialog:dialog.close()
            with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):w.close()
            if hasattr(w,'runtime_manager'):wait(lambda:not w.runtime_manager.running,65)
            (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    assert report['passed']


if __name__=='__main__':main()

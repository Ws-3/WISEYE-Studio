"""Native V4 UI and real UE integration; uses an explicitly owned preview."""
import argparse
import json
import time
from pathlib import Path
from unittest.mock import patch
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication,QMessageBox
from core.config import AppConfig
from training_client.client import Client
from training_client.workbench import Window
from apps.desktop_app.main_window import MainWindow
from apps.desktop_app.workbench_v3 import show_properties
from apps.desktop_app.route_editor import open_route_editor


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-id');parser.add_argument('--launch',action='store_true');parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    app=QApplication([]);ue=Client(port=50051);air=Client(port=50052,device='uav-01')
    w=MainWindow(AppConfig.load());w.resize(1600,940);w.show()
    if args.launch:w.launch_ue()
    else:w.connect_ue()
    t=None;report={'run_id':args.run_id,'passed':False};airborne=False
    def wait(predicate,seconds=30):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            app.processEvents()
            if predicate():return
            time.sleep(.15)
        raise TimeoutError('V4 live condition timed out')
    def settle(seconds=.35):
        until=time.monotonic()+seconds
        while time.monotonic()<until:app.processEvents();time.sleep(.01)
    def capture(widget,name):settle();assert widget.grab().save(str(args.output/(name+'.png')))
    wait(lambda:w.client.ready and w.air_client.ready and len(w.gallery.frames)>=3,300 if args.launch else 30)
    original=ue.rpc('sim.get_state')
    if args.run_id:assert original['run_id']==args.run_id
    report['run_id']=original['run_id']
    original_ir=original['sensors']['infrared']['fov_deg'];original_fields=None
    try:
        wait(lambda:w.client.ready and w.air_client.ready and len(w.gallery.frames)>=3)
        w.gallery.reset_layout();wait(lambda:len(w.gallery.frames)>=3)
        capture(w,'simulation-workbench')
        show_properties(w,'sensor','ptz-01/infrared');wait(lambda:w.sensor_settings.panels['infrared']['confirmed'] is not None)
        panel=w.sensor_settings.panels['infrared'];original_fields=w.sensor_settings.values('infrared');panel['fields']['fov_deg'].setValue(original_ir+.5);panel['apply'].click()
        wait(lambda:not w.sensor_settings.pending and not panel['dirty'])
        assert abs(ue.rpc('sim.get_state')['sensors']['infrared']['fov_deg']-original_ir-.5)<.01
        capture(w,'sensor-parameters')
        panel['fields']['fov_deg'].setValue(original_ir);panel['apply'].click();wait(lambda:not w.sensor_settings.pending and not panel['dirty']);w.sensor_dock.hide()
        w.pages.setCurrentIndex(0);wait(lambda:not w.arrangement.scene_view.source.isNull() and set(w.gallery.clients)=={'scene/observer'})
        report['arrangement_single_shared_observer']=True;capture(w,'scene-arrangement')
        w.pages.setCurrentIndex(4);settle();capture(w,'device-management')
        w.pages.setCurrentIndex(2);capture(w,'data-interfaces')
        w.pages.setCurrentIndex(3);capture(w,'settings')
        w.pages.setCurrentIndex(1);show_properties(w,'drone','uav-01');capture(w,'drone-control')
        open_route_editor(w);capture(w.route_editor,'route-editor');w.route_editor.close()
        # Same native backend; record real positive samples in the new layout.
        reply=air.rpc('flight.takeoff');airborne=True
        wait(lambda:not air.rpc('sim.get_state')['command_active'],60)
        air.rpc('flight.set_mode',mode='manual')
        target_height=max(d['position_cm'][2] for d in original['devices'] if d['id']=='ptz-01')/100+3
        deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            if -air.rpc('sim.get_state')['position_ned_m'][2]>=target_height:break
            air.rpc('flight.set_input',forward=0,right=0,up=1,yaw=0)
            settle(.15)
        air.rpc('flight.set_input',forward=0,right=0,up=0,yaw=0)
        air.rpc('flight.hover');wait(lambda:not air.rpc('sim.get_state')['command_active'],30)
        ue.rpc('gimbal.set_tracking',enabled=True)
        t=Window(argparse.Namespace(host='127.0.0.1',port=50100,device='ptz-01',output=args.output/'dataset'))
        t.resize(1600,940);t.show();t.start()
        wait(lambda:t.latest is not None and any(p['objects'] for p in t.latest['samples'].values()),25);worker=t.worker
        t.save_action.click();assert t.record.isChecked()
        times=[];seen=set();until=time.monotonic()+7
        while time.monotonic()<until:
            app.processEvents()
            if t.latest and t.latest['pair_id'] not in seen:seen.add(t.latest['pair_id']);times.append(time.monotonic())
            time.sleep(.01)
        capture(t,'training-workbench')
        assert len(list((args.output/'dataset/IR/images').glob('*.jpg')))>=3
        identity=t.latest['pair_id'];t.show_gt.setChecked(False)
        assert t.latest['pair_id']==identity and t.worker is worker
        assert t.tiles['infrared'].canvas.image==t.decoded['infrared']
        t.save_action.click();assert not t.record.isChecked() and t.worker is worker
        t.tiles['fusion'].enlarge();settle();capture(t.tiles['fusion'].popup,'fusion-window');t.tiles['fusion'].popup.close()
        report.update(sensor_ack_is_actual=True,gt_overlay_only=True,stop_save_keeps_receiver=True,
                      saved_pairs=len(list((args.output/'dataset/IR/images').glob('*.jpg'))),
                      actual_display_fps=(len(times)-1)/(times[-1]-times[0]) if len(times)>1 else 0)
        report['passed']=True
    except BaseException as error:
        report['error']=repr(error)
        raise
    finally:
      try:
        if t:t.close();wait(lambda:t.worker is None,18)
        if airborne:
            # Land descends slowly; keep this UI acceptance below the SDK's
            # 60 s transport timeout rather than testing high-altitude landing.
            air.rpc('flight.set_mode',mode='manual')
            origin=next(d['position_cm'][2]/100 for d in original['devices'] if d['id']=='uav-01')
            deadline=time.monotonic()+25
            while time.monotonic()<deadline:
                state=air.rpc('sim.get_state')
                if -state['position_ned_m'][2]<=origin+2:break
                air.rpc('flight.set_input',forward=0,right=0,up=-.6,yaw=0)
                settle(.2)
            air.rpc('flight.set_input',forward=0,right=0,up=0,yaw=0)
            air.rpc('flight.land');wait(lambda:air.rpc('sim.get_state')['flight_status']=='ready',65)
        ue.rpc('gimbal.set_angles',yaw_deg=round(original['yaw_deg'],6),pitch_deg=round(original['pitch_deg'],6))
        ue.rpc('gimbal.set_tracking',enabled=original['tracking'])
        report['final_flight']=air.rpc('sim.get_state')
        if original_fields:ue.rpc('sensor.configure',sensor='infrared',**original_fields)
      except BaseException as error:
        report['passed']=False;report['cleanup_error']=repr(error)
        raise
      finally:
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):w.close()
        if args.launch:wait(lambda:not w.runtime_manager.running,60)
        settle()
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='final_flight'},ensure_ascii=False,indent=2),flush=True)
    assert report['passed']


if __name__=='__main__':main()

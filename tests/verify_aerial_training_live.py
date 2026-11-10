"""Owned Small City acceptance for aerial IR and raw-to-reviewed dataset workflow."""
import argparse,base64,json,math,os,time
from pathlib import Path

def main():
    assert 'aerial-ir-training-test-data' in os.environ.get('WISEYE_DATA_DIR','')
    import apps.desktop_app.main
    from PySide6.QtCore import QSettings,Qt
    from PySide6.QtWidgets import QApplication,QMessageBox
    from unittest.mock import patch
    from apps.desktop_app.main_window import MainWindow
    from training_client.workbench import Window
    from training_client.dataset_ui import ReviewDialog
    from training_client.dataset import scan
    from core.config import AppConfig
    from core.local_rpc import request
    out=Path('builds/aerial-ir-training-verified');out.mkdir(exist_ok=True)
    app=QApplication([]);QSettings.setDefaultFormat(QSettings.Format.IniFormat);QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,str(out/'qt'))
    w=MainWindow(AppConfig.load());w.show();t=None;report={'passed':False};airborne=False
    def settle(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:app.processEvents();time.sleep(.02)
    def wait(predicate,seconds=70):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            app.processEvents()
            try:
                if predicate():return
            except (OSError,ValueError):pass
            time.sleep(.05)
        raise TimeoutError('Aerial IR/training live acceptance timeout')
    def rpc(command,port=50051,**payload):
        r=request(port,command,payload,timeout=8);assert r['status']=='ok',r
        return r['payload']
    def state():return rpc('sim.get_state')
    def camera(ident='uav-01'):return next(d['aerial'] for d in state()['devices'] if d['id']==ident)
    def flight():return rpc('sim.get_state',50052,device_id='uav-01')
    def frame(channel,name=None,ident='uav-01'):
        r=request(50051,'camera.stream_frame',dict(device_id=ident,channel=channel),timeout=8)
        if r['status']!='ok':return None
        if name:(out/(name+'.jpg')).write_bytes(base64.b64decode(r['payload']['image_base64']))
        return r['payload']
    def configure(**changes):return rpc('aerial.configure',**dict(camera(),device_id='uav-01',**changes))
    try:
        w.launch_ue();wait(lambda:w.client.ready and w.air_client.ready and not w.loading_screen.active,900)
        run=state()['run_id'];report['run_id']=run;data=out/'dataset'/run
        wait(lambda:state()['population']['thermal_people_components']>0 and state()['population']['thermal_vehicle_components']>0,180)
        report['population_heat_components']=state()['population']['thermal_body_proxy_components']
        report['population_people_heat']=state()['population']['thermal_people_components']
        report['population_vehicle_heat']=state()['population']['thermal_vehicle_components']
        w.mission_workspace.open_aerial('uav-01');wait(lambda:w.aerial_dialog.valid)
        w.mission_workspace.modality.setCurrentIndex(2)
        wait(lambda:'uav-01/aerial_infrared' in w.gallery.frames and 'uav-01/aerial' in w.gallery.frames)
        vis=frame('AERIAL','aerial-visible');ir=frame('AERIAL_IR','aerial-infrared')
        assert (vis['width'],vis['height'])==(1920,1080) and (ir['width'],ir['height'])==(640,512)
        assert math.isclose(math.dist(vis['camera_position_cm'],ir['camera_position_cm']),6,abs_tol=.1)
        assert vis['pose_timing']==ir['pose_timing']=='capture_tick'
        assert 'environment' in vis and 'environment' in ir
        assert ir['training_eligible'] is False and ir['annotation_status']=='unavailable'
        report['independent_cameras']={'visible':{k:v for k,v in vis.items() if k!='image_base64'},'infrared':{k:v for k,v in ir.items() if k!='image_base64'}}
        second=camera('uav-02');configure(ir_black_hot=True,ir_blur_px=1.2)
        assert not camera('uav-02')['ir_black_hot'] and camera('uav-02')['ir_blur_px']==second['ir_blur_px']
        configure(ir_enabled=False);settle(.5)
        assert not camera()['infrared']['capture_allocated'] and camera()['capture_allocated']
        assert request(50051,'camera.stream_frame',dict(device_id='uav-01',channel='AERIAL_IR'))['error']['code']=='sensor_disabled'
        configure(ir_enabled=True,ir_black_hot=False,ir_blur_px=.8)
        wait(lambda:bool(frame('AERIAL_IR')))
        rpc('flight.takeoff',50052,device_id='uav-01');airborne=True;wait(lambda:not flight()['command_active']);assert flight()['flight_status']=='active'
        rpc('flight.set_mode',50052,device_id='uav-01',mode='manual')
        for _ in range(30):
            rpc('flight.set_input',50052,device_id='uav-01',forward=0,right=0,up=1,yaw=0);settle(.12)
        rpc('flight.set_input',50052,device_id='uav-01',forward=0,right=0,up=0,yaw=0)
        rpc('flight.hover',50052,device_id='uav-01');settle(1)
        origin=frame('AERIAL')['camera_position_cm'];heading=flight()['yaw_deg']
        def aim(point,fov):
            dx,dy,dz=[a-b for a,b in zip(point,origin)]
            pitch=max(-90,min(20,math.degrees(math.atan2(dz,math.hypot(dx,dy)))))
            return configure(pitch_deg=pitch,yaw_deg=(math.degrees(math.atan2(dy,dx))-heading+180)%360-180,ir_fov_deg=fov)
        other=next(d['position_cm'] for d in state()['devices'] if d['id']=='uav-02');aim(other,30);settle(1);frame('AERIAL_IR','other-drone-infrared')
        agents=rpc('population.get_agents')['vehicle']['samples']
        if agents:
            nearest=min(agents,key=lambda a:math.dist(origin,a['position_cm']));aim(nearest['position_cm'],55);report['ground_view_target']=nearest
        else:configure(pitch_deg=-45)
        settle(1);frame('AERIAL_IR','airborne-infrared')
        # Reuse actual device discovery over the same data-only gateway.
        t=Window(argparse.Namespace(host='127.0.0.1',port=50100,device='uav-01',output=data,sensor='both'));t.show();t.discover_sources()
        wait(lambda:t.discovery is None and t.source_picker.count()>1)
        index=next(i for i in range(t.source_picker.count()) if (t.source_picker.itemData(i) or {}).get('id')=='uav-01')
        t.source_picker.setCurrentIndex(index);assert t.source_kind.currentData()=='aerial'
        t.display_fps.setValue(15);t.start();wait(lambda:t.latest is not None and t.latest.get('raw'))
        assert t.tiles['infrared'].canvas.image.width()==640 and t.badge.text()=='航拍原图已连接'
        t.record.setChecked(True);wait(lambda:len(list((data).rglob('annotations/*.json')))>=4,35)
        t.grab().save(str(out/'training-collection.png'));t.record.setChecked(False);settle(.3);t.stop();wait(lambda:t.worker is None)
        rows=scan(data)['rows'];assert rows and all(r['state']=='待标注' for r in rows)
        assert not list((data).rglob('labels/*.txt'))
        # Exercise manual editing/storage only; this synthetic test box is not real GT.
        path=next(Path(r['path']) for r in rows if r['modality']=='infrared')
        review=ReviewDialog(path,t);review.show();review.canvas.boxes=[(1,[20,20,40,60])];review.commit();review.close()
        reviewed=json.loads(path.read_text(encoding='utf-8'));assert reviewed['annotation_source']=='manual' and reviewed['objects'][0]['class_id']==1
        t.dataset_panel.root.setText(str(data));t.workspace_tabs.setCurrentIndex(1);t.dataset_panel.start_scan();wait(lambda:t.dataset_panel.scanner is None)
        t.grab().save(str(out/'dataset-review.png'));t.workspace_tabs.setCurrentIndex(0)
        report['raw_samples']=len(rows);report['manual_review_workflow']=True;report['test_box_is_synthetic']=True
        # Legacy gimbal GT collection continues to work after switching source type.
        t.device.setText('ptz-01');t.source_kind.setCurrentIndex(0);t.display_fps.setValue(2);t.start();wait(lambda:t.latest is not None and not t.latest.get('raw'),50)
        assert all(p['annotation_status']=='complete' for p in t.latest['samples'].values());report['gimbal_gt_preserved']=True
        t.stop();wait(lambda:t.worker is None)
        w.mission_workspace.choose('observation');settle(3)
        assert not camera()['capture_allocated'] and not camera()['infrared']['capture_allocated']
        rpc('flight.land',50052,device_id='uav-01');wait(lambda:flight()['flight_status']=='ready',100);airborne=False
        assert state()['run_id']==run;w.grab().save(str(out/'simulator.png'));report['passed']=True
    finally:
        if t:
            t.record.setChecked(False);t.close();wait(lambda:t.worker is None,40)
        if airborne:
            try:rpc('flight.land',50052,device_id='uav-01');wait(lambda:flight()['flight_status']=='ready',100)
            except Exception as error:report['landing_error']=str(error)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):w.close()
        wait(lambda:not w.runtime_manager.running,140);report['owned_session_stopped']=True
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');app.quit()

if __name__=='__main__':main()

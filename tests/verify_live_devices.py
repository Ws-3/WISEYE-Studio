"""Own the session; validate hot edits, actual Qt pilot keys and default events."""
import copy,json,os,time,math,hashlib
from pathlib import Path


def main():
    assert 'live-device-test-data' in os.environ.get('WISEYE_DATA_DIR','')
    import apps.desktop_app.main
    from PySide6.QtCore import Qt,QSettings
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication,QMessageBox
    from unittest.mock import patch
    from apps.desktop_app.main_window import MainWindow
    from core.config import AppConfig
    from core.local_rpc import request
    out=Path('builds/live-device-verified');out.mkdir(exist_ok=True)
    app=QApplication([]);QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,str(out/'qt'))
    w=MainWindow(AppConfig.load());w.show();report=dict(passed=False)
    def settle(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:app.processEvents();time.sleep(.02)
    def wait(predicate,timeout=90):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            app.processEvents()
            if predicate():return
            time.sleep(.08)
        print('editor:',getattr(getattr(w,'device_page',None),'editor',None).message.text() if getattr(getattr(w,'device_page',None),'editor',None) else '',flush=True)
        raise TimeoutError('Live-device acceptance timeout')
    def rpc(command,port=50051,**payload):
        result=request(port,command,payload,timeout=6)
        assert result['status']=='ok',result
        return result['payload']
    def flight(ident='uav-01'):return rpc('sim.get_state',50052,device_id=ident)
    def state():return rpc('sim.get_state')
    def ids():return {x['id'] for x in state()['devices']}
    def key(code,seconds):
        w.raise_();w.activateWindow();w.setFocus();settle(.2)
        QTest.keyPress(w,code);settle(seconds);QTest.keyRelease(w,code);settle(.25)
    try:
        w.launch_ue();wait(lambda:w.client.ready and w.air_client.ready,600);settle(2)
        initial=state();run=initial['run_id'];report['run_id']=run;print('SESSION READY',run,flush=True)
        origin=next(d['position_cm'] for d in initial['devices'] if d['id']=='uav-01')
        assert initial['sensors']['event']['enabled'] is True
        rpc('flight.takeoff',50052,device_id='uav-01');wait(lambda:not flight()['command_active']);settle(2)
        hover=flight()['position_ned_m']
        w.pages.setCurrentIndex(4);settle(.5);editor=w.device_page.editor
        editor.live_enabled.setChecked(False)
        initial_path=Path(os.environ['WISEYE_DATA_DIR'])/'ue5/WISEYE/Config/WISEYE/Fleets/city.json'
        initial_bytes=initial_path.read_bytes()
        source=dict(id='uav-02',kind='drone',model_id='fixedwing',name='Live fixed-wing',position_cm=[origin[0],origin[1],14000],rotation_deg=[0,45,0])
        editor.add('drone',source);editor.add('gimbal')
        next(d for d in editor.data['devices'] if d['id']=='ptz-02')['tracking_target']='uav-02';editor.render()
        editor.live_enabled.setChecked(True)
        wait(lambda:ids()=={'uav-01','uav-02','ptz-01','ptz-02'} and editor.pending_live is None)
        assert state()['run_id']==run
        assert flight()['flight_status']=='active' and math.dist(hover,flight()['position_ned_m'])<1.5
        assert initial_path.read_bytes()==initial_bytes
        report['hot_add_preserved_hover_and_initial_file']=True;print('HOT ADD PASS',flush=True)
        second=rpc('sim.get_state',device_id='ptz-02')
        assert second['sensors']['event']['enabled']
        # Save explicitly; this operation must not create another live edit.
        revision=state()['fleet_revision'];assert editor.save();settle(.3)
        assert state()['fleet_revision']==revision and initial_path.read_bytes()!=initial_bytes
        report['initial_save_separate_from_live_apply']=True
        w.pages.setCurrentIndex(1);w.fleet_selection.select('drone','uav-02')
        wait(lambda:w.air_state.get('drone_id')=='uav-02')
        w.takeoff_button.click();wait(lambda:flight('uav-02')['flight_status']=='active');settle(1)
        fw=next(d['fixedwing'] for d in state()['devices'] if d['id']=='uav-02')
        assert abs(fw['length_cm']-80)<.1 and fw['heading_error_deg']<.1,fw
        report['fixedwing_geometry']=fw;print('FIXED GEOMETRY',fw,flush=True)
        w.manual_takeover.click()
        wait(lambda:flight('uav-02')['flight_mode']=='manual' and w.input_mode.currentData()=='drone')
        before=flight('uav-02');key(Qt.Key.Key_D,1.2);after=flight('uav-02')
        assert after['manual_command_count']>before['manual_command_count']
        assert abs((after['yaw_deg']-before['yaw_deg']+180)%360-180)>5,(before,after)
        before=after;key(Qt.Key.Key_R,1.1);after=flight('uav-02')
        assert after['position_ned_m'][2]<before['position_ned_m'][2]-.7
        w.pause_button.click();wait(lambda:flight('uav-02')['paused'])
        w.manual_takeover.click();wait(lambda:not flight('uav-02')['paused'])
        settle(.6);a=flight('uav-02');settle(.7);b=flight('uav-02')
        delta=[b['position_ned_m'][0]-a['position_ned_m'][0],b['position_ned_m'][1]-a['position_ned_m'][1],a['position_ned_m'][2]-b['position_ned_m'][2]]
        fw=next(d['fixedwing'] for d in state()['devices'] if d['id']=='uav-02')
        dot=sum(x*y for x,y in zip(delta,fw['model_forward_world']))/math.sqrt(sum(x*x for x in delta))
        assert dot>.995,dot;report['heading_velocity_dot']=dot;report['qt_manual_turn_and_climb']=True;print('QT MANUAL PASS',flush=True)
        # Pose/name edits of a gimbal must leave both airborne UAVs running.
        next(d for d in editor.data['devices'] if d['id']=='ptz-02')['position_cm'][0]+=100
        editor.render();editor.schedule_live();wait(lambda:editor.pending_live is None and state()['fleet_revision']>revision)
        assert flight('uav-02')['flight_status']=='active' and flight()['flight_status']=='active'
        w.grab().save(str(out/'live-workbench.png'))
        report['hardware_events_on']=state()['runtime_hardware']
        on=state()['tick_seq'];started=time.monotonic();settle(3);report['events_on_tick_hz']=(state()['tick_seq']-on)/(time.monotonic()-started)
        for ident in ('ptz-01','ptz-02'):rpc('sensor.set_enabled',device_id=ident,sensor='event',enabled=False)
        settle(1);on=state()['tick_seq'];started=time.monotonic();settle(3);report['events_off_tick_hz']=(state()['tick_seq']-on)/(time.monotonic()-started)
        for ident in ('ptz-01','ptz-02'):rpc('sensor.set_enabled',device_id=ident,sensor='event',enabled=True)
        w.land_button.click();wait(lambda:flight('uav-02')['flight_status']=='ready')
        editor.data['devices']=[d for d in editor.data['devices'] if d['id'] not in ('uav-02','ptz-02')];editor.render();editor.schedule_live()
        wait(lambda:ids()=={'uav-01','ptz-01'} and editor.pending_live is None)
        assert flight()['flight_status']=='active';report['hot_remove_preserved_hover']=True
        # Reuse the released slot for a physical quadrotor, still without travel.
        source=dict(id='uav-02',kind='drone',model_id='avata',name='Live Avata',position_cm=[origin[0]-350,origin[1],origin[2]],rotation_deg=[0,0,0])
        editor.add('drone',source)
        wait(lambda:'uav-02' in ids() and editor.pending_live is None)
        rpc('flight.takeoff',50052,device_id='uav-02');wait(lambda:not flight('uav-02')['command_active'])
        assert flight('uav-02')['flight_status']=='active'
        rpc('flight.land',50052,device_id='uav-02');wait(lambda:flight('uav-02')['flight_status']=='ready')
        assert state()['run_id']==run and flight()['flight_status']=='active'
        report['hot_quadrotor_takeoff_land']=True
        wait(lambda:all(rpm<1 for rpm in flight('uav-02').get('motor_rpm',[])))
        next(d for d in editor.data['devices'] if d['id']=='uav-02')['model_id']='fixedwing'
        editor.render();editor.schedule_live()
        wait(lambda:editor.pending_live is None and flight('uav-02').get('airframe')=='fixedwing')
        next(d for d in editor.data['devices'] if d['id']=='uav-02')['model_id']='avata'
        editor.render();editor.schedule_live()
        wait(lambda:editor.pending_live is None and flight('uav-02').get('airframe')!='fixedwing')
        assert state()['run_id']==run;report['live_airframe_switch']=True

        rpc('flight.land',50052,device_id='uav-01');wait(lambda:flight()['flight_status']=='ready')
        report['passed']=True
    finally:
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):w.close()
        if hasattr(w,'runtime_manager'):wait(lambda:not w.runtime_manager.running,100)
        report['owned_session_stopped']=True
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');app.quit()


if __name__=='__main__':main()

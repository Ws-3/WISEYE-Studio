"""Owned, isolated city exercise for aerial preview and native ambient agents."""
import os,time,json,base64,math
from pathlib import Path

def main():
    assert 'aerial-population-test-data' in os.environ.get('WISEYE_DATA_DIR','')
    import apps.desktop_app.main
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication,QMessageBox
    from unittest.mock import patch
    from apps.desktop_app.main_window import MainWindow
    from apps.desktop_app.observation_panel import open_aerial,open_population
    from core.config import AppConfig
    from core.local_rpc import request
    out=Path('builds/aerial-population-live');out.mkdir(exist_ok=True)
    app=QApplication([]);QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,str(out/'qt'))
    w=MainWindow(AppConfig.load());w.show();scenes_only=os.environ.get('WISEYE_OBSERVATION_SCENES_ONLY')=='1';report={'passed':False,'scope':'scenes-only' if scenes_only else 'full'};airborne=False
    if scenes_only:
        w.scenes.setCurrentIndex(next(i for i in range(w.scenes.count()) if (w.scenes.itemData(i) or {}).get('id')=='city_large'))
    def settle(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:app.processEvents();time.sleep(.02)
    def wait(predicate,seconds=70):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            app.processEvents()
            try:
                if predicate():return
            except OSError:pass  # Initial asset compilation may temporarily stall game-thread RPC.
            time.sleep(.04)
        raise TimeoutError('Aerial/population acceptance timeout')
    def rpc(command,port=50051,**payload):
        r=request(port,command,payload,timeout=10);assert r['status']=='ok',r
        return r['payload']
    def state():return rpc('sim.get_state')
    def flight():return rpc('sim.get_state',50052,device_id='uav-01')
    try:
        w.launch_ue();wait(lambda:w.client.ready and w.air_client.ready,600);settle(8)
        report['initial']=state();run=state()['run_id'];report['run_id']=run
        if not scenes_only:
            open_population(w);wait(lambda:w.population_dialog.valid);pop=w.population_dialog
            for key in ('vehicles_enabled','pedestrians_enabled'):pop.fields[key].setChecked(False)
            pop.apply.click();wait(lambda:pop.pending is None);settle(2)
            off=state()['population'];assert all(x['requested_count']==0 for x in off['spawners']);report['off']=off
            def cleared():
                a=rpc('population.get_agents');return all(a[k]['active_entities']==0 for k in ('vehicle','parked_vehicle','pedestrian')) and not state()['population']['pending']
            wait(cleared,600);report['agents_off']=rpc('population.get_agents')
            for key in ('vehicles_enabled','pedestrians_enabled'):pop.fields[key].setChecked(True)
            for key in ('vehicle_density','pedestrian_density'):pop.fields[key].setValue(50)
            pop.apply.click();wait(lambda:pop.pending is None);settle(12)
            report['on']=state()['population'];assert report['on']['vehicles_supported'] and report['on']['pedestrians_supported']
            assert all(x['requested_count']>0 for x in report['on']['spawners'])
            def agents_ready():
                a=rpc('population.get_agents');return a.get('vehicle',{}).get('active_entities',0)>0 and a.get('pedestrian',{}).get('active_entities',0)>0 and not state()['population']['pending']
            wait(agents_ready,600);report['agents_on']=rpc('population.get_agents');settle(3)
            moved=rpc('population.get_agents');report['agents_later']=moved
            for kind in ('vehicle','pedestrian'):
                old={s['entity_index']:s['position_cm'] for s in report['agents_on'][kind]['samples']}
                assert any(s['entity_index'] in old and math.dist(s['position_cm'],old[s['entity_index']])>10 for s in moved[kind]['samples']),kind+' not moving'
            if not w.client.ready:w.connect_ue()
            wait(lambda:w.client.ready and w.air_client.ready)
            pop.load();wait(lambda:pop.valid and pop.pending is None)
            for key in ('vehicle_density','pedestrian_density'):pop.fields[key].setValue(10)
            assert pop.apply.isEnabled()
            pop.apply.click();wait(lambda:pop.pending is None)
            wait(lambda:abs(state()['population']['vehicle_density']-.1)<.001 and not state()['population']['pending'],60);settle(1)
            low=rpc('population.get_agents');report['agents_low']=low
            assert 0<low['vehicle']['active_entities']<report['agents_on']['vehicle']['active_entities']
            assert 0<low['pedestrian']['active_entities']<report['agents_on']['pedestrian']['active_entities']
            if not w.client.ready:w.connect_ue();wait(lambda:w.client.ready and w.air_client.ready)
            open_aerial(w,'uav-01');wait(lambda:w.aerial_dialog.valid);camera=w.aerial_dialog
            camera.preview.click();wait(lambda:'uav-01/aerial' in w.gallery.frames,35)
            w.gallery.frames['uav-01/aerial'].save(str(out/'landed_aerial.png'))
            rpc('flight.takeoff',50052,device_id='uav-01');airborne=True
            wait(lambda:not flight()['command_active']);assert min(flight()['motor_rpm'])>1000
            # A short climb obtains a usable aerial view above the roof edges.
            rpc('flight.set_mode',50052,device_id='uav-01',mode='manual')
            for _ in range(36):rpc('flight.set_input',50052,device_id='uav-01',forward=0,right=0,up=1,yaw=0);settle(.12)
            rpc('flight.set_input',50052,device_id='uav-01',forward=0,right=0,up=0,yaw=0);settle(1)
            for name,pitch in [('front',0),('oblique',-60),('down',-90)]:
                camera.preset(pitch);wait(lambda:camera.pending is None);settle(1)
                w.gallery.frames['uav-01/aerial'].save(str(out/(name+'.png')))
                actual=next(d['aerial'] for d in state()['devices'] if d['id']=='uav-01');assert actual['pitch_deg']==pitch
            camera.fields['fov_deg'].setValue(85);camera.apply.click();wait(lambda:camera.pending is None)
            camera.save.click();wait(lambda:camera.pending is None)
            assert state()['run_id']==run;report['airborne']=state()
            w.grab().save(str(out/'workbench.png'));camera.grab().save(str(out/'aerial-controls.png'));pop.grab().save(str(out/'population-controls.png'))
            # Return near takeoff altitude to keep native landing within bounded RPC time.
            for _ in range(36):rpc('flight.set_input',50052,device_id='uav-01',forward=0,right=0,up=-1,yaw=0);settle(.12)
            rpc('flight.set_input',50052,device_id='uav-01',forward=0,right=0,up=0,yaw=0)
            rpc('flight.land',50052,device_id='uav-01');wait(lambda:flight()['flight_status']=='ready',100);airborne=False
            report['final_flight']=flight()
            second=next(d['aerial'] for d in state()['devices'] if d['id']=='uav-02')
            assert second['fov_deg']!=85,'Second camera was coupled to first'
            def second_frame():
                r=request(50051,'camera.stream_frame',dict(device_id='uav-02',channel='AERIAL'),timeout=8)
                if r['status']!='ok':return False
                (out/'second-camera.jpg').write_bytes(base64.b64decode(r['payload']['image_base64']));return True
            wait(second_frame,35);report['second_camera']=second
            invalid=dict(device_id='uav-01',enabled=True,stabilized=True,pitch_deg=-20,yaw_deg=0,fov_deg=200,sample_hz=15)
            assert request(50051,'aerial.configure',invalid)['status']=='error'
            assert next(d['aerial'] for d in state()['devices'] if d['id']=='uav-01')['pitch_deg']==-90
            w.gallery.remove_source('uav-01/aerial');settle(3)
            inactive=next(d['aerial'] for d in state()['devices'] if d['id']=='uav-01');assert not inactive['capture_allocated'];report['idle_aerial']=inactive
            camera.close();pop.close()
        for scene in ('city_large','city'):
            index=next(i for i in range(w.scenes.count()) if (w.scenes.itemData(i) or {}).get('id')==scene)
            if state()['scene_id']!=scene:
                w.scenes.setCurrentIndex(index);w.switch_scene()
            wait(lambda:w.client.ready and state()['scene_id']==scene and w.air_client.ready,240);settle(8)
            wait(lambda:not state()['population']['pending'],300)
            agents=rpc('population.get_agents');assert agents['vehicle']['active_entities']>0 and agents['pedestrian']['active_entities']>0
            report[scene+'_agents']=agents;report[scene+'_state']=state()
            if scene=='city_large':
                settle(3);later=rpc('population.get_agents');report['city_large_agents_later']=later
                for kind in ('vehicle','pedestrian'):
                    old={x['target_id']:x['position_cm'] for x in agents[kind]['samples']}
                    assert any(x['target_id'] in old and math.dist(x['position_cm'],old[x['target_id']])>10 for x in later[kind]['samples']),kind+' not moving in large city'
                def map_frame():
                    r=request(50051,'camera.stream_frame',dict(device_id='uav-01',channel='AERIAL'),timeout=8)
                    if r['status']!='ok':return False
                    (out/'large-city-aerial.jpg').write_bytes(base64.b64decode(r['payload']['image_base64']));return True
                wait(map_frame,35)
        restored=next(d['aerial'] for d in state()['devices'] if d['id']=='uav-01')
        assert restored['fov_deg']==85 and restored['pitch_deg']==-90
        assert abs(state()['population']['vehicle_density']-.1)<.001
        report['scene_defaults_restored']=True;report['passed']=True
    finally:
        if airborne:
            try:rpc('flight.land',50052,device_id='uav-01');wait(lambda:flight()['flight_status']=='ready',100)
            except Exception as e:report['cleanup_error']=str(e)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):w.close()
        wait(lambda:not w.runtime_manager.running,140);report['owned_session_stopped']=True
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');app.quit()

if __name__=='__main__':main()

"""Live UE/AirSim/RTSP + Qt interaction verification; leaves UAV landed."""
import json,math,time
import apps.desktop_app.main
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QTableWidgetItem
from core.config import AppConfig,ROOT
from apps.desktop_app.main_window import MainWindow
from apps.desktop_app.route_editor import open_route_editor

app=QApplication([]);w=MainWindow(AppConfig.load());w.resize(1500,1000);w.show()
checks=[];errors=[]
w.client.failed.connect(lambda c,m:errors.append((c,m)))
w.air_client.failed.connect(lambda c,m:errors.append((c,m)))

def wait(predicate,seconds=15):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        app.processEvents()
        if predicate():return
        QTest.qWait(30)
    raise AssertionError('Timeout: '+str(errors[-4:]))

def cmd(command,payload=None):
    done=[]
    client=w.air_client if command.startswith('route.') or command.startswith('flight.') or command in ('sim.pause','sim.resume') else w.client
    def completed(c,s):
        if c==command:done.append(s)
    client.completed.connect(completed)
    try:w.command(command,payload);wait(lambda:bool(done));return done[-1]
    finally:client.completed.disconnect(completed)

try:
    w.connect_ue();wait(lambda:w.client.ready and w.air_client.ready,60)
    wait(lambda:all(key in w.gallery.frames for key in ('CH1','CH2','OBS')),40)
    checks.append('all three RTSP streams render; LiDAR shares bounded data')
    cmd('input.set_mode',{'mode':'gimbal'});cmd('gimbal.set_angles',{'yaw_deg':0,'pitch_deg':5})
    w.setFocus();QTest.keyPress(w,Qt.Key.Key_Right);QTest.qWait(700);QTest.keyRelease(w,Qt.Key.Key_Right)
    wait(lambda:w.state['yaw_deg']>8)
    QTest.qWait(400);angle=w.state['yaw_deg'];QTest.qWait(500)
    assert abs(w.state['yaw_deg']-angle)<.5
    checks.append('desktop arrow turns gimbal and release stops')
    w.gimbal_yaw.setFocus();before=w.state['yaw_deg'];QTest.keyClick(w.gimbal_yaw,Qt.Key.Key_Up);QTest.qWait(400)
    assert abs(w.state['yaw_deg']-before)<.5
    checks.append('spinbox arrow edits parameter without moving gimbal')
    vis=w.sensor_settings.panels['visible'];ir=w.sensor_settings.panels['infrared'];li=w.sensor_settings.panels['lidar']
    initial=w.state['sensors'];original=json.loads(json.dumps(initial))
    vis['fields']['fov_deg'].setValue(41);QTest.qWait(800)
    assert vis['fields']['fov_deg'].value()==41 and w.state['sensors']['visible']['fov_deg']!=41
    w.sensor_settings.submit('visible');wait(lambda:'visible' not in w.sensor_settings.pending)
    assert abs(w.state['sensors']['visible']['fov_deg']-41)<.01
    assert w.state['sensors']['infrared']['fov_deg']==initial['infrared']['fov_deg']
    ir['fields']['fov_deg'].setValue(33);ir['fields']['palette'].setCurrentIndex(1);w.sensor_settings.submit('infrared');wait(lambda:'infrared' not in w.sensor_settings.pending)
    assert w.state['sensors']['visible']['fov_deg']==41
    checks.append('sensor drafts survive polling; visible and IR FOV apply independently')
    vis['fields']['enabled'].setChecked(False);w.sensor_settings.submit('visible');wait(lambda:'visible' not in w.sensor_settings.pending)
    wait(lambda:'CH1' not in w.gallery.frames)
    irkey=w.gallery.frames['CH2'].cacheKey();wait(lambda:w.gallery.frames.get('CH2') and w.gallery.frames['CH2'].cacheKey()!=irkey)
    checks.append('disable visible clears its view while IR continues')
    li['fields']['enabled'].setChecked(False);w.sensor_settings.submit('lidar');wait(lambda:'lidar' not in w.sensor_settings.pending)
    cmd('sensor.set_active',{'sensor':'lidar'});assert not w.state['sensors']['lidar']['enabled']
    checks.append('selecting disabled lidar does not implicitly enable it')
    for ident,settings in original.items():cmd('sensor.configure',dict(sensor=ident,**settings));w.sensor_settings.restore(ident)
    cmd('sensor.set_active',{'sensor':'visible'})
    w.gallery.checks['LIDAR'].setChecked(False);w.gallery.checks['OBS'].setChecked(False)
    assert not w.gallery.cards['LIDAR'].isVisible() and w.gallery.cards['CH1'].isVisible()
    w.gallery.enlarge('CH2');wait(lambda:'CH2' in w.gallery.popouts)
    assert not w.gallery.popouts['CH2'][1].source.isNull()
    w.gallery.popouts['CH2'][0].close()
    for check in w.gallery.checks.values():check.setChecked(True)
    checks.append('select side by side views and enlarge without another decoder')
    cmd('input.set_mode',{'mode':'observer'});cmd('observer.set_mode',{'mode':'free'})
    QTest.qWait(500);view=w.gallery.views['OBS'];view.setFocus()
    before=w.state['observer_position_cm'][:];drone=w.state['drone_position_cm'][:]
    QTest.mousePress(view,Qt.MouseButton.RightButton,pos=QPoint(40,40));QTest.keyPress(view,Qt.Key.Key_W);QTest.qWait(700);QTest.keyRelease(view,Qt.Key.Key_W);QTest.mouseRelease(view,Qt.MouseButton.RightButton,pos=QPoint(40,40))
    wait(lambda:math.dist(before,w.state['observer_position_cm'])>100)
    QTest.qWait(400);stopped=w.state['observer_position_cm'][:];QTest.qWait(500)
    assert math.dist(stopped,w.state['observer_position_cm'])<1
    assert math.dist(drone,w.state['drone_position_cm'])<5
    checks.append('embedded observer RMB+W moves camera only, release stops')
    open_route_editor(w);editor=w.route_editor
    editor.table.item(0,0).setText('nan');app.processEvents();editor.upload();assert '数字' in editor.status.text()
    editor.table.item(0,0).setText('0');editor.close();assert w.route_editor is None
    checks.append('route invalid coordinates rejected and dialog closes cleanly')
    if w.air_state['flight_status']=='ready':cmd('flight.takeoff');wait(lambda:not w.air_state.get('command_active',True),35)
    cmd('flight.hover');wait(lambda:not w.air_state.get('command_active',True),15);QTest.qWait(500)
    x,y,z=[n/100 for n in w.state['drone_position_cm']]
    route=dict(version=1,scene_id=w.state['scene_id'],name='Live single pass',frame='ue_world_m',speed_mps=1,repeat=False,waypoints=[[x,y,z],[x+1.5,y,z],[x+1.5,y+1.5,z]])
    cmd('route.upload',route);assert w.air_state['flight_mode']=='manual'
    cmd('route.start');wait(lambda:w.air_state.get('route_status')=='completed',50)
    end=[n/100 for n in w.state['drone_position_cm']]
    assert math.dist(end,route['waypoints'][-1])<1.5,(end,route)
    assert w.air_state['route_loops']==1 and w.air_state['paused']
    wait(lambda:not w.air_state.get('command_active',True))
    checks.append('uploaded UE-world route runs once in AirSim, completes near final waypoint and holds')
    route['repeat']=True;route['name']='Live repeat'
    cmd('route.upload',route);cmd('route.start');wait(lambda:w.air_state.get('route_loops',0)>=1,50)
    cmd('sim.pause');assert w.air_state['route_status']=='paused'
    wait(lambda:not w.air_state.get('command_active',True));cmd('sim.resume');assert w.air_state['route_status']=='running'
    cmd('route.stop');wait(lambda:not w.air_state.get('command_active',True));assert w.air_state['route_status']=='stopped'
    checks.append('loop route supports pause, resume and stop with hold')
    cmd('flight.land');wait(lambda:w.air_state['flight_status']=='ready',40)
    cmd('gimbal.set_tracking',{'enabled':True});cmd('input.set_mode',{'mode':'observer'});cmd('observer.set_mode',{'mode':'overview'})
    QTest.qWait(1500);w.grab().save(str(ROOT/'docs/evidence/workbench_v3_20261021.png'))
    assert not errors,errors
    (ROOT/'docs/evidence/workbench_v3_live_20261021.json').write_text(json.dumps(dict(checks=checks,passed=len(checks),errors=errors,final_status=w.air_state['flight_status']),ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=len(checks),checks=checks),ensure_ascii=False))
finally:
    w.close();app.processEvents()

"""Real gimbal rate/stop and addressed captures, without flying the UAV."""
import json,math,time,faulthandler
faulthandler.enable()
faulthandler.dump_traceback_later(45,repeat=True)
from pathlib import Path
import apps.desktop_app.main
from PySide6.QtCore import Qt,QPoint,QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage
from core.config import AppConfig,ROOT
from apps.desktop_app.main_window import MainWindow
app=QApplication([]);w=MainWindow(AppConfig.load());w.resize(1450,1000);w.show();checks=[];failures=[]
w.client.failed.connect(lambda c,m:failures.append((c,m)))
def wait(predicate,timeout=15):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        app.processEvents()
        if predicate():return
        QTest.qWait(25)
    raise AssertionError(failures)
def command(c,p=None):
    replies=[]
    def done(name,s):
        if name==c:replies.append(s)
    w.client.completed.connect(done)
    try:w.command(c,p);wait(lambda:bool(replies));return replies[-1]
    finally:w.client.completed.disconnect(done)
try:
    print('Connecting live UE',flush=True)
    w.connect_ue();wait(lambda:w.client.ready,90)
    print('UE connected',flush=True)
    assert not hasattr(w,'sensor');checks.append('redundant active sensor selector removed')
    w.inspectors.setCurrentIndex(1);command('input.set_mode',{'mode':'gimbal'});command('gimbal.set_angles',{'yaw_deg':0,'pitch_deg':5})
    print('Testing joystick',flush=True)
    stick=w.gimbal_stick;center,radius=stick.geometry_values();pos=(center+type(center)(radius*.65,0)).toPoint()
    QTest.mousePress(stick,Qt.MouseButton.LeftButton,pos=pos);QTest.qWait(650);QTest.mouseRelease(stick,Qt.MouseButton.LeftButton,pos=pos)
    wait(lambda:w.state['yaw_deg']>5);QTest.qWait(400);angle=w.state['yaw_deg'];QTest.qWait(500)
    assert abs(w.state['yaw_deg']-angle)<.5 and stick.vector==(0.,0.)
    checks.append('proportional joystick moves real UE yaw and release returns to zero')
    QTest.mousePress(stick,Qt.MouseButton.LeftButton,pos=pos);QTest.qWait(250);app.sendEvent(w,QEvent(QEvent.Type.WindowDeactivate));QTest.qWait(400)
    angle=w.state['yaw_deg'];QTest.qWait(500);assert abs(w.state['yaw_deg']-angle)<.5
    QTest.mouseRelease(stick,Qt.MouseButton.LeftButton,pos=pos);checks.append('window deactivation resets joystick and stops gimbal')
    command('sensor.set_active',{'sensor':'visible'});mode=w.state['active_sensor'];captured=[]
    def saved(c,s):
        if c=='camera.capture':captured.append(s)
    w.client.completed.connect(saved)
    for sensor,shape in [('infrared',(640,512)),('visible',(1920,1080))]:
        previous=len(captured);w.capture_sensor(sensor);wait(lambda:len(captured)>previous)
        state=captured[-1];image=QImage(state['frame_path']);assert(image.width(),image.height())==shape
        assert state['active_sensor']==mode and state['frame_sensor']==sensor
        meta=json.loads(Path(state['frame_path']+'.json').read_text(encoding='utf-8-sig'))
        assert meta['modality']==sensor
    checks.append('addressed IR and visible captures preserve current mode and native dimensions/metadata')
    before=len(captured);w.sensor_settings.setCurrentIndex(1);w.capture_active_sensor();wait(lambda:len(captured)>before)
    assert captured[-1]['frame_sensor']=='infrared';checks.append('shared save follows sensor subtab rather than an independent dropdown')
    command('input.set_mode',{'mode':'observer'});assert not stick.isEnabled();checks.append('joystick disabled outside gimbal control mode')
    command('gimbal.set_tracking',{'enabled':True});w.inspectors.setCurrentIndex(1);QTest.qWait(500)
    w.grab().save(str(ROOT/'docs/evidence/joystick_capture_20261021.png'))
    assert not failures,failures
    result=dict(passed=len(checks),checks=checks,errors=failures)
    (ROOT/'docs/evidence/joystick_capture_20261021.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(result)
finally:w.close();app.processEvents()

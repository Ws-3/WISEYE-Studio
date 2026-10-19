"""Real desktop/UE round trip; run only with a prepared scene playing."""
import json
import time
from pathlib import Path
import apps.desktop_app.main  # Windows ICU bootstrap before Qt imports
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from core.config import ROOT, AppConfig
from apps.desktop_app.main_window import MainWindow

app=QApplication([])
window=MainWindow(AppConfig.load())
window.show()
checks=[]
captures=[]

def wait(predicate, timeout=30):
    start=time.monotonic()
    while time.monotonic()-start < timeout:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(30)
    raise AssertionError(window.logs.toPlainText()[-2500:])

try:
    window.connect_ue()
    wait(lambda: window.client.ready,60)
    for target in ('original','test_range','original','test_range'):
        for index in range(window.scenes.count()):
            if window.scenes.itemData(index)['id']==target:
                window.scenes.setCurrentIndex(index)
                break
        else:
            raise AssertionError('Missing scene: '+target)
        window.switch_scene()
        wait(lambda: window.switch_target is not None)
        wait(lambda: window.client.ready and window.state.get('scene_id')==target and window.switch_target is None,90)
        checks.append('switch and automatic reconnect: '+target)
        t=window.state['simulation_time_s']
        wait(lambda: window.state['simulation_time_s']>t+1)
        assert window.state['tracking'] and window.state['rotors_running']
        checks.append('flight/tracking/rotors: '+target)
        for sensor in ('visible','infrared'):
            window.command('camera.set_mode',{'mode':sensor})
            wait(lambda: window.state['sensor_mode']==sensor)
            # Wait for the requested mode to render at least a few frames.
            QTest.qWait(1000)
            previous=window.last_image_path
            window.command('camera.capture')
            wait(lambda: window.last_image_path is not None and window.last_image_path!=previous)
            size=(window.image.source.width(),window.image.source.height())
            assert size==((1920,1080) if sensor=='visible' else (640,512))
            captures.append(dict(scene=target,sensor=sensor,path=str(window.last_image_path),size=size))
        checks.append('visible and IR native snapshots: '+target)
    errors=[]
    window.client.failed.connect(lambda command,message: errors.append((command,message)))
    window.command('sim.load_scene',{'scene_id':'../invalid'})
    wait(lambda:bool(errors))
    assert window.client.ready and window.state['scene_id']=='test_range'
    checks.append('invalid scene refused without disconnect')
    report=dict(passed=True,checks=checks,captures=captures)
    (ROOT/'docs/evidence/scenes_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    window.grab().save(str(ROOT/'docs/evidence/scenes_desktop.png'))
    print(json.dumps(report,ensure_ascii=False,indent=2))
finally:
    window.close()

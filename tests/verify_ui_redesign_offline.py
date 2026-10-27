"""Qt-only checks for draft failures, input focus and scaled-window layout."""
import os
import sys
import json
import copy
from unittest.mock import patch
scale=float(sys.argv[1]) if len(sys.argv)>1 else 1.
os.environ['QT_SCALE_FACTOR']=str(scale)
import apps.desktop_app.main
from PySide6.QtCore import Qt,QSettings
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtTest import QTest
from core.config import AppConfig,ROOT
from apps.desktop_app.main_window import MainWindow
from apps.desktop_app.workbench_v3 import show_properties

app=QApplication([])
store=QSettings('WISEYE','Studio')
preferences={k:store.value(k) for k in ('workspace/v3','workbench/split')}
w=MainWindow(AppConfig.load())
checks=[]
try:
    available=app.primaryScreen().availableGeometry()
    w.resize(min(1600,available.width()-40),max(640,min(900,available.height()-60)))
    w.show();w.gallery.reset_layout();QTest.qWait(200)
    show_properties(w,'sensor','ptz-01/infrared')
    assert w.gallery.width()>=450 and w.sensor_settings.width()>=260
    assert w.width()<=available.width() and w.height()<=available.height()
    checks.append('layout fits scaled available screen; parameter inspector remains usable')
    forms=w.sensor_settings
    sample={'gimbal_id':'ptz-01','sensors':{'visible':dict(enabled=True,fov_deg=25)}}
    forms.update_state(sample);forms.panels['visible']['fields']['fov_deg'].setValue(38)
    forms.stash()
    forms.pending['test-request']=dict(key=('ptz-01','visible'),snapshot=dict(enabled=True,fov_deg=38),generation=forms.generation)
    forms.select_device('ptz-02')
    forms.update_state({'gimbal_id':'ptz-02','sensors':{'visible':dict(enabled=True,fov_deg=45)}})
    forms.panels['visible']['fields']['fov_deg'].setValue(52)
    forms.rejected('unknown-request','sensor.configure',{},'rejected')
    assert 'test-request' in forms.pending
    forms.rejected('test-request','sensor.configure',{},'UE 响应超时，操作结果未确认')
    assert forms.values('visible')['fov_deg']==52 and forms.panels['visible']['confirmed']['fov_deg']==45
    forms.select_device('ptz-01')
    assert forms.values('visible')['fov_deg']==38 and '待确认' in forms.panels['visible']['status'].text()
    forms.disconnected();assert forms.values('visible')['fov_deg']==38 and forms.panels['visible']['confirmed'] is None
    checks.append('unknown or timed-out request cannot alter another device; disconnect retains drafts and invalidates actual values')
    with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Cancel):w.close()
    assert w.isVisible()
    checks.append('canceling the unsaved-draft exit prompt keeps the window open')
    before=list(w.gallery.sources)
    w.gallery.add_source('ptz-02/infrared')
    assert w.gallery.sources==before
    w.gallery.enlarge('ptz-01/infrared')
    w.gallery.add_source('ptz-02/infrared',replace='ptz-01/infrared')
    assert w.gallery.sources==before,'popout reference bypassed four-source cap'
    w.gallery.popouts['ptz-01/infrared'][0].close()
    w.gallery.swap(before[0],before[1]);w.gallery.save_layout()
    saved=json.loads(store.value('workspace/v3'))
    assert saved['sources'][0]==before[1] and 'control' not in saved
    w.gallery.reset_layout()
    checks.append('four-view cap and layout order persist without control ownership')
    show_properties(w,'sensor','ptz-01/infrared');QTest.qWait(250)
    path=f'docs/evidence/ui_redesign_dpi_{round(scale*100)}_20261021.png'
    w.grab().save(str(ROOT/path))
    report=dict(success=True,checks=checks,scale=scale,device_pixel_ratio=w.devicePixelRatioF(),logical_window=[w.width(),w.height()],available=[available.width(),available.height()],screenshot=path)
    (ROOT/f'docs/evidence/ui_redesign_dpi_{round(scale*100)}_20261021.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report,ensure_ascii=False))
finally:
    with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):w.close()
    app.processEvents()
    for key,value in preferences.items():
        if value is None:store.remove(key)
        else:store.setValue(key,value)

"""Real UE terrain picking, named preset and AirSim reload acceptance."""
import ctypes
from ctypes import wintypes
import json
import math
import socket
import time
import uuid
import apps.desktop_app.main
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from core.config import ROOT, AppConfig
from apps.desktop_app.main_window import MainWindow

app=QApplication([])
window=MainWindow(AppConfig.load())
window.show()
page=window.arrangement
tools=page.tools
checks=[]
report=dict(passed=False,checks=checks)
active=page.store.directory/'original.json'
before=active.read_bytes() if active.exists() else None
created=[]
modified=False


def wait(predicate,timeout=20):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        app.processEvents()
        if predicate(): return
        QTest.qWait(25)
    raise AssertionError(page.message.text()+'\n'+window.logs.toPlainText()[-1600:])


def request(command,payload):
    with socket.create_connection(('127.0.0.1',50051),timeout=5) as peer:
        peer.sendall((json.dumps(dict(version=1,request_id='placement-test',command=command,payload=payload))+'\n').encode())
        return json.loads(peer.makefile('rb').readline())


def restore_layout():
    if before is None:
        active.unlink(missing_ok=True)
    else:
        active.write_bytes(before)


try:
    window.connect_ue()
    wait(lambda:window.client.ready and window.air_client.ready,60)
    window.pages.setCurrentIndex(0)
    wait(lambda:tools.snap.isEnabled())
    QTest.qWait(2500)  # Allow an unarmed robot to settle onto terrain after world creation.
    original=tools.draft()
    p0=list(window.state['drone_position_cm'])
    g0=list(window.state['gimbal_position_cm'])
    page.coordinates['flight_origin_cm'][0].setValue(original['flight_origin_cm'][0]/100+2)
    page.coordinates['flight_origin_cm'][1].setValue(original['flight_origin_cm'][1]/100+1)
    tools.request('placement.snap')
    wait(lambda:tools.pending is None and '写入草稿' in page.message.text())
    placement=window.state['placement']
    assert abs(placement['position_cm'][2]-placement['surface_cm'][2]-25)<.01
    assert math.dist(window.state['drone_position_cm'],p0)<1
    assert math.dist(window.state['gimbal_position_cm'],g0)<.01
    checks.append('UE surface snap writes draft with clearance and never teleports live actors')

    payload=dict(scene_id='original',device_id='uav-01',request_token='invalid',clearance_cm=25,position_cm=[1e9,0,0])
    assert request('placement.snap',payload)['status']=='error'
    assert request('placement.begin',dict(payload,scene_id='test_range'))['status']=='error'
    assert request('placement.begin',dict(payload,device_id='unknown'))['status']=='error'
    assert request('placement.snap',dict(payload,position_cm=[9000000,9000000,0]))['status']=='error'
    checks.append('bad coordinates, missing terrain, scene mismatch and unknown device rejected')

    snapped=tools.draft()
    tools.name.setText('验收预设_'+uuid.uuid4().hex[:8])
    tools.save_named(False)
    ident=tools.presets.currentData()
    assert ident
    created.append(page.store.directory/'Presets/original'/f'{ident}.json')
    page.coordinates['flight_origin_cm'][0].setValue(0)
    tools.select_preset()
    assert abs(tools.draft()['flight_origin_cm'][0]-snapped['flight_origin_cm'][0])<.01
    assert not active.exists() if before is None else active.read_bytes()==before
    tools.name.setText(tools.name.text()+'_更新')
    tools.save_named(True)
    assert page.store.load_preset('original',ident)['name']==tools.name.text()
    checks.append('named preset save/read/update stays separate from active layout')

    tools.request('placement.begin')
    wait(lambda:window.state.get('placement',{}).get('active'))
    token=tools.pending['token']
    assert request('placement.cancel',dict(scene_id='original',request_token='stale'))['status']=='error'
    tools.cancel_pending()
    wait(lambda:not window.state.get('placement',{}).get('active'))
    assert tools.draft()==snapped
    checks.append('cancellation clears pick; stale request token cannot cancel current request')
    tools.request('placement.begin')
    wait(lambda:window.state.get('placement',{}).get('active'))
    window.client.disconnect_from()
    assert tools.pending is None
    window.connect_ue()
    wait(lambda:window.client.ready and tools.cancel.isEnabled())
    tools.cancel_pending(include_remote=True)
    wait(lambda:not window.state.get('placement',{}).get('active'))
    assert tools.draft()==snapped
    checks.append('disconnect discards pending result; reconnect can cancel abandoned UE pick')

    # Focus a real running UE viewport and click an actual scene surface.
    u=ctypes.windll.user32
    u.FindWindowW.restype=wintypes.HWND
    u.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
    u.SetForegroundWindow.argtypes=[wintypes.HWND]
    hwnd=u.FindWindowW(None,'test - 虚幻编辑器')
    assert hwnd
    tools.request('placement.begin')
    wait(lambda:window.state.get('placement',{}).get('active'))
    u.ShowWindow(hwnd,9)
    u.keybd_event(0x12,0,0,0)
    u.SetForegroundWindow(hwnd)
    u.keybd_event(0x12,0,2,0)
    rect=wintypes.RECT()
    assert u.GetWindowRect(hwnd,ctypes.byref(rect))
    for rx,ry in ((.46,.5),(.40,.52),(.5,.42)):
        u.SetCursorPos(int(rect.left+(rect.right-rect.left)*rx),int(rect.top+(rect.bottom-rect.top)*ry))
        QTest.qWait(350)
        u.mouse_event(0x0002,0,0,0,0)
        QTest.qWait(100)
        u.mouse_event(0x0004,0,0,0,0)
        QTest.qWait(700)
        if tools.pending is None: break
    wait(lambda:tools.pending is None,4)
    assert window.state['placement']['has_result'],window.state['placement']
    report['clicked_surface_cm']=window.state['placement']['surface_cm']
    checks.append('real left mouse click in UE selects surface and returns coordinates to desktop')

    tools.device.setCurrentIndex(1)
    tools.request('placement.snap')
    wait(lambda:tools.pending is None and '写入草稿' in page.message.text())
    report['gimbal_anchor_minus_surface_cm']=window.state['placement']['position_cm'][2]-window.state['placement']['surface_cm'][2]
    expected_surface=window.state['placement']['surface_cm'][2]
    # Restore the stable near-origin UAV snap before the actual reload test.
    for value,spin in zip(snapped['flight_origin_cm'],page.coordinates['flight_origin_cm']):
        spin.setValue(value/100)
    run_id=window.state['run_id']
    page.save()
    modified=True
    desired=tools.draft()
    window.switch_scene()
    wait(lambda:window.state.get('run_id') not in (None,run_id) and window.air_state.get('run_id')==window.state.get('run_id') and window.air_client.ready,100)
    assert abs(window.air_state['position_ned_m'][0]-desired['flight_origin_cm'][0]/100)<.05
    assert math.dist(window.state['gimbal_position_cm'],desired['gimbal_location_cm'])<.15
    checks.append('saved snapped placement recreates actual AirSim drone and gimbal after scene reload')
    window.command('gimbal.set_angles',dict(yaw_deg=0,pitch_deg=0))
    wait(lambda:abs(window.state['pitch_deg'])<.01 and not window.state['tracking'])
    (ROOT/'runtime/placement_expected.json').write_text(json.dumps(dict(surface_z_cm=expected_surface)),encoding='utf-8')
    geometry_file=ROOT/'runtime/placement_geometry_validation.json'
    stamp=time.time()
    (ROOT/'runtime/editor-request.py').write_text("from pathlib import Path\nexec(Path('"+str(ROOT/'ue5/scripts/validate_surface_placement.py').replace('\\','/')+"').read_text(encoding='utf-8'))",encoding='utf-8')
    wait(lambda:geometry_file.exists() and geometry_file.stat().st_mtime>=stamp,12)
    report['geometry']=json.loads(geometry_file.read_text(encoding='utf-8'))
    assert report['geometry']['passed'],report['geometry']
    checks.append('actual gimbal base rests on the surface while its 80 cm reference height is preserved')
    restore_layout()
    modified=False
    run_id=window.state['run_id']
    window.switch_scene()
    wait(lambda:window.state.get('run_id') not in (None,run_id) and window.air_state.get('run_id')==window.state.get('run_id') and window.air_client.ready,100)
    page.load()
    window.pages.setCurrentIndex(0)
    window.grab().save(str(ROOT/'docs/evidence/placement_presets_20261019.png'))
    report['passed']=True
finally:
    if modified: restore_layout()
    for path in created:
        path.unlink(missing_ok=True)
    window.close()
    (ROOT/'runtime/placement_live_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

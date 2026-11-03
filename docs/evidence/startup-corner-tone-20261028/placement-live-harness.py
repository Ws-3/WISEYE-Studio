import sys,json,time,ctypes,math,base64
from pathlib import Path
sys.path.insert(0,'F:/WISEYE-Studio')
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from training_client.client import Client
from ctypes import wintypes as W
app=QApplication.instance() or QApplication([])
u=ctypes.windll.user32
u.GetForegroundWindow.restype=W.HWND
u.SetForegroundWindow.argtypes=[W.HWND]
u.GetWindowRect.argtypes=[W.HWND,ctypes.POINTER(W.RECT)]
u.GetClientRect.argtypes=[W.HWND,ctypes.POINTER(W.RECT)]
u.ClientToScreen.argtypes=[W.HWND,ctypes.POINTER(W.POINT)]
ready=json.loads(Path('E:/Projects/WISEYE-IR-Work/dual-roof-ready.json').read_text())
windows=[]
@ctypes.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
def enum(hwnd,lparam):
    pid=W.DWORD();u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
    if pid.value==ready['game_pid'] and u.IsWindowVisible(hwnd):
        title=ctypes.create_unicode_buffer(512);u.GetWindowTextW(hwnd,title,512)
        windows.append((hwnd,title.value))
    return True
u.EnumWindows(enum,0)
print('WINDOWS',windows,flush=True)
hwnd,title=max(windows,key=lambda x:len(x[1]));previous=u.GetForegroundWindow()
u.ShowWindow(hwnd,9);u.SetForegroundWindow(hwnd);time.sleep(.4)
rect=W.RECT();u.GetClientRect(hwnd,ctypes.byref(rect));origin=W.POINT(0,0);u.ClientToScreen(hwnd,ctypes.byref(origin))
c=Client(port=50051);out=Path('F:/WISEYE-Studio/docs/evidence/startup-corner-tone-20261028');out.mkdir(exist_ok=True)
report={'window_title':title,'passed':False}
original=c.rpc('sim.get_state')
def move(x,y):
    u.SetCursorPos(origin.x+int(rect.right*x),origin.y+int(rect.bottom*y));time.sleep(.3)
def screen(name):
    time.sleep(1)
    packet=c.rpc('camera.stream_frame',channel='OBS')
    (out/(name+'_observer.jpg')).write_bytes(base64.b64decode(packet['image_base64']))
    app.primaryScreen().grabWindow(int(hwnd)).save(str(out/(name+'.png')))
try:
    assert 'WISEYE' in title,title
    c.rpc('observer.set_mode',mode='overview');time.sleep(.5);screen('window_no_hud')
    c.rpc('observer.set_mode',mode='free');c.rpc('input.set_mode',mode='observer')
    until=time.monotonic()+.01
    while time.monotonic()<until:
        c.rpc('observer.set_input',forward=1,right=0,up=0,yaw_deg=0,pitch_deg=0);time.sleep(.08)
    c.rpc('observer.set_input',forward=0,right=0,up=0,yaw_deg=0,pitch_deg=0)
    for device,model in [('ptz-01',None),('uav-01','mavic3'),('uav-01','avata')]:
        client=Client(port=50051,device=device);token='preview-'+device
        if model:client.rpc('drone.set_model',model=model);time.sleep(.3)
        label=model or device
        client.rpc('placement.begin',scene_id='city',request_token=token,clearance_cm=0 if device=='ptz-01' else 25)
        points=[]
        for x,y in [(.4,.3),(.401,.3),(.5,.3),(.501,.3),(.4,.4),(.401,.4),(.5,.55),(.501,.55)]:
            move(x,y);p=client.rpc('sim.get_state')['placement']
            if p['preview_visible']:points.append(p)
            if len(points)>=2:break
        assert len(points)>=2,points
        assert math.dist(points[0]['preview_position_cm'],points[1]['preview_position_cm'])>1
        if device=='ptz-01':assert 75<points[-1]['preview_size_cm'][2]<100,points[-1]
        screen('placement_'+label)
        # The placement overlay must never enter the sensor captures.
        assert client.rpc('sim.get_state')['gimbal_position_cm']==original['gimbal_position_cm']
        report[label]={'hover':points}
        preview=points[-1]['preview_position_cm']
        u.mouse_event(2,0,0,0,0);time.sleep(.08);u.mouse_event(4,0,0,0,0);time.sleep(.3)
        committed=client.rpc('sim.get_state')['placement'];report[label]['committed']=committed
        assert committed['has_result'] and not committed['active'] and not committed['preview_visible'],committed
        assert math.dist(committed['position_cm'],preview)<.1,(preview,committed)
        client.rpc('placement.begin',scene_id='city',request_token=token,clearance_cm=25)
        move(.5,.6)
        u.SetCursorPos(origin.x-100,origin.y-100);time.sleep(.3)
        assert not client.rpc('sim.get_state')['placement']['preview_visible']
        move(.4,.3)
        u.mouse_event(8,0,0,0,0);time.sleep(.08);u.mouse_event(16,0,0,0,0);time.sleep(.3)
        assert not client.rpc('sim.get_state')['placement']['active']
    report['passed']=True
finally:
    Client(port=50051,device='uav-01').rpc('drone.set_model',model='mavic3')
    state=c.rpc('sim.get_state')
    if state['placement']['active']:c.rpc('placement.cancel',scene_id='city',request_token=state['placement']['request_token'])
    c.rpc('observer.set_mode',mode=original['observer_mode'])
    (out/'placement-preview.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    u.SetForegroundWindow(previous)
print('PLACEMENT_PREVIEW_PASSED',flush=True)

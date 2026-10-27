"""Real Windows key events must target the selected runtime instance."""
import ctypes,json,socket,time
from ctypes import wintypes
from core.config import ROOT
user=ctypes.windll.user32;user.FindWindowW.restype=wintypes.HWND;user.SetForegroundWindow.argtypes=[wintypes.HWND];user.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
def rpc(c,p=None):
    with socket.create_connection(('127.0.0.1',50051),timeout=4) as peer:
        peer.sendall((json.dumps(dict(version=1,request_id=str(time.time_ns()),command=c,payload=p or {}))+chr(10)).encode());r=json.loads(peer.makefile('rb').readline());assert r['status']=='ok',r;return r['payload']
def state(i):return rpc('sim.get_state',dict(device_id=i))
def key(code):
    user.keybd_event(code,user.MapVirtualKeyW(code,0),0,0);time.sleep(.1);user.keybd_event(code,user.MapVirtualKeyW(code,0),2,0);time.sleep(.3)
rpc('input.select_drone',dict(drone_id='uav-02'));rpc('input.select_gimbal',dict(gimbal_id='ptz-02'));rpc('input.set_mode',dict(mode='observer'))
for i in ('uav-01','uav-02'):rpc('rotors.set_enabled',dict(device_id=i,enabled=False))
for i in ('ptz-01','ptz-02'):rpc('gimbal.set_tracking',dict(device_id=i,enabled=True));rpc('camera.set_mode',dict(device_id=i,mode='visible'))
hwnd=user.FindWindowW(None,'test - 虚幻编辑器');assert hwnd
user.ShowWindow(hwnd,9);user.keybd_event(0x12,0,0,0);user.SetForegroundWindow(hwnd);user.keybd_event(0x12,0,2,0);time.sleep(.4)
rect=wintypes.RECT();assert user.GetWindowRect(hwnd,ctypes.byref(rect));user.SetCursorPos(int(rect.left+(rect.right-rect.left)*.48),int(rect.top+(rect.bottom-rect.top)*.43));user.mouse_event(2,0,0,0,0);user.mouse_event(4,0,0,0,0);time.sleep(.3)
checks=[]
try:
    if state('uav-02')['flight_backend']=='projectairsim':
        assert not state('uav-01')['rotors_running'] and not state('uav-02')['rotors_running'],'Test requires landed/disarmed aircraft'
        key(ord('O'));assert not state('uav-02')['rotors_running'] and not state('uav-01')['rotors_running'];key(ord('O'))
        checks.append('UE O cannot fake armed rotors in telemetry-driven AirSim mode')
    else:
        key(ord('O'));assert state('uav-02')['rotors_running'] and not state('uav-01')['rotors_running'];key(ord('O'));checks.append('UE O toggles only selected kinematic UAV rotors')
    key(ord('T'));assert not state('ptz-02')['tracking'] and state('ptz-01')['tracking'];key(ord('T'));checks.append('UE T toggles only selected gimbal tracking')
    key(ord('I'));assert state('ptz-02')['sensor_mode']=='infrared' and state('ptz-01')['sensor_mode']=='visible';key(ord('I'));checks.append('UE I changes only selected gimbal camera mode')
finally:
    for i in ('uav-01','uav-02'):rpc('rotors.set_enabled',dict(device_id=i,enabled=False))
    for i in ('ptz-01','ptz-02'):rpc('gimbal.set_tracking',dict(device_id=i,enabled=True));rpc('camera.set_mode',dict(device_id=i,mode='visible'))
    rpc('input.select_drone',dict(drone_id='uav-01'));rpc('input.select_gimbal',dict(gimbal_id='ptz-01'))
(ROOT/'docs/evidence/fleet_hotkeys_20261021.json').write_text(json.dumps(dict(passed=len(checks),checks=checks),indent=2),encoding='utf-8');print(checks,flush=True)

"""Windows physical-input regression for the independent UE observer camera."""
import ctypes
from ctypes import wintypes
import json
import math
import socket
import time
from core.config import ROOT

user32 = ctypes.windll.user32
user32.FindWindowW.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]


def request(command, payload=None, port=50051):
    with socket.create_connection(('127.0.0.1',port), timeout=5) as peer:
        peer.sendall((json.dumps(dict(version=1,request_id='observer-test',command=command,payload=payload or {}))+'\n').encode())
        response = json.loads(peer.makefile('rb').readline())
        assert response['status'] == 'ok', response
        return response['payload']


def key(code, down):
    user32.keybd_event(code, user32.MapVirtualKeyW(code,0), 0 if down else 2, 0)


report = dict(passed=False)
try:
    air = request('sim.get_state',port=50052)
    if air.get('flight_status') == 'ready':
        request('flight.takeoff',port=50052)
        deadline = time.monotonic()+35
        while True:
            air = request('sim.get_state',port=50052)
            if not air['command_active']:
                assert not air['last_error'], air
                break
            assert time.monotonic() < deadline
            time.sleep(.2)
    request('flight.set_mode', {'mode':'manual'}, port=50052)
    # A prior automatic route can still be braking; measure camera isolation
    # only after actual pose stability, rather than after a fixed delay.
    previous=request('sim.get_state',port=50052)['position_ned_m']
    deadline=time.monotonic()+15
    stable=0
    while stable<3:
        time.sleep(.5)
        current=request('sim.get_state',port=50052)['position_ned_m']
        stable=stable+1 if math.dist(previous,current)<.01 else 0
        previous=current
        assert time.monotonic()<deadline,'Drone did not reach stable hover'
    request('gimbal.set_angles', dict(yaw_deg=0,pitch_deg=-10))
    request('input.set_mode', {'mode':'observer'})
    request('observer.set_mode', {'mode':'free'})
    hwnd = user32.FindWindowW(None,'test - 虚幻编辑器')
    assert hwnd, 'UE editor window missing'
    user32.ShowWindow(hwnd, 9)
    key(0x12,True)
    user32.SetForegroundWindow(hwnd)
    key(0x12,False)
    user32.GetForegroundWindow.restype = wintypes.HWND
    assert user32.GetForegroundWindow() == hwnd, "Could not focus the UE window"
    time.sleep(.4)
    rect = wintypes.RECT()
    assert user32.GetWindowRect(hwnd, ctypes.byref(rect))
    user32.SetCursorPos(int(rect.left+(rect.right-rect.left)*.48),int(rect.top+(rect.bottom-rect.top)*.43))
    user32.mouse_event(0x0002,0,0,0,0)
    user32.mouse_event(0x0004,0,0,0,0)
    time.sleep(.3)
    start = request('sim.get_state')
    drone_start = request('sim.get_state',port=50052)['position_ned_m']
    user32.mouse_event(0x0008,0,0,0,0)
    key(ord('W'),True)
    time.sleep(1)
    key(ord('W'),False)
    user32.mouse_event(0x0010,0,0,0,0)
    end = request('sim.get_state')
    drone_end = request('sim.get_state',port=50052)['position_ned_m']
    report['observer_displacement_cm'] = math.dist(start['observer_position_cm'],end['observer_position_cm'])
    report['drone_drift_m'] = math.dist(drone_start,drone_end)
    assert report['observer_displacement_cm'] > 200, report
    assert report['drone_drift_m'] < .08, report
    assert abs(start['pitch_deg']-end['pitch_deg']) < .01
    assert abs(start['fov_deg']-end['fov_deg']) < .01
    request('input.set_mode', {'mode':'gimbal'})
    key(0x26,True)
    time.sleep(.6)
    key(0x26,False)
    end_gimbal = request('sim.get_state')
    report['gimbal_pitch_change_deg'] = end_gimbal['pitch_deg']-end['pitch_deg']
    assert report['gimbal_pitch_change_deg'] > 5, report
    report['passed'] = True
finally:
    key(ord('W'),False)
    key(0x26,False)
    user32.mouse_event(0x0010,0,0,0,0)
    request('input.set_mode', {'mode':'observer'})
    request('observer.set_mode', {'mode':'overview'})
    request('gimbal.set_tracking', {'enabled':True})
    (ROOT/'runtime/observer_live_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))

"""Exercise only the owned UE window; ghosts are cancelled without applying."""
import argparse
import ctypes
from ctypes import wintypes
import json
import math
from pathlib import Path
import time
import uuid
from training_client.client import Client


def main():
    p=argparse.ArgumentParser();p.add_argument('--ready',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    owned=json.loads(args.ready.read_text());c=Client(port=50051)
    original=c.rpc('sim.get_state');assert original['run_id']==owned['run_id']
    u=ctypes.WinDLL('user32');u.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    u.SetForegroundWindow.argtypes=[wintypes.HWND];u.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int]
    u.GetClientRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)];u.ClientToScreen.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.POINT)]
    windows=[];callback=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    def visit(hwnd,_):
        pid=wintypes.DWORD();u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        if pid.value==owned['game_pid'] and u.IsWindowVisible(hwnd):windows.append(hwnd)
        return True
    u.EnumWindows(callback(visit),0);assert windows
    def area(hwnd):
        rect=wintypes.RECT();u.GetClientRect(hwnd,ctypes.byref(rect));return rect.right*rect.bottom
    hwnd=max(windows,key=area);u.ShowWindow(hwnd,9);u.keybd_event(0x12,0,0,0);u.SetForegroundWindow(hwnd);u.keybd_event(0x12,0,2,0);time.sleep(.4)
    def key(code):
        u.keybd_event(code,u.MapVirtualKeyW(code,0),0,0);time.sleep(.08)
        u.keybd_event(code,u.MapVirtualKeyW(code,0),2,0);time.sleep(.15)
    def placement():return c.rpc('sim.get_state')['placement']
    token=uuid.uuid4().hex;report=dict(passed=False,run_id=owned['run_id'])
    try:
        c.rpc('observer.set_mode',mode='overview')
        time.sleep(.5)
        c.rpc('placement.begin',scene_id='city',request_token=token,clearance_cm=0)
        rect=wintypes.RECT();point=wintypes.POINT();u.GetClientRect(hwnd,ctypes.byref(rect));u.ClientToScreen(hwnd,ctypes.byref(point))
        found=False
        for rx,ry in ((.3,.3),(.4,.3),(.5,.3),(.6,.3),(.3,.4),(.4,.4),(.5,.6),(.4,.7),(.6,.7),(.3,.8),(.5,.8),(.7,.8),(.4,.9)):
            u.SetCursorPos(point.x+int(rect.right*rx),point.y+int(rect.bottom*ry));time.sleep(.3)
            if placement().get('preview_visible'):found=True;break
        assert found,'No visible placement surface'
        key(0x20);before=placement();assert before['locked']
        key(ord('W'));after_w=placement()
        distance=math.dist(before['preview_position_cm'],after_w['preview_position_cm']);assert abs(distance-10)<.1,distance
        key(ord('E'));after_e=placement();assert abs(after_e['yaw_deg']-before['yaw_deg']-1)<.01
        key(ord('R'));after_r=placement();assert abs(after_r['preview_position_cm'][2]-after_e['preview_position_cm'][2]-10)<.1
        u.keybd_event(0xA0,u.MapVirtualKeyW(0xA0,0),0,0);time.sleep(.1);key(ord('F'));u.keybd_event(0xA0,u.MapVirtualKeyW(0xA0,0),2,0)
        after_shift=placement();report.update(before=before,after_w=after_w,after_e=after_e,after_r=after_r,after_shift_f=after_shift)
        assert abs(after_shift['preview_position_cm'][2]-after_r['preview_position_cm'][2]+1)<.1
        u.keybd_event(ord('D'),u.MapVirtualKeyW(ord('D'),0),0,0);time.sleep(1)
        u.keybd_event(ord('D'),u.MapVirtualKeyW(ord('D'),0),2,0);time.sleep(.2)
        held=placement();distance=math.dist(held['preview_position_cm'],after_shift['preview_position_cm'])
        assert 40<distance<130,distance
        time.sleep(.3);released=placement();assert math.dist(held['preview_position_cm'],released['preview_position_cm'])<.01
        report['held_d_distance_cm']=distance;report['after_held_d']=held
        key(0x0D);confirmed=placement();assert confirmed['has_result'] and not confirmed['active']
        assert math.dist(confirmed['position_cm'],held['preview_position_cm'])<.1
        state=c.rpc('sim.get_state');assert state['gimbal_position_cm']==original['gimbal_position_cm']
        report.update(passed=True,before=before,after_w=after_w,after_e=after_e,after_r=after_r,after_shift_f=after_shift,confirmed=confirmed)
    finally:
        if placement().get('active'):c.rpc('placement.cancel',scene_id='city',request_token=token)
        c.rpc('observer.set_mode',mode=original['observer_mode'])
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('PLACEMENT_KEYS_PASSED')


if __name__=='__main__':main()

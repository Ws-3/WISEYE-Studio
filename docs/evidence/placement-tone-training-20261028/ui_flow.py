import os,sys,json,time,ctypes,base64
from pathlib import Path
from ctypes import wintypes as W
root=Path('F:/WISEYE-Studio');work=Path('E:/Projects/WISEYE-IR-Work');out=work/'ir-fix-1028'
os.environ['WISEYE_DATA_DIR']=str(work/'ir-fix-test-data');os.environ['WISEYE_RESOURCES_DIR']=str(root)
sys.path.insert(0,str(root))
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from core.config import AppConfig
from apps.desktop_app.main_window import MainWindow
from training_client.client import Client
app=QApplication([]);window=MainWindow(AppConfig.load());window.resize(1600,940);window.show()
u=ctypes.windll.user32
u.GetForegroundWindow.restype=W.HWND;u.SetForegroundWindow.argtypes=[W.HWND];u.ShowWindow.argtypes=[W.HWND,ctypes.c_int]
u.GetClientRect.argtypes=[W.HWND,ctypes.POINTER(W.RECT)];u.ClientToScreen.argtypes=[W.HWND,ctypes.POINTER(W.POINT)]
c=Client(port=50051);original=c.rpc('sim.get_state');report={'passed':False,'run_id':original['run_id']};training=None
def wait(test,timeout=15):
 until=time.monotonic()+timeout
 while time.monotonic()<until:
  app.processEvents();time.sleep(.05)
  if test():return
 raise TimeoutError('UI acceptance timed out')
def windows(prefix=None,pid=None):
 found=[]
 @ctypes.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
 def visit(hwnd,_):
  process=W.DWORD();u.GetWindowThreadProcessId(hwnd,ctypes.byref(process));title=ctypes.create_unicode_buffer(512);u.GetWindowTextW(hwnd,title,512)
  if u.IsWindowVisible(hwnd) and ((prefix and title.value.startswith(prefix)) or (pid and process.value==pid)):found.append(hwnd)
  return True
 u.EnumWindows(visit,0);return found
try:
 for i in range(window.scenes.count()):
  if window.scenes.itemData(i)['id']=='city':window.scenes.setCurrentIndex(i);break
 window.arrangement.load();window.connect_ue();wait(lambda:window.client.ready and window.state.get('scene_id')=='city')
 window.pages.setCurrentWidget(window.arrangement);app.processEvents()
 page=window.arrangement;tools=page.tools
 assert '读取失败' not in page.message.text(),page.message.text()
 print('LOAD',page.message.text(),'SCENE',window.scenes.currentData(),'COUNT',tools.device.count(),flush=True);assert tools.device.count()==2
 assert abs(tools.draft()['flight_origin_cm'][0]+27400)<.1
 wait(lambda:tools.pick.isEnabled())
 for i in range(tools.device.count()):
  if tools.device.itemData(i)[0]=='ptz-01':tools.device.setCurrentIndex(i);break
 report['devices_loaded']=tools.device.count();report['draft_before']=tools.draft();report['load_message']=page.message.text()
 window.grab().save(str(out/'desktop-loaded.png'))
 QTest.mouseClick(tools.pick,Qt.MouseButton.LeftButton);wait(lambda:c.rpc('sim.get_state')['placement']['active'])
 pid=int(sys.argv[1]) if len(sys.argv)>1 else json.loads((work/'dual-roof-ready.json').read_text())['game_pid'];hwnd=windows(pid=pid)[0]
 u.ShowWindow(hwnd,9);u.SetForegroundWindow(hwnd);
 current=ctypes.windll.kernel32.GetCurrentThreadId();foreground=u.GetWindowThreadProcessId(u.GetForegroundWindow(),None)
 if u.GetForegroundWindow()!=hwnd:
  u.AttachThreadInput(current,foreground,True);u.SetForegroundWindow(hwnd);u.AttachThreadInput(current,foreground,False)
 if u.GetForegroundWindow()!=hwnd:
  u.SwitchToThisWindow.argtypes=[W.HWND,W.BOOL];u.SwitchToThisWindow(hwnd,True);time.sleep(.3)
 assert u.GetForegroundWindow()==hwnd,'Cannot focus the UE window for a safe click test'
 rect=W.RECT();origin=W.POINT();u.GetClientRect(hwnd,ctypes.byref(rect));u.ClientToScreen(hwnd,ctypes.byref(origin))
 u.SetCursorPos(origin.x+int(rect.right*.4),origin.y+int(rect.bottom*.3))
 wait(lambda:c.rpc('sim.get_state')['placement']['preview_visible'])
 preview=c.rpc('sim.get_state')['placement'];report['preview']=preview
 (out/'desktop-started-preview.jpg').write_bytes(base64.b64decode(c.rpc('camera.stream_frame',channel='OBS')['image_base64']))
 u.mouse_event(2,0,0,0,0);time.sleep(.08);u.mouse_event(4,0,0,0,0)
 time.sleep(.5);app.processEvents()
 report['first_click_committed']=c.rpc('sim.get_state')['placement']['has_result']
 if not report['first_click_committed']:
  u.mouse_event(2,0,0,0,0);time.sleep(.08);u.mouse_event(4,0,0,0,0)
 wait(lambda:tools.pending is None)
 for x,y in zip(tools.draft()['gimbal_location_cm'],preview['preview_position_cm']):assert abs(x-y)<.1,(tools.draft(),preview)
 assert c.rpc('sim.get_state')['gimbal_position_cm']==original['gimbal_position_cm']
 report['draft_after']=tools.draft();report['placement_through_desktop']=True
 window.raise_();window.activateWindow();QTest.mouseClick(window.training_button,Qt.MouseButton.LeftButton)
 training=window._training_process;wait(lambda:bool(windows(prefix='WISEYE Training ·')),20)
 time.sleep(3);app.processEvents();training_window=windows(prefix='WISEYE Training ·')[0]
 report['training_pid']=training.pid;report['training_opened']=True
 QTest.mouseClick(window.training_button,Qt.MouseButton.LeftButton)
 assert window._training_process is training and len(windows(prefix='WISEYE Training ·'))==1
 report['training_second_click_reuses_window']=True
 u.ShowWindow(training_window,9);u.SetForegroundWindow(training_window);time.sleep(.5)
 app.primaryScreen().grabWindow(int(training_window)).save(str(out/'training-from-desktop.png'))
 report['passed']=True
finally:
 p=c.rpc('sim.get_state')['placement']
 if p['active']:c.rpc('placement.cancel',scene_id='city',request_token=p['request_token'])
 c.rpc('observer.set_mode',mode=original['observer_mode']);c.rpc('input.set_mode',mode=original['input_mode'])
 if training:
  for hwnd in windows(prefix='WISEYE Training ·'):u.PostMessageW(hwnd,0x10,0,0)
 window.client.ready=False;window.close();app.processEvents()
 (out/'ui-flow.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('DESKTOP_PLACEMENT_AND_TRAINING_PASSED',flush=True)

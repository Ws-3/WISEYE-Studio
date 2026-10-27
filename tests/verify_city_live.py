"""Live Small City acceptance: requires an already running city and landed UAV.

Uses real UE / AirSim commands and Qt RTSP decoding. Always attempts landing;
never changes fleet, scene manifests or route files.
"""
import json,math,socket,time
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from apps.desktop_app.main_window import MainWindow
from core.config import ROOT,AppConfig
from integrations.gimbal_client import GimbalClient

app=QApplication([]);window=None;airborne=False;checks=[]
report=dict(passed=False,checks=checks)

def rpc(command,payload=None,port=50051):
 with socket.create_connection(('127.0.0.1',port),6) as peer:
  peer.sendall((json.dumps(dict(version=1,request_id=str(time.time_ns()),command=command,payload=payload or {}))+'\n').encode())
  reply=json.loads(peer.makefile('rb').readline(16*1024*1024))
 assert reply['status']=='ok',reply
 return reply['payload']

def air(command='sim.get_state',**payload):return rpc(command,dict(payload,device_id='uav-01'),50052)
def pump(seconds):
 end=time.monotonic()+seconds
 while time.monotonic()<end:app.processEvents();time.sleep(.01)
def wait(predicate,timeout=45):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  app.processEvents()
  if predicate():return
  time.sleep(.08)
 raise AssertionError('City runtime condition timed out')
def passed(label):checks.append(label);print('PASS '+label,flush=True)

saved=None
try:
 # Wait for rendering and game-thread replies to settle before issuing motion.
 deadline=time.monotonic()+240;stable=0;previous_tick=-1
 while stable<6:
  started=time.monotonic()
  try:
   probe=rpc('sim.get_state')
   healthy=(probe.get('scene_id')=='city' and probe.get('dynamics_connected') and probe.get('tick_seq',0)>previous_tick and time.monotonic()-started<.7 and all(0<p.get('completed_frames',0) and p.get('cache_age_ms',9999)<500 for p in probe.get('streams',{}).values()))
   stable=stable+1 if healthy else 0;previous_tick=probe.get('tick_seq',-1)
  except OSError:stable=0
  assert time.monotonic()<deadline,'City streaming has not settled'
  pump(1)
 state=rpc('sim.get_state');assert state['scene_id']=='city' and state['dynamics_connected']
 config=json.loads((ROOT/'ue5/WISEYE/Config/WISEYE/Scenes/city.json').read_text(encoding='utf8'))
 assert math.dist(state['initial_drone_position_cm'],config['flight_origin_cm'])<.01
 assert math.dist(state['gimbal_position_cm'],config['gimbal_location_cm'])<.01
 ground=air();assert ground['flight_status']=='ready' and not ground['command_active'],ground
 assert math.dist([ground['position_ned_m'][0]*100,ground['position_ned_m'][1]*100],config['flight_origin_cm'][:2])<20
 # Center must be above the actual streamed sidewalk; a Z=0 collision underlay is invalid.
 assert state['drone_position_cm'][2]>80 and state['gimbal_position_cm'][2]>73
 report.update(run_id=state['run_id'],initial_state=state,ground=ground)
 passed('city origin, streamed sidewalk and actual AirSim pose')
 sdk=GimbalClient(timeout=6);saved=sdk.state();sdk.take_control();sdk.set_angles(5,0)
 before=sdk.state()['yaw_deg']
 for _ in range(5):sdk.set_velocity(15,0);pump(.1)
 sdk.stop();after=sdk.state()['yaw_deg'];assert after-before>3,(before,after)
 pump(.6);stopped=sdk.state()['yaw_deg'];pump(.5);assert abs(sdk.state()['yaw_deg']-stopped)<.2
 sdk.track('uav-01');rpc('input.set_mode',dict(mode='observer'));rpc('observer.set_mode',dict(mode='overview'))
 report['gimbal_rate_delta_deg']=after-before;passed('gimbal angle/rate/stop and tracking commands')
 air('flight.takeoff');airborne=True
 wait(lambda:not air()['command_active'],60);pump(2)
 hover=air();assert not hover['last_error'],hover
 assert ground['position_ned_m'][2]-hover['position_ned_m'][2]>1
 wait(lambda:min(air()['motor_rpm'])>1000,15)
 air('flight.set_mode',mode='manual');wait(lambda:not air()['command_active'])
 for _ in range(7):air('flight.set_input',forward=0,right=0,up=.3,yaw=0);pump(.1)
 air('flight.set_input',forward=0,right=0,up=0,yaw=0);air('flight.hover');wait(lambda:not air()['command_active']);pump(1)
 moved=air();assert hover['position_ned_m'][2]-moved['position_ned_m'][2]>.08,(hover,moved)
 report.update(hover=hover,manual=moved);passed('actual takeoff, live rotor RPM and manual upward motion')
 window=MainWindow(AppConfig.load());window.resize(1680,1000);window.show();window.connect_ue()
 window.gallery.reset_layout()
 wait(lambda:window.client.ready and window.air_client.ready and len(window.gallery.frames)>=3,50)
 for key,shape in [('ptz-01/visible',(1920,1080)),('ptz-01/infrared',(640,512)),('scene/observer',(960,540))]:
  frame=window.gallery.frames[key];assert (frame.width(),frame.height())==shape
 report['frames']={k:[v.width(),v.height()] for k,v in window.gallery.frames.items()}
 cloud=rpc('sensor.lidar.get_points',dict(device_id='ptz-01'))
 report['lidar']=cloud
 assert cloud.get('lidar_points_m'),cloud
 start=rpc('sim.get_state');pump(12);end=rpc('sim.get_state')
 assert start['run_id']==end['run_id'] and end['tick_seq']>start['tick_seq']+30
 report['tick_progress']=dict(start=start['tick_seq'],end=end['tick_seq'],seconds=12)
 window.grab().save(str(ROOT/'docs/evidence/city_workbench_20261022.png'))
 passed('native EO/IR/observer RTSP frames, nonempty point cloud and advancing simulation')
 air('flight.land');wait(lambda:air()['flight_status']=='ready' and not air()['command_active'],60)
 wait(lambda:max(air()['motor_rpm'])<1,15);airborne=False
 report['landed']=air();passed('actual landing and motors stopped')
 report['passed']=True
finally:
 if airborne:
  try:air('flight.land');wait(lambda:air()['flight_status']=='ready',65)
  except Exception as error:report['landing_error']=str(error)
 if saved:
  try:
   sdk.stop();sdk.set_angles(saved['yaw_deg'],saved['pitch_deg'])
   if saved['tracking']:sdk.track(saved.get('tracking_target','uav-01'))
   rpc('input.set_mode',dict(mode='observer'));rpc('observer.set_mode',dict(mode='overview'))
  except Exception as error:report['restore_error']=str(error)
 if window:window.close();app.processEvents()
 (ROOT/'docs/evidence/city_runtime_20261022.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps(dict(passed=report['passed'],checks=checks),ensure_ascii=False),flush=True)

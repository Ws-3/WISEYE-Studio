"""Live flight regression: explicit opt-in, real CitySample wall, no map/Fleet writes.

Run from the repo root with --allow-flight --editor-log <active absolute log>.
On assertion failure the aircraft is commanded to hover; inspect it before landing.
"""
import argparse,json,socket,time,hashlib,traceback,math
from pathlib import Path
parser=argparse.ArgumentParser(description='Opt-in physical CitySample building collision regression; takes off and returns to land.')
parser.add_argument('--allow-flight',action='store_true')
parser.add_argument('--editor-log',type=Path,required=True)
args=parser.parse_args()
if not args.allow_flight:parser.error('Pass --allow-flight only when WISEYE is idle and the test airspace is available')
root=Path(__file__).resolve().parents[1];log=args.editor_log.resolve()
if not log.is_file():parser.error('The active UE editor log must exist')
report=dict(passed=False,checks=[],rounds=[])
started=time.monotonic();flight_started=False
def rpc(cmd,payload=None,port=50051):
 with socket.create_connection(('127.0.0.1',port),3) as s:
  s.settimeout(6);s.sendall(json.dumps(dict(version=1,request_id=str(time.time_ns()),command=cmd,payload=payload or {})).encode()+b'\n');r=json.loads(s.makefile('rb').readline())
  assert r['status']=='ok',r
  return r['payload']
def air():return rpc('sim.get_state',port=50052)
def cmd(command,**p):return rpc(command,p,50052)
def wait(fn,timeout=40):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  try:
   v=fn()
   if v:return v
  except (OSError,TimeoutError):pass
  time.sleep(.2)
 raise AssertionError('Runtime wait expired')
def push(forward,duration):
 end=time.monotonic()+duration
 while time.monotonic()<end:
  yaw=math.radians(air()['yaw_deg'])
  cmd('flight.set_input',forward=forward*math.cos(yaw),right=-forward*math.sin(yaw));time.sleep(.12)
 cmd('flight.set_input')
def contacts():return log.read_text(encoding='utf8',errors='replace').count("Collision detected between 'Frame' and 'FastGeoSurrogateActor")
def route(points,name):
 cmd('route.upload',version=1,name=name,scene_id='city',frame='ue_world_m',speed_mps=3,repeat=False,waypoints=points)
 cmd('route.start')
 def near():
  a=air();p=a['position_ned_m'];q=points[-1]
  return a['route_status']=='completed' or math.dist(p,[q[0],q[1],-q[2]])<.85
 wait(near,50)
 cmd('flight.hover');wait(lambda:not air()['command_active'],12)
try:
 wait(lambda: air().get('connected'),140)
 original=rpc('sim.get_state');assert original['scene_id']=='city'
 assert air()['flight_status']=='ready','Test requires a landed/disarmed drone'
 assert sum(d['kind']=='drone' for d in original['devices'])==1,'This wall fixture is validated with one drone'
 assert all(abs(a-b)<1 for a,b in zip(original['initial_drone_position_cm'],[-29298.7,-100.7,98])), 'City wall fixture requires the documented original takeoff point'
 path=root/'ue5/WISEYE/Config/WISEYE/Fleets/city.json';digest=hashlib.sha256(path.read_bytes()).hexdigest()
 report['fleet_sha256_before']=digest;report['original_devices']=original['devices'];report['run_id']=original['run_id']
 flight_started=True
 rpc('input.set_mode',dict(mode='observer'))
 if air()['flight_status']=='ready':cmd('flight.takeoff')
 wait(lambda:not air()['command_active'],20)
 origin=original['initial_drone_position_cm'];x,y=origin[0]/100,origin[1]/100
 p=air()['position_ned_m']
 route([[-247,4.7,max(15.3,-p[2])],[-247,4.7,15.3],[-243,4.7,15.3]] if -p[2]>15.4 else [[x,y,15.3],[-243,4.7,15.3]],'collision verification approach')
 print('APPROACH',air(),flush=True)
 report['checks'].append('Flight approach to the real CitySample wall using uploaded waypoints (within 0.85m target tolerance, then hover)')
 for index in range(3):
  if index:
   route([[-247,4.7,15.3],[-243,4.7,15.3]],'repeat wall approach')
  cmd('flight.set_mode',mode='manual');before=air();n=contacts();t0=rpc('sim.get_state')['simulation_time_s']
  push(1,4);time.sleep(.8);hit=air();n2=contacts();assert n2>n,'No real collision observed'
  push(-1,2.5);time.sleep(.8);released=air();t1=rpc('sim.get_state')['simulation_time_s']
  row=dict(index=index+1,before=before['position_ned_m'],contact=hit['position_ned_m'],released=released['position_ned_m'],new_collision_events=n2-n,simulation_advanced_s=t1-t0,error=released['last_error'])
  report['rounds'].append(row);print('ROUND',json.dumps(row),flush=True)
  assert released['position_ned_m'][0]<hit['position_ned_m'][0]-1,'Reverse input did not release wall contact'
  assert t1-t0>3 and not released['last_error']
 report['checks'].append('Three repeated real building collisions; reverse input moves >1m away each time while simulation and controls remain live')
 p=air()['position_ned_m'];route([[p[0],p[1],16],[x,y,16],[x,y,4]],'collision verification return')
 cmd('flight.land');wait(lambda:air()['flight_status']=='ready',35)
 report['checks'].append('Return to takeoff area via uploaded waypoints, physical landing and real motor disarm after repeated collisions')
 report['fleet_file_unchanged']=hashlib.sha256(path.read_bytes()).hexdigest()==digest;assert report['fleet_file_unchanged']
 report['final']=air();report['passed']=True
except Exception:
 report['error']=traceback.format_exc();print(report['error'],flush=True)
 if flight_started:
  try:cmd('flight.hover')
  except Exception:pass
finally:
 if flight_started and 'original' in globals():
  try:rpc('input.set_mode',dict(mode=original['input_mode']));rpc('observer.set_mode',dict(mode=original['observer_mode']))
  except Exception:pass
 report['elapsed_s']=time.monotonic()-started
 (root/'docs/evidence/collision_recovery_live_20261022.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('PASSED',report['passed'],flush=True)
raise SystemExit(0 if report['passed'] else 1)

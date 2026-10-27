"""Verify independent device counts; restore the user's original fleet bytes."""
import copy,json,socket,time
from core.config import ROOT
path=ROOT/'ue5/WISEYE/Config/WISEYE/Fleets/original.json'
backup=path.read_bytes();original=json.loads(backup.decode('utf-8-sig'));checks=[]
def rpc(command,payload=None,port=50051):
    with socket.create_connection(('127.0.0.1',port),timeout=4) as peer:
        peer.sendall((json.dumps(dict(version=1,request_id='shape-'+str(time.time_ns()),command=command,payload=payload or {}))+chr(10)).encode())
        return json.loads(peer.makefile('rb').readline(65536))
def reload_and_wait(drones,gimbals):
    before=rpc('sim.get_state')['payload']['run_id'];assert rpc('sim.load_scene',dict(scene_id='original'))['status']=='ok'
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        try:
            state=rpc('sim.get_state')['payload'];air=rpc('sim.get_state',port=50052)['payload']
            if state['run_id']!=before and air.get('run_id')==state['run_id'] and len(air.get('fleet',[]))==drones:
                assert sum(d['kind']=='drone' for d in state['devices'])==drones
                assert sum(d['kind']=='gimbal' for d in state['devices'])==gimbals
                assert all(s['flight_status']=='ready' for s in air['fleet'])
                return state
        except (OSError,KeyError,ValueError):pass
        time.sleep(.2)
    raise AssertionError('Fleet reload did not recover')
try:
    for drones,gimbals in [(1,2),(2,1)]:
        data=copy.deepcopy(original)
        data['devices']=[d for d in data['devices'] if not(d['id']=='uav-02' and drones==1) and not(d['id']=='ptz-02' and gimbals==1)]
        for d in data['devices']:
            if d['kind']=='gimbal' and drones==1:d['tracking_target']='uav-01'
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        state=reload_and_wait(drones,gimbals)
        removed='uav-02' if drones==1 else 'ptz-02'
        assert rpc('sim.get_state',dict(device_id=removed),50052 if drones==1 else 50051)['status']=='error'
        checks.append(f'{drones} UAV + {gimbals} PTZ: distinct inventory, actual AirSim robot count, ready and removed-ID rejection')
        print(checks[-1],flush=True)
finally:
    path.write_bytes(backup)
    reload_and_wait(2,2)
assert path.read_bytes()==backup
checks.append('original 2+2 configuration restored byte-for-byte and reloaded')
(ROOT/'docs/evidence/fleet_shapes_20261021.json').write_text(json.dumps(dict(passed=len(checks),checks=checks),ensure_ascii=False,indent=2),encoding='utf-8')
print(dict(passed=len(checks)),flush=True)

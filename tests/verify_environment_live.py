"""Read host telemetry and capture actual scene lighting/fog/rain; restore on exit."""
import argparse,base64,json,socket,time
from pathlib import Path
import cv2
import numpy as np

parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
args.output.mkdir(parents=True,exist_ok=True)
def rpc(command,payload=None,ok=True):
    with socket.create_connection(('127.0.0.1',50051),4) as peer:
        peer.settimeout(8);peer.sendall((json.dumps(dict(version=1,request_id=str(time.time_ns()),command=command,payload=payload or {}))+'\n').encode())
        value=json.loads(peer.makefile('rb').readline(16*1024*1024))
    if ok:assert value['status']=='ok',value
    return value['payload'] if ok else value
def capture(name,delay=2):
    time.sleep(delay)
    value=rpc('camera.stream_frame',dict(device_id='ptz-02',channel='CH1'))
    image=cv2.imdecode(np.frombuffer(base64.b64decode(value['image_base64']),np.uint8),cv2.IMREAD_COLOR)
    assert image.shape==(1080,1920,3)
    cv2.imencode('.jpg',image)[1].tofile(str(args.output/(name+'.jpg')))
    return image
initial=rpc('sim.get_state')['environment']
keys=('time_override','hour','fog','rain')
initial={key:initial[key] for key in keys}
report=dict(passed=False,initial=initial)
try:
    state=rpc('environment.reset');report['capabilities']=state['environment']
    time.sleep(2);state=rpc('sim.get_state');report['hardware']=state['runtime_hardware']
    assert report['hardware']['gpu_name']
    assert report['hardware']['gpu_dedicated_total_bytes']>1024**3
    assert report['hardware']['ue_vram_budget_bytes']>0
    normal=capture('original')
    state=rpc('environment.configure',dict(time_override=True,hour=12,fog=0,rain=0));assert state['environment']['time_override']
    noon=capture('noon',4)
    rpc('environment.configure',dict(time_override=True,hour=0,fog=0,rain=0))
    night=capture('night',4)
    daylight_diff=float(np.abs(noon.astype(float)-night).mean());assert daylight_diff>3,daylight_diff
    rpc('environment.configure',dict(time_override=False,hour=12,fog=.8,rain=0))
    fog=capture('fog');fog_diff=float(np.abs(fog.astype(float)-normal).mean());assert fog_diff>3,fog_diff
    state=rpc('environment.configure',dict(time_override=False,hour=12,fog=0,rain=.8))
    assert state['environment']['rain_view_volumes']>=2
    rain=capture('rain',4)
    rain_diff=float(np.abs(rain.astype(float)-normal).mean())
    for invalid in [dict(hour=24),dict(fog=2),dict(rain=-1)]:
        before=rpc('sim.get_state')['environment']
        result=rpc('environment.configure',dict(initial,**invalid),ok=False)
        assert result['status']!='ok';assert rpc('sim.get_state')['environment']==before
    state=rpc('environment.reset');restored=capture('reset',3)
    report.update(passed=True,day_night_mean_difference=daylight_diff,fog_mean_difference=fog_diff,
                  rain_mean_difference=rain_diff,rain_visual_verified=False,
                  reset_mean_difference=float(np.abs(restored.astype(float)-normal).mean()),invalid_requests_rejected=3)
finally:
    rpc('environment.configure',initial)
    report['restored']=True
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))

"""A/B the real UE sensor at the same pose. Restores per-device runtime settings."""
import argparse
import base64
import json
from pathlib import Path
import socket
import time
import cv2
import numpy as np

parser=argparse.ArgumentParser()
parser.add_argument('--device',default='ptz-02')
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
args.output.mkdir(parents=True,exist_ok=True)


def rpc(command,payload=None,ok=True):
    with socket.create_connection(('127.0.0.1',50051),5) as peer:
        peer.settimeout(10)
        peer.sendall((json.dumps(dict(version=1,request_id=str(time.time_ns()),command=command,
                                     payload=dict(device_id=args.device,**(payload or {}))))+'\n').encode())
        reply=json.loads(peer.makefile('rb').readline(16*1024*1024))
    if ok:assert reply['status']=='ok',reply
    return reply['payload'] if ok else reply


def frame(channel='CH2'):
    payload=rpc('camera.stream_frame',dict(channel=channel,quality=60))
    image=cv2.imdecode(np.frombuffer(base64.b64decode(payload['image_base64']),dtype=np.uint8),cv2.IMREAD_COLOR)
    assert image is not None
    return image,payload


def capture(name):
    # Configuration acknowledgement precedes GPU readback. Wait for fresh frames.
    _,start=frame()
    deadline=time.monotonic()+12
    while time.monotonic()<deadline:
        image,meta=frame()
        if meta['frame_number']>=start['frame_number']+3:break
        time.sleep(.1)
    else:raise TimeoutError('IR frame did not advance')
    assert image.shape==(512,640,3),image.shape
    assert np.ptp(image,axis=2).max()<=2,'IR must be grayscale'
    assert image.std()>2,'Reject blank/constant image'
    cv2.imencode('.png',image)[1].tofile(str(args.output/(name+'.png')))
    return image,meta


state=rpc('sim.get_state')
initial=dict(state['sensors']['infrared'])
assert initial.get('enhanced_available'),'New runtime/material required'
keys=('enabled','fov_deg','palette','noise','thermal_profile','blur_px','contrast','background_detail')
initial={key:initial[key] for key in keys}
report=dict(passed=False,device=args.device,scene=state['scene_id'],initial=initial)
def configure(**changes):
    config=dict(initial,enabled=True,**{})
    config.update(changes)
    return rpc('sensor.configure',dict(sensor='infrared',**config))
try:
    configure(thermal_profile='legacy',noise=0,palette='white_hot')
    legacy,_=capture('legacy')
    configure(thermal_profile='enhanced',noise=0,palette='white_hot')
    enhanced,_=capture('enhanced')
    difference=float(np.abs(enhanced.astype(float)-legacy).mean())
    assert difference>2,'New profile had no visible effect'
    configure(thermal_profile='enhanced',noise=0,palette='black_hot')
    black,_=capture('enhanced_black_hot')
    inversion=float(np.abs(enhanced.astype(float)+black.astype(float)-255).mean())
    assert inversion<8,('Palette is not inverted',inversion)
    configure(thermal_profile='enhanced',noise=.03,palette='white_hot')
    noisy,_=capture('enhanced_noise')
    noise_difference=float(np.abs(noisy.astype(float)-enhanced).mean())
    assert noise_difference>.2,'Noise control had no effect'
    for change in [dict(blur_px=-1),dict(contrast=4),dict(background_detail=2),dict(thermal_profile='invalid')]:
        before=rpc('sim.get_state')['sensors']['infrared']
        rejected=rpc('sensor.configure',{'sensor':'infrared',**initial,**change},ok=False)
        assert rejected['status']!='ok',rejected
        assert rpc('sim.get_state')['sensors']['infrared']==before,'Rejected update mutated state'
    visible,_=frame('CH1');assert visible.shape==(1080,1920,3)
    cv2.imencode('.jpg',visible)[1].tofile(str(args.output/'visible.jpg'))
    tiles=[]
    for title,image in [('LEGACY',legacy),('ENHANCED / noise=0',enhanced),('ENHANCED / noise=0.03',noisy)]:
        tile=cv2.copyMakeBorder(image,35,0,0,0,cv2.BORDER_CONSTANT,value=(25,25,25))
        cv2.putText(tile,title,(15,25),cv2.FONT_HERSHEY_SIMPLEX,.65,(220,220,220),1,cv2.LINE_AA)
        tiles.append(tile)
    cv2.imencode('.png',np.hstack(tiles))[1].tofile(str(args.output/'comparison.png'))
    report.update(passed=True,profile_mean_difference=difference,palette_inversion_error=inversion,
                  noise_mean_difference=noise_difference,native_ir=[640,512],native_visible=[1920,1080],
                  malformed_updates_rejected=4)
finally:
    rpc('sensor.configure',dict(sensor='infrared',**initial))
    report['restored']=True
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))

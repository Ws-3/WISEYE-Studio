import sys,json,time,base64
from pathlib import Path
import cv2,numpy as np
sys.path.insert(0,'F:/WISEYE-Studio')
from training_client.client import Client
c=Client(port=50051);out=Path(__file__).parent
before=json.loads((out/'before-state.json').read_text())
sensor=before['sensors']['infrared']
keys=['enabled','fov_deg','palette','noise','thermal_profile','gain_mode','stable_agc','manual_low','manual_high','brightness','sky_denoise','noise_seed','agc_enabled','agc_response_s','sampling_scale','blur_px','contrast','background_detail']
c.rpc('sensor.configure',sensor='infrared',**{k:sensor[k] for k in keys})
c.rpc('gimbal.set_angles',yaw_deg=before['yaw_deg'],pitch_deg=before['pitch_deg'])
time.sleep(5)
for ch in ['CH1','CH2','OBS']:
 (out/(ch+'_after.jpg')).write_bytes(base64.b64decode(c.rpc('camera.stream_frame',channel=ch)['image_base64']))
c.rpc('camera.signal_recording',enabled=True);time.sleep(.7)
p=c.rpc('camera.signal_frame')
for key,suffix in [('signal_base64','.f32'),('sky_mask_base64','.sky.u8'),('target_mask_base64','.target.u8')]:
 (out/('after'+suffix)).write_bytes(base64.b64decode(p[key]))
c.rpc('camera.signal_recording',enabled=False)
s=c.rpc('sim.get_state');(out/'after-state.json').write_text(json.dumps(s,indent=2),encoding='utf8')
report={}
for tag in ['before','after']:
 image=cv2.imread(str(out/('CH2_'+tag+'.jpg')),0)
 sky=np.fromfile(out/(tag+'.sky.u8'),np.uint8).reshape(image.shape)>0
 target=np.fromfile(out/(tag+'.target.u8'),np.uint8).reshape(image.shape)>0
 def stats(mask):
  v=image[mask]
  if not v.size:return dict(count=0)
  return dict(count=int(v.size),median=float(np.median(v)),p05=float(np.percentile(v,5)),p95=float(np.percentile(v,95)),above235=float((v>235).mean()))
 report[tag]={name:stats(mask) for name,mask in [('background',~sky&~target),('target',target),('sky',sky)]}
print(json.dumps(report,indent=2),flush=True)
(out/'tone-statistics.json').write_text(json.dumps(report,indent=2),encoding='utf8')
c.rpc('gimbal.set_tracking',enabled=before['tracking'])

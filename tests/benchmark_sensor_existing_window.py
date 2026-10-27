"""Read UE timecodes from the existing 1600x1000 WISEYE window; no extra decoder."""
import argparse,ctypes,json,time,math,statistics
from PIL import ImageGrab
from pathlib import Path
from integrations.gimbal_client import GimbalClient
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=40);p.add_argument('--label',default='baseline');a=p.parse_args()
assert a.label.replace('_','').replace('-','').isalnum(), 'Label must be a safe filename suffix'
user32=ctypes.windll.user32;user32.FindWindowW.restype=ctypes.c_void_p
hwnd=user32.FindWindowW(None,'WISEYE Studio · 智瞳控制台');assert hwnd,'Existing WISEYE window required'
assert ImageGrab.grab(window=hwnd).size==(1600,1000),'This screen calibration expects 1600x1000'
origin=time.perf_counter();(ROOT/'runtime/latency_probe_config.json').write_text(json.dumps(dict(origin=origin)))
def fixture(command):
 request=ROOT/'runtime/latency-probe-request.json';assert not request.exists(),'Probe request busy'
 temp=request.with_suffix('.tmp');temp.write_text(json.dumps(dict(command=command,origin=origin)),encoding='utf8');temp.replace(request)
def decode(image,box):
 x,y,width,height=box
 for shift in (0,-.5,.5,-1,1):
  values=[image.getpixel((round(x+shift+width*(.05+(i+.5)*.9/34)),round(y+height/2)))[0] for i in range(34)]
  black,white=values[:2]
  if abs(white-black)<20:continue
  word=sum(int((v-(black+white)/2)*(white-black)>0)<<i for i,v in enumerate(values[2:]));stamp=word&0xFFFFFF
  if (word>>24)==((stamp&255)^((stamp>>8)&255)^((stamp>>16)&255)^0xA7):
   age=(time.perf_counter()-origin)*1000-stamp
   if 0<age<10000:return stamp,age
 return None
boxes={'visible':(271,739,250,140),'infrared':(653,739,175,140),'observer':(363,235,756,426)}
rows={k:[] for k in boxes};invalid={k:0 for k in boxes};grabs=[]
try:
 fixture('start')
 deadline=time.monotonic()+15
 while time.monotonic()<deadline:
  flag=ROOT/'logs/latency_probe_ready.json'
  if flag.exists() and json.loads(flag.read_text()).get('origin')==origin:break
  time.sleep(.05)
 else:raise RuntimeError('Fixture failed')
 time.sleep(5);began=time.monotonic();end=began+a.seconds
 while time.monotonic()<end:
  t=time.perf_counter();image=ImageGrab.grab(window=hwnd);grabs.append((time.perf_counter()-t)*1000)
  for key,box in boxes.items():
   sample=decode(image,box)
   if sample:rows[key].append(dict(stamp=sample[0],age_ms=sample[1]))
   else:invalid[key]+=1
  time.sleep(max(0,.05-(time.perf_counter()-t)))
 image.save(str(ROOT/'logs/latency_existing_window_pattern.png'))
 def stats(v):
  if not v:return None
  v=sorted(v);return dict(samples=len(v),median_ms=round(statistics.median(v),1),p95_ms=round(v[math.ceil((len(v)-1)*.95)],1),max_ms=round(max(v),1))
 sources={}
 for key,values in rows.items():
  unique={}
  for r in values:unique.setdefault(r['stamp'],r['age_ms'])
  sources[key]=dict(content_age=stats([r['age_ms'] for r in values]),first_observed_source_frames=stats(list(unique.values())),unique_fps=round(len(unique)/a.seconds,2),invalid=invalid[key])
 state=GimbalClient(timeout=4).state()
 skew=[v['stamp']-i['stamp'] for v,i in zip(rows['visible'],rows['infrared'])] if not any(invalid.values()) else []
 report=dict(scope='Actual existing WISEYE window via PrintWindow, no second viewer/decoder; periodic window-content observation, not exact paint onset',scene=state['scene_id'],profile=state['performance_profile'],seconds=a.seconds,poll_interval_ms=50,window_grab_ms=stats(grabs),sources=sources,layout='Existing 1600x1000 scene-led layout',original_resolutions=dict(visible=[1920,1080],infrared=[640,512],observer=[960,540]),visible_minus_infrared_source_time_ms=round(statistics.median(skew),1) if skew else None,absolute_eo_ir_source_skew=stats([abs(s) for s in skew]))
 suffix='' if a.label=='baseline' else '_'+a.label
 (ROOT/f'docs/evidence/sensor_existing_window_latency_20261022{suffix}.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 (ROOT/f'logs/latency_existing_window{suffix}_raw.json').write_text(json.dumps(rows))
 print(json.dumps(report,indent=2),flush=True)
finally:
 fixture('stop')

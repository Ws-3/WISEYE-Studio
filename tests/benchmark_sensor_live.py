"""Measure actual UE-rendered optical timecodes at native RTSP input and Qt paint.

Requires the temporary PIE fixture from ue5/scripts/probe_video_latency.py.
Does not infer video delay from TCP ping or the GUI 'received ago' label.
"""
import argparse,json,time,statistics,math,threading
from integrations.rtsp.rtsp_gateway import UEFrameClient
from PySide6.QtGui import QImage
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication,QLabel
from apps.desktop_app.main_window import MainWindow,ImageView
from core.config import ROOT,AppConfig
from integrations.gimbal_client import GimbalClient
from apps.desktop_app.lidar_view import LidarView
p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=30);p.add_argument('--label',default='economy');p.add_argument('--motion',action='store_true');p.add_argument('--direct',action='store_true');p.add_argument('--native-preview',action='store_true');args=p.parse_args()
origin=time.perf_counter()
(ROOT/'runtime/latency_probe_config.json').write_text(json.dumps(dict(origin=origin)))
def fixture(command):
 request=ROOT/'runtime/latency-probe-request.json';temporary=request.with_suffix('.tmp')
 if request.exists():raise RuntimeError('Another editor request is pending')
 temporary.write_text(json.dumps(dict(command=command,origin=origin)),encoding='utf8');temporary.replace(request)
app=QApplication([]);records={};bad={};debug={};cloud_records=[];stop=threading.Event();window=None
oldshow=ImageView.show_image

def decode(frame,key):
 width,height=frame.width(),frame.height()
 values=[frame.pixelColor(round(width*(.05+(i+.5)*.9/34)),height//2).red() for i in range(34)]
 debug[key]=values
 black,white=values[:2]
 if abs(white-black)<20:return None
 bits=[int((v-(white+black)/2)*(white-black)>0) for v in values[2:]]
 word=sum(v<<i for i,v in enumerate(bits));stamp=word&0xFFFFFF;crc=word>>24
 if crc!=((stamp&255)^((stamp>>8)&255)^((stamp>>16)&255)^0xA7):return None
 return stamp

def show(view,frame):
 key=getattr(view,'probe_key',None)
 if key:
  stamp=decode(frame,key);view.probe_stamp=stamp;view.probe_counter=getattr(view,'probe_counter',0)+1
  if stamp is None:bad[key]=bad.get(key,0)+1
  else:view.probe_received_ms=(time.perf_counter()-origin)*1000-stamp
 oldshow(view,frame)

def paint(view,event):
 QLabel.paintEvent(view,event)
 key=getattr(view,'probe_key',None);stamp=getattr(view,'probe_stamp',None);number=getattr(view,'probe_counter',0)
 if key and stamp is not None and number!=getattr(view,'probe_painted',-1):
  view.probe_painted=number;age=(time.perf_counter()-origin)*1000-stamp
  if 0<age<10000:records.setdefault(key,[]).append(dict(stamp=stamp,receive_ms=view.probe_received_ms,paint_ms=age))
ImageView.show_image=show;ImageView.paintEvent=paint
oldcloud=LidarView.set_points;oldcloudpaint=LidarView.paintEvent
def cloud(view,points,total_count,rays=0):
 view.probe_cloud=None
 if points:
  x=statistics.median(p[0] for p in points);index=round((x-2.435)/.25)
  if 0<=index<32 and abs(x-(2.435+index*.25))<.04:view.probe_cloud=dict(index=index,x=x,received_ms=(time.perf_counter()-origin)*1000)
 oldcloud(view,points,total_count,rays)
def cloudpaint(view,event):
 oldcloudpaint(view,event)
 data=getattr(view,'probe_cloud',None)
 if data:cloud_records.append(dict(data,paint_ms=(time.perf_counter()-origin)*1000));view.probe_cloud=None
LidarView.set_points=cloud;LidarView.paintEvent=cloudpaint
saved=GimbalClient(timeout=5).state();worker=None;direct_worker=None;direct_rows=[]
try:
 fixture('start')
 deadline=time.monotonic()+15
 while time.monotonic()<deadline:
  ready=ROOT/'logs/latency_probe_ready.json'
  if ready.exists() and json.loads(ready.read_text()).get('origin')==origin:break
  time.sleep(.05)
 else:raise RuntimeError('UE optical fixture did not become ready; inspect runtime/request-error.txt')
 window=MainWindow(AppConfig.load());window.resize(1600,960);window.show()
 for key,view in window.gallery.views.items():
  if key.endswith(('/visible','/infrared','/observer')):view.probe_key=key
 window.connect_ue()
 deadline=time.monotonic()+20
 while time.monotonic()<deadline and len(window.gallery.frames)<3:app.processEvents();time.sleep(.005)
 if args.motion:
  def motion():
   sdk=GimbalClient(timeout=5)
   try:
    for angle in [saved['yaw_deg']+d for d in (6,-6,8,-8,5,-5,0)*5]:
     if stop.is_set():return
     sdk.set_angles(max(-170,min(170,angle)),saved['pitch_deg']);stop.wait(2)
   except Exception as e:print('Motion stopped:',e,flush=True)
  worker=threading.Thread(target=motion,daemon=True);worker.start()
 if args.direct:
  def direct():
   client=UEFrameClient('127.0.0.1',50051,'CH1',60,'ptz-01')
   try:
    while not stop.is_set():
     began=time.perf_counter();encoded=client.frame();received=time.perf_counter();stamp=decode(QImage.fromData(encoded),'direct_visible')
     if stamp is not None:direct_rows.append(dict(time=time.perf_counter(),age_ms=(received-origin)*1000-stamp,request_ms=(received-began)*1000))
     stop.wait(max(0,.2-(time.perf_counter()-began)))
   except (OSError,ValueError,RuntimeError) as error:print('Direct probe stopped:',error,flush=True)
   finally:client.close()
  direct_worker=threading.Thread(target=direct,daemon=True);direct_worker.start()
 warmup=time.monotonic()+5
 while time.monotonic()<warmup:app.processEvents();time.sleep(.004)
 records.clear();bad.clear();cloud_records.clear();direct_rows.clear();started=time.monotonic();deadline=started+args.seconds
 while time.monotonic()<deadline:app.processEvents();time.sleep(.004)
 result={}
 def stats(values):
  if not values:return None
  values=sorted(values);return dict(samples=len(values),median_ms=round(statistics.median(values),1),p95_ms=round(values[math.ceil((len(values)-1)*.95)],1),max_ms=round(max(values),1))
 for key,rows in records.items():
  first={}
  for row in rows:first.setdefault(row['stamp'],row)
  result[key]=dict(all_presented=stats([r['paint_ms'] for r in rows]),new_source_frames=stats([r['paint_ms'] for r in first.values()]),receive=stats([r['receive_ms'] for r in rows]),qt_paint_after_receive=stats([r['paint_ms']-r['receive_ms'] for r in rows]),unique_fps=round(len(first)/args.seconds,2),invalid_frames=bad.get(key,0))
 path=ROOT/'docs/evidence/sensor_end_to_end_latency_20261022.json';previous=json.loads(path.read_text(encoding='utf8')) if path.exists() else {}
 from apps.desktop_app.ue_preview_client import UEPreviewClient
 transport='UE native latest-JPEG preview' if all(isinstance(c,UEPreviewClient) for c in window.gallery.clients.values()) else 'RTSP'
 previous[args.label]=dict(scope=f'UE PIE pre-Slate scene timecode -> {transport} -> MainWindow ImageView paint; excludes physical monitor scanout',seconds=args.seconds,motion=args.motion,scene=saved['scene_id'],profile=saved['performance_profile'],resolution={k:[v.width(),v.height()] for k,v in window.gallery.frames.items()},sources=result,invalid=bad)
 fixture('stop')
 deadline=time.monotonic()+5
 while time.monotonic()<deadline:
  flag=ROOT/'logs/latency_probe_cleaned.json'
  if flag.exists() and flag.stat().st_mtime>time.time()-5:break
  app.processEvents();time.sleep(.02)
 events=json.loads((ROOT/'logs/latency_probe_lidar_events.json').read_text())
 first={}
 for row in cloud_records:
  matches=[e for e in events if e['index']==row['index'] and e['time_ms']<=row['paint_ms']]
  if matches:
   e=matches[-1];first.setdefault(e['time_ms'],dict(paint_ms=row['paint_ms']-e['time_ms'],receive_ms=row['received_ms']-e['time_ms']))
 previous[args.label]['lidar_transition_to_paint']=stats([r['paint_ms'] for r in first.values()])
 previous[args.label]['lidar_valid_updates']=len(cloud_records)
 previous[args.label]['visible_direct_jpeg_receive']=stats([r['age_ms'] for r in direct_rows])
 previous[args.label]['direct_request_duration']=stats([r['request_ms'] for r in direct_rows])
 (ROOT/'logs'/('latency_'+args.label+'_raw.json')).write_text(json.dumps(dict(video=records,lidar=cloud_records,direct=direct_rows)),encoding='utf8')
 previous[args.label]['test_conditions']='One additional instrumented MainWindow; existing desktop and UE viewport remain running; 5 second preview warmup; original native resolutions; temporary PIE targets only.'
 path.write_text(json.dumps(previous,indent=2),encoding='utf8');print(json.dumps(previous[args.label],indent=2),flush=True)
 for key,image in window.gallery.frames.items():image.save(str(ROOT/'logs'/('latency_'+key.replace('/','_')+'.png')))
finally:
 stop.set()
 if worker:worker.join(timeout=6)
 if direct_worker:direct_worker.join(timeout=9)
 if args.motion:
  sdk=GimbalClient(timeout=5);sdk.stop();sdk.set_angles(saved['yaw_deg'],saved['pitch_deg'])
  if saved['tracking']:sdk.track(saved.get('tracking_target','uav-01'))
 if window:window.close();app.processEvents()
 if not (ROOT/'logs/latency_probe_cleaned.json').exists() or (ROOT/'logs/latency_probe_cleaned.json').stat().st_mtime<time.time()-10:
  fixture('stop')

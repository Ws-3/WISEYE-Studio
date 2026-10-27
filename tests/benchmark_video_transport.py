"""Measure MJPEG->H264->RTSP->Qt latency using a timestamp encoded into pixels.

Runs isolated MediaMTX on loopback:18554; does not change UE or production streams.
"""
import io,json,shutil,statistics,subprocess,threading,time,sys
from pathlib import Path
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PIL import Image,ImageDraw
from apps.desktop_app.rtsp_client import RTSPVideoClient
from integrations.rtsp.rtsp_gateway import ffmpeg_command
from core.config import ROOT
width,height=map(int,sys.argv[2].split('x')) if len(sys.argv)>2 else (640,512)
app=QApplication([]);origin=time.monotonic();flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
config=ROOT/'logs/latency_probe.yml';config.write_text('logLevel: error\nmoq: no\nplayback: no\napi: no\nmetrics: no\npprof: no\nrtspAddress: 127.0.0.1:18554\nrtspTransports: [tcp]\nrtmp: no\nhls: no\nwebrtc: no\nsrt: no\npaths:\n  all_others:\n    source: publisher\n')
server=subprocess.Popen([str(ROOT/'third_party/mediamtx/mediamtx.exe'),str(config)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
result={}
try:
 QTest.qWait(400)
 assert server.poll() is None,server.returncode
 for label in [sys.argv[1] if len(sys.argv)>1 else 'after']:
  stop=threading.Event();ages=[];writes=[];url=f'rtsp://127.0.0.1:18554/{label}'
  publisher=subprocess.Popen(ffmpeg_command(shutil.which('ffmpeg'),25,url),stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=(ROOT/f'logs/latency_{label}_encoder.log').open('wb'),creationflags=flags)
  def write_frames():
   try:
    while not stop.is_set():
     began=time.monotonic();stamp=round((began-origin)*1000)
     frame=Image.new('RGB',(width,height),(90,90,90));draw=ImageDraw.Draw(frame)
     for bit in range(32):draw.rectangle((bit*12,0,bit*12+11,31),fill='white' if stamp&(1<<bit) else 'black')
     buffer=io.BytesIO();frame.save(buffer,format='JPEG',quality=95)
     publisher.stdin.write(buffer.getvalue());publisher.stdin.flush();writes.append(time.monotonic()-began)
     stop.wait(max(0,.04-(time.monotonic()-began)))
   except (OSError,ValueError):pass
  worker=threading.Thread(target=write_frames,daemon=True);worker.start()
  client=RTSPVideoClient(size=(width,height))
  def receive(frame,fps):
   stamp=sum((1<<i) for i in range(32) if frame.pixelColor(i*12+6,15).red()>128)
   age=(time.monotonic()-origin)*1000-stamp
   if 0<=age<10000:ages.append(age)
  client.state_changed.connect(lambda connected,text:print('PLAYER',connected,text,flush=True))
  client.frame_received.connect(receive);client.start(url)
  deadline=time.monotonic()+12
  while time.monotonic()<deadline:
   app.processEvents();time.sleep(.005)
  client.stop();stop.set();publisher.terminate();worker.join(timeout=2);publisher.wait(timeout=5)
  assert len(ages)>=30,(label,len(ages),len(writes))
  result[label]=dict(width=width,height=height,scope='MJPEG timestamp generation through RTSP to Qt; excludes UE',frames=len(ages),median_ms=statistics.median(ages),p95_ms=sorted(ages)[int(len(ages)*.95)],max_write_ms=max(writes)*1000)
finally:
 server.terminate();server.wait(timeout=5)
path=ROOT/'docs/evidence/video_transport_latency_20261022.json'
previous=json.loads(path.read_text(encoding='utf8')) if path.exists() else {}
previous.update(result);path.write_text(json.dumps(previous,indent=2),encoding='utf8');print(json.dumps(result,indent=2))

"""Event packets rendered as a short polarity window, never as fake RTSP."""
import time
import numpy as np
from PySide6.QtGui import QImage
from apps.desktop_app.rtsp_client import RTSPVideoClient
from core.local_rpc import request


class EventPreviewClient(RTSPVideoClient):
    def start_source(self,host,port,channel,device_id=None):self.start((host,int(port),device_id))

    def _worker(self,generation,endpoint):
        host,port,device=endpoint;cursor=0;run=None;previous=None
        while self.running and generation==self._generation:
            began=time.monotonic()
            try:
                payload=dict(device_id=device,after_sequence=cursor,max_events=5000,latest=True)
                if run:payload['run_id']=run
                # request() is loopback-oriented; keep the configured host for
                # source identity and reject unsupported remote control explicitly.
                if host not in ('localhost','127.0.0.1'):raise ValueError('事件预览当前使用本机控制接口')
                packet=request(port,'sensor.event.get_packet',payload,timeout=1)
                if packet.get('status')!='ok':raise ValueError(packet.get('error',{}).get('message','等待事件相机'))
                data=packet['payload'];run=data['run_id'];cursor=data['next_cursor']
                identity=(run,data['generation'],data['world_time_s'],data['latest_sequence'])
                if identity==previous:
                    time.sleep(.05);continue
                previous=identity
                rgb=np.empty((480,640,3),dtype=np.uint8);rgb[:]=[16,20,25]
                events=np.asarray(data['events'],dtype=np.int64)
                if events.size:
                    events=events.reshape(-1,4)
                    cutoff=int(data['world_time_s']*1e6)-50000
                    events=events[(events[:,2]>=cutoff)&(events[:,0]>=0)&(events[:,0]<640)&(events[:,1]>=0)&(events[:,1]<480)]
                    for polarity,color in [(1,[65,230,210]),(-1,[245,90,90])]:
                        selected=events[events[:,3]==polarity];rgb[selected[:,1],selected[:,0]]=color
                image=QImage(rgb.data,640,480,640*3,QImage.Format.Format_RGB888).copy()
                with self._lock:
                    if not self.running or generation!=self._generation:break
                    if self._pending is not None:self._overwritten+=1
                    self.last_frame=time.monotonic();self._pending=(generation,image,20.)
            except (OSError,ValueError,KeyError,RuntimeError):
                run=None;cursor=0
                if not self.running or generation!=self._generation:return
                try:self._worker_state.emit(generation,False,'等待事件相机数据…')
                except RuntimeError:return  # QObject can be destroyed during a bounded RPC.
                time.sleep(.2)
            time.sleep(max(.001,.05-(time.monotonic()-began)))

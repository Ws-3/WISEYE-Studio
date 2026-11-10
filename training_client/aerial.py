"""Unlabelled aircraft camera acquisition; never passed off as GT or paired data."""
import base64,hashlib,json,math,re
from pathlib import Path
from .client import RPCError

def validate_raw(packet,device=None,sensor=None):
    if not isinstance(packet.get('device_id'),str) or not re.fullmatch(r'uav-[0-9]{2}',packet['device_id']):raise ValueError('Invalid aerial device ID')
    if packet.get('modality') not in ('visible','infrared') or packet.get('channel')!=('AERIAL_IR' if packet['modality']=='infrared' else 'AERIAL'):raise ValueError('Aerial modality/channel mismatch')
    if device and packet.get('device_id')!=device:raise ValueError('Wrong aerial device')
    if sensor and packet.get('modality')!=sensor:raise ValueError('Wrong aerial modality')
    if packet.get('channel') not in ('AERIAL','AERIAL_IR') or not packet.get('run_id'):raise ValueError('Missing aerial frame identity')
    w,h=packet.get('width'),packet.get('height')
    if type(w) is not int or type(h) is not int or not (0<w<=4096 and 0<h<=4096):raise ValueError('Invalid aerial dimensions')
    for k in ('frame_number','simulation_time_s'):
        if type(packet.get(k)) not in (int,float) or not math.isfinite(packet[k]) or packet[k]<0:raise ValueError('Invalid aerial timestamp')
    if packet.get('encoding')!='jpeg':raise ValueError('Unsupported aerial encoding')
    data=base64.b64decode(packet['image_base64'],validate=True)
    if not data.startswith(b'\xff\xd8') or not data.endswith(b'\xff\xd9'):raise ValueError('Invalid aerial JPEG')
    return data

def acquire(client,sensors,stop):
    samples={}
    for sensor in sensors:
        if stop.is_set():raise InterruptedError('Stopped')
        packet=client.rpc('camera.stream_frame',channel='AERIAL_IR' if sensor=='infrared' else 'AERIAL',quality=90)
        validate_raw(packet,client.device,sensor)
        packet=dict(packet,source_sensor_id=packet['sensor_id'],sensor_id=sensor,objects=[],ignored_objects=[],
                    annotation_status='pending_manual',training_eligible=False,negative_sample=False)
        packet['frame_id']=frame_identity(packet)
        samples[sensor]=packet
    if len({p['run_id'] for p in samples.values()})!=1:raise ValueError('Aerial session changed during acquisition')
    return dict(samples=samples,raw=True,source_kind='aerial')

def frame_identity(packet):
    # Native frame counters restart when a camera is released or power-cycled.
    # World capture time disambiguates those frames within the same simulator run.
    return f"{packet['run_id']}/{packet['device_id']}/{packet['channel']}/{packet['frame_number']}/{packet['simulation_time_s']:.9f}"

def save_raw(packet,output):
    image=validate_raw(packet)
    identity=frame_identity(packet)
    name=('IR_' if packet['modality']=='infrared' else 'VIS_')+hashlib.sha256(identity.encode()).hexdigest()[:24]
    root=Path(output)/'RawAerial'/packet['device_id']/('IR' if packet['modality']=='infrared' else 'visible')
    meta=root/'annotations'/(name+'.json')
    if meta.exists():return False
    metadata={k:v for k,v in packet.items() if k!='image_base64'}
    metadata['frame_id']=identity
    metadata.update(image_sha256=hashlib.sha256(image).hexdigest(),dataset_schema=4,annotation_status='pending_manual',training_eligible=False,negative_sample=False,objects=[],ignored_objects=[],class_names={'0':'drone','1':'person','2':'vehicle'})
    for relative,data in [('images/'+name+'.jpg',image),('annotations/'+name+'.json',json.dumps(metadata,ensure_ascii=False,indent=2).encode('utf-8'))]:
        path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix(path.suffix+'.tmp');temp.write_bytes(data);temp.replace(path)
    return True

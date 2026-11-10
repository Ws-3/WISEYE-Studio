"""Readable sensor names and append-only modality folders, without pair manifests."""
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import tempfile


def _slug(value,limit=24):
    return re.sub(r'[^A-Za-z0-9.-]+','-',str(value)).strip('.-')[:limit] or 'Unknown'


def weather_name(environment):
    if not isinstance(environment,dict):return 'EnvUnknown'
    values=[environment.get(k) for k in ('clouds','rain','fog')]
    if any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in values):return 'EnvUnknown'
    labels=[name for name,value in zip(('Clouds','Rain','Fog'),values) if value>0]
    name='-'.join(labels) if labels else 'Clear'
    hour=environment.get('hour')
    if environment.get('time_override') is True and type(hour) in (int,float) and math.isfinite(hour) and 0<=hour<24:
        name+='-Day' if 6<=hour<18 else '-Night'
    return name


def model_name(packets):
    models=set()
    for packet in packets:
        models.update(m for m in packet.get('scenario_models',[]) if isinstance(m,str) and m)
    if not models:
        for packet in packets:
            models.update(o['model_id'] for o in packet['objects']+packet['ignored_objects'] if o.get('model_id'))
    names={'mavic3':'Mavic3','avata':'Avata','fixedwing':'Fixedwing'}
    return '-'.join(names.get(m,_slug(m,16)) for m in sorted(models)) if models else 'ModelUnknown'


def shared_name(packets,group_id):
    first=packets[0]
    environments=[p.get('environment') for p in packets]
    if any(e!=environments[0] for e in environments[1:]):raise ValueError('Pair environment snapshots differ')
    models=model_name(packets);weather=weather_name(environments[0])
    scene=_slug(first.get('scene_id','SceneUnknown'),16);device=_slug(first.get('device_id','DeviceUnknown'),12)
    session=_slug(first['run_id'],8)
    return f'{models}_{weather}_{scene}_{device}_s{session}_{group_id}',models,weather


def _files(packet,name,extra):
    from .client import validate_packet
    image=validate_packet(packet)
    metadata={key:value for key,value in packet.items() if key!='image_base64'}
    metadata.update(extra);metadata['image_sha256']=hashlib.sha256(image).hexdigest();metadata['dataset_schema']=2
    lines=[]
    for obj in packet['objects']:
        x1,y1,x2,y2=obj['bbox_xyxy'];width,height=packet['width'],packet['height']
        lines.append(f"{obj['class_id']} {(x1+x2)/2/width:.8f} {(y1+y2)/2/height:.8f} {(x2-x1)/width:.8f} {(y2-y1)/height:.8f}\n")
    return {f'images/{name}.jpg':image,f'labels/{name}.txt':''.join(lines).encode(),
            f'annotations/{name}.json':json.dumps(metadata,ensure_ascii=False,indent=2).encode('utf8')}


def save_sample(packet,output):
    from .client import validate_packet
    validate_packet(packet)
    if not packet['training_eligible']:return None
    group=hashlib.sha256(packet['frame_id'].encode()).hexdigest()[:24]
    shared,model,weather=shared_name([packet],group)
    sensor={'visible':'VIS','infrared':'IR'}.get(packet['sensor_id'],_slug(packet['sensor_id'],12))
    name=f'{sensor}_{shared}';root=Path(output)
    files=_files(packet,name,dict(filename_model=model,filename_weather=weather,sample_group_id=group))
    for relative,data in files.items():
        target=root/relative;target.parent.mkdir(parents=True,exist_ok=True)
        temporary=target.with_suffix(target.suffix+'.tmp');temporary.write_bytes(data);temporary.replace(target)
    return name


def save_pair(pair,output):
    from .client import validate_pair
    samples=validate_pair(pair)
    # Pair-only export: never leave a lone modality when a visible target was
    # excluded by policy in the other modality. Valid paired negatives remain.
    if not all(packet['training_eligible'] for packet in samples.values()):return None
    group=hashlib.sha256((pair['run_id']+'/'+pair['pair_id']).encode()).hexdigest()[:24]
    shared,model,weather=shared_name([samples['visible'],samples['infrared']],group)
    names={'visible':'VIS_'+shared,'infrared':'IR_'+shared}
    files={}
    for sensor,packet in samples.items():
        partner='infrared' if sensor=='visible' else 'visible'
        extra=dict(sample_group_id=group,pair_id=pair['pair_id'],filename_model=model,filename_weather=weather,
                   counterpart_image=names[partner]+'.jpg',counterpart_directory='IR' if partner=='infrared' else 'visible',
                   capture_delta_ms=1000*(samples['visible']['simulation_time_s']-samples['infrared']['simulation_time_s']),
                   request_round_trip_ms=pair.get('request_round_trip_ms'))
        modality='IR' if sensor=='infrared' else 'visible'
        for relative,data in _files(packet,names[sensor],extra).items():
            if relative.startswith('annotations/'):
                metadata=json.loads(data);metadata['dataset_schema']=3
                data=json.dumps(metadata,ensure_ascii=False,indent=2).encode('utf8')
            files[f'{modality}/{relative}']=data
    root=Path(output).resolve();root.mkdir(parents=True,exist_ok=True)
    pending=root/'.pending'
    if not pending.resolve().is_relative_to(root):raise ValueError('Staging must stay inside the selected dataset')
    for relative in files:
        if not (root/relative).resolve().is_relative_to(root):raise ValueError('Dataset folders must stay inside the selected dataset')
    existing=[relative for relative in files if (root/relative).exists()]
    if existing:
        if len(existing)!=len(files):raise ValueError('Existing paired sample is incomplete; refusing to overwrite')
        for relative,data in files.items():
            path=root/relative
            if not path.is_file():raise ValueError('Existing paired directory is incomplete')
            if '/annotations/' not in relative and path.read_bytes()!=data:raise ValueError('Existing paired sample content differs')
        return group
    pending.mkdir(exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix='pair-',dir=pending)).resolve()
    published=[]
    try:
        for relative,data in files.items():
            path=staging/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        # Stage the entire pair first; annotations publish last. Across two
        # fixed modality directories there is no atomic directory rename.
        for relative in sorted(files,key=lambda p:'/annotations/' in p):
            target=root/relative;target.parent.mkdir(parents=True,exist_ok=True)
            (staging/relative).rename(target);published.append(target)
    except BaseException:
        for target in reversed(published):target.unlink(missing_ok=True)
        raise
    finally:
        if staging.exists():
            if not staging.is_relative_to(pending.resolve()):raise ValueError('Invalid staging cleanup path')
            shutil.rmtree(staging)
        try:pending.rmdir()
        except OSError:pass
    return group

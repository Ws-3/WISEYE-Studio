"""Validated model templates and scene instances. Layout files remain compatible."""
import copy,json,math,re
from pathlib import Path
from core.layouts import LayoutStore

DEVICE_ID=re.compile(r'^(uav|ptz)-[0-9]{2}$')
MODELS={'mavic3':dict(kind='drone',name='Mavic 3',physics='shared_quadrotor'),
        'avata':dict(kind='drone',name='Avata',physics='shared_quadrotor'),
        'eo80':dict(kind='gimbal',name='80 cm 光电云台',sensors=['visible','infrared','lidar','event'])}

def validate_devices(data,scene_id):
    if not isinstance(data,dict) or type(data.get('version')) is not int or data['version']!=1 or data.get('scene_id')!=scene_id:
        raise ValueError('设备配置版本或场景不匹配')
    devices=data.get('devices');ids=set()
    if not isinstance(devices,list) or not 2<=len(devices)<=8:raise ValueError('支持 1–4 架无人机与 1–4 套云台')
    for item in devices:
        if not isinstance(item,dict):raise ValueError('设备配置必须为对象')
        ident=item.get('id');kind=item.get('kind');model=MODELS.get(item.get('model_id'))
        if not isinstance(ident,str) or not DEVICE_ID.fullmatch(ident) or ident.endswith('-00') or ident in ids:raise ValueError('设备 ID 无效或重复')
        if not model or model['kind']!=kind or not ident.startswith('uav-' if kind=='drone' else 'ptz-'):raise ValueError('型号与设备类型不匹配')
        ids.add(ident)
        if not isinstance(item.get('name'),str) or not 1<=len(item['name'].strip())<=60:raise ValueError('设备名称需要 1–60 字')
        for key in ('position_cm','rotation_deg'):
            values=item.get(key)
            limit=1e7 if key=='position_cm' else 180
            if not isinstance(values,list) or len(values)!=3 or not all(type(x) in (int,float) and abs(x)<=limit and math.isfinite(x) for x in values):raise ValueError(f'{key} 需要三个有限坐标')
        # UE stores pitch / yaw / roll; heading is allowed, tilt is not.
        if kind=='drone' and any(item['rotation_deg'][i] for i in (0,2)):raise ValueError('无人机初始俯仰/横滚暂仅支持 0')
    for kind,required in [('drone','uav-01'),('gimbal','ptz-01')]:
        group=[x for x in devices if x['kind']==kind]
        if not 1<=len(group)<=4 or required not in ids:raise ValueError('保留默认 uav-01 / ptz-01，每类最多 4 个实例')
    drones={x['id'] for x in devices if x['kind']=='drone'}
    for item in devices:
        if item['kind']=='gimbal' and item.get('tracking_target') not in drones:raise ValueError('云台跟踪目标必须为已配置无人机')
    return data

class DeviceStore:
    def __init__(self,root):self.root=Path(root);self.directory=self.root/'ue5/WISEYE/Config/WISEYE/Fleets'
    def load(self,scene):
        path=self.directory/(scene['id']+'.json')
        if path.exists():return copy.deepcopy(validate_devices(json.loads(path.read_text(encoding='utf-8-sig')),scene['id']))
        layout=LayoutStore(self.root).load(scene)
        return dict(version=1,scene_id=scene['id'],devices=[
            dict(id='uav-01',kind='drone',model_id='mavic3',name='无人机 1',position_cm=layout['flight_origin_cm'],rotation_deg=[0,0,0]),
            dict(id='ptz-01',kind='gimbal',model_id='eo80',name='云台 1',position_cm=layout['gimbal_location_cm'],rotation_deg=[0,0,0],tracking_target='uav-01')])
    def save(self,data):
        validate_devices(data,data.get('scene_id'))
        from core.scenes import ID
        if not isinstance(data['scene_id'],str) or not ID.fullmatch(data['scene_id']):raise ValueError('场景 ID 无效')
        return LayoutStore._write(self.directory/(data['scene_id']+'.json'),data)

"""Field patches distinguish live scene edits from saved initial layouts."""
import copy
from core.devices import validate_devices

FIELDS=('name','model_id','position_cm','rotation_deg','tracking_target')


def from_state(state):
    devices=[]
    for item in state.get('devices',[]):
        row={k:copy.deepcopy(item[k]) for k in ('id','kind','model_id','name','position_cm')}
        row['rotation_deg']=list(item.get('rotation_deg',[0,item.get('placement_yaw_deg',0),0]))
        if row['kind']=='gimbal':row['tracking_target']=item['tracking_target']
        devices.append(row)
    return validate_devices(dict(version=1,scene_id=state['scene_id'],devices=devices),state['scene_id'])


def changes(before, after):
    validate_devices(before,before['scene_id']);validate_devices(after,before['scene_id'])
    old={d['id']:d for d in before['devices']};new={d['id']:d for d in after['devices']}
    result=[]
    for ident,item in new.items():
        if ident not in old:result.append(dict(copy.deepcopy(item),action='add'))
        else:
            patch={k:copy.deepcopy(item[k]) for k in FIELDS if item.get(k)!=old[ident].get(k)}
            if patch:result.append(dict(patch,id=ident,action='update'))
    result.extend(dict(id=ident,action='remove') for ident in old if ident not in new)
    return result


def apply(before, edits):
    if not isinstance(edits,list) or len(edits)>16:raise ValueError('Invalid device changes')
    data=copy.deepcopy(before);rows={d['id']:d for d in data['devices']};seen=set()
    for patch in edits:
        if not isinstance(patch,dict):raise ValueError('Device patch must be an object')
        ident=patch.get('id');action=patch.get('action')
        if not isinstance(ident,str) or ident in seen:raise ValueError('Duplicate device patch')
        seen.add(ident)
        if action=='add':
            if ident in rows:raise ValueError('Device already exists')
            rows[ident]={k:copy.deepcopy(v) for k,v in patch.items() if k!='action'}
        elif action=='update':
            if ident not in rows or set(patch)-{'id','action',*FIELDS}:raise ValueError('Invalid device update')
            rows[ident].update({k:copy.deepcopy(v) for k,v in patch.items() if k in FIELDS})
        elif action=='remove':
            if ident in ('uav-01','ptz-01') or ident not in rows:raise ValueError('Cannot remove default/missing device')
            del rows[ident]
        else:raise ValueError('Unknown device change')
    data['devices']=list(rows.values())
    return validate_devices(data,before['scene_id'])

"""Explicit simulation WGS84 anchor, ECEF and local ENU; no map survey claim."""
from dataclasses import dataclass, asdict
import json
import math
from pathlib import Path
from core.scenes import ID
from core.layouts import LayoutStore

A=6378137.0
F=1/298.257223563
E2=F*(2-F)


def finite(value,limit):
    if type(value) not in (int,float) or not math.isfinite(value) or abs(value)>limit:
        raise ValueError('坐标必须是范围内的有限数值')
    return float(value)


def vector(value):
    if not isinstance(value,(list,tuple)) or len(value)!=3:raise ValueError('需要三个世界坐标分量')
    return tuple(finite(x,1e7) for x in value)


def ecef(latitude_deg,longitude_deg,height_m):
    p,l=map(math.radians,(finite(latitude_deg,90),finite(longitude_deg,180)))
    h=finite(height_m,1e6);n=A/math.sqrt(1-E2*math.sin(p)**2)
    return ((n+h)*math.cos(p)*math.cos(l),(n+h)*math.cos(p)*math.sin(l),(n*(1-E2)+h)*math.sin(p))


def geodetic(x,y,z):
    r=math.hypot(x,y);lon=math.atan2(y,x)
    if r<1e-8:return math.copysign(90,z),0.,abs(z)-A*(1-F)
    lat=math.atan2(z,r*(1-E2))
    for _ in range(15):
        n=A/math.sqrt(1-E2*math.sin(lat)**2)
        next_lat=math.atan2(z+E2*n*math.sin(lat),r)
        if abs(next_lat-lat)<1e-14:lat=next_lat;break
        lat=next_lat
    n=A/math.sqrt(1-E2*math.sin(lat)**2)
    h=r/math.cos(lat)-n if abs(math.cos(lat))>.5 else z/math.sin(lat)-n*(1-E2)
    return math.degrees(lat),math.degrees(lon),h


@dataclass(frozen=True)
class GeoReference:
    scene_id:str
    latitude_deg:float
    longitude_deg:float
    ellipsoid_height_m:float
    world_origin_cm:tuple=(0.,0.,0.)
    x_axis_azimuth_deg:float=0.

    def __post_init__(self):
        if not isinstance(self.scene_id,str) or not ID.fullmatch(self.scene_id):raise ValueError('场景ID无效')
        ecef(self.latitude_deg,self.longitude_deg,self.ellipsoid_height_m)
        finite(self.x_axis_azimuth_deg,360)
        object.__setattr__(self,'world_origin_cm',vector(self.world_origin_cm))

    def world_to_enu(self,position_cm):
        x,y,z=((v-o)/100 for v,o in zip(vector(position_cm),self.world_origin_cm))
        a=math.radians(self.x_axis_azimuth_deg)
        return x*math.sin(a)+y*math.cos(a),x*math.cos(a)-y*math.sin(a),z

    def enu_to_world(self,enu):
        e,n,u=(finite(v,1e6) for v in enu);a=math.radians(self.x_axis_azimuth_deg)
        xyz=(e*math.sin(a)+n*math.cos(a),e*math.cos(a)-n*math.sin(a),u)
        return tuple(o+100*v for o,v in zip(self.world_origin_cm,xyz))

    def basis(self):
        p,l=map(math.radians,(self.latitude_deg,self.longitude_deg))
        return ((-math.sin(l),math.cos(l),0.),(-math.sin(p)*math.cos(l),-math.sin(p)*math.sin(l),math.cos(p)),(math.cos(p)*math.cos(l),math.cos(p)*math.sin(l),math.sin(p)))

    def world_to_geodetic(self,position_cm):
        enu=self.world_to_enu(position_cm);base=ecef(self.latitude_deg,self.longitude_deg,self.ellipsoid_height_m)
        xyz=[base[i]+sum(v*axis[i] for v,axis in zip(enu,self.basis())) for i in range(3)]
        return geodetic(*xyz)

    def geodetic_to_world(self,latitude_deg,longitude_deg,ellipsoid_height_m):
        target=ecef(latitude_deg,longitude_deg,ellipsoid_height_m);base=ecef(self.latitude_deg,self.longitude_deg,self.ellipsoid_height_m)
        delta=[v-o for v,o in zip(target,base)]
        return vector(self.enu_to_world([sum(v*b for v,b in zip(delta,axis)) for axis in self.basis()]))

    def to_dict(self):return dict(version=1,datum='WGS84',height_reference='ellipsoid',purpose='simulation_anchor',**asdict(self))

    @classmethod
    def from_dict(cls,value):
        if not isinstance(value,dict) or type(value.get('version')) is not int or value.get('version')!=1 or value.get('datum')!='WGS84' or value.get('height_reference')!='ellipsoid' or value.get('purpose')!='simulation_anchor':
            raise ValueError('只接受WGS84椭球高的仿真地理基准')
        try:return cls(**{key:value[key] for key in cls.__dataclass_fields__})
        except (KeyError,TypeError) as error:raise ValueError('地理基准字段缺失或类型错误') from error


class GeoReferenceStore:
    def __init__(self,root):self.root=Path(root)
    def path(self,scene_id):
        if not isinstance(scene_id,str) or not ID.fullmatch(scene_id):raise ValueError('场景ID无效')
        return self.root/'configs/georeferences'/f'{scene_id}.json'
    def load(self,scene_id):
        path=self.path(scene_id)
        if not path.exists():return None
        value=GeoReference.from_dict(json.loads(path.read_text(encoding='utf-8-sig')))
        if value.scene_id!=scene_id:raise ValueError('地理基准场景不匹配')
        return value
    def save(self,reference):LayoutStore._write(self.path(reference.scene_id),reference.to_dict())

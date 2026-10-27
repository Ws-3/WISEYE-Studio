"""Shared route schema: UE world metres, Z up; no implicit takeoff or avoidance."""
import json
import math
from pathlib import Path
from core.scenes import ID


def validate_route(data, scene_id=None):
    if not isinstance(data,dict) or type(data.get('version')) is not int or data['version']!=1:
        raise ValueError('航线版本必须为 1')
    scene=data.get('scene_id')
    if not isinstance(scene,str) or not ID.fullmatch(scene) or (scene_id and scene!=scene_id):
        raise ValueError('航线与当前场景不匹配')
    if data.get('frame')!='ue_world_m':
        raise ValueError('航线坐标系必须为 ue_world_m（米，Z 向上）')
    if not isinstance(data.get('name'),str) or not 1<=len(data['name'].strip())<=80:
        raise ValueError('航线名称需要 1–80 个字符')
    speed=data.get('speed_mps')
    if type(speed) not in (int,float) or not .2<=speed<=15 or not math.isfinite(speed):
        raise ValueError('航线速度需要在 0.2–15 m/s 之间')
    if type(data.get('repeat')) is not bool:
        raise ValueError('repeat 必须为布尔值')
    points=data.get('waypoints')
    if not isinstance(points,list) or not 2<=len(points)<=128:
        raise ValueError('航线需要 2–128 个航点')
    for point in points:
        if not isinstance(point,list) or len(point)!=3 or not all(type(n) in (int,float) and abs(n)<=100000 and math.isfinite(n) for n in point):
            raise ValueError('每个航点需要三个有限的米制坐标（绝对值不超过 100000）')
    if any(math.dist(a,b)<.05 for a,b in zip(points,points[1:])):
        raise ValueError('相邻航点间距至少 0.05 m')
    return data


def load_route(path, scene_id):
    path=Path(path)
    if path.stat().st_size>65536:
        raise ValueError('航线文件超过 64 KiB')
    return validate_route(json.loads(path.read_text(encoding='utf-8-sig')),scene_id)


def save_route(path,data):
    validate_route(data)
    # Same atomic writer as initial layouts; never append partially saved JSON.
    from core.layouts import LayoutStore
    return LayoutStore._write(Path(path),data)

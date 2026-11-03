"""Versioned initial poses shared with UE. Runtime state never overwrites presets."""
import json
import math
import os
import re
from pathlib import Path
import tempfile
import uuid
from core.scenes import ID


def validate_layout(data, scene_id):
    if not isinstance(data, dict) or not ID.fullmatch(scene_id) or type(data.get('version')) is not int or data.get('version') != 1 or data.get('scene_id') != scene_id:
        raise ValueError('预设版本或场景 ID 无效')
    position_keys=('gimbal_location_cm','flight_origin_cm')+tuple(key for key in data if re.fullmatch(r'(uav|ptz)-[0-9]{2}',key))
    for key in position_keys:
        value = data.get(key)
        if not isinstance(value, list) or len(value) != 3 or not all(type(n) in (float, int) and math.isfinite(n) and abs(n) <= 1e7 for n in value):
            raise ValueError(f'{key} 必须是有效的三维坐标')
    headings=data.get('headings_deg',{})
    if not isinstance(headings,dict) or any(key not in position_keys or type(value) not in (int,float) or not math.isfinite(value) or abs(value)>180 for key,value in headings.items()):
        raise ValueError('朝向必须是 -180 到 180 度的有限数值')
    return data


class LayoutStore:
    def __init__(self, root):
        self.directory = Path(root) / 'ue5/WISEYE/Config/WISEYE/Layouts'

    def load(self, scene):
        scene_id = scene['id']
        if not ID.fullmatch(scene_id):
            raise ValueError('场景 ID 无效')
        path = self.directory / f'{scene_id}.json'
        if path.exists():
            return validate_layout(json.loads(path.read_text(encoding='utf-8-sig')), scene_id)
        return dict(version=1, scene_id=scene_id, gimbal_location_cm=list(scene['gimbal_location_cm']), flight_origin_cm=list(scene['flight_origin_cm']))

    def save(self, data):
        validate_layout(data, data['scene_id'])
        target = self.directory / (data['scene_id'] + '.json')
        return self._write(target, data)

    @staticmethod
    def _write(target, data):
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=target.parent, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, target)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        return target

    def _preset_directory(self, scene_id):
        if not isinstance(scene_id, str) or not ID.fullmatch(scene_id):
            raise ValueError('场景 ID 无效')
        return self.directory / 'Presets' / scene_id

    def load_preset(self, scene_id, preset_id):
        if not isinstance(preset_id, str) or not ID.fullmatch(preset_id):
            raise ValueError('预设 ID 无效')
        path = self._preset_directory(scene_id) / (preset_id+'.json')
        data = validate_layout(json.loads(path.read_text(encoding='utf-8-sig')), scene_id)
        if data.get('preset_id') != preset_id:
            raise ValueError('预设 ID 与文件名不一致')
        self._validate_name(data.get('name'))
        return data

    @staticmethod
    def _validate_name(name):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or any(ord(c) < 32 for c in name):
            raise ValueError('预设名称需要 1–80 个字符，不能包含控制字符')

    def list_presets(self, scene_id):
        result, errors = [], []
        for path in self._preset_directory(scene_id).glob('*.json'):
            try:
                result.append(self.load_preset(scene_id, path.stem))
            except (ValueError, OSError, TypeError) as exc:
                errors.append(f'{path.name}: {exc}')
        return sorted(result, key=lambda item:(item['name'].casefold(),item['preset_id'])), errors

    def save_preset(self, data, name, preset_id=None):
        validate_layout(data, data['scene_id'])
        self._validate_name(name)
        name = name.strip()
        directory = self._preset_directory(data['scene_id'])
        if preset_id is not None:
            # Updating requires an existing selected preset; never create a typo ID.
            self.load_preset(data['scene_id'], preset_id)
        items, _ = self.list_presets(data['scene_id'])
        if any(item['name'].casefold() == name.casefold() and item['preset_id'] != preset_id for item in items):
            raise ValueError('已有同名预设，请换名或更新所选预设')
        preset_id = preset_id or ('preset_'+uuid.uuid4().hex[:16])
        saved = dict(data, preset_id=preset_id, name=name)
        self._write(directory/(preset_id+'.json'), saved)
        return saved

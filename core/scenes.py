"""Versioned scene manifests and transactional, non-overwriting scene-pack import."""
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
import zipfile

ID = re.compile(r'^[a-z][a-z0-9_]{0,47}$')
MAP = re.compile(r'^/Game/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+$')


def validate_scene(data):
    if not isinstance(data, dict) or data.get('version') != 1:
        raise ValueError('场景配置 version 必须为 1')
    if not ID.fullmatch(data.get('id', '')):
        raise ValueError('场景 ID 仅支持小写字母、数字和下划线，以字母开头')
    if not isinstance(data.get('name'), str) or not 1 <= len(data['name']) <= 100:
        raise ValueError('请填写场景名称（1–100 字）')
    if not MAP.fullmatch(data.get('map', '')):
        raise ValueError('地图路径必须是 /Game/目录/地图名，不含扩展名')
    for key in ('gimbal_location_cm', 'flight_origin_cm', 'overview_location_cm', 'overview_rotation_deg'):
        v = data.get(key)
        if not isinstance(v, list) or len(v) != 3 or not all(type(x) in (int, float) and math.isfinite(x) and abs(x) <= 1e8 for x in v):
            raise ValueError(f'{key} 必须是三个有限数值')
    for key, low, high in [('flight_radius_cm', 1, 1e6), ('period_s', 1, 86400),
                           ('vertical_amplitude_cm', 0, 1e6), ('fov_deg', 5, 120)]:
        value = data.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'{key} 必须位于 [{low}, {high}]')
    if data.get('rig') != 'standard_v1':
        raise ValueError('当前支持的设备配置为 standard_v1')
    if data.get('source_map') and not MAP.fullmatch(data['source_map']):
        raise ValueError('源地图路径无效')
    return data


class SceneStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.project = self.root / 'ue5/WISEYE'
        self.directory = self.project / 'Config/WISEYE/Scenes'

    def list(self):
        result, errors = [], []
        for file in sorted(self.directory.glob('*.json')):
            try:
                scene = validate_scene(json.loads(file.read_text(encoding='utf-8-sig')))
                if file.stem != scene['id']:
                    raise ValueError('文件名必须与场景 ID 一致')
                scene = dict(scene)
                scene['installed'] = self.map_file(scene['map']).is_file() and scene.get('prepared', False) is True
                result.append(scene)
            except (ValueError, OSError, TypeError) as exc:
                errors.append(f'{file.name}: {exc}')
        return result, errors

    def map_file(self, package):
        if not MAP.fullmatch(package):
            raise ValueError('无效地图路径')
        return self.project / 'Content' / (package[6:] + '.umap')

    def register(self, scene, require_map=True):
        scene = validate_scene(scene)
        if require_map and not self.map_file(scene['map']).is_file():
            raise ValueError('地图尚未导入当前 UE 工程')
        self.directory.mkdir(parents=True, exist_ok=True)
        dest = self.directory / (scene['id'] + '.json')
        with dest.open('x', encoding='utf-8') as stream:
            json.dump(scene, stream, ensure_ascii=False, indent=2)
        return dest

    def import_pack(self, path):
        """Only Content/WISEYE/Scenes/<id> assets; no scripts, plugins or overwrite.

        Original package paths are preserved. Dependencies outside this namespace
        must already exist; the producer lists and hashes all included assets.
        """
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [i.filename for i in infos]
            if len(names) != len(set(n.casefold() for n in names)):
                raise ValueError('场景包包含重复路径')
            if len(names) > 50000 or sum(i.file_size for i in infos) > 20 * 1024**3:
                raise ValueError('场景包超过 20 GiB 或 50000 文件限制')
            if 'scene.json' not in names or archive.getinfo('scene.json').file_size > 65536:
                raise ValueError('场景包缺少有效的 scene.json')
            manifest = json.loads(archive.read('scene.json'))
            if manifest.get('engine_version', '5.8') != '5.8':
                raise ValueError('场景包引擎版本必须为 UE 5.8')
            scene = validate_scene(manifest['scene'])
            if scene.get('prepared') is not True:
                raise ValueError('场景包必须已完成标准设备安装')
            required = manifest.get('required_assets', {})
            if not isinstance(required, dict):
                raise ValueError('required_assets 必须为资源路径和 SHA256 对照表')
            for package, digest in required.items():
                if not MAP.fullmatch(package) or not re.fullmatch(r'[0-9a-f]{64}', str(digest)):
                    raise ValueError('依赖资源路径或哈希无效')
                asset = self.project / 'Content' / (package[6:] + '.uasset')
                actual = None
                if asset.is_file():
                    with asset.open('rb') as file:
                        actual = hashlib.file_digest(file, 'sha256').hexdigest()
                if actual != digest:
                    raise ValueError(f'缺少或不匹配的依赖资源，请先通过 UE 迁移：{package}')
            files = manifest.get('files')
            if not isinstance(files, dict) or set(names) != {'scene.json', *files}:
                raise ValueError('文件清单与场景包内容不一致（不要包含目录条目）')
            prefix = f"Content/WISEYE/Scenes/{scene['id']}/"
            if not scene['map'].startswith(f"/Game/WISEYE/Scenes/{scene['id']}/"):
                raise ValueError('标准包地图必须在自身场景命名空间内')
            for name, digest in files.items():
                p = PurePosixPath(name)
                if ('\\' in name or ':' in name or '..' in p.parts or not name.startswith(prefix)
                        or p.suffix.lower() not in ('.umap', '.uasset', '.ubulk', '.uexp')
                        or not re.fullmatch(r'[0-9a-f]{64}', str(digest))):
                    raise ValueError(f'不支持的资源路径或哈希：{name}')
            required_map = 'Content/' + scene['map'][6:] + '.umap'
            if required_map not in files:
                raise ValueError('场景包未包含入口地图')
            dest = self.project / prefix
            manifest_dest = self.directory / (scene['id'] + '.json')
            if dest.exists() or manifest_dest.exists():
                raise ValueError('同 ID 场景已存在；请使用新 ID，系统不会覆盖已有资源')
            self.directory.mkdir(parents=True, exist_ok=True)
            # Stage on the destination volume, verify before exposing any assets.
            with tempfile.TemporaryDirectory(prefix='wiseeye-import-', dir=self.project / 'Saved' if (self.project / 'Saved').exists() else self.project) as temp:
                staging = Path(temp)
                for name, digest in files.items():
                    target = staging / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    sha = hashlib.sha256()
                    with archive.open(name) as source, target.open('wb') as output:
                        while chunk := source.read(1024 * 1024):
                            sha.update(chunk)
                            output.write(chunk)
                    if sha.hexdigest() != digest:
                        raise ValueError(f'资源校验失败：{name}')
                dest.parent.mkdir(parents=True, exist_ok=True)
                (staging / prefix).rename(dest)
                try:
                    self.register(scene)
                except Exception:
                    # Only the newly installed directory belongs to this transaction.
                    shutil.rmtree(dest)
                    raise
            return scene

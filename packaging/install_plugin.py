"""Install a WISEYE source bundle into an existing Unreal project, without overwriting assets."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil


def install(bundle, project, scene, map_path, apply=False):
    bundle = Path(bundle).resolve()
    project = Path(project).resolve()
    if project.suffix.lower() != '.uproject' or not project.is_file():
        raise ValueError('Select an existing .uproject')
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,47}', scene):
        raise ValueError('Scene ID must use lowercase ASCII letters, digits and underscores')
    if not re.fullmatch(r'/Game/[A-Za-z0-9_/]+', map_path) or '..' in map_path:
        raise ValueError('Map must be an existing /Game/... asset path without an object suffix')
    host = project.parent
    document = json.loads(project.read_text(encoding='utf-8-sig'))
    if any(m['Name'].casefold() == 'test' for m in document.get('Modules', [])):
        raise ValueError('Host already owns module test; use another host to preserve /Script/test compatibility')
    manifest = json.loads((bundle / 'bundle.json').read_text(encoding='utf-8'))
    payload = bundle / 'payload'
    planned = []
    for relative, expected in manifest['files'].items():
        rel = PurePosixPath(relative)
        if rel.is_absolute() or '..' in rel.parts or not rel.parts or ':' in relative or '\\' in relative:
            raise ValueError(f'Unsafe bundle path: {relative}')
        source, target = payload / relative, host / relative
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Bundle checksum mismatch: {relative}')
        if not target.resolve().is_relative_to(host):
            raise ValueError(f'Host junction escapes project: {target}')
        if target.exists():
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                raise FileExistsError(f'Existing host file differs; no files installed: {target}')
        else:
            planned.append((source, target))
    config = host / 'Config/WISEYE/Scenes' / (scene + '.json')
    scene_data = {'version': 1, 'id': scene, 'name': scene, 'map': map_path,
                  'rig': 'standard_v1', 'prepared': False,
                  'gimbal_location_cm': [0, 0, 100], 'flight_origin_cm': [1200, 0, 100],
                  'overview_location_cm': [-1500, 0, 1500], 'overview_rotation_deg': [-25, 0, 0],
                  'flight_radius_cm': 600, 'period_s': 24, 'vertical_amplitude_cm': 150,
                  'fov_deg': 25, 'requires_external_asset': False}
    if config.exists():
        existing = json.loads(config.read_text(encoding='utf-8-sig'))
        if existing.get('id') != scene or existing.get('map') != map_path:
            raise FileExistsError(f'Existing scene configuration conflicts: {config}')
    elif any((host / 'Config/WISEYE' / kind / (scene + '.json')).exists()
             for kind in ['Fleets', 'Layouts', 'Observation']):
        raise FileExistsError('Choose a scene ID that does not reuse orphaned user configuration')
    engine = host / 'Config/DefaultEngine.ini'
    engine_text = engine.read_text(encoding='utf-8-sig') if engine.is_file() else ''
    # A shared project setting is needed for semantic thermal masks; conflicting values require review.
    for match in re.finditer(r'^\s*r\.CustomDepth\s*=\s*(\S+)', engine_text, re.M | re.I):
        if match.group(1) != '3':
            raise ValueError('Host CustomDepth setting differs from 3; resolve before installing')
    game = host / 'Config/DefaultGame.ini'
    game_text = game.read_text(encoding='utf-8-sig') if game.is_file() else ''
    report = {'files_to_add': len(planned), 'project': str(project), 'scene': scene,
              'map': map_path, 'applied': False, 'city_sample_required': False}
    if not apply:
        return report
    # All deterministic validation occurs before the first mutation. No user assets are overwritten.
    for source, target in planned:
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open('rb') as incoming, target.open('xb') as outgoing:
            shutil.copyfileobj(incoming, outgoing)
    if not config.exists():
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(json.dumps(scene_data, indent=2), encoding='utf-8')
    plugins = document.setdefault('Plugins', [])
    for name in ['WISEYE', 'ProjectAirSim', 'Drone', 'PythonScriptPlugin', 'EditorScriptingUtilities']:
        found = next((p for p in plugins if p['Name'] == name), None)
        if found is None:
            plugins.append({'Name': name, 'Enabled': True})
        else:
            found['Enabled'] = True
    if 'r.CustomDepth=3' not in engine_text.replace(' ', ''):
        engine.parent.mkdir(parents=True, exist_ok=True)
        engine.write_text(engine_text + '\n; WISEYE semantic mask support\n[/Script/Engine.RendererSettings]\nr.CustomDepth=3\n', encoding='utf-8')
    marker = '; WISEYE dynamic sensor and vehicle assets'
    if marker not in game_text:
        directories = ['/Game/WISEYE/DroneModels', '/Game/WISEYE/Sensors', '/Engine/BasicShapes', '/Drone', '/ProjectAirSim']
        block = '\n' + marker + '\n[/Script/UnrealEd.ProjectPackagingSettings]\n'
        block += ''.join('+DirectoriesToAlwaysCook=(Path="' + path + '")\n' for path in directories)
        game.parent.mkdir(parents=True, exist_ok=True)
        game.write_text(game_text + block, encoding='utf-8')
    backup = project.with_suffix('.uproject.before-wiseye')
    if not backup.exists():
        shutil.copy2(project, backup)
    temporary = project.with_suffix('.uproject.wiseye-tmp')
    temporary.write_text(json.dumps(document, indent=2), encoding='utf-8')
    temporary.replace(project)
    report['applied'] = True
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--scene', default='custom')
    parser.add_argument('--map', required=True)
    parser.add_argument('--apply', action='store_true', help='Default is a read-only preflight')
    args = parser.parse_args()
    print(json.dumps(install(Path(__file__).resolve().parent, args.project, args.scene, args.map, args.apply), indent=2))

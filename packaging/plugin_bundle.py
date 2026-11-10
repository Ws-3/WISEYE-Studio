"""Export the canonical UE sources as an installable custom-environment bundle.

The legacy /Script/test and /Game asset namespaces are intentionally preserved.
Generated sources are build artifacts, never a second editable source tree.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'Binaries', 'Intermediate', 'Saved', 'DerivedDataCache', '.git', '__pycache__'}


def copy_tree(source, target):
    if not source.is_dir():
        raise FileNotFoundError(source)
    for directory, dirs, files in os.walk(source, followlinks=False):
        dirs[:] = [n for n in dirs if n not in SKIP and not n.endswith('-F-Reference')]
        for name in dirs[:]:
            p = Path(directory) / name
            if p.is_junction() or p.is_symlink():
                # Dependencies are explicitly materialized; never preserve an absolute junction.
                copy_tree(p.resolve(strict=True), target / p.relative_to(source))
                dirs.remove(name)
        for name in files:
            p = Path(directory) / name
            if p.suffix.lower() in {'.log', '.tmp', '.pyc'}:
                continue
            q = target / p.relative_to(source)
            q.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, q)


def export(destination, root=ROOT):
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(f'Choose a new output directory: {destination}')
    project = root / 'ue5/WISEYE'
    destination.mkdir(parents=True)
    payload = destination / 'payload'
    plugin = payload / 'Plugins/WISEYE'
    copy_tree(project / 'Source/test', plugin / 'Source/test')
    module = plugin / 'Source/test/test.cpp'
    text = module.read_text(encoding='utf-8')
    old = 'IMPLEMENT_PRIMARY_GAME_MODULE( FWiseEyeGameModule, test, "test" );'
    if old not in text:
        raise ValueError('Canonical module startup changed; review exporter')
    module.write_text(text.replace(old, 'IMPLEMENT_MODULE(FWiseEyeGameModule, test);'), encoding='utf-8')
    descriptor = {
        'FileVersion': 3, 'Version': 11000, 'VersionName': '1.1.0',
        'FriendlyName': 'WISEYE Simulation', 'Category': 'Simulation',
        'Description': 'Dual-spectrum UAV and gimbal simulation; legacy module namespace preserved.',
        'CanContainContent': False, 'IsBetaVersion': True,
        'Modules': [{'Name': 'test', 'Type': 'Runtime', 'LoadingPhase': 'Default'}],
        'Plugins': [{'Name': n, 'Enabled': True} for n in
                    ['ProjectAirSim', 'Drone', 'MassAI', 'MassGameplay', 'MassCrowd', 'EnhancedInput']],
    }
    (plugin / 'WISEYE.uplugin').write_text(json.dumps(descriptor, indent=2), encoding='utf-8')
    for name in ['ProjectAirSim', 'Drone']:
        copy_tree(project / 'Plugins' / name, payload / 'Plugins' / name)
    copy_tree(project / 'ThirdParty', payload / 'ThirdParty')
    # Build.cs resolves ThirdParty relative to ModuleDirectory; runtime resolves the host project.
    copy_tree(project / 'ThirdParty', plugin / 'ThirdParty')
    for name in ['DroneModels', 'PTZRecovered', 'Sensors']:
        copy_tree(project / 'Content/WISEYE' / name, payload / 'Content/WISEYE' / name)
    # The calibrated legacy rig still references assets at /Game/Mesh*. Preserve these paths.
    for source in (project / 'Content').iterdir():
        if source.is_file() and source.suffix.lower() in {'.uasset', '.ubulk', '.uexp'}:
            target = payload / 'Content' / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    config = payload / 'Config/WISEYE'
    config.mkdir(parents=True)
    for name in ['standard_rig.json', 'device_dimensions.json']:
        shutil.copy2(project / 'Config/WISEYE' / name, config / name)
    scripts = payload / 'Scripts/WISEYE'
    scripts.mkdir(parents=True)
    for name in ['scene_tools.py', 'initialize_custom_scene.py']:
        shutil.copy2(root / 'ue5/scripts' / name, scripts / name)
    shutil.copy2(root / 'packaging/install_plugin.py', destination / 'install.py')
    notices = root / 'third_party/notices'
    if notices.is_dir():
        copy_tree(notices, destination / 'Licenses')
    shutil.copy2(root / 'docs/PLUGIN_DISTRIBUTION.md', destination / 'README.md')
    files = {p.relative_to(payload).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(payload.rglob('*')) if p.is_file()}
    manifest = {'schema': 1, 'release_version': '1.1.0', 'engine': '5.8', 'platform': 'Win64',
                'kind': 'source-plugin-and-host-assets', 'module': 'test',
                'city_sample_required': False, 'files': files,
                'status': 'local-preview-not-clean-machine-certified'}
    (destination / 'bundle.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return {'output': str(destination), 'files': len(files),
            'bytes': sum(p.stat().st_size for p in payload.rglob('*') if p.is_file())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    print(json.dumps(export(parser.parse_args().output), indent=2))

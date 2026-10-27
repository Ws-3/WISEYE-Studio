"""Shared development/release paths; release writes never target the install tree."""
import json
import os
from pathlib import Path
import shutil
import sys

SOURCE_ROOT = Path(__file__).resolve().parents[1]
IS_RELEASE = bool(getattr(sys, 'frozen', False) or os.environ.get('WISEYE_RELEASE_ROOT'))
INSTALL_ROOT = Path(os.environ.get('WISEYE_RELEASE_ROOT', Path(sys.executable).parent if IS_RELEASE else SOURCE_ROOT)).resolve()
RESOURCE_ROOT = Path(os.environ.get('WISEYE_RESOURCES_DIR', INSTALL_ROOT / 'Resources' if IS_RELEASE else SOURCE_ROOT)).resolve()
DATA_ROOT = Path(os.environ.get('WISEYE_DATA_DIR', Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'WISEYE' if IS_RELEASE else SOURCE_ROOT)).resolve()


def initialize_data():
    """Exclusive creation preserves user settings on every subsequent launch."""
    if not IS_RELEASE:
        return
    for subtree in ('configs', 'ue5/WISEYE/Config/WISEYE'):
        source = RESOURCE_ROOT / subtree
        for path in source.rglob('*'):
            if not path.is_file():
                continue
            target = DATA_ROOT / path.relative_to(RESOURCE_ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with target.open('xb') as output, path.open('rb') as incoming:
                    shutil.copyfileobj(incoming, output)
            except FileExistsError:
                pass
    for directory in ('logs', 'configs/routes', 'ue5/WISEYE/Saved/WISEYE'):
        (DATA_ROOT / directory).mkdir(parents=True, exist_ok=True)


def installed_scenes():
    if not IS_RELEASE:
        return None
    return set(json.loads((INSTALL_ROOT / 'release.json').read_text(encoding='utf-8'))['scenes'])

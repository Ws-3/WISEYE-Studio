"""Launched by Start-WISEYE -PrepareScene; keeps editor open for inspection."""
import os
import sys
from pathlib import Path
import json
import unreal
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scene_tools import prepare_scene, PROJECT
identifier = os.environ.get('WISEYE_PREPARE_SCENE', '')
assert identifier and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in identifier)
config = PROJECT / 'Config/WISEYE/Scenes' / (identifier + '.json')
scene = json.loads(config.read_text(encoding='utf-8-sig'))
prepare_scene(config, scene.get('source_map'))
unreal.EditorPythonScripting.set_keep_python_script_alive(True)

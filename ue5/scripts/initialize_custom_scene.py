"""Run in the host UE Python console after opening the desired map and saving work.

exec(open(r'<Host>/Scripts/WISEYE/initialize_custom_scene.py', encoding='utf-8').read())
Uses WISEYE_CUSTOM_SCENE (default custom). Never creates a replacement city.
"""
import json
import os
from pathlib import Path
import sys
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0, str(project / 'Scripts/WISEYE'))
from scene_tools import install_current_scene

scene_id = os.environ.get('WISEYE_CUSTOM_SCENE', 'custom')
if not scene_id or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in scene_id):
    raise ValueError('Invalid WISEYE_CUSTOM_SCENE')
config = project / 'Config/WISEYE/Scenes' / (scene_id + '.json')
scene = json.loads(config.read_text(encoding='utf-8-sig'))
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actual = world.get_path_name().split('.')[0]
if actual != scene['map']:
    raise RuntimeError('Open the configured map first: ' + scene['map'])
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
if any(isinstance(actor, unreal.WiseEyeDemo) for actor in actors):
    raise RuntimeError('Map already contains a WISEYE rig; do not install it twice')
install_current_scene(config)
unreal.log('WISEYE initialized in custom map: ' + scene['map'])

"""Rebuild the two source-camera materials; leaves maps and user settings alone."""
from pathlib import Path
import unreal

folder=Path(__file__).parent
for name in ['configure_infrared_facade.py','configure_visible_camera.py']:
    script=folder/name
    exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),
         {'__file__':str(script),'__name__':'__main__'})
unreal.log('WISEYE_IMAGING_REALISM_MATERIALS_SAVED')

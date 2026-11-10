"""Create the next independent asset; leave the first reference asset untouched."""
from pathlib import Path
import json
import sys
import unreal

folder=Path(__file__).parent
sys.path.insert(0,str(folder))
from thermal_material_rules import validated_rules
config=Path(unreal.Paths.project_dir())/'Config/WISEYE/thermal_material_classes.json'
rules=validated_rules(json.loads(config.read_text(encoding='utf8')))
day=[r['day_signal'] for r in rules]+[0,0]
night=[r['night_signal'] for r in rules]+[0,0]
vectors=dict(ClassDay1=day[:4],ClassDay2=day[4:],ClassNight1=night[:4],ClassNight2=night[4:])
vectors.update({f'MotorSpot{i}':(0,0,.001,0) for i in range(4)})
generator=folder/'configure_infrared_reference.py'
extras=dict(Classified=0,DayWeight=1,TargetDepth=0,TargetAvata=0,MotorWarmth=0)
extras.update(globals().get('WISEYE_CLASS_EXTRA_SCALARS',{}))
exec(compile(generator.read_text(encoding='utf8'),str(generator),'exec'),dict(
    __file__=str(generator),__name__='__main__',WISEYE_IR_ASSET=globals().get('WISEYE_CLASS_ASSET','M_IR_Classified'),
    WISEYE_IR_EXTRA_SCALARS=extras,
    WISEYE_IR_EXTRA_TEXTURES=globals().get('WISEYE_CLASS_EXTRA_TEXTURES',{}),
    WISEYE_IR_EXTRA_VECTORS=vectors,WISEYE_IR_STENCIL_MIN=32,
    WISEYE_IR_WORLD_POSITION=globals().get('WISEYE_CLASS_WORLD_POSITION',False),
    WISEYE_IR_CODE_PREFIX=globals().get('WISEYE_CLASS_PREFIX','')+(folder/'infrared_classified.hlsl').read_text(encoding='utf8')+'\n'))
unreal.log('WISEYE_IR_CLASSIFIED_SAVED')

"""Read-only audit of the duplicated city map before placing WISEYE equipment."""
import unreal,json
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[2]
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
current=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if not current or current.get_path_name().split('.')[0]!='/Game/WISEYE/Scenes/city/CitySample':
    assert levels.load_level('/Game/WISEYE/Scenes/city/CitySample')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
descs=unreal.WorldPartitionBlueprintLibrary.get_actor_descs()
def v(value):return [value.x,value.y,value.z]
records=[]
for d in descs:
 label=str(d.label);cls=d.native_class.get_name();path=str(d.class_)
 if any(x in (label+' '+cls+' '+path).lower() for x in ['playerstart','spawner','road','ground','traffic']):
  records.append(dict(label=label,cls=cls,path=path,guid=str(d.guid),actor_path=str(d.actor_path),bounds=[v(d.bounds.min),v(d.bounds.max)]))
report=dict(map=world.get_path_name(),descriptors=len(descs),classes=Counter(d.native_class.get_name() for d in descs),candidates=records,loaded=[dict(label=a.get_actor_label(),cls=a.get_class().get_name(),position=v(a.get_actor_location())) for a in actors])
(ROOT/'logs/city_map_inspect.json').write_text(json.dumps(report,indent=2),encoding='utf8')
unreal.log('WISEYE CITY INSPECT COMPLETE')

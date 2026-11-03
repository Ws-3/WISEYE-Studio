"""Read-only inspection of the WISEYE Big City copy; never the licensed source."""
import collections
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert levels.load_level('/Game/WISEYE/Scenes/city_large/BigCity')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
descs = unreal.WorldPartitionBlueprintLibrary.get_actor_descs()
def vec(v): return [v.x, v.y, v.z]
def record(d):
    return dict(label=str(d.label), cls=d.native_class.get_name(), path=str(d.class_),
                guid=str(d.guid), bounds=[vec(d.bounds.min),vec(d.bounds.max)])
candidates = [d for d in descs if any(w in (str(d.label)+' '+str(d.native_class)).lower()
                                     for w in ('playerstart','spawner','nightmode'))]
starts=[d for d in candidates if 'playerstart' in (str(d.label)+' '+str(d.native_class)).lower()]
unreal.WorldPartitionBlueprintLibrary.load_actors([d.guid for d in starts])
settings=world.get_world_settings()
wp=settings.get_editor_property('world_partition')
report=dict(map=world.get_path_name(),descriptors=len(descs),
            classes=dict(collections.Counter(d.native_class.get_name() for d in descs)),
            candidates=[record(d) for d in candidates], partition=str(wp),
            loaded=[dict(label=a.get_actor_label(),cls=a.get_class().get_name(),position=vec(a.get_actor_location()))
                    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()])
for field,native in (('enable_streaming','bEnableStreaming'),('runtime_hash','RuntimeHash')):
    try: report[field]=str(wp.get_editor_property(native))
    except Exception as e: report[field]=str(e)
out=root/'Saved/WISEYE/big_city'
out.mkdir(parents=True,exist_ok=True)
(out/'inspect.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('WISEYE_BIG_CITY_INSPECT_COMPLETE '+str(len(descs)))

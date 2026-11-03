"""Read-only visible/physics surface probes for the Big City pilot district."""
import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert levels.load_level('/Game/WISEYE/Scenes/city_large/BigCity')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
box=unreal.Box(min=unreal.Vector(-76000,-45000,-1000),max=unreal.Vector(-68000,-36000,12000))
descs=unreal.WorldPartitionBlueprintLibrary.get_intersecting_actor_descs(box)
def overlap(d):
    b=d.bounds
    return all(getattr(b.min,k)<=getattr(box.max,k) and getattr(b.max,k)>=getattr(box.min,k) for k in ('x','y','z'))
near=[d for d in descs if overlap(d) and not d.actor_is_editor_only and 'hlod' not in str(d.native_class).lower()]
unreal.WorldPartitionBlueprintLibrary.load_actors([d.guid for d in near])
rig=json.loads((root/'Config/WISEYE/standard_rig.json').read_text(encoding='utf-8'))
labels={r['label'] for r in rig['actors']}
ignore=[a for a in actors.get_all_level_actors() if a.get_actor_label() in labels or a.get_actor_label().startswith('WISEYE_') or '_visual_' in a.get_actor_label()]
def vec(v):return [v.x,v.y,v.z]
def hit_record(hit):
    d=hit.to_dict()
    return dict(location=vec(d['location']),normal=vec(d['impact_normal']),distance=d['distance'])
rows=[]
for name,x,y in [('old_cloud',-73372.265625,-38796.578125),('old_drone',-72172.265625,-38796.578125),
                 ('street_cloud',-72172.265625,-39996.578125),('street_drone',-70972.265625,-39996.578125),
                 ('street2_cloud',-71172.265625,-40796.578125),('street2_drone',-69972.265625,-40796.578125)]:
    row=dict(name=name,xy_cm=[x,y],hits={})
    for complex_trace in (False,True):
        result=unreal.SystemLibrary.line_trace_multi_for_objects(world,unreal.Vector(x,y,100000),unreal.Vector(x,y,-100000),
            [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1,unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2],complex_trace,ignore,unreal.DrawDebugTrace.NONE,True)
        row['hits'][str(complex_trace)]=[hit_record(h) for h in (result or [])][:12]
    rows.append(row)
out=root/'Saved/WISEYE/big_city/surfaces.json'
out.write_text(json.dumps(dict(descriptors_returned=len(descs),loaded_descriptors=len(near),probe_start_z_cm=100000,probes=rows),indent=2),encoding='utf-8')
unreal.log('WISEYE_BIG_CITY_SURFACE_AUDIT_COMPLETE')

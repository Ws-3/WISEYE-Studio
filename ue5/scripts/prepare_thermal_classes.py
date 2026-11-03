"""Tag only WISEYE's city copy, in bounded WP batches. Opt-in, no geometry edits.

WISEYE_THERMAL_TAG_APPLY=1 saves tags; otherwise audits without modifying assets.
Reports include unknown/conflicting materials. External Actor packages are saved
before unload. Never targets /Game/Map/Small_City_LVL or changes visible materials.
"""
import collections
import json
import os
from pathlib import Path
import sys
import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thermal_material_rules import classify,validated_rules

root = Path(unreal.Paths.project_dir()).resolve()
config = root / 'Config/WISEYE'
rules = validated_rules(json.loads((config / 'thermal_material_classes.json').read_text(encoding='utf8')))
scene_id = os.environ.get('WISEYE_THERMAL_SCENE', 'city')
assert scene_id in ('city', 'city_large'), 'Only WISEYE city copies may be tagged'
scene = json.loads((config / f'Scenes/{scene_id}.json').read_text(encoding='utf8'))
assert scene['map'] == {'city':'/Game/WISEYE/Scenes/city/CitySample', 'city_large':'/Game/WISEYE/Scenes/city_large/BigCity'}[scene_id]
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert not editor.get_game_world(), 'Stop game before preparing thermal labels'
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert levels.load_level(scene['map'])
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
fleet = json.loads((config / f'Fleets/{scene_id}.json').read_text(encoding='utf8'))
descs = {}
radius = 12000
for device in fleet['devices']:
    x,y,z = device['position_cm']
    box = unreal.Box(min=unreal.Vector(x-radius,y-radius,-3000),max=unreal.Vector(x+radius,y+radius,20000))
    for desc in unreal.WorldPartitionBlueprintLibrary.get_intersecting_actor_descs(box):
        if not desc.actor_is_editor_only and 'hlod' not in str(desc.native_class).lower():
            descs[str(desc.guid)] = desc
apply = os.environ.get('WISEYE_THERMAL_TAG_APPLY') == '1'
counts = collections.Counter(); reasons = collections.Counter(); unknown = collections.Counter(); seen = set(); changed = []
items = list(descs.values())
for offset in range(0,len(items),128):
    batch = items[offset:offset+128]
    packages = set()
    unreal.WorldPartitionBlueprintLibrary.load_actors([d.guid for d in batch])
    for actor in actors.get_all_level_actors():
        if actor.get_path_name() in seen:
            continue
        seen.add(actor.get_path_name())
        for mesh in actor.get_components_by_class(unreal.StaticMeshComponent):
            asset = mesh.static_mesh
            if not asset or asset.get_path_name().startswith(('/Game/WISEYE/','/Game/Mesh_ncl_')):
                continue
            # Respect other users of CustomDepth. Idempotently accept our own tags.
            tagged = 'WISEYE_ThermalClass_v1' in [str(t) for t in mesh.component_tags]
            if (mesh.get_editor_property('render_custom_depth') or mesh.get_editor_property('custom_depth_stencil_value')!=0) and not tagged:
                reasons['reserved_custom_depth'] += 1;continue
            materials = [str(m.get_path_name()) if m else 'unknown' for m in mesh.get_materials()]
            ident,reason = classify(asset.get_path_name(),materials,rules)
            counts[str(ident)] += 1;reasons[reason] += 1
            if not ident:
                unknown[asset.get_path_name()+' | '+', '.join(materials)] += 1
                if apply and tagged:
                    # A later rule edit must not silently retain a stale category.
                    actor.modify();mesh.modify()
                    mesh.set_editor_property('render_custom_depth',False)
                    mesh.set_editor_property('custom_depth_stencil_value',0)
                    mesh.set_editor_property('component_tags',[t for t in mesh.component_tags if str(t)!='WISEYE_ThermalClass_v1'])
                    reasons['stale_label_reset'] += 1
                    packages.add(actor.get_package())
                continue
            if apply:
                actor.modify();mesh.modify()
                mesh.set_editor_property('render_custom_depth',True)
                mesh.set_editor_property('custom_depth_stencil_value',ident)
                tags=list(mesh.component_tags)
                if 'WISEYE_ThermalClass_v1' not in [str(t) for t in tags]:
                    tags.append('WISEYE_ThermalClass_v1');mesh.set_editor_property('component_tags',tags)
                changed.append(mesh.get_path_name())
                packages.add(actor.get_package())
    if apply:
        # Restrict writes to our external Actor packages, never every dirty asset.
        assert all(p.get_name().startswith(f'/Game/__ExternalActors__/WISEYE/Scenes/{scene_id}/') or p.get_name()==scene['map'] for p in packages)
        if packages:assert unreal.EditorLoadingAndSavingUtils.save_packages(list(packages),True)
    unreal.WorldPartitionBlueprintLibrary.unload_actors([d.guid for d in batch])
    unreal.log('WISEYE_THERMAL_TAG_PROGRESS '+str(min(offset+128,len(items)))+'/'+str(len(items)))
report=dict(version=1,map=scene['map'],applied=apply,radius_cm=radius,descriptors=len(items),components_by_class=dict(counts),reasons=dict(reasons),changed_components=len(changed),unknown_examples=unknown.most_common(30),rules=rules,scope='120m around initial devices, component-level filename heuristics; mixed/unknown skipped; not per-triangle, temperature or emissivity calibration')
output=root/'Saved/WISEYE/thermal_classes';output.mkdir(parents=True,exist_ok=True)
(output/(scene_id+'.json' if apply else scene_id+'_audit.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
unreal.log('WISEYE_THERMAL_TAG_COMPLETE '+json.dumps({k:v for k,v in report.items() if k not in ('unknown_examples','rules')}))

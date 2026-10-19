"""Repair generated standard_v1 rigs; preserve independent device root placements.

Open the generated scene, stop Play, then call repair_current_scene().
Never applies to the original manually assembled WISEYE-test level.
"""
import json
import unreal
from scene_tools import ACTORS, EDITOR, CONFIG, no_play, restore_local_assembly, group_equipment


def repair_current_scene():
    no_play()
    world = EDITOR.get_editor_world()
    path = world.get_path_name().split('.')[0]
    assert path.startswith('/Game/WISEYE/Scenes/'), '仅修复生成的场景，不修改原始地图'
    data = json.loads((CONFIG/'standard_rig.json').read_text(encoding='utf-8'))
    by_label = {a.get_actor_label(): a for a in ACTORS.get_all_level_actors()}
    # Validate before changing anything, including all expected visual children.
    for record in data['actors']:
        assert record['label'] in by_label, '缺少设备节点：' + record['label']
        for index, mesh in enumerate(record['meshes']):
            label = record['label']+'_visual_'+str(index)
            assert label in by_label, '缺少设备网格：' + label
            component = by_label[label].get_component_by_class(unreal.StaticMeshComponent)
            assert component.static_mesh.get_path_name() == mesh['mesh'], '网格不匹配：' + label
    actors = {r['id']: by_label[r['label']] for r in data['actors']}
    demo = actors[data['demo']]
    config = CONFIG/'Scenes'/f'{demo.scene_id}.json'
    scene = json.loads(config.read_text(encoding='utf-8'))
    assert scene['map'] == path
    restore_local_assembly(data, actors)
    group_equipment(demo)
    # Keep the user's current assembly position when Play applies the scene config.
    p = demo.get_actor_location()
    scene['gimbal_location_cm'] = [p.x, p.y, p.z]
    scene['assembly_revision'] = 2
    assert unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    config.write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding='utf-8')
    return demo

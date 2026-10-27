"""Run inside UE editor. Export calibrated rig, prepare maps without reimporting meshes."""
import json
from pathlib import Path
import unreal

PROJECT = Path(unreal.Paths.project_dir()).resolve()
CONFIG = PROJECT / 'Config/WISEYE'
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EDITOR = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def vector(v):
    return [v.x, v.y, v.z]


def transform(t):
    r = t.rotation.rotator()
    return dict(location=vector(t.translation), rotation=[r.pitch, r.yaw, r.roll], scale=vector(t.scale3d))


def ue_transform(t, offset=None):
    p = t['location']
    if offset:
        p = [a+b for a, b in zip(p, offset)]
    pitch, yaw, roll = t['rotation']
    # Python Rotator positional arguments are (roll, pitch, yaw), unlike C++.
    return unreal.Transform(location=unreal.Vector(*p), rotation=unreal.Rotator(pitch=pitch, yaw=yaw, roll=roll), scale=unreal.Vector(*t['scale']))


def source_parent_frame(record, data):
    records = {r['id']: r for r in data['actors']}
    parent = records[record['parent']]
    frame = ue_transform(parent['transform'])
    if parent['id'] == data['demo']:
        chain = {'YawPivot': ['YawPivot'], 'PitchPivot': ['YawPivot', 'PitchPivot'],
                 'EO_Camera': ['YawPivot', 'PitchPivot', 'EO_Camera']}
        for name in chain.get(record['parent_component'], []):
            frame = unreal.MathLibrary.compose_transforms(ue_transform(data['components'][name]), frame)
    return frame


def restore_local_assembly(data, actors):
    """Preserve each equipment root pose; restore all calibrated child offsets."""
    keep = unreal.AttachmentRule.KEEP_WORLD
    demo = actors[data['demo']]
    for c in (demo.yaw_pivot, demo.pitch_pivot, demo.camera, demo.capture, demo.infrared_capture):
        c.modify()
        c.set_relative_transform(ue_transform(data['components'][c.get_name()]), False, True)
    for record in data['actors']:
        actor = actors[record['id']]
        actor.modify()
        actor.root_component.modify()
        actor.tags = list(set(actor.tags) | {unreal.Name('WISEYE_Rig_standard_v1'), unreal.Name('WISEYE_Node_'+record['id'])})
        if record['parent'] is not None:
            parent = actors[record['parent']]
            component = next((c for c in parent.get_components_by_class(unreal.SceneComponent)
                              if c.get_name() == record['parent_component']), parent.root_component)
            actor.attach_to_component(component, '', keep, keep, keep, False)
            relative = unreal.MathLibrary.make_relative_transform(ue_transform(record['transform']), source_parent_frame(record, data))
            actor.root_component.set_relative_transform(relative, False, True)
    by_label = {a.get_actor_label(): a for a in ACTORS.get_all_level_actors()}
    for record in data['actors']:
        actor = actors[record['id']]
        for index, mesh in enumerate(record['meshes']):
            part = by_label[record['label']+'_visual_'+str(index)]
            part.modify()
            part.root_component.modify()
            part.attach_to_actor(actor, '', keep, keep, keep, False)
            relative = unreal.MathLibrary.make_relative_transform(ue_transform(mesh['transform']), ue_transform(record['transform']))
            part.root_component.set_relative_transform(relative, False, True)


def group_equipment(demo):
    """Locked editor groups make selection/drag operate on the whole device."""
    utils = unreal.ActorGroupingUtils.get()
    unreal.ActorGroupingUtils.set_grouping_active(True)
    mount = demo
    while mount.get_attach_parent_actor():
        mount = mount.get_attach_parent_actor()
    for root, label in ((mount, 'WISEYE_Gimbal_Assembly'), (demo.drone, 'WISEYE_Drone_Assembly')):
        group, pending = [], [root]
        while pending:
            actor = pending.pop()
            group.append(actor)
            pending.extend(actor.get_attached_actors())
        created = utils.group_actors(group)
        if not created:
            raise RuntimeError('无法建立设备整体选择组：' + label)
        created.modify()
        created.set_actor_label(label)
        ACTORS.set_selected_level_actors([root])
        utils.lock_selected_groups()
    ACTORS.clear_actor_selection_set()


def no_play():
    if EDITOR.get_game_world():
        raise RuntimeError('请先停止播放')


def export_rig():
    """Read-only extraction of the known, calibrated original level."""
    no_play()
    assert EDITOR.get_editor_world().get_name() == 'WISEYE-test', '请打开原始 WISEYE-test 地图'
    demo = next(a for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.WiseEyeDemo))
    roots = [demo, demo.drone]
    if demo.overview:
        roots.append(demo.overview)
    for actor in list(roots):
        while actor.get_attach_parent_actor():
            actor = actor.get_attach_parent_actor()
        roots.append(actor)
    group = []
    def visit(actor):
        if actor in group:
            return
        group.append(actor)
        for child in actor.get_attached_actors():
            visit(child)
    for actor in roots:
        visit(actor)
    ids = {a: str(i) for i, a in enumerate(group)}
    records = []
    for actor in group:
        root = actor.root_component
        parent = root.get_attach_parent() if root else None
        meshes = []
        for c in actor.get_components_by_class(unreal.StaticMeshComponent):
            if c.static_mesh and not c.static_mesh.get_path_name().startswith('/Engine/EditorMeshes/'):
                meshes.append(dict(mesh=c.static_mesh.get_path_name(), transform=transform(c.get_world_transform()),
                                   materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]))
        records.append(dict(id=ids[actor], label=actor.get_actor_label(), transform=transform(actor.get_actor_transform()),
                            parent=ids.get(parent.get_owner()) if parent else None,
                            parent_component=parent.get_name() if parent else None,
                            kind='demo' if actor == demo else ('camera' if isinstance(actor, unreal.CameraActor) else 'root'),
                            direction=actor.direction if isinstance(actor, unreal.WiseEyeRotor) else 1,
                            tags=[str(t) for t in actor.tags], meshes=meshes))
    properties = ('flight_radius', 'period', 'vertical_amplitude', 'field_of_view', 'yaw_rate', 'pitch_rate',
                  'min_pitch', 'max_pitch', 'manual_speed', 'manual_yaw_rate', 'minimum_altitude', 'maximum_altitude',
                  'model_heading_offset', 'rotor_rpm')
    data = dict(version=1, actors=records, demo=ids[demo], drone=ids[demo.drone], overview=ids.get(demo.overview),
                rotors=[ids[a] for a in demo.rotors], origin=vector(demo.get_actor_location()),
                flight_origin=vector(demo.flight_origin), target_offset=vector(demo.target_offset),
                properties={key: demo.get_editor_property(key) for key in properties},
                components={c.get_name(): transform(c.get_relative_transform()) for c in (demo.yaw_pivot, demo.pitch_pivot, demo.camera, demo.capture, demo.infrared_capture)},
                # UE does not expose its weak HiddenComponents array to Python.
                # The calibrated original hides the optical housing and pitch body.
                hidden=list({ids[a] for a in demo.capture.hidden_actors if a in ids} |
                            {ids[a] for a in group if a.get_actor_label() in ('camera', 'ptz')}))
    assert len(data['rotors']) == 4 and sum(len(r['meshes']) for r in records) > 10, '设备未完整加载'
    (CONFIG / 'standard_rig.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log(f'WISEYE exported rig: {len(records)} actors')
    return data


def install_rig(scene):
    no_play()
    assert not any(isinstance(a, unreal.WiseEyeDemo) for a in ACTORS.get_all_level_actors()), '地图已经包含设备；请勿重复安装'
    data = json.loads((CONFIG / 'standard_rig.json').read_text(encoding='utf-8'))
    offset = [a-b for a, b in zip(scene['gimbal_location_cm'], data['origin'])]
    spawned = {}
    mesh_actors = []
    keep = unreal.AttachmentRule.KEEP_WORLD
    for record in data['actors']:
        cls = {'demo': unreal.WiseEyeDemo, 'camera': unreal.CameraActor, 'root': unreal.WiseEyeRotor}[record['kind']]
        actor = ACTORS.spawn_actor_from_class(cls, unreal.Vector())
        actor.modify()
        # Simulation devices must stay loaded outside the observer's WP cells.
        actor.set_editor_property('is_spatially_loaded', False)
        actor.set_actor_label(record['label'])
        actor.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        actor.set_actor_transform(ue_transform(record['transform'], offset), False, True)
        actor.tags = [unreal.Name(t) for t in record['tags']]
        if record['kind'] == 'root':
            actor.direction = record['direction']
        spawned[record['id']] = actor
    demo = spawned[data['demo']]
    for c in (demo.yaw_pivot, demo.pitch_pivot, demo.camera, demo.capture, demo.infrared_capture):
        c.modify()
        c.set_relative_transform(ue_transform(data['components'][c.get_name()]), False, True)
    for record in data['actors']:
        actor = spawned[record['id']]
        if record['parent'] is not None:
            parent = spawned[record['parent']]
            component = next((c for c in parent.get_components_by_class(unreal.SceneComponent)
                              if c.get_name() == record['parent_component']), parent.root_component)
            actor.attach_to_component(component, '', keep, keep, keep, False)
        for index, mesh in enumerate(record['meshes']):
            asset = unreal.load_asset(mesh['mesh'])
            if not asset:
                raise RuntimeError('缺少设备资源：' + mesh['mesh'])
            part = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector())
            part.modify()
            part.set_editor_property('is_spatially_loaded', False)
            part.set_actor_label(record['label'] + '_visual_' + str(index))
            part.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
            part.static_mesh_component.set_static_mesh(asset)
            for i, path in enumerate(mesh['materials']):
                if path:
                    material = unreal.load_asset(path)
                    if not material:
                        raise RuntimeError('缺少材质：' + path)
                    part.static_mesh_component.set_material(i, material)
            part.tags = actor.tags
            part.set_actor_transform(ue_transform(mesh['transform'], offset), False, True)
            part.attach_to_actor(actor, '', keep, keep, keep, False)
            mesh_actors.append((record['id'], part))
    for key, value in data['properties'].items():
        demo.set_editor_property(key, value)
    restore_local_assembly(data, spawned)
    demo.drone = spawned[data['drone']]
    demo.overview = spawned.get(data['overview'])
    demo.rotors = [spawned[key] for key in data['rotors']]
    demo.target_offset = unreal.Vector(*data['target_offset'])
    demo.flight_origin = unreal.Vector(*scene['flight_origin_cm'])
    demo.flight_radius = scene['flight_radius_cm']
    demo.period = scene['period_s']
    demo.vertical_amplitude = scene['vertical_amplitude_cm']
    demo.field_of_view = scene['fov_deg']
    demo.scene_id = scene['id']
    hidden = [spawned[key] for key in data['hidden']]
    hidden += [actor for key, actor in mesh_actors if key in data['hidden']]
    for actor in hidden:
        demo.capture.hide_actor_components(actor)
        demo.infrared_capture.hide_actor_components(actor)
    demo.drone.set_actor_location(unreal.Vector(*scene['flight_origin_cm']), False, True)
    if demo.overview:
        demo.overview.set_actor_location(unreal.Vector(*scene['overview_location_cm']), False, True)
        pitch, yaw, roll = scene['overview_rotation_deg']
        demo.overview.set_actor_rotation(unreal.Rotator(pitch=pitch, yaw=yaw, roll=roll), True)
    world = EDITOR.get_editor_world()
    world.get_world_settings().modify()
    world.get_world_settings().set_editor_property('default_game_mode', unreal.WiseEyeGameMode)
    group_equipment(demo)
    return demo


def prepare_scene(config_path, source_map=None):
    """New destination only. Source maps are never modified. Run after saving work."""
    no_play()
    scene = json.loads(Path(config_path).read_text(encoding='utf-8-sig'))
    if scene.get('requires_external_asset') and not source_map:
        raise RuntimeError('请先获取真实城市资产并迁移地图，再设置 source_map 或使用 install_current_scene；不会生成替代街区。')
    destination = scene['map']
    if unreal.EditorAssetLibrary.does_asset_exist(destination):
        raise RuntimeError('目标地图已存在，不会覆盖：' + destination)
    if source_map:
        source = unreal.load_asset(source_map)
        if source.get_world_settings().get_editor_property('world_partition'):
            raise RuntimeError('World Partition 地图请按 docs/SCENES.md 在 UE 中制作副本，再运行 install_current_scene')
        if not unreal.EditorAssetLibrary.duplicate_asset(source_map, destination):
            raise RuntimeError('无法复制地图；World Partition 地图请使用 UE 的地图复制工具，保留外部 Actor 后在副本调用 install_rig')
        assert LEVELS.load_level(destination)
    else:
        assert LEVELS.new_level(destination)
        floor = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, -50))
        floor.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
        floor.set_actor_scale3d(unreal.Vector(200, 200, 1))
        floor.set_actor_label('WISEYE_TestGround')
        sun = ACTORS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 2000), unreal.Rotator(pitch=-45, yaw=-30, roll=0))
        sun.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        ACTORS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector())
        sky = ACTORS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000))
        sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        sky.light_component.set_editor_property('real_time_capture', True)
    install_rig(scene)
    assert unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    scene['prepared'] = True
    scene['assembly_revision'] = 2
    Path(config_path).write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('WISEYE scene prepared: ' + destination)


def install_current_scene(config_path):
    """Adapt a manually duplicated World Partition or ordinary map in the editor."""
    no_play()
    scene = json.loads(Path(config_path).read_text(encoding='utf-8-sig'))
    actual = EDITOR.get_editor_world().get_path_name().split('.')[0]
    assert actual == scene['map'], '当前地图必须与配置入口完全一致，禁止误改原地图'
    install_rig(scene)
    assert unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    scene['prepared'] = True
    scene['assembly_revision'] = 2
    Path(config_path).write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding='utf-8')

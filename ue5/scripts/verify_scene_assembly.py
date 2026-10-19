"""Check local geometry, whole-device moves and gimbal articulation without saving test poses."""
import json
import math
import unreal
from scene_tools import ACTORS, CONFIG, no_play, source_parent_frame, ue_transform


def distance(a,b):
    return (a-b).length()


def family(root):
    result, pending = [], [root]
    while pending:
        actor=pending.pop()
        result.append(actor)
        pending.extend(actor.get_attached_actors())
    return result


def verify():
    no_play()
    data=json.loads((CONFIG/'standard_rig.json').read_text(encoding='utf-8'))
    by_label={a.get_actor_label():a for a in ACTORS.get_all_level_actors()}
    actors={r['id']:by_label[r['label']] for r in data['actors']}
    demo=actors[data['demo']]
    checks=[]
    maximum=0.0
    for record in data['actors']:
        actor=actors[record['id']]
        if record['parent'] is not None:
            expected=unreal.MathLibrary.make_relative_transform(ue_transform(record['transform']),source_parent_frame(record,data))
            actual=actor.root_component.get_relative_transform()
            error=distance(actual.translation,expected.translation)
            assert error<.001, (record['label'],error)
            # Compare the orientation by its three unit basis points, not Euler aliases.
            for axis in (unreal.Vector(1,0,0),unreal.Vector(0,1,0),unreal.Vector(0,0,1)):
                error=max(error,distance(unreal.MathLibrary.transform_location(actual,axis),unreal.MathLibrary.transform_location(expected,axis)))
            assert error<.001, (record['label'],'rotation/scale mismatch',error)
            maximum=max(maximum,error)
    checks.append('all calibrated node relative positions, rotations and scales')
    mount=demo
    while mount.get_attach_parent_actor(): mount=mount.get_attach_parent_actor()
    for root in (mount,demo.drone):
        group=family(root)
        saved=root.get_actor_transform()
        original={a:a.get_actor_location() for a in group}
        delta=unreal.Vector(137,-263,89)
        try:
            root.set_actor_location(saved.translation+delta,False,True)
            assert all(distance(a.get_actor_location(),p+delta)<.001 for a,p in original.items()), 'whole-device translation separated parts'
            root.set_actor_rotation(unreal.Rotator(pitch=12,yaw=47,roll=5),True)
            for actor in group:
                p=unreal.MathLibrary.inverse_transform_location(saved,original[actor])
                expected=unreal.MathLibrary.transform_location(root.get_actor_transform(),p)
                assert distance(actor.get_actor_location(),expected)<.001, actor.get_actor_label()
        finally:
            root.set_actor_transform(saved,False,True)
    checks.append('whole gimbal and drone translate and rotate as assemblies')
    yaw,pitch=demo.yaw_pivot.get_relative_transform(),demo.pitch_pivot.get_relative_transform()
    bottom=by_label['bottom_visual_0']
    bottom2=by_label['bottom2_visual_0']
    before_bottom=bottom.get_actor_transform()
    try:
        demo.yaw_pivot.set_relative_rotation(unreal.Rotator(yaw=35),False,True)
        before_bottom2=bottom2.get_actor_transform()
        camera=by_label['camera_visual_0']
        ptz=by_label['ptz_visual_0']
        local_camera=unreal.MathLibrary.make_relative_transform(camera.get_actor_transform(),demo.pitch_pivot.get_world_transform())
        local_ptz=unreal.MathLibrary.make_relative_transform(ptz.get_actor_transform(),demo.pitch_pivot.get_world_transform())
        demo.pitch_pivot.set_relative_rotation(unreal.Rotator(pitch=40),False,True)
        assert distance(bottom.get_actor_location(),before_bottom.translation)<.001
        assert distance(bottom2.get_actor_location(),before_bottom2.translation)<.001
        for actor,local in ((camera,local_camera),(ptz,local_ptz)):
            expected=unreal.MathLibrary.compose_transforms(local,demo.pitch_pivot.get_world_transform())
            assert distance(actor.get_actor_location(),expected.translation)<.001
    finally:
        demo.yaw_pivot.set_relative_transform(yaw,False,True)
        demo.pitch_pivot.set_relative_transform(pitch,False,True)
    checks.append('bottom fixed; bottom2 yaw only; camera and ptz share pitch')
    groups=[a for a in ACTORS.get_all_level_actors() if isinstance(a,unreal.GroupActor)]
    assert len([g for g in groups if g.get_actor_label() in ('WISEYE_Gimbal_Assembly','WISEYE_Drone_Assembly')])==2
    unreal.ActorGroupingUtils.set_grouping_active(True)
    for root in (mount,demo.drone):
        members=family(root)
        ACTORS.set_selected_level_actors([members[-1]])
        selected=ACTORS.get_selected_level_actors()
        assert all(actor in selected for actor in members), 'selecting a part must select its whole equipment group'
    ACTORS.clear_actor_selection_set()
    checks.append('selecting one part selects the full equipment group')
    return dict(passed=True,checks=checks,max_local_transform_error_cm=maximum)

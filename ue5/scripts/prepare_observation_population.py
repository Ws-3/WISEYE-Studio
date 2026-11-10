"""Prepare native traffic/crowd infrastructure in WISEYE copies only.

Does not alter the original CitySample maps or device placements. Actor packages
are explicitly saved; merely saving a World Partition map does not save actors.
"""
import json
from pathlib import Path
import unreal

report={};presets={}
GENERATOR_PROPERTIES={
    'MassTrafficVehicleSpawnDataGenerator':['vehicle_type_spacings','default_space','random_seed','min_gap_between_spaces','max_gap_between_spaces','obstacle_exclusion_radius'],
    'MassTrafficParkedVehicleSpawnDataGenerator':['entity_type_to_parking_space_type','parking_spaces','use_all_parking_spaces','obstacle_exclusion_radius'],
    'MassEntityZoneGraphSpawnPointsGenerator':['tag_filter','min_gap','max_gap'],
    'MassTrafficIntersectionSpawnDataGenerator':['intersection_entity_config_index','traffic_light_types_data','traffic_light_instance_data','traffic_light_search_distance','intersection_side_to_crosswalk_search_distance'],
}
def snapshot(value):
    if isinstance(value,(list,unreal.Array)):return [snapshot(x) for x in value]
    if isinstance(value,(dict,unreal.Map)):return {k:snapshot(v) for k,v in value.items()}
    if isinstance(value,unreal.StructBase):return value.copy()
    return value
for scene,map_name in [('city','CitySample'),('city_large','BigCity')]:
    path=f'/Game/WISEYE/Scenes/{scene}/{map_name}'
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(path)
    descs=unreal.WorldPartitionBlueprintLibrary.get_actor_descs()
    wanted=[d for d in descs if any(word in (str(d.label)+' '+str(d.native_class)+' '+str(d.class_)).lower() for word in ('mass','zonegraph','trafficcoordinator'))]
    unreal.WorldPartitionBlueprintLibrary.load_actors([d.guid for d in wanted])
    actor_sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    existing=actor_sub.get_all_level_actors()
    # The old large-city installer removed spawners. Restore the sample presets,
    # bounded by the runtime controller, rather than regenerating road geometry.
    for preset in ['/Game/AI/Traffic/Spawners/BP_MassTrafficIntersectionSpawner','/Game/AI/Traffic/Spawners/BP_MassTrafficVehicleSpawner','/Game/AI/Traffic/Spawners/BP_MassTrafficParkedVehicleSpawner','/Game/AI/AgentConfig/BP_MassCrowdSpawner']:
        name=preset.split('/')[-1]+'_C'
        if not any(a.get_class().get_name()==name for a in existing):
            actor=actor_sub.spawn_actor_from_class(unreal.EditorAssetLibrary.load_blueprint_class(preset),unreal.Vector())
            assert actor;actor.set_actor_label('WISEYE_'+name);existing.append(actor)
    packages=set();items=[]
    for actor in existing:
        cls=actor.get_class().get_name()
        if not any(k in cls.lower() for k in ('mass','zonegraph','trafficcoordinator')):continue
        item={'actor':actor.get_path_name(),'class':cls,'package':actor.get_package().get_name(),'before':{}}
        actor.modify()
        if isinstance(actor,unreal.MassSpawner) and not actor.get_editor_property('spawn_data_generators'):
            # Spawned Blueprint instances do not contain the placed sample's
            # generator overrides. Recreate instanced UObjects under this actor;
            # references to the other map's generator would not survive loading.
            assert cls in presets,'Missing prepared generator preset: '+cls
            restored=[]
            for spec in presets[cls]:
                generator=unreal.new_object(spec['class'],outer=actor)
                for prop,value in spec['properties'].items():generator.set_editor_property(prop,value)
                entry=unreal.MassSpawnDataGenerator();entry.set_editor_property('generator_instance',generator);entry.set_editor_property('proportion',spec['proportion']);restored.append(entry)
            actor.set_editor_property('spawn_data_generators',restored)
        for prop,value in [('is_spatially_loaded',False),('is_editor_only_actor',False),('data_layer_assets',[])]:
            try:item['before'][prop]=str(actor.get_editor_property(prop));actor.set_editor_property(prop,value)
            except Exception as e:item[prop+'_error']=str(e)
        if 'TrafficTrailerSpawner' in cls:
            # No articulated trucks in this first preset. Its Blueprint otherwise
            # hooks vehicle completion and loads a separate trailer fleet.
            actor.set_editor_property('is_editor_only_actor',True)
            actor.set_editor_property('auto_spawn_on_begin_play',False)
            if actor.get_editor_property('count')<=0:actor.set_editor_property('count',1000)
        if isinstance(actor,unreal.MassSpawner) and any(k in cls for k in ('CrowdSpawner','TrafficVehicleSpawner','ParkedVehicleSpawner')):
            item['before']['auto_spawn_on_begin_play']=str(actor.get_editor_property('auto_spawn_on_begin_play'))
            actor.set_editor_property('auto_spawn_on_begin_play',False)
            # One sedan preset avoids loading every bus/truck/destruction rig just
            # to start a bounded aerial-target population. Density controls count.
            if 'VehicleSpawner' in cls:
                types=actor.get_editor_property('entity_types')
                selected=[t for t in types if 'vehCar_vehicle03_' in str(t.get_editor_property('entity_config'))]
                assert selected,cls
                actor.set_editor_property('entity_types',selected[:1])
        if isinstance(actor,unreal.MassSpawner):
            city_name='SmallCity' if scene=='city' else 'BigCity'
            for entry in actor.get_editor_property('spawn_data_generators'):
                generator=entry.get_editor_property('generator_instance')
                if not generator:continue
                if 'ParkedVehicleSpawner' in cls:
                    generator.modify();generator.set_editor_property('parking_spaces',unreal.load_asset('/Game/AI/Traffic/ParkingSpaces/CitySample'+city_name+'ParkingSpaces'))
                    generator.set_editor_property('use_all_parking_spaces',False)
                if 'IntersectionSpawner' in cls:
                    generator.modify();generator.set_editor_property('traffic_light_instance_data',unreal.load_asset('/Game/AI/Traffic/TrafficLights/CitySample'+city_name+'TrafficLights'))
            entries=actor.get_editor_property('spawn_data_generators')
            item['generator_count']=len(entries)
            if scene=='city' and entries:
                presets[cls]=[]
                for entry in entries:
                    generator=entry.get_editor_property('generator_instance')
                    assert generator
                    names=next((props for base,props in GENERATOR_PROPERTIES.items() if isinstance(generator,getattr(unreal,base))),None)
                    if names is None:continue  # Unmanaged trailer presets are not restored.
                    presets[cls].append({'class':generator.get_class(),'proportion':entry.get_editor_property('proportion'),'properties':{p:snapshot(generator.get_editor_property(p)) for p in names}})
        packages.add(actor.get_package());items.append(item)
    assert all(p.get_name().startswith(f'/Game/__ExternalActors__/WISEYE/Scenes/{scene}/') or p.get_name()==path for p in packages)
    if packages:assert unreal.EditorLoadingAndSavingUtils.save_packages(list(packages),True)
    report[scene]=items
out=Path(unreal.Paths.project_saved_dir())/'WISEYE/observation-population-prepare.json';out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2),encoding='utf8')
unreal.log('WISEYE_OBSERVATION_POPULATION_PREPARED')

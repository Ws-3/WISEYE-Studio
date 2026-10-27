"""Temporary PIE-only optical timecode. Never save the map or create assets."""
import unreal,time,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class Probe:
 def __init__(self):
  self.origin=json.loads((ROOT/'runtime/latency_probe_config.json').read_text())['origin']
  self.world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
  assert self.world and '/WISEYE/Scenes/city/' in self.world.get_path_name()
  self.demo=unreal.GameplayStatics.get_all_actors_of_class(self.world,unreal.WiseEyeDemo)[0]
  captures=self.demo.get_components_by_class(unreal.SceneCaptureComponent2D)
  self.eo=next(c for c in captures if c.get_name()=='EO_Capture');self.ir=next(c for c in captures if c.get_name()=='IR_Capture');self.obs=next(c for c in captures if c not in (self.eo,self.ir))
  base=unreal.load_asset('/Engine/BasicShapes/BasicShapeMaterial');self.cube=unreal.load_asset('/Engine/BasicShapes/Cube')
  self.white=unreal.MaterialLibrary.create_dynamic_material_instance(self.world,base);self.white.set_vector_parameter_value('Color',unreal.LinearColor(1,1,1,1));self.white.set_scalar_parameter_value('Roughness',1)
  self.black=unreal.MaterialLibrary.create_dynamic_material_instance(self.world,base);self.black.set_vector_parameter_value('Color',unreal.LinearColor(0,0,0,1));self.black.set_scalar_parameter_value('Roughness',1)
  self.actors=[];self.tiles=[];self.lastbits=[];self.samples=[];self.handle=None;self.lidar_events=[];self.lidar_index=None
  unreal._wise_latency_probe=self
  for source,cap in [('sensor',self.eo),('observer',self.obs)]:
   width=2*50*math.tan(math.radians(cap.get_editor_property('fov_angle')/2))*.9;step=width/34
   scale=cap.get_world_scale()
   tiles=[]
   for i in range(34):
    # Spawn helpers are reflected but have no generated Python glue in UE 5.8.
    library=unreal.get_default_object(unreal.GameplayStatics)
    a=library.call_method('BeginDeferredActorSpawnFromClass',args=(self.world,unreal.StaticMeshActor.static_class(),unreal.Transform(),unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN))
    self.actors.append(a)
    mesh=a.static_mesh_component;mesh.set_mobility(unreal.ComponentMobility.MOVABLE);mesh.set_static_mesh(self.cube);mesh.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION);mesh.set_cast_shadow(False);mesh.set_render_custom_depth(True)
    library.call_method('FinishSpawningActor',args=(a,unreal.Transform()))
    a.attach_to_component(cap,'',unreal.AttachmentRule.KEEP_RELATIVE,unreal.AttachmentRule.KEEP_RELATIVE,unreal.AttachmentRule.KEEP_RELATIVE,False)
    a.set_actor_relative_location(unreal.Vector(50/scale.x,(i-16.5)*step/scale.y,0),False,True);a.set_actor_relative_scale3d(unreal.Vector(.002/scale.x,step/100/scale.y,1.5/100/scale.z))
    a.tags=['WISEYE_TemporaryLatencyProbe']
    tiles.append(mesh)
    if source=='sensor':self.obs.hide_actor_components(a)
    else:self.eo.hide_actor_components(a);self.ir.hide_actor_components(a)
   self.tiles.append(tiles)
  self.lidar=next(c for c in self.demo.get_components_by_class(unreal.SceneComponent) if c.get_name()=='GimbalLidarMount')
  library=unreal.get_default_object(unreal.GameplayStatics)
  self.target=library.call_method('BeginDeferredActorSpawnFromClass',args=(self.world,unreal.StaticMeshActor.static_class(),unreal.Transform(),unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN))
  self.actors.append(self.target)
  mesh=self.target.static_mesh_component;mesh.set_mobility(unreal.ComponentMobility.MOVABLE);mesh.set_static_mesh(self.cube);mesh.set_cast_shadow(False)
  library.call_method('FinishSpawningActor',args=(self.target,unreal.Transform()))
  # Keep this target outside the rig: the real lidar ignores attached housing.
  self.target.set_actor_hidden_in_game(True)
  mesh.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
  ignore=unreal.CollisionResponseType.ECR_IGNORE
  block=unreal.CollisionResponseType.ECR_BLOCK
  visibility=unreal.CollisionChannel.ECC_VISIBILITY
  mesh.set_collision_response_to_all_channels(ignore);mesh.set_collision_response_to_channel(visibility,block)
  self.target.set_actor_scale3d(unreal.Vector(.05,7,2))
  self.target.tags=['WISEYE_TemporaryLatencyProbe']
  self.began=time.perf_counter()
  self.lastbits=[None]*34
  self.handle=unreal.register_slate_pre_tick_callback(self.tick)
  unreal._wise_latency_probe=self
  (ROOT/'logs/latency_probe_ready.json').write_text(json.dumps(dict(ready=True,origin=self.origin,actors=len(self.actors),clock=time.get_clock_info('perf_counter').implementation,perf=time.perf_counter())))
 def tick(self,dt):
  if not unreal.SystemLibrary.is_valid(self.demo):self.close();return
  if time.perf_counter()-self.began>180:self.close();return
  stamp=int((time.perf_counter()-self.origin)*1000)&0xFFFFFF
  crc=((stamp&255)^((stamp>>8)&255)^((stamp>>16)&255)^0xA7)
  word=stamp|(crc<<24);bits=[0,1]+[(word>>i)&1 for i in range(32)]
  for i,bit in enumerate(bits):
   if bit!=self.lastbits[i]:
    for tiles in self.tiles:
     tiles[i].set_material(0,self.white if bit else self.black);tiles[i].set_custom_depth_stencil_value(230 if bit else 24)
  self.lastbits=bits
  index=int((time.perf_counter()-self.began)/.75)%32
  self.target.set_actor_rotation(self.lidar.get_world_rotation(),True)
  self.target.set_actor_location(self.lidar.get_world_location()+self.lidar.get_forward_vector()*(250+index*25),False,True)
  if index!=self.lidar_index:
   self.lidar_events.append(dict(time_ms=(time.perf_counter()-self.origin)*1000,index=index,front_x_m=2.435+index*.25));self.lidar_index=index
  self.samples.append([time.perf_counter()-self.origin,float(self.demo.yaw_pivot.get_relative_rotation().yaw),float(self.demo.pitch_pivot.get_relative_rotation().pitch)])
 def close(self):
  if self.handle:unreal.unregister_slate_pre_tick_callback(self.handle);self.handle=None
  for a in self.actors:
   if unreal.SystemLibrary.is_valid(a):a.destroy_actor()
  (ROOT/'logs/latency_probe_ue_samples.json').write_text(json.dumps(self.samples))
  (ROOT/'logs/latency_probe_lidar_events.json').write_text(json.dumps(self.lidar_events))
  (ROOT/'logs/latency_probe_cleaned.json').write_text(json.dumps(dict(cleaned=True,actors=len(self.actors),origin=self.origin)))
  unreal._wise_latency_probe=None
if getattr(unreal,'_wise_latency_probe',None):raise RuntimeError('An optical probe is already active; clean it before starting another')
Probe()

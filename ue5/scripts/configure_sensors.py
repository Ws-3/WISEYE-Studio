"""Create and save the dual sensor assets in WISEYE-test, outside PIE.

Heat is normalized synthetic intensity, not temperature or physical radiation.
"""
import json
from pathlib import Path
import unreal

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'Stop PIE first'
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name()=='WISEYE-test'
actors={a.get_actor_label():a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
demo=actors['WISEYE_Demo']
tools=unreal.AssetToolsHelpers.get_asset_tools()
folder='/Game/WISEYE/Sensors'
mat=unreal.load_asset(folder+'/M_IR_Minimal')
if not mat:
    mat=tools.create_asset('M_IR_Minimal',folder,unreal.Material,unreal.MaterialFactoryNew())
mat.modify()
unreal.MaterialEditingLibrary.delete_all_material_expressions(mat)
mat.set_editor_property('material_domain',unreal.MaterialDomain.MD_POST_PROCESS)
mat.set_editor_property('blendable_location',unreal.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
mat.set_editor_property('blendable_output_alpha',True)

def node(cls,x,y):
    return unreal.MaterialEditingLibrary.create_material_expression(mat,cls,x,y)

custom=node(unreal.MaterialExpressionCustom,400,0)
custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
custom.set_editor_property('description','Normalized synthetic heat with visible-surface stencil masking')
names=['Stencil','CustomDepth','Depth','Normal','UV','BackgroundHeat','SkyHeat','NoiseStrength','BlackHot']
inputs=[]
for name in names:
    item=unreal.CustomInput()
    item.set_editor_property('input_name',name)
    inputs.append(item)
custom.set_editor_property('inputs',inputs)
custom.set_editor_property('code',r'''
float d=Depth.r;
float marked=step(0.5,Stencil.r);
float visible=marked*step(CustomDepth.r,d+1.0);
float sky=step(10000000.0,d);
float3 normal=Normal.rgb;
float structure=0.025*dot(normal,normalize(float3(0.3,0.4,1.0)));
float background=lerp(BackgroundHeat+structure,SkyHeat,sky);
float heat=lerp(background,saturate(Stencil.r/255.0),visible);
float2 pixel=floor(UV*float2(640.0,512.0));
float noise=frac(sin(dot(pixel,float2(12.9898,78.233)))*43758.5453)-0.5;
heat=saturate(heat+noise*NoiseStrength);
float value=lerp(heat,1.0-heat,BlackHot);
return float3(value,value,value);
''')
for i,(name,kind) in enumerate([('Stencil',unreal.SceneTextureId.PPI_CUSTOM_STENCIL),('CustomDepth',unreal.SceneTextureId.PPI_CUSTOM_DEPTH),('Depth',unreal.SceneTextureId.PPI_SCENE_DEPTH),('Normal',unreal.SceneTextureId.PPI_WORLD_NORMAL)]):
    tex=node(unreal.MaterialExpressionSceneTexture,-600,i*150)
    tex.set_editor_property('scene_texture_id',kind)
    unreal.MaterialEditingLibrary.connect_material_expressions(tex,'Color',custom,name)
uv=node(unreal.MaterialExpressionTextureCoordinate,-600,650)
unreal.MaterialEditingLibrary.connect_material_expressions(uv,'',custom,'UV')
for i,(name,value) in enumerate([('BackgroundHeat',.27),('SkyHeat',.08),('NoiseStrength',.008),('BlackHot',0)]):
    p=node(unreal.MaterialExpressionScalarParameter,-100,i*150)
    p.set_editor_property('parameter_name',name)
    p.set_editor_property('default_value',value)
    unreal.MaterialEditingLibrary.connect_material_expressions(p,'',custom,name)
unreal.MaterialEditingLibrary.connect_material_property(custom,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
opacity=node(unreal.MaterialExpressionConstant,400,250)
opacity.set_editor_property('r',1.0)
unreal.MaterialEditingLibrary.connect_material_property(opacity,'',unreal.MaterialProperty.MP_OPACITY)
unreal.MaterialEditingLibrary.recompile_material(mat)

visible=unreal.load_asset('/Game/WISEYE/RT_EO')
assert visible
infrared=unreal.load_asset(folder+'/RT_IR')
if not infrared:
    infrared=tools.create_asset('RT_IR',folder,unreal.TextureRenderTarget2D,unreal.TextureRenderTargetFactoryNew())
for target,w,h in [(visible,1920,1080),(infrared,640,512)]:
    target.modify()
    target.set_editor_property('size_x',w)
    target.set_editor_property('size_y',h)
    target.set_editor_property('render_target_format',unreal.TextureRenderTargetFormat.RTF_RGBA8)
demo.modify()
demo.set_editor_property('render_target',visible)
demo.set_editor_property('infrared_target',infrared)
demo.set_editor_property('thermal_material',mat)
demo.set_editor_property('infrared_mode',False)
demo.set_editor_property('black_hot',False)
for c,target in [(demo.capture,visible),(demo.infrared_capture,infrared)]:
    c.modify()
    c.set_editor_property('texture_target',target)
    c.set_editor_property('fov_angle',demo.field_of_view)
demo.infrared_capture.set_relative_location(unreal.Vector(),False,True)
demo.infrared_capture.set_relative_rotation(unreal.Rotator(),False,True)
for label in ['bottom','bottom2','camera','ptz']:
    actor=actors[label]
    actor.modify()
    tags=list(actor.tags)
    if 'WISEYE_ThermalPTZ' not in [str(t) for t in tags]: tags.append('WISEYE_ThermalPTZ')
    actor.set_editor_property('tags',tags)
unreal.EditorAssetLibrary.save_asset(mat.get_path_name(),only_if_is_dirty=False)
unreal.EditorAssetLibrary.save_asset(visible.get_path_name(),only_if_is_dirty=False)
unreal.EditorAssetLibrary.save_asset(infrared.get_path_name(),only_if_is_dirty=False)
assert unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
config=Path(unreal.Paths.project_dir())/'Config/WISEYE/sensors.json'
config.write_text(json.dumps({'visible':{'width':1920,'height':1080,'aspect_ratio':'16:9'},'infrared':{'width':640,'height':512,'aspect_ratio':'5:4','palettes':['white_hot','black_hot'],'model':'normalized synthetic heat, not radiometric'},'pose':'shared optical mount and horizontal FOV; different vertical FOV','heat_defaults':{'body':.65,'motors':.92,'rotors':.48,'ground':.27,'sky':.08,'noise_strength':.008},'keys':{'I':'visible/infrared','B':'white/black hot','P':'export active native-resolution PNG'}},indent=2),encoding='utf8')
unreal.log('WISEYE dual sensors configured: VIS 1920x1080, IR 640x512')

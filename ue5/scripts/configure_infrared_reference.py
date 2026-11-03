"""Build a separate reference pilot material. Original A/B assets stay intact."""
from pathlib import Path
import unreal

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'Stop PIE first'
asset_name=globals().get('WISEYE_IR_ASSET','M_IR_Reference')
path='/Game/WISEYE/Sensors/'+asset_name
material=unreal.load_asset(path)
if not material:
    material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(asset_name,'/Game/WISEYE/Sensors',unreal.Material,unreal.MaterialFactoryNew())
material.modify()
edit=unreal.MaterialEditingLibrary
edit.delete_all_material_expressions(material)
material.set_editor_property('material_domain',unreal.MaterialDomain.MD_POST_PROCESS)
material.set_editor_property('blendable_location',unreal.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
material.set_editor_property('blendable_output_alpha',True)
def node(cls,x,y):return edit.create_material_expression(material,cls,x,y)
custom=node(unreal.MaterialExpressionCustom,400,0)
custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
custom.set_editor_property('description','WISEYE reference thermal signal; normalized, not radiometric')
defaults=dict(BackgroundHeat=.27,SkyHeat=.08,NoiseStrength=.008,BlackHot=0,Enhanced=1,
              BlurPixels=.8,Contrast=1.35,BackgroundDetail=.65,NoiseFrame=0,
              Reference=1,BodyCode=97,BatteryWarmth=0,DisplayReadout=0)
textures={'Stencil':unreal.SceneTextureId.PPI_CUSTOM_STENCIL,'CustomDepth':unreal.SceneTextureId.PPI_CUSTOM_DEPTH,
          'Depth':unreal.SceneTextureId.PPI_SCENE_DEPTH,'Normal':unreal.SceneTextureId.PPI_WORLD_NORMAL,
          'SceneColor':unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0}
textures.update(globals().get('WISEYE_IR_EXTRA_TEXTURES',{}))
defaults.update(globals().get('WISEYE_IR_EXTRA_SCALARS',{}))
vectors=globals().get('WISEYE_IR_EXTRA_VECTORS',{})
inputs=[]
for key in [*textures,'UV',*defaults,'BatterySpot','DisplayColor',*vectors]:
    item=unreal.CustomInput();item.set_editor_property('input_name',key);inputs.append(item)
custom.set_editor_property('inputs',inputs)
folder=Path(__file__).parent
code=(folder/'infrared_reference.hlsl').read_text(encoding='utf8')+'\n'+(folder/'infrared_appearance.hlsl').read_text(encoding='utf8')
if globals().get('WISEYE_IR_STENCIL_MIN'):
    code=code.replace('step(.5,Stencil.r)','step(32.,Stencil.r)').replace('step(.5,s)','step(32.,s)')
custom.set_editor_property('code',globals().get('WISEYE_IR_CODE_PREFIX','')+code)
for i,(key,kind) in enumerate(textures.items()):
    tex=node(unreal.MaterialExpressionSceneTexture,-650,i*150);tex.set_editor_property('scene_texture_id',kind)
    assert edit.connect_material_expressions(tex,'Color',custom,key)
uv=node(unreal.MaterialExpressionTextureCoordinate,-650,850)
assert edit.connect_material_expressions(uv,'',custom,'UV')
for i,(key,value) in enumerate(defaults.items()):
    parameter=node(unreal.MaterialExpressionScalarParameter,-100,i*150)
    parameter.set_editor_property('parameter_name',key);parameter.set_editor_property('default_value',value)
    assert edit.connect_material_expressions(parameter,'',custom,key)
spot=node(unreal.MaterialExpressionVectorParameter,-100,2200)
spot.set_editor_property('parameter_name','BatterySpot');spot.set_editor_property('default_value',unreal.LinearColor(.5,.5,.01,0))
assert edit.connect_material_expressions(spot,'RGBA',custom,'BatterySpot')
for i,(key,value) in enumerate(vectors.items()):
    parameter=node(unreal.MaterialExpressionVectorParameter,-100,2600+i*150)
    parameter.set_editor_property('parameter_name',key);parameter.set_editor_property('default_value',unreal.LinearColor(*value))
    assert edit.connect_material_expressions(parameter,'RGBA',custom,key)
display=node(unreal.MaterialExpressionTextureSampleParameter2D,-650,2400)
display.set_editor_property('parameter_name','DisplayTexture')
display.set_editor_property('texture',unreal.load_asset('/Engine/EngineResources/DefaultTexture'))
assert edit.connect_material_expressions(uv,'',display,'UVs')
assert edit.connect_material_expressions(display,'RGB',custom,'DisplayColor')
assert edit.connect_material_property(custom,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
opacity=node(unreal.MaterialExpressionConstant,400,300);opacity.set_editor_property('r',1.)
assert edit.connect_material_property(opacity,'',unreal.MaterialProperty.MP_OPACITY)
edit.recompile_material(material)
assert unreal.EditorAssetLibrary.save_asset(path,only_if_is_dirty=False)
unreal.log('WISEYE_IR_REFERENCE_SAVED '+path)

"""Create only the experimental material; never edit maps, actors or legacy assets."""
from pathlib import Path
import unreal

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'Stop PIE first'
folder='/Game/WISEYE/Sensors'
name='M_IR_Experimental'
material=unreal.load_asset(folder+'/'+name)
if not material:
    material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
material.modify()
edit=unreal.MaterialEditingLibrary
edit.delete_all_material_expressions(material)
material.set_editor_property('material_domain',unreal.MaterialDomain.MD_POST_PROCESS)
material.set_editor_property('blendable_location',unreal.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
material.set_editor_property('blendable_output_alpha',True)
def node(cls,x,y):return edit.create_material_expression(material,cls,x,y)
custom=node(unreal.MaterialExpressionCustom,400,0)
custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
custom.set_editor_property('description','WISEYE IR appearance v2; legacy A/B switch; not radiometric')
defaults={'BackgroundHeat':.27,'SkyHeat':.08,'NoiseStrength':.008,'BlackHot':0,
          'Enhanced':1,'BlurPixels':.8,'Contrast':1.35,'BackgroundDetail':.65,'NoiseFrame':0}
textures={'Stencil':unreal.SceneTextureId.PPI_CUSTOM_STENCIL,'CustomDepth':unreal.SceneTextureId.PPI_CUSTOM_DEPTH,
          'Depth':unreal.SceneTextureId.PPI_SCENE_DEPTH,'Normal':unreal.SceneTextureId.PPI_WORLD_NORMAL,
          'SceneColor':unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0}
inputs=[]
for key in [*textures,'UV',*defaults]:
    item=unreal.CustomInput();item.set_editor_property('input_name',key);inputs.append(item)
custom.set_editor_property('inputs',inputs)
custom.set_editor_property('code',Path(__file__).with_name('infrared_appearance.hlsl').read_text(encoding='utf8'))
for i,(key,kind) in enumerate(textures.items()):
    tex=node(unreal.MaterialExpressionSceneTexture,-650,i*150)
    tex.set_editor_property('scene_texture_id',kind)
    assert edit.connect_material_expressions(tex,'Color',custom,key)
uv=node(unreal.MaterialExpressionTextureCoordinate,-650,850)
assert edit.connect_material_expressions(uv,'',custom,'UV')
for i,(key,value) in enumerate(defaults.items()):
    parameter=node(unreal.MaterialExpressionScalarParameter,-100,i*150)
    parameter.set_editor_property('parameter_name',key);parameter.set_editor_property('default_value',value)
    assert edit.connect_material_expressions(parameter,'',custom,key)
assert edit.connect_material_property(custom,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
opacity=node(unreal.MaterialExpressionConstant,400,300);opacity.set_editor_property('r',1.)
assert edit.connect_material_property(opacity,'',unreal.MaterialProperty.MP_OPACITY)
edit.recompile_material(material)
assert unreal.EditorAssetLibrary.save_asset(material.get_path_name(),only_if_is_dirty=False)
unreal.log('WISEYE_IR_EXPERIMENTAL_SAVED '+material.get_path_name())

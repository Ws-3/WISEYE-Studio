"""Create the operator-only translucent placement ghost material."""
import unreal
path='/Game/WISEYE/Sensors/M_PlacementPreview'
material=unreal.load_asset(path)
if not material:
    material=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_PlacementPreview','/Game/WISEYE/Sensors',unreal.Material,unreal.MaterialFactoryNew())
edit=unreal.MaterialEditingLibrary
edit.delete_all_material_expressions(material)
material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
material.set_editor_property('two_sided',True)
color=edit.create_material_expression(material,unreal.MaterialExpressionConstant3Vector)
color.set_editor_property('constant',unreal.LinearColor(.03,.8,.65,1))
opacity=edit.create_material_expression(material,unreal.MaterialExpressionConstant)
opacity.set_editor_property('r',.6)
# Keep operator tint legible under both bright daylight and dark exposures.
adaptation=edit.create_material_expression(material,unreal.MaterialExpressionEyeAdaptation)
divide=edit.create_material_expression(material,unreal.MaterialExpressionDivide)
assert edit.connect_material_expressions(color,'',divide,'A')
assert edit.connect_material_expressions(adaptation,'',divide,'B')
assert edit.connect_material_property(divide,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
edit.connect_material_property(opacity,'',unreal.MaterialProperty.MP_OPACITY)
edit.recompile_material(material)
assert unreal.EditorAssetLibrary.save_asset(path,only_if_is_dirty=False)
unreal.log('WISEYE_PLACEMENT_PREVIEW_SAVED')

"""Create a project-owned, depth-tested rain-streak material; no lens refraction."""
import unreal

path='/Game/WISEYE/Sensors/M_RainStreaks'
material=unreal.load_asset(path)
if not material:
    material=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_RainStreaks','/Game/WISEYE/Sensors',unreal.Material,unreal.MaterialFactoryNew())
    material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided',True)
    unreal.MaterialEditingLibrary.set_material_usage(material,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    uv=unreal.MaterialEditingLibrary.create_material_expression(material,unreal.MaterialExpressionTextureCoordinate)
    depth=unreal.MaterialEditingLibrary.create_material_expression(material,unreal.MaterialExpressionPixelDepth)
    alpha=unreal.MaterialEditingLibrary.create_material_expression(material,unreal.MaterialExpressionCustom)
    alpha.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    inputs=[]
    for name in ('UV','Depth'):
        item=unreal.CustomInput()
        item.set_editor_property('input_name',name)
        inputs.append(item)
    alpha.set_editor_property('inputs',inputs)
    alpha.set_editor_property('code','float x=(UV.x-.5)*3.5; float y=saturate(1-abs(UV.y-.5)*2); return .35*exp(-x*x)*y*y*exp(-Depth/20000.);')
    unreal.MaterialEditingLibrary.connect_material_expressions(uv,'',alpha,'UV')
    unreal.MaterialEditingLibrary.connect_material_expressions(depth,'',alpha,'Depth')
    unreal.MaterialEditingLibrary.connect_material_property(alpha,'',unreal.MaterialProperty.MP_OPACITY)
    tint=unreal.MaterialEditingLibrary.create_material_expression(material,unreal.MaterialExpressionVectorParameter)
    tint.set_editor_property('parameter_name','RainTint');tint.set_editor_property('default_value',unreal.LinearColor(.4,.48,.58,1))
    unreal.MaterialEditingLibrary.connect_material_property(tint,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    unreal.MaterialEditingLibrary.recompile_material(material)
assert unreal.EditorAssetLibrary.save_loaded_asset(material)
unreal.log('WISEYE_RAIN_STREAKS_READY')

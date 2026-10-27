"""Build a translucent swept rotor disc material, used only for visual high-RPM blur."""
import unreal
path='/Game/WISEYE/DroneModels/Avata/Animated'
material=unreal.load_asset(path+'/M_RotorBlur')
if not material:
    material=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_RotorBlur',path,unreal.Material,unreal.MaterialFactoryNew())
    material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('two_sided',True)
    material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    color=unreal.MaterialEditingLibrary.create_material_expression(material,unreal.MaterialExpressionConstant3Vector)
    color.set_editor_property('constant',unreal.LinearColor(.10,.12,.14,1))
    opacity=unreal.MaterialEditingLibrary.create_material_expression(material,unreal.MaterialExpressionConstant)
    opacity.set_editor_property('r',.28)
    unreal.MaterialEditingLibrary.connect_material_property(color,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    unreal.MaterialEditingLibrary.connect_material_property(opacity,'',unreal.MaterialProperty.MP_OPACITY)
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material)
unreal.log('Rotor blur material ready')

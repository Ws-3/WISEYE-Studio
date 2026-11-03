"""Idempotent visible-only navigation lamp material; run in Unreal Editor Python."""
import unreal

path = '/Game/WISEYE/DroneModels/Common'
asset = path + '/M_NavigationLamp'
material = unreal.load_asset(asset)
if not material:
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        'M_NavigationLamp', path, unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    color = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionVectorParameter)
    color.set_editor_property('parameter_name', 'LampColor')
    color.set_editor_property('default_value', unreal.LinearColor(8, .01, .005, 1))
    unreal.MaterialEditingLibrary.connect_material_property(
        color, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material)
unreal.log('WISEYE_NAVIGATION_LIGHT_MATERIAL_OK')

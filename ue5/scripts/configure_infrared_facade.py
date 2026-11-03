"""Independent facade pilot; preserves the classified/reference comparison assets."""
from pathlib import Path
import unreal

folder=Path(__file__).parent
# Reuse the validated palette and target model without changing their assets.
source=(folder/'configure_infrared_classified.py').read_text(encoding='utf8')
exec(compile(source,str(folder/'configure_infrared_classified.py'),'exec'),dict(
    __file__=str(folder/'configure_infrared_classified.py'),__name__='__main__',
    WISEYE_CLASS_ASSET='M_IR_Facade',WISEYE_CLASS_EXTRA_SCALARS=dict(Facade=0),
    WISEYE_CLASS_EXTRA_TEXTURES=dict(BaseColor=unreal.SceneTextureId.PPI_BASE_COLOR,Roughness=unreal.SceneTextureId.PPI_ROUGHNESS),
    WISEYE_CLASS_PREFIX='#define WISEYE_FACADE 1\n'+(folder/'infrared_facade.hlsl').read_text(encoding='utf8')+'\n'))
unreal.log('WISEYE_IR_FACADE_SAVED')
# A project-owned reference makes cloud textures/parent material cook dependencies.
cloud='/Game/WISEYE/Sensors/M_Cloud_Runtime'
if not unreal.EditorAssetLibrary.does_asset_exist(cloud):
    parent=unreal.load_asset('/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst')
    assert parent
    instance=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_Cloud_Runtime','/Game/WISEYE/Sensors',unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    assert instance
    unreal.MaterialEditingLibrary.set_material_instance_parent(instance,parent)
assert unreal.EditorAssetLibrary.save_asset(cloud,only_if_is_dirty=False)
unreal.log('WISEYE_CLOUD_RUNTIME_SAVED')

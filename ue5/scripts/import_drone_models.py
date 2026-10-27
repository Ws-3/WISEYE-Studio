from pathlib import Path
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
source = project.parents[1] / 'Models' / 'Avata_black.fbx'
destination = '/Game/WISEYE/DroneModels/Avata'
asset_path = destination + '/Avata_black'
if not source.is_file():
    raise RuntimeError(f'Avata source model is missing: {source}')

if not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
    options = unreal.FbxImportUI()
    options.set_editor_property('import_mesh', True)
    options.set_editor_property('import_as_skeletal', False)
    options.set_editor_property('import_materials', True)
    options.set_editor_property('import_textures', True)
    static_data = options.get_editor_property('static_mesh_import_data')
    static_data.set_editor_property('combine_meshes', True)
    static_data.set_editor_property('generate_lightmap_u_vs', True)
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', str(source))
    task.set_editor_property('destination_path', destination)
    task.set_editor_property('destination_name', 'Avata_black')
    task.set_editor_property('automated', True)
    task.set_editor_property('save', True)
    task.set_editor_property('replace_existing', False)
    task.set_editor_property('options', options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

asset = unreal.EditorAssetLibrary.load_asset(asset_path)
if not asset:
    raise RuntimeError(f'Avata import did not create {asset_path}')
blur_builder = project.parent / 'scripts' / 'build_rotor_blur.py'
exec(compile(blur_builder.read_text(encoding='utf-8-sig'), str(blur_builder), 'exec'))
unreal.EditorAssetLibrary.save_directory(destination, only_if_is_dirty=False, recursive=True)
animated = destination + '/Animated/'
if any(not unreal.EditorAssetLibrary.does_asset_exist(animated + name)
       for name in ['AvataBody'] + ['AvataRotor' + str(i) for i in range(4)]):
    builder = project.parent / 'scripts' / 'build_avata_rotors.py'
    exec(compile(builder.read_text(encoding='utf-8-sig'), str(builder), 'exec'))
print(f'WISEYE_DRONE_IMPORT_OK {asset_path}')

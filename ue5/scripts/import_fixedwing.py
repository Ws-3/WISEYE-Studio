"""Idempotent isolated FBX import; scale is calibrated at runtime to 80 cm."""
import json
import os
from pathlib import Path
import unreal

source_root = Path(os.environ.get('WISEYE_SOURCE_ROOT', str(Path(unreal.Paths.project_dir()).resolve().parents[1])))
source = source_root / 'Models/FixedwingUAV_gray.fbx'
destination = '/Game/WISEYE/DroneModels/Fixedwing'
asset_path = destination + '/FixedwingUAV_gray'
if not source.is_file():
    raise RuntimeError('Fixed-wing FBX missing: ' + str(source))
if not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = True
    options.import_textures = True
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.generate_lightmap_u_vs = True
    options.static_mesh_import_data.auto_generate_collision = True
    task = unreal.AssetImportTask()
    task.filename = str(source)
    task.destination_path = destination
    task.destination_name = 'FixedwingUAV_gray'
    task.automated = True
    task.save = True
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh = unreal.EditorAssetLibrary.load_asset(asset_path)
if not isinstance(mesh, unreal.StaticMesh):
    raise RuntimeError('Fixed-wing static mesh import failed')
bounds = mesh.get_bounds()
size = bounds.box_extent * 2
report = {'asset': asset_path, 'source': str(source),
          'raw_size_cm': [size.x, size.y, size.z],
          'raw_center_cm': [bounds.origin.x, bounds.origin.y, bounds.origin.z],
          'user_length_cm': 80, 'materials': [str(m.material_slot_name) for m in mesh.static_materials]}
output = source_root / 'builds/fixedwing-import.json'
output.parent.mkdir(exist_ok=True)
output.write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.EditorAssetLibrary.save_directory(destination, only_if_is_dirty=False, recursive=True)
print('WISEYE_FIXEDWING_IMPORT_OK ' + json.dumps(report))

"""UE editor: rebuild Avata body + four original propellers (GeometryScripting required).
Run with -EnablePlugins=PythonScriptPlugin,GeometryScripting -ExecCmds="py <this file>".
Original FBX/combined mesh stay untouched. Generated assets ship in Git; no runtime plugin required.
"""
import json
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve().parents[1]
DEST = '/Game/WISEYE/DroneModels/Avata/Animated'
SCRATCH = DEST + '/SourceParts'
PAIRS = ('d96ef349-3639-4fe5-afd8-0f42b0b27645', 'de9ed733-b681-4063-aed2-e02f683716f1')
original = unreal.load_asset('/Game/WISEYE/DroneModels/Avata/Avata_black')
assert original
materials = {str(m.material_slot_name): m.material_interface for m in original.static_materials}
options = unreal.FbxImportUI()
options.import_mesh = True
options.import_as_skeletal = False
options.import_materials = False
options.import_textures = False
options.static_mesh_import_data.combine_meshes = False
options.static_mesh_import_data.transform_vertex_to_absolute = True
task = unreal.AssetImportTask()
task.filename = str(ROOT / 'Models/Avata_black.fbx')
task.destination_path = SCRATCH
task.destination_name = 'Avata'
task.automated = True
task.save = True
task.replace_existing = True
task.options = options
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
meshes = {unreal.load_asset(p).get_name(): unreal.load_asset(p) for p in task.imported_object_paths if isinstance(unreal.load_asset(p), unreal.StaticMesh)}
assert len(meshes) == 9

def dynamic(mesh):
    d = unreal.DynamicMesh()
    _, outcome = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh, d, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    assert outcome == unreal.GeometryScriptOutcomePins.SUCCESS
    return d

def save(d, name, mats):
    path = DEST + '/' + name
    asset = unreal.load_asset(path)
    if not asset:
        asset, outcome = unreal.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(d, path, unreal.GeometryScriptCreateNewStaticMeshAssetOptions(enable_collision=False))
        assert outcome == unreal.GeometryScriptOutcomePins.SUCCESS
    opts = unreal.GeometryScriptCopyMeshToAssetOptions(replace_materials=True, new_materials=mats, enable_recompute_normals=False)
    _, outcome = unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(d, asset, opts, unreal.GeometryScriptMeshWriteLOD())
    assert outcome == unreal.GeometryScriptOutcomePins.SUCCESS
    unreal.EditorAssetLibrary.save_loaded_asset(asset)
    return asset

body = unreal.DynamicMesh()
body_mats = []
source_triangles = 0
for name, mesh in meshes.items():
    d = dynamic(mesh)
    source_triangles += d.get_triangle_count()
    if name in PAIRS:
        continue
    mats = [materials[str(m.material_slot_name)] for m in mesh.static_materials]
    _, body_mats = unreal.GeometryScript_MeshEdits.append_mesh_with_materials(body, body_mats, d, mats, unreal.Transform())
body_asset = save(body, 'AvataBody', body_mats)
for sock in [body_asset.find_socket('Rotor' + str(i)) for i in range(4)]:
    if sock: body_asset.remove_socket(sock)
report = {'body_triangles': body.get_triangle_count(), 'source_triangles': source_triangles, 'rotors': []}
for pair_index, name in enumerate(PAIRS):
    mesh = meshes[name]
    d = dynamic(mesh)
    _, islands = unreal.GeometryScript_MeshDecomposition.split_mesh_by_components(d, None)
    # Circular lower hub surfaces: 720 triangles, symmetric around each real motor axis.
    hubs = [unreal.GeometryScript_MeshQueries.get_mesh_bounding_box(m) for m in islands if m.get_triangle_count() == 720]
    assert len(hubs) == 2, 'Source topology changed; re-evaluate shaft centers'
    for side in range(2):
        normal = unreal.Vector(-1 if side == 0 else 1, 0, 0)
        _, selection = unreal.GeometryScript_MeshSelection.select_mesh_elements_with_plane(d, plane_normal=normal)
        rotor = unreal.DynamicMesh()
        unreal.GeometryScript_MeshDecomposition.copy_mesh_selection_to_mesh(d, rotor, selection)
        hub = next(b for b in hubs if (b.min.x + b.max.x > 0) == (side == 1))
        center = (hub.min + hub.max) * .5
        unreal.GeometryScript_MeshTransforms.translate_pivot_to_location(rotor, center)
        index = pair_index * 2 + side
        asset = save(rotor, 'AvataRotor' + str(index), [materials[str(m.material_slot_name)] for m in mesh.static_materials])
        socket = unreal.StaticMeshSocket(outer=body_asset)
        socket.set_editor_property('socket_name', 'Rotor' + str(index))
        socket.set_editor_property('relative_location', center)
        body_asset.add_socket(socket)
        report['rotors'].append(dict(index=index, center=[center.x,center.y,center.z], triangles=rotor.get_triangle_count()))
assert report['body_triangles'] + sum(r['triangles'] for r in report['rotors']) == source_triangles, 'Triangles lost or duplicated'
unreal.EditorAssetLibrary.save_loaded_asset(body_asset)
# Only this script's intermediate import folder; original FBX and asset are preserved.
assert SCRATCH == '/Game/WISEYE/DroneModels/Avata/Animated/SourceParts'
unreal.EditorAssetLibrary.delete_directory(SCRATCH)
(ROOT / 'runtime').mkdir(exist_ok=True)
(ROOT / 'runtime/avata_asset_build.json').write_text(json.dumps(report, indent=2), encoding='utf8')
unreal.log('Avata animated assets rebuilt successfully')

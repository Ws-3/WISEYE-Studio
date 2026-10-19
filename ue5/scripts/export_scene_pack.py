"""UE editor utility: export_pack('test_range', 'D:/.../test_range.zip').

Bundles the scene namespace, enumerates transitive game dependencies, and hashes
shared assets that must already be installed in the receiving WISEYE project.
For this v1 format, World Partition packages use UE migration instead.
"""
import hashlib
import json
from pathlib import Path
import zipfile
import unreal


def digest(path):
    with path.open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def export_pack(identifier, destination):
    project = Path(unreal.Paths.project_dir()).resolve()
    scene = json.loads((project/'Config/WISEYE/Scenes'/f'{identifier}.json').read_text(encoding='utf-8'))
    assert scene.get('prepared'), '场景尚未准备完成'
    namespace = f'/Game/WISEYE/Scenes/{identifier}/'
    assert scene['map'].startswith(namespace), '请先创建标准场景副本'
    world = unreal.load_asset(scene['map'])
    assert not world.get_world_settings().get_editor_property('world_partition'), 'World Partition 场景请使用 UE Migrate，完整迁移外部 Actor'
    root = project/'Content/WISEYE/Scenes'/identifier
    files = {p.relative_to(project).as_posix(): p for p in root.rglob('*') if p.suffix.lower() in ('.umap','.uasset','.ubulk','.uexp')}
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True,
                                                    include_searchable_names=False, include_soft_management_references=False,
                                                    include_hard_management_references=False)
    pending, seen, required = [scene['map'], '/Game/WISEYE/Sensors/M_IR_Minimal'], set(), {}
    while pending:
        package = pending.pop()
        if package in seen:
            continue
        seen.add(package)
        if package.startswith(('/Script/', '/Engine/', '/InterchangeAssets/')):
            continue
        assert package.startswith('/Game/'), f'插件资源 {package} 请先通过 UE 安装并适配，不能放入 v1 场景包'
        if not package.startswith(namespace):
            path = project/'Content'/(package[6:]+'.uasset')
            assert path.is_file(), f'依赖不是普通资产：{package}；请使用 UE 迁移'
            required[package] = digest(path)
        pending.extend(str(dep) for dep in registry.get_dependencies(package, options))
    manifest = dict(engine_version='5.8', scene=scene, required_assets=required,
                    files={name:digest(path) for name,path in files.items()})
    # Exclusive create keeps an existing user's package intact.
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('scene.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        for name,path in files.items():
            archive.write(path,name)
    unreal.log('WISEYE exported scene pack: '+str(destination))

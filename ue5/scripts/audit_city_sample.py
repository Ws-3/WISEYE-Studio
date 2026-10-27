import unreal,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
out=ROOT/'logs/city_asset_audit.json'
r=unreal.AssetRegistryHelpers.get_asset_registry();r.search_all_assets(True)
assets=r.get_assets_by_package_name('/Game/Map/Small_City_LVL')
opts=unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,include_searchable_names=False,include_soft_management_references=False,include_hard_management_references=False)
seen=set();pending=['/Game/Map/Small_City_LVL']
# Plugin assets may refer back into /Game, including assets loaded by a module
# rather than by the map. Follow those edges before filtering copied packages.
local_plugins=Path(unreal.Paths.project_dir())/'Plugins'
plugin_mounts=[]
for descriptor in local_plugins.glob('*/*.uplugin'):
 if (descriptor.parent/'Content').is_dir():
  mount='/'+descriptor.stem
  plugin_mounts.append(mount)
  pending.extend(str(a.package_name) for a in r.get_assets_by_path(mount,recursive=True))
while pending:
 p=pending.pop()
 if p in seen:continue
 seen.add(p)
 pending.extend(str(v) for v in r.get_dependencies(p,opts) if str(v).startswith('/Game/') or any(str(v).startswith(m+'/') for m in plugin_mounts))
content=Path(unreal.Paths.project_dir())/'Content'
game_packages=sorted(p for p in seen if p.startswith('/Game/'))
missing=[p for p in game_packages if not any((content/(p[6:]+ext)).is_file() for ext in ('.uasset','.umap'))]
out.write_text(json.dumps(dict(source_project=str(Path(unreal.Paths.project_dir()).resolve()/'CitySample.uproject'),map_sha256=hashlib.sha256((content/'Map/Small_City_LVL.umap').read_bytes()).hexdigest(),map_assets=[str(a.asset_name) for a in assets],packages=[p for p in game_packages if p not in missing],missing_source_references=missing,plugin_mounts=plugin_mounts,asset_tools=[x for x in dir(unreal.AssetToolsHelpers.get_asset_tools()) if 'migrat' in x],migration_options=str(unreal.MigrationOptions())),indent=2),encoding='utf8')
if missing:unreal.log_warning('City Sample source itself has unavailable references; retained in audit: '+str(missing))
unreal.log('WISEYE CITY AUDIT COMPLETE '+str(len(seen)))

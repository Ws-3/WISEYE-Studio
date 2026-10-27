"""Run in the downloaded City Sample project with UE's Python commandlet."""
import unreal,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
source=Path(unreal.Paths.project_dir()).resolve()
target=ROOT/'ue5/WISEYE/Content'
assert (source/'CitySample.uproject').exists(),'Must run in the original City Sample project'
assert (target.parent/'test.uproject').exists()
assert not (target/'Map/Small_City_LVL.umap').exists(),'Imported map exists; refusing to overwrite'
report=ROOT/'logs/city_migration.json'
report.write_text(json.dumps(dict(status='running',source=str(source),destination=str(target))),encoding='utf8')
options=unreal.MigrationOptions()
options.set_editor_property('prompt',False)
options.set_editor_property('ignore_dependencies',False)
options.set_editor_property('asset_conflict',unreal.AssetMigrationConflict.SKIP)
unreal.AssetToolsHelpers.get_asset_tools().migrate_packages(['/Game/Map/Small_City_LVL'],str(target),options)
assert (target/'Map/Small_City_LVL.umap').is_file(),'Map migration failed; inspect log'
actors=list((target/'__ExternalActors__/Map/Small_City_LVL').rglob('*.uasset'))
assert actors,'World Partition actors missing'
# Preserve original package paths while keeping downloaded third-party assets local.
excludes=['/ue5/WISEYE/Content/'+p.name+'/' for p in (source/'Content').iterdir() if p.is_dir() and p.name not in ('__ExternalActors__','__ExternalObjects__','Developers','Collections')]
excludes += ['/ue5/WISEYE/Content/__ExternalActors__/Map/','/ue5/WISEYE/Content/__ExternalObjects__/Map/']
ignore=ROOT/'.gitignore';text=ignore.read_text(encoding='utf8');missing=[line for line in excludes if line not in text.splitlines()]
if missing:ignore.write_text(text+'\n# Local migrated City Sample assets\n'+'\n'.join(missing)+'\n',encoding='utf8')
report.write_text(json.dumps(dict(status='migrated',source=str(source),destination=str(target),external_actors=len(actors)),indent=2),encoding='utf8')
unreal.log('WISEYE CITY MIGRATION COMPLETE')

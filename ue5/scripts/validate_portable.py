"""Use UnrealEditor-Cmd -run=pythonscript -script=<this file>."""
import unreal
import json
from pathlib import Path
paths=['/Game/WISEYE-test','/Game/WISEYE/RT_EO']
paths += ['/Game/WISEYE/PTZRecovered/'+n for n in ['Mesh','Mesh_ncl_1','Mesh_ncl_2','Mesh_ncl_3']]
results={p:bool(unreal.load_asset(p)) for p in paths}
assert all(results.values()),str(results)
assert unreal.load_class(None,'/Script/test.WiseEyeDemo')
assert unreal.load_class(None,'/Script/test.WiseEyeGameMode')
out=Path(unreal.Paths.project_saved_dir())/'WISEYE'
out.mkdir(parents=True,exist_ok=True)
(out/'portable_validation.json').write_text(json.dumps({'passed':True,'assets':results},indent=2),encoding='utf-8')
unreal.log('WISEYE PORTABLE VALIDATION PASSED')

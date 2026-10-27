"""Bounded-memory transfer of an audited package closure without changing package paths."""
import argparse,hashlib,json,shutil,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--project',required=True);a=p.parse_args()
 source=Path(a.project).resolve().parent/'Content';target=ROOT/'ue5/WISEYE/Content'
 audit=json.loads((ROOT/'logs/city_asset_audit.json').read_text(encoding='utf8'));files=set();missing=[]
 if audit.get('map_sha256')!=digest(source/'Map/Small_City_LVL.umap'):raise RuntimeError('Audited map differs from source; regenerate the audit')
 for package in audit['packages']+['/Game/Audio/Soundscape/SoundscapeGameplayTags','/Game/Audio/Blueprints/MetaHumanAudio/DT_FoleyGameplayTags']:
  assert package.startswith('/Game/') and '..' not in package
  path=source/package[6:]
  assets=[path.with_suffix(ext) for ext in ('.uasset','.umap','.uexp','.ubulk','.uptnl') if path.with_suffix(ext).is_file()]
  if not assets:missing.append(package)
  files.update(assets)
 # External non-asset objects are stored adjacent to the corresponding map hierarchy.
 for package in audit['packages']:
  if (source/(package[6:]+'.umap')).is_file():
   for category in ('__ExternalActors__','__ExternalObjects__'):
    external=source/category/package[6:]
    if external.is_dir():files.update(f for f in external.rglob('*') if f.is_file())
 if missing:raise RuntimeError('Missing audited packages: '+str(missing[:10]))
 # Preflight all conflicts before copying anything; never overwrite project-owned assets.
 for f in files:
  dst=target/f.relative_to(source)
  if dst.exists() and (dst.stat().st_size!=f.stat().st_size or digest(dst)!=digest(f)):raise RuntimeError('Conflicting destination: '+str(dst))
 transferred=0;manifest=[];started=time.monotonic()
 for index,f in enumerate(sorted(files),1):
  relative=f.relative_to(source);dst=target/relative;dst.parent.mkdir(parents=True,exist_ok=True)
  if not dst.exists():shutil.copy2(f,dst)
  actual=digest(dst);expected=digest(f)
  if actual!=expected:raise RuntimeError('Hash mismatch: '+str(relative))
  transferred+=f.stat().st_size;manifest.append(dict(path=relative.as_posix(),bytes=f.stat().st_size,sha256=actual))
  if index%2000==0:print(f'{index}/{len(files)} files verified',flush=True)
 report=dict(status='migrated',method='audited same-path package transfer',files=len(files),bytes=transferred,seconds=time.monotonic()-started,source=str(source),external_actors=sum(1 for f in files if '/__ExternalActors__/Map/Small_City_LVL/' in f.as_posix()))
 (ROOT/'logs/city_migration_files.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
 (ROOT/'logs/city_migration.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report),flush=True)
if __name__=='__main__':main()

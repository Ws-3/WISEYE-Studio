"""Install locally owned City Sample dependencies; never copy WISEYE code into the sample."""
import argparse,json,shutil,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def adapt_primary_module(support):
    entry = support/'Source/CitySample/CitySample.cpp'
    if entry.is_file():
        text = entry.read_text(encoding='utf8')
        old = 'IMPLEMENT_PRIMARY_GAME_MODULE( FDefaultGameModuleImpl, CitySample, "CitySample" );'
        if old in text:
            entry.write_text(text.replace(old, 'IMPLEMENT_GAME_MODULE( FDefaultGameModuleImpl, CitySample );'), encoding='utf8')

def copy_tree(source,destination):
    if destination.exists():
        raise RuntimeError(f'Destination already exists; refusing overwrite: {destination}')
    shutil.copytree(source,destination,ignore=shutil.ignore_patterns('Intermediate','Saved','DerivedDataCache','.vs'))

def main():
    args=argparse.ArgumentParser();args.add_argument('--project',required=True);args.add_argument('--install',action='store_true');args.add_argument('--audit',action='store_true');a=args.parse_args()
    project=Path(a.project).resolve();source=project.parent;data=json.loads(project.read_text(encoding='utf8'))
    if data['EngineAssociation']!='5.8':raise RuntimeError('This integration requires UE 5.8 assets')
    target=ROOT/'ue5/WISEYE';support=target/'Plugins/CitySampleSupport'
    report=dict(source=str(project),engine=data['EngineAssociation'],modules=data['Modules'],installed=False)
    if a.install:
        if support.exists():
            existing=support/'CitySampleSupport.uplugin'
            if not existing.is_file():raise RuntimeError('Incomplete dependency directory; inspect before changing it')
            installed=json.loads(existing.read_text(encoding='utf8'))
            if {m['Name'] for m in installed['Modules']}!={m['Name'] for m in data['Modules']}:raise RuntimeError('Installed modules differ from source')
            if all((support/'Source'/m['Name']/(m['Name']+'.Build.cs')).is_file() for m in data['Modules']):
                adapt_primary_module(support)
                print('City Sample dependencies already installed; no files overwritten.');return
        imports=[]
        for folder in (source/'Plugins').iterdir():
            if folder.is_dir() and folder.name!='Experimental':
                destination=target/'Plugins'/folder.name
                if not destination.exists():copy_tree(folder,destination)
                elif not list(destination.glob('*.uplugin')):raise RuntimeError('Incomplete local plugin; inspect before retrying: '+str(destination))
                imports.append(folder.name)
        support.mkdir(parents=True,exist_ok=True)
        copied_modules=set()
        for module in data['Modules']:
            destination=support/'Source'/module['Name']
            if not destination.exists():
                copy_tree(source/'Source'/module['Name'],destination);copied_modules.add(module['Name'])
            elif not (destination/(module['Name']+'.Build.cs')).is_file():raise RuntimeError('Incomplete module: '+str(destination))
        adapt_primary_module(support)
        # .uproject AdditionalDependencies are not applied to a plugin module.
        for module in data['Modules']:
            additional=module.get('AdditionalDependencies',[])
            if additional and module['Name'] in copied_modules:
                build=support/'Source'/module['Name']/(module['Name']+'.Build.cs')
                text=build.read_text(encoding='utf8')
                insertion='PublicDependencyModuleNames.AddRange(new string[] { '+', '.join(json.dumps(n) for n in additional)+' });'
                marker='PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;'
                if marker in text:text=text.replace(marker,marker+'\n        '+insertion)
                else:
                    marker='PrivateIncludePaths.Add(ModuleDirectory);';text=text.replace(marker,marker+'\n        '+insertion)
                build.write_text(text,encoding='utf8')
        (support/'Binaries/Win64').mkdir(parents=True,exist_ok=True)
        for f in (source/'Binaries/Win64').iterdir():
            if f.name.startswith('UnrealEditor-CitySample') and f.suffix=='.dll':shutil.copy2(f,support/'Binaries/Win64'/f.name)
        shutil.copy2(source/'Binaries/Win64/UnrealEditor.modules',support/'Binaries/Win64/UnrealEditor.modules')
        descriptor=dict(FileVersion=3,Version=1,VersionName='5.8-local',FriendlyName='WISEYE City Sample compatibility',CanContainContent=False,EnabledByDefault=False,Modules=data['Modules'],Plugins=[p for p in data['Plugins'] if p['Name']!='CitySamplePCG'])
        descriptor['Plugins'].extend(dict(Name=n,Enabled=True) for n in ('AISupport','ChaosEditor','WorldPartitionHLODUtilities') if not any(p['Name']==n for p in descriptor['Plugins']))
        engine_config=target/'Config/DefaultEngine.ini';engine_text=engine_config.read_text(encoding='utf8')
        source_engine=(source/'Config/DefaultEngine.ini').read_text(encoding='utf8')
        surfaces=[line for line in source_engine.splitlines() if line.startswith('+PhysicalSurfaces=')]
        if 'PhysicalSurfaces=' not in engine_text:engine_text+='\n[/Script/Engine.PhysicsSettings]\n'+'\n'.join(surfaces)+'\n'
        if 'p.Chaos.EnableAsyncInitBody=' not in engine_text:engine_text+='\n[SystemSettings]\np.Chaos.EnableAsyncInitBody=True\n'
        engine_config.write_text(engine_text,encoding='utf8')
        mass_source=(source/'Config/DefaultMass.ini').read_text(encoding='utf8')
        section='[/Script/WorldAudioDataSystem.WorldAudioMassProcessor]';begin=mass_source.index(section);end=mass_source.find('\n[',begin+2)
        mass_target=target/'Config/DefaultMass.ini'
        if not mass_target.exists():mass_target.write_text(mass_source[begin:end if end>=0 else len(mass_source)]+'\n',encoding='utf8')
        tags_source=source/'Config/DefaultGameplayTags.ini';tags_target=target/'Config/DefaultGameplayTags.ini'
        if tags_source.exists() and not tags_target.exists():shutil.copy2(tags_source,tags_target)
        (support/'CitySampleSupport.uplugin').write_text(json.dumps(descriptor,indent=2),encoding='utf8')
        target_project=target/'test.uproject';current=json.loads(target_project.read_text(encoding='utf8'))
        if not any(p['Name']=='CitySampleSupport' for p in current['Plugins']):current['Plugins'].append(dict(Name='CitySampleSupport',Enabled=True))
        target_project.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        excludes=['/ue5/WISEYE/Plugins/'+n+'/' for n in imports]+['/ue5/WISEYE/Plugins/CitySampleSupport/Source/']
        with (ROOT/'.gitignore').open('a',encoding='utf8') as stream:stream.write('\n# Local Epic City Sample dependencies; install from licensed source project.\n'+'\n'.join(excludes)+'\n')
        report.update(installed=True,plugins=imports)
    (ROOT/'logs/city_dependencies.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

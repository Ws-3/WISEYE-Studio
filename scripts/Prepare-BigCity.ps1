param(
    [ValidateSet('Build','Duplicate','Inspect','Surface','Assemble','Place','Thermal')][string]$Stage='Inspect',
    [string]$BuildWorkspace=(Join-Path (Split-Path -Parent $PSScriptRoot) 'ue5\WISEYE'),
    [string]$EngineRoot=(Join-Path (Split-Path -Parent $PSScriptRoot) 'Tools\UE_5.8')
)
$ErrorActionPreference='Stop'
$sourceRoot=Split-Path -Parent $PSScriptRoot
$project=Join-Path $BuildWorkspace 'test.uproject'
$editor=Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
foreach($file in @($project,$editor)) {if(-not(Test-Path -LiteralPath $file)){throw "Missing dependency: $file"}}
if(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -like "*$project*"}) {
    throw 'Save and close the build project before preparing Big City.'
}
$work=Join-Path $BuildWorkspace 'Saved\WISEYE\big_city'
New-Item -ItemType Directory -Path $work -Force | Out-Null
if($Stage -eq 'Build') {
    $native=Join-Path $sourceRoot 'ue5\WISEYE\Source'
    Get-ChildItem -LiteralPath $native | Copy-Item -Destination (Join-Path $BuildWorkspace 'Source') -Recurse -Force
    & (Join-Path $EngineRoot 'Engine\Build\BatchFiles\Build.bat') Win64 Development ("-Project="+$project) -TargetType=Editor -WaitMutex -NoHotReloadFromIDE
} elseif($Stage -eq 'Duplicate') {
    # No -Rename: never modify the source world. Never overwrite a partial copy.
    foreach($path in @('Content\WISEYE\Scenes\city_large','Content\__ExternalActors__\WISEYE\Scenes\city_large')) {
        if(Test-Path -LiteralPath (Join-Path $BuildWorkspace $path)){throw "Destination exists; inspect it instead of overwriting: $path"}
    }
    & $editor $project /Game/Map/Big_City_LVL -run=WorldPartitionBuilderCommandlet -builder=WorldPartitionRenameDuplicateBuilder -NewPackage=/Game/WISEYE/Scenes/city_large/BigCity -SCCProvider=None -unattended -nullrhi -nosound -nosplash ("-abslog="+(Join-Path $work 'duplicate.log'))
} else {
    $filename=switch($Stage){Inspect{'inspect_big_city.py'} Surface{'audit_big_city_surfaces.py'} Assemble{'install_big_city.py'} Place{'place_big_city_rig.py'} Thermal{'prepare_thermal_classes.py'}}
    $previousScene=$env:WISEYE_THERMAL_SCENE
    $previousApply=$env:WISEYE_THERMAL_TAG_APPLY
    try {
        if($Stage -eq 'Thermal'){$env:WISEYE_THERMAL_SCENE='city_large';$env:WISEYE_THERMAL_TAG_APPLY='1'}
        & $editor $project -run=pythonscript ("-script="+(Join-Path $sourceRoot "ue5\scripts\$filename")) -unattended -nullrhi -nosound -nosplash ("-abslog="+(Join-Path $work "$Stage.log"))
    } finally {$env:WISEYE_THERMAL_SCENE=$previousScene;$env:WISEYE_THERMAL_TAG_APPLY=$previousApply}
}
if($LASTEXITCODE -ne 0){throw "Big City $Stage failed. See $work; no automatic destructive retry."}
Write-Host "Big City $Stage complete. Runtime verification is required before prepared=true."

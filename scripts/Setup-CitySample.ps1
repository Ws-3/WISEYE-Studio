param(
    [string]$SourceProject='E:\Projects\Scene\CitySample\CitySample.uproject',
    [string]$EngineRoot='',
    [string]$Python='',
    [ValidateSet('Dependencies','Assets','Duplicate','Assemble','All')][string]$Stage='All',
    [switch]$SkipBuild,
    [switch]$InstallDependencies
)
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
if (-not $Python) {$Python=Join-Path $repo '.venv\Scripts\python.exe'}
if (-not $EngineRoot) {$EngineRoot=$env:UE_ROOT}
if (-not $EngineRoot -and (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'engine-root.local.txt'))) {$EngineRoot=(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'engine-root.local.txt') -Raw).Trim()}
if (-not $EngineRoot) {throw 'Specify -EngineRoot or UE_ROOT for this computer'}
$editor=Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$project=Join-Path $repo 'ue5\WISEYE\test.uproject'
if (-not (Test-Path -LiteralPath $SourceProject)) {throw 'CitySample.uproject not found'}
if (Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe'" -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like "*$project*"}) {throw 'Save and close the WISEYE UE editor before importing dependencies or assets'}
New-Item -ItemType Directory -Path (Join-Path $repo 'logs') -Force | Out-Null
function Invoke-EditorScript([string]$ProjectPath,[string]$ScriptName,[string]$LogName) {
    & $editor $ProjectPath -run=pythonscript ("-script="+(Join-Path $repo "ue5\scripts\$ScriptName")) -unattended -nop4 -nosplash -NullRHI ("-abslog="+(Join-Path $repo "logs\$LogName"))
    if ($LASTEXITCODE -ne 0) {throw "UE stage failed; inspect logs/$LogName"}
}
if ($Stage -in @('Dependencies','All') -or $InstallDependencies) {
    & $Python -X utf8 (Join-Path $repo 'scripts\city_sample_dependencies.py') --project $SourceProject --install
    if ($LASTEXITCODE -ne 0) {throw 'City Sample dependency setup failed'}
    if (-not $SkipBuild) {& (Join-Path $PSScriptRoot 'Start-WISEYE.ps1') -EngineRoot $EngineRoot -BuildOnly}
}
if ($Stage -in @('Assets','All')) {
    Invoke-EditorScript $SourceProject 'audit_city_sample.py' 'city_asset_audit.log'
    & $Python -X utf8 (Join-Path $repo 'scripts\copy_city_packages.py') --project $SourceProject
    if ($LASTEXITCODE -ne 0) {throw 'Package verification failed; no project-owned file is overwritten'}
}
if ($Stage -in @('Duplicate','All')) {
    $destination=Join-Path $repo 'ue5\WISEYE\Content\WISEYE\Scenes\city\CitySample.umap'
    if (Test-Path -LiteralPath $destination) {throw 'City map already exists. Refusing to overwrite; inspect it or run the next explicit stage.'}
    & $editor $project /Game/Map/Small_City_LVL -run=WorldPartitionBuilderCommandlet -Builder=WorldPartitionRenameDuplicateBuilder -NewPackage=/Game/WISEYE/Scenes/city/CitySample -SCCProvider=None -unattended -nop4 -nosplash -NullRHI ("-abslog="+(Join-Path $repo 'logs\city_duplicate.log'))
    if ($LASTEXITCODE -ne 0) {throw 'World Partition duplication failed; inspect logs/city_duplicate.log'}
}
if ($Stage -in @('Assemble','All')) {
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Save and close UE before assembling a city map'}
    Invoke-EditorScript $project 'install_city_sample.py' 'city_assembly.log'
    Write-Host 'City rig saved. Runtime checks are still required before enabling the city entry.'
}

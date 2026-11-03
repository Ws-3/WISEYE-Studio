param(
    [string]$BuildWorkspace = (Join-Path (Split-Path -Parent $PSScriptRoot) 'ue5\WISEYE'),
    [string]$EngineRoot = (Join-Path (Split-Path -Parent $PSScriptRoot) 'Tools\UE_5.8'),
    [switch]$Apply
)
$ErrorActionPreference='Stop'
$sourceRoot=Split-Path -Parent $PSScriptRoot
$project=Join-Path $BuildWorkspace 'test.uproject'
if (-not (Test-Path -LiteralPath $project)) {$project=Join-Path $BuildWorkspace 'ue5\WISEYE\test.uproject'}
$editor=Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
foreach ($file in @($project,$editor)) {if (-not (Test-Path -LiteralPath $file)) {throw "Missing dependency: $file"}}
$projectRoot=Split-Path -Parent $project
if (Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -like "*$project*" }) {
    throw 'Save and close this UE project before auditing or saving thermal labels.'
}
$rules=Join-Path $projectRoot 'Config\WISEYE\thermal_material_classes.json'
if (-not (Test-Path -LiteralPath $rules)) {Copy-Item -LiteralPath (Join-Path $sourceRoot 'ue5\WISEYE\Config\WISEYE\thermal_material_classes.json') -Destination $rules}
$work=Join-Path $projectRoot 'Saved\WISEYE\thermal_classes'
New-Item -ItemType Directory -Path $work -Force | Out-Null
$scripts=@()
if ($Apply) {
    $scripts+=Join-Path $sourceRoot 'ue5\scripts\configure_infrared_classified.py'
    $scripts+=Join-Path $sourceRoot 'ue5\scripts\configure_infrared_facade.py'
}
$scripts+=Join-Path $sourceRoot 'ue5\scripts\prepare_thermal_classes.py'
$paths=($scripts | ForEach-Object {ConvertTo-Json -InputObject ($_.Replace('\','/')) -Compress}) -join ','
$entry=Join-Path $work 'prepare.py'
$code=@"
from pathlib import Path
for filename in [$paths]:
    exec(compile(Path(filename).read_text(encoding='utf8'),filename,'exec'),{'__file__':filename,'__name__':'__main__'})
"@
[IO.File]::WriteAllText($entry,$code,[Text.UTF8Encoding]::new($false))
$previousApply=$env:WISEYE_THERMAL_TAG_APPLY
try {
    $env:WISEYE_THERMAL_TAG_APPLY=if ($Apply) {'1'} else {'0'}
    & $editor $project '-run=pythonscript' ("-script="+$entry) '-unattended' '-nop4' '-nosplash' '-NullRHI' ("-abslog="+(Join-Path $work 'prepare.log'))
    if ($LASTEXITCODE -ne 0) {throw 'Thermal preparation failed. Inspect Saved/WISEYE/thermal_classes/prepare.log.'}
} finally {$env:WISEYE_THERMAL_TAG_APPLY=$previousApply}
$reportName=if ($Apply) {'city.json'} else {'city_audit.json'}
Write-Host "Report: $(Join-Path $work $reportName)"
if ($Apply) {Write-Host 'Saved thermal labels and the classified material in the selected build project. Re-cook required for Shipping.'}
else {Write-Host 'Audit only. Use -Apply only on the intended WISEYE city copy to save thermal labels.'}

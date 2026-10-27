param([string]$EngineRoot = $env:UE_ROOT)
$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) { throw 'Save and close UE before importing drone models.' }
if (-not $EngineRoot) { $EngineRoot = (Get-Content (Join-Path $PSScriptRoot 'engine-root.local.txt') -Raw).Trim() }
$editor = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$project = Join-Path $repository 'ue5\WISEYE\test.uproject'
$script = Join-Path $repository 'ue5\scripts\import_drone_models.py'
& $editor $project "-ExecutePythonScript=$script" -EnablePlugins=PythonScriptPlugin,GeometryScripting -unattended -nop4 -nosplash
if ($LASTEXITCODE -ne 0) { throw "Drone model import failed ($LASTEXITCODE)." }

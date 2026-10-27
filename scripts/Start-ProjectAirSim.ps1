param(
    [ValidateSet('original','test_range','city')][string]$Scene = 'original',
    [int]$Loops = 0,
    [switch]$SkipBuild
)
$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$airSimRoot = Join-Path (Split-Path -Parent $repository) 'ProjectAirSim-Evaluation'
$python = Join-Path $airSimRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw "Project AirSim Python environment not found at $python. Run scripts\Setup-ProjectAirSim.ps1 first."
}
$sceneConfig = Get-Content -LiteralPath (Join-Path $repository "ue5\WISEYE\Config\WISEYE\Scenes\$Scene.json") -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $sceneConfig.prepared) { throw 'Scene assets are not ready. See docs/CITY_SAMPLE_SETUP.md for City Sample acquisition and integration.' }
$map = $sceneConfig.map
# A runner connected to a previous UE PIE session keeps port 50052 open but its
# Project AirSim objects are closed. Replace only that exact WISEYE runner.
$existingRunners = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like '*run_wiseye_flight.py*' }
foreach ($runner in $existingRunners) { Stop-Process -Id $runner.ProcessId -Force -ErrorAction SilentlyContinue }
& (Join-Path $PSScriptRoot 'Start-RTSP.ps1')
& (Join-Path $PSScriptRoot 'Start-WISEYE.ps1') -Map $map -SkipBuild:$SkipBuild -AutoPlay
if ($Loops -gt 0) { Write-Host 'UE is opening. Automatic flight regression will start after Play.' }
else { Write-Host 'UE is opening. Drone will stay ready; use the desktop Takeoff control to begin.' }
& $python (Join-Path $repository 'integrations\ProjectAirSim\run_wiseye_flight.py') --scene $Scene --loops $Loops
if ($LASTEXITCODE -ne 0) { throw "WISEYE Project AirSim runner failed ($LASTEXITCODE)." }

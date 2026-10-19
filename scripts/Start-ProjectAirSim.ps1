param(
    [ValidateSet('original','test_range')][string]$Scene = 'original',
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
$map = if ($Scene -eq 'test_range') { '/Game/WISEYE/Scenes/test_range/TestRange' } else { '/Game/WISEYE-test' }
# A runner connected to a previous UE PIE session keeps port 50052 open but its
# Project AirSim objects are closed. Replace only that exact WISEYE runner.
$existingRunners = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like '*run_wiseye_flight.py*' }
foreach ($runner in $existingRunners) { Stop-Process -Id $runner.ProcessId -Force -ErrorAction SilentlyContinue }
& (Join-Path $PSScriptRoot 'Start-RTSP.ps1')
& (Join-Path $PSScriptRoot 'Start-WISEYE.ps1') -Map $map -SkipBuild:$SkipBuild -AutoPlay
Write-Host 'UE is opening. Play mode and aerodynamic flight will start automatically.'
& $python (Join-Path $repository 'integrations\ProjectAirSim\run_wiseye_flight.py') --scene $Scene --loops $Loops
if ($LASTEXITCODE -ne 0) { throw "WISEYE Project AirSim runner failed ($LASTEXITCODE)." }
